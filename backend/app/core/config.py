from __future__ import annotations
import os
from pathlib import Path

NAME = os.getenv("BAREMETAL_ADAPTER_NAME", "Bare-Metal Adapter")
DB_URL = os.getenv("BAREMETAL_ADAPTER_DB_URL", "sqlite:////scratch/baremetal.db")
STORAGE_ROOT = Path(os.getenv("BAREMETAL_ADAPTER_STORAGE_ROOT", "/storage"))
SCRATCH_ROOT = Path(os.getenv("BAREMETAL_ADAPTER_SCRATCH_ROOT", "/scratch"))
SCRATCH_LIMIT_GIB = int(os.getenv("BAREMETAL_ADAPTER_SCRATCH_LIMIT_GIB", "20"))
MIN_FREE_GIB = int(os.getenv("BAREMETAL_ADAPTER_MIN_FREE_GIB", "10"))
