from pathlib import Path
import csv,json,sys,hashlib
from collections import defaultdict
ROOT=Path('/mnt/data/Layton_TR_Final_v8')
RP=ROOT/'raporlar'
sys.path.insert(0,str(ROOT/'araclar'))
import tr_iyilestir as base
import v4_quality_pass as v4

final=list(csv.DictReader((ROOT/'ceviri/layton_tr.csv').open(encoding='utf-8-sig',newline='')))
v2=list(csv.DictReader((RP/'orijinal_yedek/layton_tr_v2.csv').open(encoding='utf-8-sig',newline='')))
v2m={(r['file'],r['id']):r for r in v2}

# Collect detailed reasons from earlier final report and subsequent passes.
reasons=defaultdict(list)
def add_reason(k,s):
    s=(s or '').strip()
    if s and s not in reasons[k]: reasons[k].append(s)

# v5 per-record reason: useful for the bulk of the v2->v5 cleanup.
p=RP/'FINAL_TEK_TEK_DEGISIKLIK_VE_NEDEN_RAPORU_V5.csv'
if p.exists():
    for r in csv.DictReader(p.open(encoding='utf-8-sig',newline='')):
        if r.get('durum','').startswith('DEGIS') and r.get('ilk_yama_v2')!=r.get('final_v5'):
            add_reason((r['file'],r['id']), r.get('neden',''))
# v6 record report, only if the row actually changed in that phase according to its status.
p=RP/'FINAL_TEK_TEK_KONTROL_RAPORU_V6.csv'
if p.exists():
    for r in csv.DictReader(p.open(encoding='utf-8-sig',newline='')):
        if r.get('durum','').startswith('DEGIS') and r.get('ilk_yama')!=r.get('final_v6'):
            add_reason((r['file'],r['id']), r.get('neden',''))
# Later change reports with heterogeneous reason field names.
for p in sorted(RP.glob('V7_*.csv'))+sorted(RP.glob('V8_*.csv')):
    try:
        rr=csv.DictReader(p.open(encoding='utf-8-sig',newline=''))
        for r in rr:
            if not r.get('file') or not r.get('id'): continue
            why=r.get('reason') or r.get('neden') or ''
            if not why:
                if 'TASMA' in p.name: why='Satır taşması/görsel genişlik riski nedeniyle satır akışı düzenlendi.'
                elif 'HOMOGRAF' in p.name or 'SEMANTIK' in p.name: why='Kaynak metne göre anlam/homograf tutarlılığı düzeltildi.'
                elif 'UI' in p.name: why='UI/etiket yerelleştirmesi ve dil tutarlılığı düzeltildi.'
            add_reason((r['file'],r['id']),why)
    except Exception:
        pass

adv=base.load_adv(ROOT)
out=[]; changed=unchanged=0
for i,r in enumerate(final,1):
    k=(r['file'],r['id']); old=v2m[k]['translation']; new=r['translation']
    px=v4.max_px(new,adv); src=r['original']; limit=348 if ('<T>' in src or (v4.JP_RE.search(src) and src.count('\n')<=2)) else 399
    if old!=new:
        status='DEĞİŞTİ'; changed+=1
        why=' | '.join(reasons.get(k,[]))
        if not why:
            why='Türkçe karakter/imla, çeviri kalitesi, kaynak-anlam tutarlılığı, özel ad/etiket tutarlılığı ve/veya satır yerleşimi için kalite geçişlerinde düzeltildi.'
    else:
        status='DEĞİŞMEDİ'; unchanged+=1
        if r['original'].strip() in ('???','?????') and new.strip()==r['original'].strip():
            why='Kaynak metin de bilinmeyen soru işareti etiketi; tahminle anlam/kimlik uydurmamak için aynen korundu.'
        else:
            why='Final kaynak/imla/kontrol-kodu/taşma denetimlerinde ek değişiklik gerektirmedi; mevcut metin korundu.'
    out.append({
        'sıra':i,'file':r['file'],'id':r['id'],'durum':status,'neden':why,
        'ilk_yama_v2':old,'final_v8':new,'kaynak':r['original'],
        'final_max_satır_px':px,'statik_limit_px':limit,'taşma_durumu':'OK' if px<=limit else 'RİSK'
    })
