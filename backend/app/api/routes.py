from __future__ import annotations
import hashlib, json, os, shutil
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.config import NAME, STORAGE_ROOT, REDIS_URL, STORAGE_READ_ONLY
from redis import Redis
from app.services.storage import safe_resolve
from sqlalchemy.exc import IntegrityError
from app.models.entities import StorageLocation, Media, Job
from app.services.iso_inspector import inspect

router=APIRouter(prefix="/api/v1")

class StorageCreate(BaseModel):
    name:str; path:str; role:str="media"; kind:str="mounted"

class AnalyzeRequest(BaseModel):
    storage_id:int; relative_path:str

@router.get("/health")
def health(db:Session=Depends(get_db)):
    db.execute(text("SELECT 1"))
    cache = Redis.from_url(REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
    try:
        cache.ping()
        worker_online = bool(cache.exists('baremetal:worker:core:heartbeat'))
    finally:
        cache.close()
    return {"status":"ok" if worker_online else "degraded", "product":NAME,
            "database":"ok", "redis":"ok", "worker":"online" if worker_online else "unavailable",
            "storage_root":str(STORAGE_ROOT), "storage_read_only":STORAGE_READ_ONLY}


def resolve_storage(s, relative="."):
    if not s.enabled: raise HTTPException(409, "Storage location is disabled")
    try: return safe_resolve(s.path, relative)
    except ValueError as e: raise HTTPException(400, str(e))
    except OSError as e: raise HTTPException(409, "Storage location is not accessible") from e

@router.get("/capabilities")
def capabilities():
    return {"media":{"iso_analysis":True,"wrapper_build":"unavailable","image_conversion":"profile"},
            "bare_metal":{"capture":"scaffolded","deploy":"scaffolded","golden_images":"scaffolded"},
            "pxe":{"heimdal_adapter":"stage-1","standalone":"optional-profile"},
            "storage":{"external_first":True,"types":["mounted","smb","nfs","local","s3-planned"]}}

@router.get("/storage")
def storage_list(db:Session=Depends(get_db)):
    return [{"id":s.id,"name":s.name,"kind":s.kind,"path":s.path,"role":s.role,"enabled":s.enabled} for s in db.scalars(select(StorageLocation)).all()]

@router.post("/storage")
def storage_create(req:StorageCreate,db:Session=Depends(get_db)):
    p=Path(req.path)
    if not p.is_absolute(): raise HTTPException(400,"Storage path must be absolute inside appliance, e.g. /storage/iso")
    try:
        safe_resolve(req.path)
    except (ValueError, OSError) as e:
        raise HTTPException(400, str(e))
    s=StorageLocation(**req.model_dump()); db.add(s)
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A storage location with that name already exists")
    db.refresh(s)
    return {"id":s.id,"name":s.name,"path":s.path}


@router.get("/storage/{storage_id}/status")
def storage_status(storage_id:int,db:Session=Depends(get_db)):
    s=db.get(StorageLocation,storage_id)
    if not s: raise HTTPException(404,"Storage location not found")
    try: p=resolve_storage(s)
    except HTTPException: return {"id":s.id,"online":False,"path":s.path}
    usage=shutil.disk_usage(p)
    return {"id":s.id,"online":True,"path":s.path,"total_bytes":usage.total,"used_bytes":usage.used,"free_bytes":usage.free}

@router.post("/media/upload")
def media_upload(storage_id:int,relative_dir:str="",file:UploadFile=File(...),db:Session=Depends(get_db)):
    if STORAGE_READ_ONLY: raise HTTPException(403,"This media library is read-only; analyze an existing file instead")
    s=db.get(StorageLocation,storage_id)
    if not s: raise HTTPException(404,"Storage location not found")
    root=resolve_storage(s); target_dir=resolve_storage(s, relative_dir or ".")
    if root != target_dir and root not in target_dir.parents: raise HTTPException(400,"Path escape blocked")
    target_dir.mkdir(parents=True,exist_ok=True)
    safe_name=Path(file.filename or "upload.iso").name
    target=(target_dir/safe_name).resolve()
    if target.exists(): raise HTTPException(409,"A file with that name already exists")
    total=0
    with target.open("wb") as out:
        while True:
            chunk=file.file.read(8*1024*1024)
            if not chunk: break
            out.write(chunk); total+=len(chunk)
    rel=str(target.relative_to(root))
    return {"name":safe_name,"relative_path":rel,"size_bytes":total,"storage_id":s.id,"stored_at":str(target)}

@router.get("/media")
def media_list(db:Session=Depends(get_db)):
    return [{"id":m.id,"name":m.name,"media_type":m.media_type,"size_bytes":m.size_bytes,"sha256":m.sha256,"relative_path":m.relative_path,"storage_id":m.storage_id,"analysis":json.loads(m.analysis_json) if m.analysis_json else None} for m in db.scalars(select(Media).order_by(Media.created_at.desc())).all()]

@router.post("/media/analyze")
def analyze_media(req:AnalyzeRequest,db:Session=Depends(get_db)):
    s=db.get(StorageLocation,req.storage_id)
    if not s: raise HTTPException(404,"Storage location not found")
    root=resolve_storage(s); path=resolve_storage(s, req.relative_path)
    if root != path and root not in path.parents: raise HTTPException(400,"Path escape blocked")
    if not path.is_file(): raise HTTPException(404,"Media file not found")
    job=Job(kind="analyze-iso",payload_json=json.dumps({"storage_id":s.id,"path":str(path),"relative_path":str(path.relative_to(root))}))
    db.add(job); db.commit(); db.refresh(job)
    return {"job_id":job.id,"status":job.status}

@router.get("/jobs")
def jobs(db:Session=Depends(get_db)):
    return [{"id":j.id,"kind":j.kind,"status":j.status,"progress":j.progress,"log":j.log_text,"result":json.loads(j.result_json) if j.result_json else None} for j in db.scalars(select(Job).order_by(Job.id.desc()).limit(100)).all()]

@router.get("/jobs/{job_id}")
def job(job_id:int,db:Session=Depends(get_db)):
    j=db.get(Job,job_id)
    if not j: raise HTTPException(404,"Job not found")
    return {"id":j.id,"kind":j.kind,"status":j.status,"progress":j.progress,"log":j.log_text,"result":json.loads(j.result_json) if j.result_json else None}
