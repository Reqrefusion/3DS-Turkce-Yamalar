#!/usr/bin/env python3
from __future__ import annotations
import csv, re, sys, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from msbt_toolkit import control_signature

# Manually curated after comparing EN/FR/DE/IT/ES/JP/ZH rows.
OVERRIDES = {
('episode1.csv',872): "Olayın gerçekleştiği yeri—yani tam burayı—\ninceleyip geride kalan izleri ara.",
('episode4.csv',228): "Aslında her şeyi kayda geçirdikten hemen sonra\nofiste bir şey unuttuğumu fark edip\ngeri dönmem gerekti.",
('episode4.csv',230): "Evet, ama sadece birkaç dakikalığına.\nDöndüğümde Louise'in her zamanki kokusu\nyok olmuştu. Tuhaf geldi.",
('episode4.csv',303): "*güler* Hassas bir burnun her zaman\nişe yaramadığı da oluyormuş! Görüşürüz, hapşırıkçı!",
('episode4.csv',310): "Ne, hâlâ kızgın mısın? Dostum,\nşakadan hiç anlamıyorsun, değil mi?",
('episode4.csv',421): "Şimdi Timburrlardan beni belli bir yere\ngötürmelerini isteyeceğim. Belki bu sayede\nWaals'ın masumiyetini kesin olarak kanıtlayabilirim.",
('episode4.csv',666): "Bu tavırlar da ne?! Biraz gevşe!\n*dil çıkarır*",
('episode4.csv',908): "Aynen, ben de şaşırdım.",
('episode4.csv',930): "Aslında Milo'nun arkadaşlarından biri,\nCrawdaunt'u buraya getirmekle suçlanıyor.",
('episode4.csv',1078): "*güler* Haklısın—bunu yapabilirdim.\nAma Timburrları ta göle kadar götürecek\nzamanı nereden bulacaktım?",
('episode4.csv',1148): "Demek Waals gerçekten masummuş.\nAma yine de...",
('episode4.csv',1245): "Şöyle yazıyor,\n— Göle ulaşmak istersen\n- {{CTRL:0000:0003:FF4B4BFF}}ay ışığını takip et{{CTRL:0000:0003:FDFDFDFF}}\n- Ve üç sınavla yüzleş",
('episode4.csv',1549): "*homurdanır* Benim bacaklarım seninkinden daha kısa,{{CTRL:0001:0006:}}\nbiliyorsun!",
('episode4.csv',1571): "Demek PCL'deki olayla Harry'nin kazası\ngerçekten bağlantılıymış.",
('episode4.csv',1765): "*iç çeker* Umarım bu da ona yeni\n‘dâhiyane’ teoriler döktürmez...",
('episode5.csv',600): "Aynen... Hımm...\nAa, buldum! Ya duvar resmi?\nOnarırsak Smeargle'ın biraz keyfi yerine gelir belki.",
('episode6.csv',1213): "O imza seninkinden esinlenilmiş, değil mi?",
('episode6.csv',1218): "*hıçkırır*",
('episode6.csv',1224): "*hıçkırır*",
('episode6.csv',1357): "Aynen. Bu kadar uzun sürmesine\nne sebep oluyor acaba?",
('episode6.csv',1482): "*güler* Çekimlere başlamak için çok\nheyecanlısın, değil mi? Ben de sabırsızlanıyorum.",
('episode7.csv',77): "Aynen...\nMewtwo, ha...\nO ismi her duyduğumda nedense\niçime bir huzursuzluk çöküyor.",
('episode7.csv',350): "Aynen.",
('episode7.csv',732): "Aynen öyle. Şu an her yeri sıkı gözetliyorlar.\nAma şöyle düşün...\nGeçmek için fabrika müdürüyle\niki güvenliği atlatmamız yeter.",
('episode7.csv',880): "*iç çeker* Aynen öyle!\n*homurdanır* Seni uyandırdığım için üzgünüm. Ama sanırım\nbir şeyi unutuyorum—verdiğim bir sözü.",
('episode8.csv',661): "*kıkırdar* Sana güvenebileceğimizi biliyordum, Tim.\nHadi, bunun arkasında kimin olduğunu anlat.",
('episode8.csv',692): "Öf... *ürperir* Ee... Ne yapmamı bekliyordun ki?!\nYeni menü fikirlerim tükendi.\nMüşterilerimi şaşırtmam gerek!\nİnsanın üzerinde büyük baskı oluyor!",
('episode8.csv',718): "Evet, bu kez bizi fena avladı.\nBu vakayı çözmeden Keith'in\nyakınına bile yaklaşamayacağız.",
('episode8.csv',762): "*homurdanır* Hadi bakalım! *homurdanır*",
('episode9.csv',101): "Pikachu! *homurdanır*\nOlamaz! Pikachu, iyi misin?!",
('episode9.csv',103): "*iç çeker* Çok şükür. Kendine geldi.",
('episode9.csv',187): "Tamam, hadi R'yi bulalım!\nŞüpheli bir şey görürsen {{CTRL:0000:0003:FF4B4BFF}}bana seslen{{CTRL:0000:0003:FDFDFDFF}}.\nDikkatimi nasıl çekeceğini biliyorsun, değil mi?\n{{CTRL:0000:0003:FF4B4BFF}}Sinyalimi fark ettiğinde yaptığınla aynı{{CTRL:0000:0003:FDFDFDFF}}.",
('episode9.csv',274): "*şaşkınlıkla nefes alır*\nPikachu!\nNe oldu?!",
('episode9.csv',379): "Pekâlâ Tim, ben müsaadenle gideyim. Sen de\ndikkatli ol, tamam mı?\nSonuçta Pikachu'n hamle kullanamıyor.\nİşler tehlikeli bir hâl alırsa hemen kaç.",
('stream.csv',135): "Gündüz geçidi şimdi başlıyor.\nHerkes parkın sevilen Pokémonlarını\ngeçitte görmek için heyecanlı!\nEn önde de Charizard'dan iyisi düşünülemez!\nBu yılki geçidin temasıysa\n‘rüyalar’! *şaşkınlıkla nefes alır*",
('stream.csv',172): "*inler* Ah evet. Demek bu hiç de rüya{{CTRL:0001:0006:}}\ndeğilmiş...",
}


