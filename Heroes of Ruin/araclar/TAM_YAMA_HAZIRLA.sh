#!/bin/sh
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
python3 "$SCRIPT_DIR/tam_yama_hazirla.py" "$1"
