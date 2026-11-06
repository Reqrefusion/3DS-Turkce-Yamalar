#!/usr/bin/env python3
from pathlib import Path
import argparse,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]; TITLE="000400000018A500"
def run(cmd): print("+"," ".join(map(str,cmd))); subprocess.run([str(x) for x in cmd],check=True)
def main():
 ap=argparse.ArgumentParser(description="Rhythm Heaven Megamix TR v22 — bağımsız LayeredFS build"); ap.add_argument("--out",type=Path,default=ROOT/"build_v22"); a=ap.parse_args(); out=a.out.resolve(); shutil.rmtree(out,ignore_errors=True)
 src=ROOT/TITLE; dst=out/TITLE; shutil.copytree(src,dst)
 run([sys.executable,ROOT/"araclar/rhm_tr_text_tool.py","build-message-folder","--source",src/"romfs/EUENmessage/pajama.zlib","--project",ROOT/"ceviri/proje/project/EUENmessage/pajama_sarc/arc","--out",dst/"romfs/EUENmessage/pajama.zlib"])
 run([sys.executable,ROOT/"araclar/validate_v22.py","--base",src,"--new",dst,"--project",ROOT/"ceviri/proje/project/EUENmessage/pajama_sarc/arc","--rhm-tool",ROOT/"araclar/rhm_tr_text_tool.py"])
 print("Hazır LayeredFS ağacı:",dst)
if __name__=="__main__": main()
