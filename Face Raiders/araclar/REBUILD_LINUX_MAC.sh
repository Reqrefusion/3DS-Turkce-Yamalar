#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
if [ "$#" -lt 1 ]; then
  echo "Kullanim: $0 /yol/faceraiders.zip"
  exit 1
fi
python3 "$SCRIPT_DIR/build_working_universal.py" "$1" "$PROJECT_DIR/ceviri/StgFace_all_languages_TR.csv" "$PROJECT_DIR/BUILD_OUT"
python3 "$SCRIPT_DIR/verify_prebuilt.py" "$PROJECT_DIR/ceviri/StgFace_all_languages_TR.csv" "$PROJECT_DIR/BUILD_OUT"
