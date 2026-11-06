#!/usr/bin/env python3
from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'build'; OUT.mkdir(exist_ok=True)
target=OUT/'pajama.zlib'
subprocess.run([sys.executable,ROOT/'tools/rhm_tr_text_tool.py','build-message-folder',
 '--source',ROOT/'source/pajama_base.zlib',
 '--project',ROOT/'project/EUENmessage/pajama_sarc/arc',
 '--out',target],check=True)
print('Hazır mesaj arşivi:',target)
print('LayeredFS hedefi: 000400000018A500/romfs/EUENmessage/pajama.zlib')
