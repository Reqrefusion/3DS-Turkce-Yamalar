#!/usr/bin/env sh
cd "$(dirname "$0")/.." || exit 1
python3 araclar/kirby_font_tr_patch.py patch-all varliklar/fontlar/ORIJINAL_CMP varliklar/fontlar/TR_PATCHED_CMP --used-chars-file araclar/used_chars_all_messages.txt --report raporlar/FONT_PATCH_RAPORU.csv --previews 06_FONT_ONIZLEMELERI
