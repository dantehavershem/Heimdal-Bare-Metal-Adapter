from __future__ import annotations
import argparse, hashlib, json, time
from pathlib import Path
from sqlalchemy import select
from app.core.db import Base, engine, SessionLocal
from app.models.entities import Job, Media
from app.services.iso_inspector import inspect

Base.metadata.create_all(engine)

def log(job,msg):
    job.log_text=(job.log_text or "")+msg+"\n"; job.updated_at=__import__('datetime').datetime.utcnow()

def sha256(path:Path, job, db):
    h=hashlib.sha256(); total=path.stat().st_size; done=0
    with path.open('rb') as f:
        while True:
            b=f.read(8*1024*1024)
            if not b: break
            h.update(b); done+=len(b); job.progress=min(55,int(done/max(total,1)*55)); db.commit()
    return h.hexdigest()

def handle(db,job):
    p=json.loads(job.payload_json)
    if job.kind=="analyze-iso":
        path=Path(p['path']); job.status='running'; job.progress=1; log(job,f"Source: {path}"); db.commit()
        digest=sha256(path,job,db); log(job,f"SHA-256: {digest}")
        result=inspect(path); job.progress=85; db.commit(); log(job,f"Adapter: {result.get('recommended_adapter')}")
        m=Media(storage_id=p['storage_id'],relative_path=p['relative_path'],name=path.name,media_type='installer-iso',size_bytes=path.stat().st_size,sha256=digest,analysis_json=json.dumps(result))
        db.add(m); db.flush(); result['media_id']=m.id
        job.result_json=json.dumps(result); job.progress=100; job.status='complete'; log(job,"Analysis complete"); db.commit()
        return
    job.status='failed'; log(job,f"Unknown job type: {job.kind}"); db.commit()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--capability',default='core'); ap.parse_args()
    while True:
        with SessionLocal() as db:
            job=db.scalars(select(Job).where(Job.status=='queued').order_by(Job.id).limit(1)).first()
            if job:
                try: handle(db,job)
                except Exception as e:
                    job.status='failed'; log(job,f"ERROR: {type(e).__name__}: {e}"); db.commit()
            else: time.sleep(2)
if __name__=='__main__': main()
