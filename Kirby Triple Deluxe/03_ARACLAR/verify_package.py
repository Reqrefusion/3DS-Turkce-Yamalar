from pathlib import Path
import csv, importlib.util, sys, hashlib, re

ROOT=Path(__file__).resolve().parent.parent
TOOLS=ROOT/'03_ARACLAR'
CSV_DIR=ROOT/'02_CEVIRI'/'MSBT_CSV'
READY=ROOT/'01_HAZIR_YAMA'/'ROMFS_ONLY'/'romfs'
TR='ÇĞİÖŞÜçğıöşü'

# load local modules
spec=importlib.util.spec_from_file_location('msbtmod',TOOLS/'kirby_msbt_tool.py'); msbtmod=importlib.util.module_from_spec(spec); sys.modules['msbtmod']=msbtmod; spec.loader.exec_module(msbtmod)
spec2=importlib.util.spec_from_file_location('fontmod',TOOLS/'kirby_font_tr_patch.py'); fontmod=importlib.util.module_from_spec(spec2); sys.modules['fontmod']=fontmod; spec2.loader.exec_module(fontmod)

font_expected=[
'ALL/CommonStd.bcfnt.cmp','ALL/CommonStd_OL.bcfnt.cmp','ALL/UIBossMessage_OL.bcfnt.cmp','ALL/UIHeadline_OL.bcfnt.cmp','ALL/UIPauseHeadline_OL.bcfnt.cmp','ALL/UIStaffCredit_OL.bcfnt.cmp','ALL/UIStdL.bcfnt.cmp','ALL/UIStdL_OL.bcfnt.cmp','ALL/UIStickFixed_OL.bcfnt.cmp','EU/UIStdBold_OL.bcfnt.cmp']

def malformed_tokens(s):
    out=[]
    for m in re.finditer(r'⟦MSBT:([0-9A-Fa-f]+)⟧',s):
        try:b=bytes.fromhex(m.group(1))
        except: out.append('hex'); continue
        if len(b)>=8 and b[:2] in (b'\x0e\x00',b'\x00\x0e'):
            endian='little' if b[:2]==b'\x0e\x00' else 'big'
            declared=int.from_bytes(b[6:8],endian); actual=len(b)-8
            if declared!=actual: out.append(f'{declared}!={actual}')
    return out

def main():
    problems=[]; total=0
    csvs=sorted(CSV_DIR.glob('*.csv'))
    msbts=sorted((READY/'msg'/'EU_English').glob('*.msbt'))
    if len(csvs)!=23: problems.append(f'CSV sayısı 23 değil: {len(csvs)}')
    if len(msbts)!=23: problems.append(f'MSBT sayısı 23 değil: {len(msbts)}')
    for cp in csvs:
        mp=READY/'msg'/'EU_English'/(cp.stem+'.msbt')
        if not mp.exists(): problems.append(f'MSBT yok: {cp.stem}.msbt'); continue
        m=msbtmod.MSBT.from_file(mp)
        by_label={m.primary_label(i):m.texts[i] for i in range(len(m.texts))}
        with cp.open('r',encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
        total+=len(rows)
        if len(rows)!=len(m.texts): problems.append(f'{cp.name}: satır {len(rows)} != MSBT {len(m.texts)}')
        for n,r in enumerate(rows,2):
            lab=r.get('label',''); tr=r.get('TR_Turkish','')
            if by_label.get(lab)!=tr: problems.append(f'{cp.name}:{n} CSV/MSBT farkı: {lab}')
            bad=malformed_tokens(tr)
            if bad: problems.append(f'{cp.name}:{n} bozuk MSBT token: {lab} {bad}')
    for rel in font_expected:
        p=READY/'font'/rel
        if not p.exists(): problems.append(f'Font yok: {rel}'); continue
        try: f=fontmod.BCFNT(p.read_bytes())
        except Exception as e: problems.append(f'Font açılamadı {rel}: {e}'); continue
        miss=''.join(ch for ch in TR if ch not in f.mapping)
        if miss: problems.append(f'Font Türkçe eksik {rel}: {miss}')
        runtime_miss=''.join(ch for ch in TR if f.runtime_lookup(ch) is None)
        if runtime_miss: problems.append(f'Font runtime CMAP Türkçe eksik {rel}: {runtime_miss}')
        # v12 dotless-i QA. Generated U+0131 keeps the authored top/bottom
        # caps of capital I and shortens only the straight middle stem. The
        # first visible lowercase outline row is the target top; unlike v11,
        # faint top shadow/antialias is intentionally preserved.
        if all(ch in f.mapping for ch in 'Iiı'):
            xh=fontmod.xheight_top(f, threshold=0)
            ib=fontmod.bbox(f.get_cell('i'), threshold=0); db=fontmod.bbox(f.get_cell('ı'), threshold=0)
            Icell=f.get_cell('I'); Ibb=fontmod.bbox(Icell, threshold=0)
            if f.get_cell('i') == f.get_cell('ı'):
                problems.append(f'Font ı hâlâ i ile aynı: {rel}')
            if xh is None or db is None or db[1] != xh:
                problems.append(f'Font ı görünür x-height hatası {rel}: xheight={xh}, bbox={db}')
            native_pairs=all(f.mapping[b] == f.mapping[a] + 1 for a,b in [('Ğ','ğ'),('İ','ı'),('Ş','ş')])
            if not native_pairs:
                expected=fontmod.make_dotless_i(f)
                actual=f.get_cell('ı')
                exp_alpha=[[px[1] for px in row] for row in expected]
                act_alpha=[[px[1] for px in row] for row in actual]
                if exp_alpha != act_alpha:
                    problems.append(f'Font ı büyük I orta-kesim v12 geometrisiyle eşleşmiyor: {rel}')
                if Ibb and db:
                    if actual[db[1]:db[1]+2] != Icell[Ibb[1]:Ibb[1]+2]:
                        problems.append(f'Font ı üst cap/gölgesi korunmamış: {rel}')
                    if actual[db[3]-2:db[3]] != Icell[Ibb[3]-2:Ibb[3]]:
                        problems.append(f'Font ı alt cap/gölgesi korunmamış: {rel}')
            if ib and db and db[1] <= ib[1]:
                problems.append(f'Font ı üst sınırı i noktasından ayrışmıyor {rel}: i_top={ib[1]}, ı_top={db[1]}')
    print(f'CSV: {len(csvs)} | MSBT: {len(msbts)} | metin: {total} | Türkçe denetlenen font: {len(font_expected)}')
    if problems:
        print(f'HATA/UYARI: {len(problems)}')
        for x in problems[:200]: print('-',x)
        return 1
    print('SONUÇ: TAMAM — CSV/MSBT birebir, bozuk kontrol tokenı yok; Türkçe glifler parser/runtime CMAP ile erişilebilir ve noktasız ı büyük-I orta-kesim/x-height geometrisi ve cap gölgeleri doğrulandı.')
    return 0
if __name__=='__main__': raise SystemExit(main())