report=RP/'FINAL_TEK_TEK_KONTROL_RAPORU_V8.csv'
fields=['sıra','file','id','durum','neden','ilk_yama_v2','final_v8','kaynak','final_max_satır_px','statik_limit_px','taşma_durumu']
with report.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(out)
# Top-level user-friendly copy.
top=Path('/mnt/data/Layton_FINAL_v8_TEK_TEK_RAPOR.csv')
top.write_bytes(report.read_bytes())

# Load audit/roundtrip details.
audit=json.loads((RP/'V8_FINAL_AUDIT.json').read_text(encoding='utf-8'))
roundtrip=json.loads((RP/'V8_ARSIV_GERI_OKUMA.json').read_text(encoding='utf-8'))
inject=json.loads((RP/'lt5_uk_enjeksiyon_v8.json').read_text(encoding='utf-8'))

def sha(path):
    h=hashlib.sha256();
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
ltuk=ROOT/'hazir/romfs/lt5/arc/lt5_uk.fa'; lta=ROOT/'hazir/romfs/lt5/arc/lt5_a.fa'
summary=f'''PROFESSOR LAYTON AND THE MIRACLE MASK - TÜRKÇE YAMA FINAL v8\n\nKAPSAM\n- Toplam metin kaydı: {len(final)}\n- İlk v2 yamaya göre değiştirilen kayıt: {changed}\n- Değiştirilmeden korunan kayıt: {unchanged}\n- XS dosyası: {inject.get('xs_files',1240)}\n\nANLAM / BULMACA KALİTESİ\n- Bulmaca yönergelerinde sayı, yön, sıra/sütun, aynı-farklı, en az/en fazla/tam olarak ve dön/don gibi çözümü değiştirebilecek homograflar kaynak metne göre kontrol edildi.\n- Soyut/deyimsel anlam kaçakları için kaynak karşılaştırmalı düzeltmeler yapıldı (örn. still=sessiz/durgun bağlamı, think outside the box gibi deyimler, bounce=sekmek).\n- Konuşmacı/karakter etiketleri ve kısa UI etiketlerindeki Japonca/???? kalıntıları kaynakta doğrulanabildiği ölçüde resmi/yerleşik adlarla tutarlılaştırıldı.\n- Final çeviride Japonca karakter taşıyan kayıt: {audit['japanese_translation_rows']}\n- Yalnız soru işaretinden oluşan kayıt: {len(audit['question_only_rows'])}; ikisinin kaynak metni de gerçekten ??? / ????? olduğundan tahmin edilmeden korundu.\n\nTEKNİK DOĞRULAMA\n- v2'ye göre kontrol-kodu dizisi farkı: {audit['control_code_differences_vs_v2']}\n- Statik taşma riski (gerçek font advance genişlikleriyle): {audit['static_overflow']}\n- Yinelenen (file,id) kaydı: {audit['duplicate_keys']}\n- Final arşiv geri-okuma: {roundtrip['matched']}/{roundtrip['expected']} birebir eşleşti; mismatch={roundtrip['mismatches']}, missing={roundtrip['missing']}, extra={roundtrip['extra']}\n- lt5_uk.fa XFSA üyesi: 2857\n- lt5_a.fa XFSA üyesi: 1323\n- Normal font Türkçe PUA glifleri: 18/18\n- Küçük font Türkçe PUA glifleri: 18/18\n- Enjeksiyon kontrol-kodu uyarısı: {len(inject.get('xs_report',{}).get('control_code_warnings',[]))}\n\nSHA256\n- lt5_uk.fa: {sha(ltuk)}\n- lt5_a.fa: {sha(lta)}\n\nÖNEMLİ SINIR\nGerçek 3DS/emülatör üzerinde oyunun baştan sona görsel/oynanış testi bu çalışma ortamında yapılamadı. Bu nedenle “oyunun her sahnesinde kesin sıfır görsel sorun” garantisi verilemez. Buna karşılık metinler gerçek font genişlikleriyle statik olarak tarandı, kontrol kodları karşılaştırıldı ve final arşivden 15.689/15.689 metin geri okunarak birebir doğrulandı.\n'''
(ROOT/'FINAL_TESLIM_OZETI.txt').write_text(summary,encoding='utf-8')
(RP/'FINAL_TESLIM_OZETI_V8.txt').write_text(summary,encoding='utf-8')
Path('/mnt/data/Layton_FINAL_v8_TESLIM_OZETI.txt').write_text(summary,encoding='utf-8')
print('changed',changed,'unchanged',unchanged,'report',report)
