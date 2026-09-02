#!/usr/bin/env python3
"""V16 private single-byte Turkish mapping. FNT remains original."""
MAP={'Ğ':0xD1,'İ':0xCD,'Ş':0xC8,'ğ':0xA7,'ı':0xA1,'ş':0xA2}
def encode(s):
    out=bytearray()
    for ch in s:
        if ch in MAP: out.append(MAP[ch])
        else: out.extend(ch.encode('cp1254'))
    return bytes(out)
