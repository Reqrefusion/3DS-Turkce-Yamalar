from __future__ import annotations
import csv, re, zipfile
from pathlib import Path
from .msbt import MsbtFile, control_tokens

LOCALES=['EU_English','US_English','EU_French','US_French','EU_German','EU_Italian','EU_Spanish','US_Spanish','JP_Japanese','KR_Korean']
TITLE_SMDH="Kirby'nin Ekstra Epik İpliği"
TITLE_CODE='Kirby Ekstra Epik İplik'
TEST_SAMPLE_TR='Türkçe yazı testi\nÇç Ğğ İı Öö Şş Üü\n123456789\nabcdefghijklmnoprstuvyz'
PH_RE=re.compile(r'<[^>\n]+>')

def _rows(csv_path, source_zip=None):
    with open(csv_path,encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    by={r.get('Label',''):r.get('Turkish','') for r in rows}
    # Canonical target is EU English structure: source text -> Turkish required, intentional source blank -> Turkish blank.
    bad=[]
    for r in rows:
        src=r.get('EU_English',''); tr=r.get('Turkish','')
        if bool(src.strip()) != bool(tr.strip()):
            bad.append(f"{r.get('Label','?')}: EU boş/dolu yapısı korunmamış")
        if src.strip() and sorted(control_tokens(src)) != sorted(control_tokens(tr)):
            bad.append(f"{r.get('Label','?')}: kontrol kodu uyuşmuyor")
        if src.strip() and sorted(PH_RE.findall(src)) != sorted(PH_RE.findall(tr)):
            bad.append(f"{r.get('Label','?')}: <X>/<Y> değişkenleri uyuşmuyor")
    if bad: raise ValueError('CSV doğrulaması başarısız:\n'+'\n'.join(bad[:40]))
    return rows,by

def patch_smdh(data: bytes) -> bytes:
    b=bytearray(data)
    if b[:4]!=b'SMDH': raise ValueError('icon.bin SMDH değil')
    def put(off,size,text):
        raw=text.encode('utf-16le')
        if len(raw)>size-2: raise ValueError('SMDH metni alana sığmıyor')
        b[off:off+size]=raw+b'\0'*(size-len(raw))
    for i in range(16):
        off=8+i*0x200
        put(off,0x80,TITLE_SMDH);put(off+0x80,0x100,TITLE_SMDH);put(off+0x180,0x80,'Nintendo')
    return bytes(b)

def patch_code_title(data: bytes) -> bytes:
    b=bytearray(data)
    old="Kirby's Extra Epic Yarn".encode('utf-16le')
    new=TITLE_CODE.encode('utf-16le')
    if len(new)>len(old): raise ValueError('Türkçe code.bin başlığı uzun')
    hits=[];p=0
    while True:
        p=b.find(old,p)
        if p<0:break
        hits.append(p);p+=1
    if len(hits)!=1: raise ValueError(f'code.bin oyun adı beklenen şekilde bulunamadı: {hits}')
    p=hits[0];b[p:p+len(old)]=new+b'\0'*(len(old)-len(new))
    return bytes(b)

def build_full_patched_zip(source_zip,csv_path,out_zip,banner_texture=None):
    rows,by=_rows(csv_path,source_zip)
    with zipfile.ZipFile(source_zip) as zin, zipfile.ZipFile(out_zip,'w',compression=zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            data=b'' if info.is_dir() else zin.read(info.filename)
            if info.filename=='exefs/icon.bin': data=patch_smdh(data)
            elif info.filename=='exefs/code.bin': data=patch_code_title(data)
            # banner.bin intentionally preserved byte-for-byte: stylized art is not replaced by an approximate recreation.
            elif re.fullmatch(r'message/[^/]+/fluff\.msbt',info.filename):
                m=MsbtFile.from_bytes(data);data=m.to_bytes([by[x] for x in m.labels])
            elif re.fullmatch(r'message/[^/]+/test_sample\.msbt',info.filename):
                m=MsbtFile.from_bytes(data);data=m.to_bytes([TEST_SAMPLE_TR for _ in m.labels])
            zout.writestr(info,data)
    return {'output':str(out_zip),'rows':len(rows),'locales':LOCALES,'banner':'preserved_original','icon':True,'code_title':True}

def build_layeredfs_all(source_zip,csv_path,out_dir,title_id='00040000001D1F00'):
    rows,by=_rows(csv_path,source_zip);root=Path(out_dir)/'luma'/'titles'/title_id/'romfs'/'message'
    with zipfile.ZipFile(source_zip) as z:
        for loc in LOCALES:
            d=root/loc;d.mkdir(parents=True,exist_ok=True)
            m=MsbtFile.from_bytes(z.read(f'message/{loc}/fluff.msbt'));(d/'fluff.msbt').write_bytes(m.to_bytes([by[x] for x in m.labels]))
            t=MsbtFile.from_bytes(z.read(f'message/{loc}/test_sample.msbt'));(d/'test_sample.msbt').write_bytes(t.to_bytes([TEST_SAMPLE_TR for _ in t.labels]))
            (d/'fluff.msbp').write_bytes(z.read(f'message/{loc}/fluff.msbp'))
    return {'path':str(root),'locales':LOCALES,'rows':len(rows),'note':'Tüm dil klasörleri aynı EU-yapılı Türkçe metni kullanır; banner tam olarak orijinal bırakılır.'}