# Additional multilingual disambiguations / idiom repairs.
OVERRIDES.update({
('episode4.csv',378): "Üzerinde iki pul bulunan anıt\nikisinin arasında olabilir!",
('episode4.csv',2101): "Üzerinde iki pul bulunan anıt\nikisinin arasında bir yerde olabilir!",
('episode7.csv',691): "Nefis mi kokuyor?\nNe güzel, senin adına sevindim.",
('episode4.csv',1749): "Evet, çok şükür! Hepsi Waals'ın\nbenim için yaptığı bu İksir sayesinde.",
('episode8.csv',532): "Yine başladın...\nYoksa bütün bunları sadece açık artırmaya\nkatılmak istediğin için mi söylüyorsun?",
('episode6.csv',1056): "Öyle mi?! Biliyordum!\n*güler* Al, sana bir imza vereyim!",
('episode3.csv',2032): "Soğuk ve mesafeli, ha? Tahmin etmiştim.\n(Peki sana karşı nasıl davranıyor?)",
('mpika.csv',163): "Dur bakayım... Ah!\nVay!\nBu... bu fena acı!",
('mpika.csv',164): "Dur bakayım... Ah!\nOf... çok ekşi!",
('episode4.csv',2261): "Şimdi geriye dönüp düşününce, Bay Waals hakkındaki kötü\nsöylentileri ilk çıkaran kişi kesin Louise'ti.\nOndan özür dilemem gerek.",
('episode3.csv',1546): "Ha? Tim'in de çok iyi biri olduğunu mu söylüyorsun?\nSen söyleyince fark ettim; galiba haklısın.",
('episode3.csv',1213): "Bu şişenin konuyla ilgisi yok.",
})

# Safe lexical/orthographic cleanup.
TYPO_REPL = [
    ('Söyle ki', 'Şöyle ki'), ('söyle ki', 'şöyle ki'),
    ('söyle düşün', 'şöyle düşün'), ('Söyle düşün', 'Şöyle düşün'),
    ('şeninkinden', 'seninkinden'), ('Şeninkinden', 'Seninkinden'),
    ('hapsirik', 'hapşırık'), ('Hapsirik', 'Hapşırık'),
    ('hiç bir', 'hiçbir'), ('yani sıra', 'yanı sıra'),
]

