from pathlib import Path
import shutil, subprocess, sys, hashlib

ROOT=Path(__file__).resolve().parent.parent
TOOLS=ROOT/'03_ARACLAR'
CSV=ROOT/'02_CEVIRI'/'MSBT_CSV'
BASE=ROOT/'04_ARA_DOSYALAR'/'MSBT_SABLON'
READY=ROOT/'01_HAZIR_YAMA'/'ROMFS_ONLY'/'romfs'
BUILD=ROOT/'BUILD_OUTPUT'
TITLE='000400000010C000'

def run(*args):
    print('>', ' '.join(map(str,args)))
    subprocess.run([sys.executable, *map(str,args)], check=True)

def sha256(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def main():
    if BUILD.exists(): shutil.rmtree(BUILD)
    romfs=BUILD/'ROMFS_ONLY'/'romfs'
    (romfs/'msg').mkdir(parents=True,exist_ok=True)
    run(TOOLS/'kirby_msbt_tool.py','inject',BASE,CSV,romfs/'msg','--base','EU_English','--target','TR_Turkish','--out-lang','EU_English')
    shutil.copytree(READY/'font',romfs/'font')
    sd=BUILD/'SD_ROOT'/'luma'/'titles'/TITLE/'romfs'
    shutil.copytree(romfs,sd)
    # hashes
    files=sorted([p for p in BUILD.rglob('*') if p.is_file()])
    with (BUILD/'SHA256SUMS.txt').open('w',encoding='utf-8') as f:
        for p in files:
            f.write(f'{sha256(p)}  {p.relative_to(BUILD).as_posix()}\n')
    print('\nYama üretildi:')
    print('  ',romfs)
    print('  ',BUILD/'SD_ROOT')
    print('\nSon adım: 02_PAKETI_DOGRULA.bat çalıştırın.')

if __name__=='__main__': main()
