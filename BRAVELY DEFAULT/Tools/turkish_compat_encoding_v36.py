#!/usr/bin/env python3
"""Bravely Default Turkish compatibility encoding (v3.6).
The game can replace U+0100+ Latin letters with ? in some runtime paths.
The patch stores six Turkish letters in unused Latin-1 slots and makes the CFNT
fonts draw the intended Turkish glyphs for those slots.
"""
ENCODE = {"Ğ":"Ð","ğ":"ð","İ":"Þ","ı":"þ","Ş":"Æ","ş":"æ"}
DECODE = {v:k for k,v in ENCODE.items()}
def encode_text(s): return "".join(ENCODE.get(c,c) for c in s)
def decode_text(s): return "".join(DECODE.get(c,c) for c in s)
if __name__ == "__main__":
 import sys
 print(encode_text(" ".join(sys.argv[1:])))
