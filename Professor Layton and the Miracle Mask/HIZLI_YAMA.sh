#!/usr/bin/env sh
set -eu
if [ "$#" -ne 1 ]; then
  echo "Kullanim: $0 /yol/lt5_uk.fa" >&2
  exit 2
fi
paket_dizini=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
kaynak=$1
taban=${kaynak%.*}
python3 "$paket_dizini/arac/layton5_tool.py" fa-replace \
  "$kaynak" \
  "$paket_dizini/hazir_xs" \
  "${taban}_tr.fa" \
  --report "${taban}_tr_raporu.json"
echo "Hazir: ${taban}_tr.fa"
