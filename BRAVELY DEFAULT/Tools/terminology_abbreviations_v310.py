#!/usr/bin/env python3
"""Turkish terminology-derived abbreviations for Bravely Default TR v3.10.

Büyü Puanı -> BP
Cesaret Puanı -> CP
Meslek Puanı -> MP

The mapping is simultaneous: original game MP/BP/JP tokens are normalized to BP/CP/MP.
"""
import re
TOKEN_MAP={"MP":"BP","BP":"CP","JP":"MP"}
TOKEN_RE=re.compile(r"(?<![A-Za-z])(MP|BP|JP)(?![A-Za-z])")
def normalize(s):
    s=s.replace("İş Puanı","Meslek Puanı").replace("İş puanı","Meslek puanı").replace("iş puanı","meslek puanı")
    return TOKEN_RE.sub(lambda m:TOKEN_MAP[m.group(1)],s)
