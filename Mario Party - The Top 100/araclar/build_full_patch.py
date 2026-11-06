#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, shutil, subprocess, sys, zipfile, hashlib
from pathlib import Path

HERE=Path(__file__).resolve().parent

def sha256(p:Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(description='Mario Party: The Top 100 Türkçe tam LayeredFS paketi oluşturur.')
    ap.add_argument('rom_zip',type=Path)
    ap.add_argument('csv',type=Path)
    ap.add_argument('output_zip',type=Path)
    ap.add_argument('--work-dir',type=Path,default=None)
    a=ap.parse_args()
    work=a.work_dir or a.output_zip.with_suffix('')
    base=work.parent/(work.name+'_base')
    for p in (base,work):
        if p.exists(): shutil.rmtree(p)
    subprocess.run([sys.executable,str(HERE/'mp100_tool.py'),'build',str(a.rom_zip),str(a.csv),str(base),'--all-eu'],check=True)
    subprocess.run([sys.executable,str(HERE/'patch_ui_graphics.py'),str(a.rom_zip),str(base),str(work)],check=True)
    shutil.rmtree(base)
    # Bundle rebuild sources without requiring them on the SD card.
    src=work/'SOURCE'
    src.mkdir(exist_ok=True)
    for name in ('mp100_tool.py','patch_ui_graphics.py','bflim_codec.py','build_full_patch.py'):
        shutil.copy2(HERE/name,src/name)
    shutil.copy2(a.csv,src/'mp100_translation_complete.csv')
    # README belongs at root; luma/ is directly SD-copyable.
    readme=work/'README_TR.txt'
    readme.write_text(
'''Mario Party: The Top 100 - Türkçe Yama (Tam Paket)\n\n'
'Kurulum:\n'
'1) Bu ZIP dosyasını SD kartın köküne çıkarın.\n'
'2) Luma3DS yapılandırmasında Enable game patching açık olmalı.\n'
'3) Oyun Title ID: 00040000001C4D00\n\n'
'İçerik:\n'
'- 2254/2254 Türkçe metin.\n'
'- EU English/French/German/Spanish/Italian/Dutch dil yuvalarının tamamı Türkçe.\n'
'- Türkçe font glifleri: ğ Ğ ş Ş ı İ.\n'
'- Logo/marka grafikleri DEĞİŞTİRİLMEDİ.\n'
'- Logo dışı arayüz texture yazısı: START -> BAŞLA.\n'
'- A/B/X/Y, km/h, m, % gibi kontrol/birim sembolleri korunur.\n\n'
'Kaynak ve yeniden build araçları SOURCE klasöründedir.\n'
'Tam build: python build_full_patch.py <ROM.zip> mp100_translation_complete.csv cikti.zip\n'''.replace("'\n'",''),encoding='utf-8')
    report=json.loads((work/'build_report.json').read_text('utf-8'))
    report['package_kind']='full'
    report['branding_policy']='logos/brand artwork untouched'
    (work/'build_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    # Checksums for every payload/source file except the checksum list itself.
    sums=[]
    for p in sorted(work.rglob('*')):
        if p.is_file() and p.name!='SHA256SUMS.txt':
            sums.append(f'{sha256(p)}  {p.relative_to(work).as_posix()}')
    (work/'SHA256SUMS.txt').write_text('\n'.join(sums)+'\n',encoding='utf-8')
    a.output_zip.parent.mkdir(parents=True,exist_ok=True)
    if a.output_zip.exists(): a.output_zip.unlink()
    with zipfile.ZipFile(a.output_zip,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(work.rglob('*')):
            if p.is_file(): z.write(p,p.relative_to(work).as_posix())
    print(json.dumps({'output':str(a.output_zip),'sha256':sha256(a.output_zip),'files':sum(1 for p in work.rglob('*') if p.is_file())},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
