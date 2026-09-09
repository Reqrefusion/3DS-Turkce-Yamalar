#!/usr/bin/env sh
set -eu
if [ "$#" -lt 1 ]; then
  echo "Kullanim: $0 /yol/faceraiders.zip"
  exit 1
fi
python3 02_TOOLS/build_working_universal.py "$1" 01_TRANSLATION/StgFace_all_languages_TR.csv BUILD_OUT
python3 02_TOOLS/verify_prebuilt.py 01_TRANSLATION/StgFace_all_languages_TR.csv BUILD_OUT
