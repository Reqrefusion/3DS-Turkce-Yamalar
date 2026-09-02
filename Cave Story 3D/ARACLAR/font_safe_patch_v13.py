#!/usr/bin/env python3
"""V13 font strategy documentation/reproducer.
Default V13 deliberately keeps font_batang.fnt byte-identical to the original game.
Only bitmap pixels in CP1254 slots D0/DD/DE/F0/FD/FE are replaced.
See RAPORLAR/FONT_RESET_QA_V13.txt.
"""
print("V13: FNT metrics/kerning are original; only six glyph bitmap slots are patched.")
