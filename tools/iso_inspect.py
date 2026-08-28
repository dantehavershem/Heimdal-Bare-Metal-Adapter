#!/usr/bin/env python3
from pathlib import Path
import argparse, json, sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.services.iso_inspector import inspect
p=argparse.ArgumentParser(description='Inspect a bootable ISO for Bare-Metal Adapter boot strategies'); p.add_argument('iso'); p.add_argument('--pretty',action='store_true'); a=p.parse_args(); print(json.dumps(inspect(Path(a.iso)),indent=2 if a.pretty else None,sort_keys=True))
