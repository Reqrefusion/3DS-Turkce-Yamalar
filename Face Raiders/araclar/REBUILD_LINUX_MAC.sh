#!/usr/bin/env sh
set -eu
if [ "$#" -lt 1 ]; then
  echo "Kullanim: $0 /yol/faceraiders.zip"
  exit 1
fi
python3 araclar/build_working_universal.py "$1" ceviri/StgFace_all_languages_TR.csv BUILD_OUT
python3 araclar/verify_prebuilt.py ceviri/StgFace_all_languages_TR.csv BUILD_OUT
