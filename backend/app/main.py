from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routes import router
from app.core.config import NAME, STORAGE_READ_ONLY
from fastapi.responses import JSONResponse
from app.core.schema import initialize_schema

@asynccontextmanager
async def lifespan(app):
    initialize_schema()
    yield

app = FastAPI(title=NAME, version='0.1.0', lifespan=lifespan)
app.include_router(router)

@app.middleware("http")
async def reject_read_only_upload(request, call_next):
    if STORAGE_READ_ONLY and request.method == 'POST' and request.url.path == '/api/v1/media/upload':
        return JSONResponse(status_code=403, content={'detail':'This media library is read-only; analyze an existing file instead'})
    return await call_next(request)
