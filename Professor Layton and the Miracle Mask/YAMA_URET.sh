#!/usr/bin/env sh
set -eu
[ "$#" -eq 2 ] || { echo "Kullanim: $0 temiz_lt5_a.fa temiz_lt5_uk.fa" >&2; exit 2; }
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cp "$ROOT/hazir/romfs/lt5/arc/lt5_a.fa" "$(dirname "$1")/lt5_a_TR.fa"
python3 "$ROOT/araclar/layton_xfsa_text_tool.py" "$2" "$ROOT/ceviri/layton_tr.jsonl" "$(dirname "$2")/lt5_uk_TR.fa" --report "$(dirname "$2")/lt5_uk_TR_rapor.json"
