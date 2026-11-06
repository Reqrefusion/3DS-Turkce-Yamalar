#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
rm -rf calisma/uretim/FONT_TR_V12 calisma/uretim/FONT_TR_V12_ONIZLEME
python3 araclar/kirby_font_tr_patch.py patch-all kaynaklar/FONT_ORIJINAL calisma/uretim/FONT_TR_V12 --used-chars-file araclar/used_chars_all_messages.txt --report calisma/uretim/FONT_TR_V12_RAPOR.csv --previews calisma/uretim/FONT_TR_V12_ONIZLEME
echo "v12 fontlari calisma/uretim/FONT_TR_V12 altinda olusturuldu."
