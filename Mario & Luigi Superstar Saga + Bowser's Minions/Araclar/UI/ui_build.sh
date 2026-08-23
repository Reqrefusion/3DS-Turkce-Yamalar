#!/usr/bin/env bash
set -e
BASE="$(cd "$(dirname "$0")" && pwd)"
if [ "$#" -lt 2 ]; then
  echo 'Kullanım: ./ui_build.sh "/kaynak/Obj/EU" "/cikti/Obj/EU"'
  exit 1
fi
python -c 'import numpy, PIL' >/dev/null 2>&1 || {
  echo 'Gerekli Python paketleri eksik. Bu klasörde: pip install -r requirements_ui.txt'
  exit 2
}
python "$BASE/mlss_ui_tool.py" "$1" "$BASE/ui_translations.csv" "$2" --preview "$2/_onizleme"
