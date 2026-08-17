#!/usr/bin/env python3
from pathlib import Path
import hashlib, sys
EXPECTED_SHA256 = "a6d5278c851b6a6695d28626ecb1b031cbaf59e7f92d0656ba0b5b509ecdfe3f"
OFFSET = 0x55BD78
OLD = bytes.fromhex("00 40 A0 E3")
NEW = bytes.fromhex("01 40 A0 E3")

def main():
    if len(sys.argv) != 2:
        print("Kullanım: python verify_v130_code_guard.py <decompressed_code.bin>")
        raise SystemExit(2)
    p=Path(sys.argv[1]); b=p.read_bytes()
    h=hashlib.sha256(b).hexdigest()
    print("SHA256:", h)
    if h != EXPECTED_SHA256:
        print("UYARI: Bu, analiz edilen v1.3.0 .code ile aynı değil.")
        raise SystemExit(1)
    print("Original instruction:", b[OFFSET:OFFSET+4].hex(' '))
    assert b[OFFSET:OFFSET+4] == OLD
    ips=b"PATCH"+OFFSET.to_bytes(3,"big")+(4).to_bytes(2,"big")+NEW+b"EOF"
    Path("code.ips").write_bytes(ips)
    print("code.ips üretildi.")
if __name__ == '__main__': main()
