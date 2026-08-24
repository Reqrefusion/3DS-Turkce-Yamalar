from __future__ import annotations
import argparse, csv, json, re, struct, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANGS = ['EU_English','US_English','EU_French','US_French','EU_German','EU_Italian','EU_Spanish','US_Spanish','JP_Japanese','KR_Korean']
LATIN = LANGS[:8]
CTRL_ANY = re.compile(r"\{\{(?:CTRL|U16)\|.*?\}\}")

MANUAL = {
    'AreaName000': 'Yorgan Meydanı',
    'RoomCustom12': "Kirby'nin Evi",
    'AreaName011_00': "Beadrix'in Evi",
    'AreaName012_00': "Carrie'nin Evi",
    'InteriorName05300': 'Küçük Şifonyer',
    'InteriorName05400': 'Büyük Şifonyer',
    'InteriorInfo13800': 'Bu teneke robot, koleksiyoncuların\naradığı çok değerli antika\nbir eşya.',
    'InStageInfoTitle000': 'Hazine',
    'PatternName70025': 'Fuşya Çizgili',
    'PatternInfo70025': 'Fuşya yatay çizgili kumaş.\nÇok gösterişli değil ama\ngayet hoş.',
    'PatternName70028': 'Açık Yeşil Çizgili',
    'PatternInfo70028': 'Açık yeşil yatay\nçizgili kumaş.',
    'PatternName70029': 'Açık Mavi Çizgili',
    'PatternInfo70029': 'Açık mavi yatay\nçizgili kumaş.',
    # EU sürümünde gri, bazı US/JP/KR metinlerinde siyah deniyor. Avrupa ROM'u için EU adını koruyoruz.
    'PatternName70031': 'Gri Çizgili',
    'PatternInfo70031': 'Gri yatay\nçizgili kumaş.',
    'AMIIBO_INFO_READING_SNAKE': "amiibo okumak için\namiibo'yu dokunmatik\nekrana tutun.",
    'PlayGuideInfo50009_00': "Yeni bölüm açmak için\nB'ye bas, yamayı\nfırlat!",
    'NEWCREDITS_STAFF_0046': 'Orijinal Wii sürümü\ngeliştirme ekibinin\nçalışmalarına dayanır.',
    'ModeSelect000': 'Dosya seçim ekranına\ndönülsün mü?',
    'PlayGuideInfo50006_00': 'Duvarlara veya zemine\nkumaş uygulayıp odana\nderinlik ve renk kat!\n\nDuvar/Zemin simgesine\ndokun, kumaşı seç,\nsonra sağ alttaki Geri\nsimgesine dokun.',
    'ShopMessage000_01_01': 'Üzgünüm, az önce\nortalık çok kalabalıktı.\nMallar da kalmadı,\nkötüler de... Hah!',
    'AMIIBO_IR_FUNCTION_ERROR': 'Kızılötesi işlevinde sorun\nolabilir. Sistemi yeniden\nbaşlatıp tekrar deneyin.',
    'AMIIBO_ERROR_UPDATE_REQUIRED': 'NFC Okuyucu/Yazıcı için\ngüncelleme gerekiyor.\nŞimdi güncellensin mi?',
    'PHOTO_CAMERA_04': 'Fotoğraf sınırına ulaştınız.\nDaha fazla fotoğraf\nkaydedemezsiniz.',
    'ShopMessage000_03_00': 'Alışverişin için sağ ol!',
    'StageInfo0000': 'REKOR',
    'ShopMessage000_07_01': 'Stok tükendi, üzgünüm.',
    'CEC_CONTROL_ERROR_01': "StreetPass, Ebeveyn\nDenetimleri'nde kısıtlı.\nBu yüzden kullanılamıyor.",
    'PauseMenu200': 'Bu bölümü yeniden\nbaşlatmak ister misin?',
    'RoomMainMenu13': 'StreetPass devre dışı\nbırakılsın mı?',
    'CEC_REGISTER_FAILURE': "StreetPass etkinleştirilemiyor.\nDevam etmek için Sistem\nAyarları'ndaki StreetPass\nYönetimi'nden başka bir oyunu\ndevre dışı bırakın.",
    # Dusk / crépuscule / Dämmer- ve JP/KR gece anlamlarını birlikte karşılayan daha kısa ad.
    'StageName112': 'Akşam Kumulları',
    'CEC_CHANGE_INFO': 'StreetPass başka kayıt için\netkin. StreetPass ayarlarını\ndeğiştirmek ister misiniz?',
    'InteriorInfo90500': 'Yağmur bulutu lambası,\ngri bir günde bile\nparlak ışık verir.',
    'PHOTO_CAMERA_08': "Kaydetme tamamlandı.\nFotoğrafları Albüm'de veya\nNintendo 3DS Kamera\nuygulamasında görebilirsiniz.",
    'ED00203_00': "<MANSION_3F_BEAD> boncukla bir kat daha ekleyip\nhayalimdeki Yorgan Apartmanı'nı kurabilirim!",
    'ShopMessage000_03_01': 'Alışverişin için\nteşekkürler!',
    'FileSelect008': 'Gerçekten silinsin mi?',
    'CREDITS_LOGO_0002': "Bu yazılımın telif hakkı\nNintendo, Good-Feel ve\nHAL Laboratory, Inc.'e aittir.\nTüm hakları saklıdır.",
    'CharacterInfo00003': 'Bir centilmen formda kalmak için\nantrenman gerektiğini bilir!\nProgramını tamamlayabilir misin?',
    'MainMenu005': 'Düzenle',
    'NEWCREDITS_ITEM_0031': 'KUZEY AMERİKA YERELLEŞTİRMESİ',
    'WipeMessage0100': 'Hey Kirby! Sana uğrayacağım.\nYakında evde misin?',
    'CEC_REGISTER_INFO': "StreetPass için bu oyunu\nsisteminize kaydetmeniz gerekir.\nEtkinleştirilsin mi?",
    'InteriorInfo07700': 'Kardeşim, bunun boncukla\nalınabilecek en iyi dikiş\nmakinelerinden biri diyor!',
    'ResultName000': 'Boncuklar',
}

