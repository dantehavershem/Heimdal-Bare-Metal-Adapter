from __future__ import annotations
import argparse
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from redis import Redis
from sqlalchemy import select, update
from app.core.config import REDIS_URL, JOB_LEASE_SECONDS
from app.core.db import SessionLocal
from app.core.schema import initialize_schema
from app.models.entities import Job, Media, StorageLocation
from app.services.iso_inspector import inspect
from app.services.storage import safe_resolve

logger = logging.getLogger(__name__)
redis = Redis.from_url(REDIS_URL, socket_connect_timeout=2, socket_timeout=2)


def heartbeat():
    try:
        redis.set('baremetal:worker:core:heartbeat', datetime.utcnow().isoformat(), ex=30)
    except Exception:
        logger.exception('Worker heartbeat unavailable')


def log(job, message):
    job.log_text = (job.log_text or '') + message + '\n'
    job.updated_at = datetime.utcnow()


def claim_job(db):
    # A crashed worker leaves a durable job; require deliberate resubmission.
    db.execute(update(Job).where(Job.status == 'running', Job.updated_at < datetime.utcnow()-timedelta(seconds=JOB_LEASE_SECONDS)).values(status='failed', log_text=Job.log_text+'Worker lease expired; resubmit the analysis.\n'))
    job = db.scalars(select(Job).where(Job.status == 'queued', Job.kind == 'analyze-iso').order_by(Job.id).with_for_update(skip_locked=True).limit(1)).first()
    if job:
        job.status = 'running'
        job.progress = 1
        log(job, 'Analysis claimed by worker')
    db.commit()
    return job.id if job else None


def checkpoint(db, job_id, progress):
    changed = db.execute(update(Job).where(Job.id == job_id, Job.status == 'running').values(progress=progress, updated_at=datetime.utcnow())).rowcount
    db.commit()
    if changed != 1:
        raise RuntimeError('Job is no longer owned by this worker')
    heartbeat()


def sha256(path: Path, job_id, db):
    digest = hashlib.sha256()
    total = path.stat().st_size
    done = 0
    previous = 0.0
    with path.open('rb') as source:
        while chunk := source.read(8*1024*1024):
            digest.update(chunk)
            done += len(chunk)
            now = time.monotonic()
            if now-previous >= 2:
                checkpoint(db, job_id, min(70, int(done/max(total, 1)*70)))
                previous = now
    return digest.hexdigest()


def process_job(job_id):
    with SessionLocal() as db:
        try:
            job = db.get(Job, job_id)
            payload = json.loads(job.payload_json)
            storage = db.get(StorageLocation, payload['storage_id'])
            if not storage or not storage.enabled:
                raise ValueError('Storage location is unavailable or disabled')
            path = safe_resolve(storage.path, payload['relative_path'])
            before = path.stat()
            log(job, f'Source: {path}')
            db.commit()
            digest = sha256(path, job_id, db)
            result = inspect(path)
            after = path.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ValueError('Source changed during analysis; retry when the file is stable')
            checkpoint(db, job_id, 85)
            job = db.scalars(select(Job).where(Job.id == job_id).with_for_update()).one()
            if job.status != 'running':
                raise RuntimeError('Job lease expired')
            media = db.scalars(select(Media).where(Media.storage_id == storage.id, Media.relative_path == payload['relative_path'])).first()
            if media is None:
                media = Media(storage_id=storage.id, relative_path=payload['relative_path'], name=path.name)
                db.add(media)
            media.media_type = 'installer-iso'
            media.size_bytes = after.st_size
            media.sha256 = digest
            media.analysis_json = json.dumps(result)
            db.flush()
            result['media_id'] = media.id
            job.result_json = json.dumps(result)
            job.progress = 100
            job.status = 'complete'
            log(job, f'SHA-256: {digest}')
            log(job, f"Candidate adapter: {result['recommended_adapter']}")
            log(job, 'Analysis complete; boot compatibility is not yet validated')
            db.commit()
        except Exception as error:
            db.rollback()
            job = db.get(Job, job_id)
            if job and job.status == 'running':
                job.status = 'failed'
                log(job, f'ERROR: {type(error).__name__}: {error}')
                db.commit()
            logger.exception('Analysis failed for job %s', job_id)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--capability', choices=['core'], default='core')
    parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    initialize_schema()
    while True:
        try:
            heartbeat()
            with SessionLocal() as db:
                job_id = claim_job(db)
            if job_id:
                process_job(job_id)
            else:
                time.sleep(2)
        except Exception:
            logger.exception('Worker iteration failed; retrying')
            time.sleep(2)

if __name__ == '__main__':
    main()
