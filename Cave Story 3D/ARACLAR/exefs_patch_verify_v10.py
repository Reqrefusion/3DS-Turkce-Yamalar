#!/usr/bin/env python3
from pathlib import Path
import hashlib
base=Path(__file__).resolve().parents[1]
p=base/'000400000004D200/exefs/code.bin'
print('code.bin',p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest())
print('code.ips',(base/'000400000004D200/code.ips').stat().st_size)
