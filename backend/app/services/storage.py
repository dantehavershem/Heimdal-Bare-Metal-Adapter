from pathlib import Path
import os
from app.core.config import STORAGE_ROOT


def safe_resolve(base: str, relative: str = '.') -> Path:
    boundary = STORAGE_ROOT.resolve(strict=True)
    root = Path(base).resolve(strict=True)
    if not root.is_relative_to(boundary):
        raise ValueError('Storage path must be within the configured storage root')
    if not root.is_dir():
        raise ValueError('Storage path must be a directory')
    if Path(relative).is_absolute():
        raise ValueError('Provide a relative media path')
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise ValueError('Path escapes the registered storage location')
    return target


def stat_path(path: Path) -> dict:
    st = os.statvfs(path)
    return {'exists': path.is_dir(), 'path': str(path),
            'free_bytes': st.f_bavail * st.f_frsize,
            'total_bytes': st.f_blocks * st.f_frsize}