# Stage directions that were translated as awkward nouns / sound effects.
STAGE_RULES = [
    (r'\*groan\*|\*moan\*', [('*inleme*','*inler*'),('*inleme','*inler'),('*inler*','*inler*')]),
    (r'\*sigh\*', [('*iç çekiş*','*iç çeker*')]),
    (r'\*laugh\*', [('*gülüş*','*güler*'),('*kahkaha*','*güler*')]),
    (r'\*grunt', [('*homurtu*','*homurdanır*'),('*homurdanma*','*homurdanır*'),('*homur homur*','*homurdanır*')]),
    (r'\*struggle\*', [('*zorlanma*','*çırpınır*'),('*boğuşma*','*çırpınır*'),('*debelenme*','*çırpınır*')]),
    (r'\*shudder\*', [('*titreme*','*ürperir*')]),
    (r'\*shiver\*', [('*titreme*','*titrer*')]),
    (r'\*sob', [('*hiçk hiçk*','*hıçkırır*')]),
    (r'\*hum hum hum\*', [('*him him him*','*mırıldanır*')]),
    (r'\*raspberry\*', [('*dil çıkarma*','*dil çıkarır*')]),
    (r'\*pant', [('*puf puf puf*','*nefes nefese*'),('*puf puf*','*nefes nefese*'),('*puf*','*nefes nefese*'),('*soluma*','*nefes nefese*')]),
    (r'\*huff', [('*puf puf puf*','*soluk soluğa*'),('*puf puf*','*soluk soluğa*'),('*puf*','*soluk soluğa*')]),
    (r'\*gasp', [('*hik*','*şaşkınlıkla nefes alır*'),('*şaşkın nefes*','*şaşkınlıkla nefes alır*')]),
    (r'\*sneeze\*', [('*hapşırık*','*hapşırır*'),('*hapşu*','*hapşırır*')]),
    (r'\*growl\*', [('*hırlama*','*hırlar*')]),
    (r'\*cheer cheer\*', [('*alkış alkış*','*tezahürat*')]),
    (r'\*scream scream\*', [('*çığlık çığlığa*','*çığlıklar*')]),
    (r'\*sinister laugh\*', [('*sinsi kahkaha*','*sinsice güler*'),('*kötücül kahkaha*','*sinsice güler*')]),
    (r'\*nervous giggle\*', [('*gergin gülüş*','*gergin bir kahkaha atar*')]),
]

# Detective terminology: only applied if source confirms the sense.
CASE_FORMS = [
('Davayla','Vakayla'),('davayla','vakayla'),('Davaya','Vakaya'),('davaya','vakaya'),
('Davayı','Vakayı'),('davayı','vakayı'),('Davadan','Vakadan'),('davadan','vakadan'),
('Davanın','Vakanın'),('davanın','vakanın'),('Davada','Vakada'),('davada','vakada'),
('Davası','Vakası'),('davası','vakası'),('Davasını','Vakasını'),('davasını','vakasını'),
('Davasından','Vakasından'),('davasından','vakasından'),('Davasıyla','Vakasıyla'),('davasıyla','vakasıyla'),
('Dava belgeleri','Vaka belgeleri'),('dava belgeleri','vaka belgeleri'),
('Dava evrakları','Vaka evrakları'),('dava evrakları','vaka evrakları'),
('Dava','Vaka'),('dava','vaka')]
TESTIMONY_FORMS = [
('Tanıklıklarla','İfadelerle'),('tanıklıklarla','ifadelerle'),('Tanıklıkları','İfadeleri'),('tanıklıkları','ifadeleri'),
('Tanıklıklar','İfadeler'),('tanıklıklar','ifadeler'),('Tanıklığı','İfadeyi'),('tanıklığı','ifadeyi'),
('Tanıklık','İfade'),('tanıklık','ifade')]

