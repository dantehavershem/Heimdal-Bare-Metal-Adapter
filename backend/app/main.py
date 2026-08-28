from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.db import Base, engine
from app.api.routes import router
from app.core.config import NAME

Base.metadata.create_all(engine)
app=FastAPI(title=NAME,version="0.1.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])
app.include_router(router)
