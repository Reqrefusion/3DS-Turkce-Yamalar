#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
rm -rf BUILD_OUTPUT/FONT_TR_V12 BUILD_OUTPUT/FONT_TR_V12_ONIZLEME
python3 03_ARACLAR/kirby_font_tr_patch.py patch-all 04_ARA_DOSYALAR/FONT_ORIJINAL BUILD_OUTPUT/FONT_TR_V12 --used-chars-file 03_ARACLAR/used_chars_all_messages.txt --report BUILD_OUTPUT/FONT_TR_V12_RAPOR.csv --previews BUILD_OUTPUT/FONT_TR_V12_ONIZLEME
echo "v12 fontlari BUILD_OUTPUT/FONT_TR_V12 altinda olusturuldu."