# Exact corrections of common idiom mistranslations.
IDIOM_OVERRIDES = {
('episode4.csv',1148): OVERRIDES[('episode4.csv',1148)],
('episode4.csv',421): OVERRIDES[('episode4.csv',421)],
('episode7.csv',77): OVERRIDES[('episode7.csv',77)],
('episode7.csv',350): OVERRIDES[('episode7.csv',350)],
('episode6.csv',1357): OVERRIDES[('episode6.csv',1357)],
('episode5.csv',600): OVERRIDES[('episode5.csv',600)],
}

def polish(file_name:str, idx:int, en:str, tr:str):
    out=tr; notes=[]
    for a,b in TYPO_REPL:
        if a in out:
            out=out.replace(a,b); notes.append(f'Yazım/doğallık: {a} → {b}')

    if re.search(r'\bcases?\b', en, re.I) and re.search(r'\bdava', out, re.I):
        old=out
        for a,b in CASE_FORMS: out=out.replace(a,b)
        if out!=old: notes.append('Dedektiflik terminolojisi: case → vaka')

    if re.search(r'\btestimony\b', en, re.I) and 'tanıklık' in out.lower():
        old=out
        for a,b in TESTIMONY_FORMS: out=out.replace(a,b)
        if out!=old: notes.append('Dedektiflik terminolojisi: testimony → ifade')

    if re.search(r'dressing\s+rooms?', en, re.I) and re.search(r'soyunma od', out, re.I):
        old=out
        out=out.replace('Soyunma Odaları','Kulisler').replace('soyunma odaları','kulisler')
        out=out.replace('Soyunma Odası','Kulis').replace('soyunma odası','kulis')
        out=out.replace('soyunma odasında','kuliste').replace('soyunma odasına','kulise').replace('soyunma odalarında','kulislerde')
        if out!=old: notes.append('TV stüdyosu: dressing room → kulis (FR loge / ES camerino / JP 控室)')

    # "Come to think of it" is a discourse marker, not literal thinking instruction.
    if 'come to think of it' in en.lower():
        old=out
        out=re.sub(r'(?i)(?<!şimdi )düşününce', lambda m: 'Şimdi düşününce' if m.group(0)[0].isupper() else 'şimdi düşününce', out)
        if out!=old: notes.append('Deyim: come to think of it → şimdi düşününce')

    for enr,repls in STAGE_RULES:
        if re.search(enr,en,re.I):
            for a,b in repls:
                if a in out:
                    out=out.replace(a,b); notes.append(f'Sahne yönergesi: {a} → {b}')

    key=(file_name,idx)
    if key in OVERRIDES:
        out=OVERRIDES[key]; notes.append('Çok-dilli bağlamla elle yeniden yazım')
    return out, notes

def main():
    if len(sys.argv)!=3:
        print('usage: polish_v3.py INPUT_CSV_DIR OUTPUT_CSV_DIR'); raise SystemExit(2)
    src=Path(sys.argv[1]); dst=Path(sys.argv[2]); dst.mkdir(parents=True,exist_ok=True)
    audit=[]; manifest=[]; total_changed=0
    for p in sorted(x for x in src.glob('*.csv') if not x.name.startswith('_')):
        with p.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f)); fields=list(rows[0].keys()) if rows else []
        if 'Turkish_Revised_v3' not in fields: fields += ['Turkish_Revised_v3','V3_Notes']
        changed=0
        for r in rows:
            idx=int(r['Index']); before=r['Turkish_Revised']; after,notes=polish(p.name,idx,r['English'],before)
            if control_signature(after)!=control_signature(r['English']):
                raise ValueError(f'control mismatch {p.name}:{idx}\nEN={r["English"]}\nTR={after}')
            r['Turkish_Revised_v3']=after; r['V3_Notes']='; '.join(notes)
            if after!=before:
                changed+=1; total_changed+=1
                audit.append({'File':p.name, **r})
        out=dst/p.name
        with out.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
        manifest.append([p.name,len(rows),changed])
    with (dst/'_manifest_v3.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f); w.writerow(['File','Rows','V3AdditionalChanges']); w.writerows(manifest)
    if audit:
        fields=['File']+[x for x in audit[0].keys() if x!='File']
        with (dst/'_v3_changes.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(audit)
    print(f'V3 built: {len(manifest)} files, {total_changed} additional changed rows')

if __name__=='__main__': main()