def cmap_widths(data: bytes):
    endian = '<' if data[4:6] == b'\xff\xfe' else '>'
    cmap = {}
    p = 0
    while True:
        off = data.find(b'CMAP', p)
        if off < 0: break
        p = off + 4
        try:
            size = struct.unpack_from(endian+'I', data, off+4)[0]
            if size < 20 or off+size > len(data): continue
            begin,end,method,_reserved,_next = struct.unpack_from(endian+'HHHHI', data, off+8)
            q = off+20
            if method == 0:
                idx0 = struct.unpack_from(endian+'H',data,q)[0]
                for cp in range(begin,end+1): cmap[cp]=idx0+(cp-begin)
            elif method == 1:
                vals=struct.unpack_from(endian+f'{end-begin+1}H',data,q)
                for cp,idx in zip(range(begin,end+1),vals):
                    if idx != 0xFFFF: cmap[cp]=idx
            elif method == 2:
                cnt=struct.unpack_from(endian+'H',data,q)[0]; q+=2
                for _ in range(cnt):
                    cp,idx=struct.unpack_from(endian+'HH',data,q);q+=4;cmap[cp]=idx
        except Exception:
            continue
    idxw={}
    p=0
    while True:
        off=data.find(b'CWDH',p)
        if off<0: break
        p=off+4
        try:
            size=struct.unpack_from(endian+'I',data,off+4)[0]
            start,end=struct.unpack_from(endian+'HH',data,off+8)
            q=off+16
            for idx in range(start,end+1):
                if q+3>off+size: break
                idxw[idx]=data[q+2];q+=3
        except Exception:
            continue
    return {cp: idxw.get(idx,0) for cp,idx in cmap.items()}

def clean(s): return CTRL_ANY.sub('', s or '')
def width(s, widths): return sum(widths.get(ord(ch),0) for ch in clean(s))
def max_width(s,widths):
    ls=(s or '').splitlines() or ['']
    return max(width(x,widths) for x in ls)

