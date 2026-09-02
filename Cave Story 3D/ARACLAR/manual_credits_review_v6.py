#!/usr/bin/env python3
"""Cave Story 3D TR v6 - jenerik için manuel kalite geçişi.

credit.sjs içindeki [] yüklerini indeksle hedefler; 0xC2 yerleşim baytları ve
[] dışındaki ikili yapı aynen korunur. Altı credits_text*.txt varyantında ise
yalnız görünür metin parçalarına seçilmiş manuel düzeltmeler uygulanır.
"""
from pathlib import Path
import re, sys

ROOT = Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'000400000004D200/romfs/data'
BR = re.compile(br'\[([^\]]*)\]')
MARK = '§'

def dec(b:bytes)->str:
    return b.replace(b'\xC2',b'\x00').decode('cp1254').replace('\x00',MARK)
def enc(s:str)->bytes:
    return b'\xC2'.join(x.encode('cp1254') for x in s.split(MARK))

# Bracket payload indices were manually reviewed against the English ROMFS.
CREDIT_PATCH = {
    10: " Sue'nun kendine",
    11: f'{MARK}  dede bildiği kişi',
    34: ' Rengârenk',
    78: f'{MARK}  lanetlenen',
    134: ' Tam bir böcek: Böcek',
    135: ' Büyük uçucu: Basu',
    177: ' Kudurmuş Mimiga;',
    180: " Misery'nin Balrog'u",
    181: ' dönüştürdüğü hâl',
    184: ' makine canavar',
    204: ' Kırmızı kristalle',
    205: ' kuduran',
}

TEXT_REPL = {
    "Sue'nun dede": "Sue'nun kendine",
    'yerine koyduğu kişi': 'dede bildiği kişi',
    'Renkli': 'Rengârenk',
    'Örnek böcek: Böcek': 'Tam bir böcek: Böcek',
    'Büyük uçan: Basu': 'Büyük uçucu: Basu',
    'Kuduz Mimiga;': 'Kudurmuş Mimiga;',
    'makine-canavar': 'makine canavar',
    'Kırmızı kristalin': 'Kırmızı kristalle',
    'çılgın gücü': 'kuduran',
    'YÖNETİCİ YAPIMCI': 'YÜRÜTÜCÜ YAPIMCI',
    'ÇEVRE TASARIMCILARI': 'ÇEVRE SANATÇILARI',
    'NESNE TASARIMCILARI': 'OBJE SANATÇILARI',
}

def patch_credit():
    p=ROOT/'credit.sjs'; raw=p.read_bytes(); matches=list(BR.finditer(raw))
    out=bytearray(); pos=0; changed=0
    for i,m in enumerate(matches):
        out += raw[pos:m.start(1)]
        old=dec(m.group(1)); new=CREDIT_PATCH.get(i,old)
        if new!=old: changed+=1
        out += enc(new); pos=m.end(1)
    out += raw[pos:]
    out=bytes(out)
    # Structural invariants.
    assert BR.sub(b'[]',raw)==BR.sub(b'[]',out)
    assert raw.count(b'\xC2')==out.count(b'\xC2')==32
    p.write_bytes(out)
    return changed

def patch_text_file(p:Path):
    s=p.read_bytes().decode('cp1254','surrogateescape'); changed=0
    for a,b in TEXT_REPL.items():
        n=s.count(a)
        if n: s=s.replace(a,b); changed+=n
    p.write_bytes(s.encode('cp1254','surrogateescape'))
    return changed

def main():
    n=patch_credit(); print('credit.sjs manuel payload:',n)
    total=0
    files=sorted(ROOT.glob('credits_text*.txt'))
    for p in files:
        k=patch_text_file(p); total+=k; print(p.name,k)
    print('credits_text toplam manuel düzeltme:',total,'dosya:',len(files))
if __name__=='__main__': main()
