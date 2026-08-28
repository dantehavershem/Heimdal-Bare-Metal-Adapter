from __future__ import annotations
from pathlib import Path
import os
from app.core.config import STORAGE_ROOT

def safe_resolve(base: str, relative: str = ".") -> Path:
    root = (STORAGE_ROOT / base).resolve()
    target = (root / relative).resolve()
    if root != target and root not in target.parents:
        raise ValueError("Path escapes configured storage root")
    return target

def stat_path(path: Path) -> dict:
    st=os.statvfs(path)
    return {
        "exists": path.exists(),
        "path": str(path),
        "free_bytes": st.f_bavail*st.f_frsize,
        "total_bytes": st.f_blocks*st.f_frsize,
    }