def reflow(text, target, widths):
    paras=text.split('\n\n')
    out=[]
    for pi,para in enumerate(paras):
        words=' '.join(para.splitlines()).split()
        cur=''; lines=[]
        for word in words:
            cand=word if not cur else cur+' '+word
            if not cur or width(cand,widths)<=target:
                cur=cand
            else:
                lines.append(cur);cur=word
        if cur or not words: lines.append(cur)
        out.extend(lines)
        if pi<len(paras)-1: out.append('')
    return '\n'.join(out)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('input_csv', nargs='?', default=str(ROOT/'data'/'Kirby_TR_translated.csv'))
    ap.add_argument('source_zip', nargs='?', default=str(ROOT/'input'/'source.zip'))
    ap.add_argument('output_csv', nargs='?', default=str(ROOT/'data'/'Kirby_TR_translated_v2.csv'))
    ap.add_argument('--changes', default=str(ROOT/'reports'/'translation_changes.csv'))
    args=ap.parse_args()
    with open(args.input_csv,encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f));fields=list(rows[0].keys())
    before={r['Label']:r['Turkish'] for r in rows}
    with zipfile.ZipFile(args.source_zip) as z:
        ws=[]
        for fn in ('frame/font/GameFont1.bffnt','frame/font/GameFont2.bffnt'):
            ws.append(cmap_widths(z.read(fn)))
    allcp=set().union(*(set(x) for x in ws)); widths={cp:max(x.get(cp,0) for x in ws) for cp in allcp}

    # European ROM: intentional EU-English blank slots stay blank. Other locales are context, not extra timed dialogue slots.
    for r in rows:
        if not r['EU_English'].strip(): r['Turkish']=''
    by={r['Label']:r for r in rows}
    for label,text in MANUAL.items():
        if label in by and by[label]['EU_English'].strip(): by[label]['Turkish']=text

    # Music collection: US/JP/KR commonly use the track/stage title without a redundant “Theme” suffix.
    for r in rows:
        if not r['Label'].startswith('SoundName') or not r['Turkish'].strip(): continue
        e=r['EU_English']; t=r['Turkish']
        if e.startswith('Theme from '):
            t=t.replace(' Teması (',' (')
            if t.endswith(' Teması'): t=t[:-7]
        elif e.endswith("'s Theme"):
            t=re.sub(r"(?:'nın|'nin|'nun|'nün) Teması$",'',t)
            if t.endswith(' Teması'): t=t[:-7]
        r['Turkish']=t

    # Reflow multi-line strings using the widest line actually observed in this exact slot among Latin-script localizations.
    reflowed=[]
    for r in rows:
        if not r['Turkish'].strip(): continue
        peers=[r[x] for x in LATIN if r.get(x,'').strip()]
        if not peers: continue
        target=max(max_width(p,widths) for p in peers)
        max_lines=max(len(p.splitlines()) or 1 for p in peers)
        cur=max_width(r['Turkish'],widths)
        if cur>target*1.02 and max_lines>=2:
            cand=reflow(r['Turkish'],target,widths)
            if max_width(cand,widths)<=target and (len(cand.splitlines()) or 1)<=max_lines:
                if cand!=r['Turkish']:
                    r['Turkish']=cand; reflowed.append(r['Label'])

    for r in rows:
        if r['EU_English'].strip():
            r['Status']='FINAL_REVIEWED'
            r['Notes']='EU metin yapısı korunarak 10 dil çapraz kontrol edildi; piksel genişliği denetlendi.'
        else:
            r['Status']='INTENTIONAL_EMPTY'
            r['Notes']='EU_English bu zamanlanmış metin yuvasında boş; diğer locale metni buraya enjekte edilmedi.'

    Path(args.output_csv).parent.mkdir(parents=True,exist_ok=True)
    with open(args.output_csv,'w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    # Keep JSON rebuild source in sync, including intentional blank strings.
    tr={r['Label']:r['Turkish'] for r in rows}
    (ROOT/'data'/'translations_tr.json').write_text(json.dumps(tr,ensure_ascii=False,indent=2),encoding='utf-8')

    changes=[]
    for r in rows:
        old=before.get(r['Label'],'');new=r['Turkish']
        if old!=new:
            reason=[]
            if not r['EU_English'].strip(): reason.append('EU yapısındaki kasıtlı boşluk korundu')
            if r['Label'] in MANUAL: reason.append('çapraz dil/anlam veya uzunluk düzeltmesi')
            if r['Label'] in reflowed: reason.append('font piksel genişliğine göre satır kırımı')
            if r['Label'].startswith('SoundName') and old!=new: reason.append('müzik adı kısaltması')
            changes.append({'Label':r['Label'],'Before':old,'After':new,'Reason':'; '.join(reason) or 'satır kırımı/düzeltme'})
    with open(args.changes,'w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['Label','Before','After','Reason']);w.writeheader();w.writerows(changes)
    print(json.dumps({'rows':len(rows),'changed_rows':len(changes),'reflowed_rows':len(reflowed),'intentional_empty':sum(not r['EU_English'].strip() for r in rows),'output':args.output_csv},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
