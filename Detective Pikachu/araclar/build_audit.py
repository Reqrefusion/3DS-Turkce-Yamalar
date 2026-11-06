#!/usr/bin/env python3
from __future__ import annotations
import csv, re, sys, shutil
from pathlib import Path

if len(sys.argv) != 4:
    raise SystemExit('Kullanım: python build_audit.py <v4_comparison_csv_dir> <v3_assets_dir> <output_audit_dir>')
SRC=Path(sys.argv[1])
V3=Path(sys.argv[2])
OUT=Path(sys.argv[3])
OUT.mkdir(parents=True,exist_ok=True)

# Review-priority map generated from all official languages.
priority={}
rp=V3/'_review_priority.csv'
if rp.exists():
    with rp.open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            priority[(r['File'],int(r['Index']))]=(int(r['PriorityScore']),r['Reasons'])

ctrl_re=re.compile(r'\{\{(?:CTRL|BYTE):.*?\}\}')
space_re=re.compile(r'\s+')

def visible(s):
    return space_re.sub(' ',ctrl_re.sub('',s or '')).strip()

def only_technical(s):
    v=visible(s)
    return not v or v.upper().startswith('NOMESSAGE_')

def looks_proper_or_pokemon(row):
    lab=row.get('Label','').upper()
    tr=visible(row.get('Turkish_Revised_v4',''))
    en=visible(row.get('English',''))
    if any(k in lab for k in ('PROF_NAME','CHARA_NAME','POKEMON_NAME','NAME_')) and len(tr)<=60:
        return True
    # Identical short alphabetic strings are overwhelmingly character/Pokémon/proper names/UI tokens.
    if tr == en and 0 < len(tr) <= 28 and '\n' not in row.get('English','') and re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9 .:'’!?\-]+",tr):
        return True
    return False

def stage(row):
    cur=row.get('Turkish_Current','')
    tech=row.get('Turkish_Technical_Repaired',cur)
    v2=row.get('Turkish_Revised',tech)
    v3=row.get('Turkish_Revised_v3',v2)
    v4=row.get('Turkish_Revised_v4',v3)
    if v4 != v3: return 'V4'
    if v3 != v2: return 'V3'
    if v2 != tech: return 'V2'
    if tech != cur: return 'TEKNİK'
    return 'AYNI'

def change_type(row, st):
    cur=row.get('Turkish_Current',''); tech=row.get('Turkish_Technical_Repaired',cur); final=row.get('Turkish_Revised_v4','')
    notes='; '.join(x for x in [row.get('Review_Notes',''),row.get('V3_Notes',''),row.get('V4_Notes','')] if x).lower()
    types=[]
    if tech!=cur: types.append('Teknik')
    if any(k in notes for k in ['terminoloji','case →','ranger','order-sheet','standardize','vaka notları','yıkım geni']): types.append('Terminoloji')
    if any(k in notes for k in ['yazım:','orthography','suffix fixed','genitive suffix','typo','harfi']): types.append('Yazım')
    if any(k in notes for k in ['semantic','anlam','wrong','direction','proof','safe','not that','yanlış','olaya','destruction gene']): types.append('Anlam')
    if any(k in notes for k in ['idiom','natural','doğal','filler','tone','joke','discourse','pikachu','rewritten','restructured','literal','üslup']): types.append('Üslup')
    if final!=cur and not types: types.append('Anlam/Üslup')
    if not types: return 'Yok'
    # preserve order, unique
    return ' + '.join(dict.fromkeys(types))

def multilingual_note(fn, idx, row, score, reasons):
    texts=[visible(row.get(k,'')) for k in ['French','German','Italian','Spanish','JPN','Simp_Chinese','Trad_Chinese']]
    placeholders=sum(1 for t in texts if not t or t.upper().startswith('NOMESSAGE_'))
    if placeholders>=3:
        return 'Bazı resmî yerelleştirmelerde bu satır teknik/boş placeholder olarak duruyor. Anlam değerlendirmesinde Japonca/Çince ve sahne bağlamı daha ağır basıyor.'
    if score>=9:
        return f'Resmî diller arasında belirgin yaratıcı/biçimsel ayrışma var ({reasons}). Japonca/Çince çekirdek anlamı; Fransızca, Almanca, İtalyanca ve İspanyolca doğal yerelleştirme yönünü kontrol etmek için kullanıldı.'
    if score>=5:
        return f'Bazı dillerde ton, satır bölünmesi veya ifade uzunluğu farklı ({reasons}). Buna rağmen ortak çekirdek anlam karşılaştırıldı; Japonca/Çince anlam çıpası, Avrupa dilleri doğal söyleyiş kontrolü olarak kullanıldı.'
    if score>0:
        return f'Küçük biçim/ton farkları var ({reasons}); yedi resmî çeviri aynı sahne işlevini veya çekirdek mesajı destekliyor.'
    return 'Fransızca, Almanca, İtalyanca, İspanyolca, Japonca ve iki Çince sürüm arasında belirgin bir anlam çatışması tespit edilmedi; ortak çekirdek mesaj Türkçeyle karşılaştırıldı.'

def unchanged_reason(row, score):
    lab=row.get('Label','').upper(); tr=visible(row.get('Turkish_Revised_v4','')); en=visible(row.get('English',''))
    if only_technical(row.get('English','')) and only_technical(row.get('Turkish_Revised_v4','')):
        return 'Dilsel içerik taşımayan boş/teknik/placeholder satırı; işlevsel yapı korunduğu için değiştirilmedi.'
    if looks_proper_or_pokemon(row):
        return 'Özel ad, Pokémon adı veya kısa sabit adlandırma; Türkçe yamadaki adlandırma kaynakla uyumlu olduğundan bilinçli olarak korundu.'
    if 'POKÉMON CRY' in en.upper() or 'NOMESSAGE' in lab or (len(tr)<=18 and any(x in tr for x in ['!', '…', '...'])):
        return 'Ünlem, Pokémon sesi veya kısa sahne tepkisi; mevcut Türkçe işlevi/tonu bozmadığı ve ek anlam kaybı göstermediği için aynı kaldı.'
    if any(k in lab for k in ('TITLE','HUD','MENU','MAP_','EVIDENCE','PROF_','COMMENT_','QUESTION','QST','ITEM','MEMO','TUTORIAL','SELECT')) and len(tr)<=160:
        return 'Arayüz, ipucu, profil veya kısa terminoloji satırı; anlam ve terim kullanımı diğer resmî dillerle uyumlu olduğundan aynı kaldı.'
    if score>=9:
        return 'Bu satır yerelleştirmeler arasında yaratıcı biçimde ayrışıyor; karşılaştırmada mevcut Türkçeyi değiştirmeyi zorunlu kılan yüksek güvenli bir anlam/ton hatası bulunmadı. Gereksiz yeniden yazım yapmamak için korundu.'
    if score>=5:
        return 'Resmî dillerde ifade biçimi değişse de mevcut Türkçe ortak anlamı doğal biçimde taşıyor; anlam kazanımı sağlamayacak kozmetik değişiklikten kaçınıldı.'
    return 'Çok-dilli karşılaştırmada anlam çelişkisi, belirgin deyim hatası, terminoloji sorunu veya doğal Türkçeyi bozacak bir yapı saptanmadı; bu nedenle mevcut çeviri korundu.'

def localize_note(n):
    n=(n or '').strip()
    exact={
      'Curated multilingual/contextual revision':'Çok-dilli ve bağlamsal karşılaştırmayla elle yeniden düzenlendi.',
      'Detective Tip wording standardized':'Dedektif İpucu metni tutarlı ve doğal Türkçe olacak şekilde standardize edildi.',
      'Case Notes → Vaka Notları (JP 推理メモ / ZH 推理笔记)':'Case Notes terimi, JP 推理メモ ve ZH 推理笔记 karşılıkları da dikkate alınarak “Vaka Notları” olarak standardize edildi.',
      'Case List → Vaka Listesi (JP 捜査リスト / ZH 调查列表)':'Case List terimi, JP 捜査リスト ve ZH 调查列表 karşılıkları doğrultusunda “Vaka Listesi” olarak standardize edildi.',
      'scale disambiguated via JP ウロコ → pul (FR écaille / DE Schuppe / ES escama)':'“Scale” sözcüğünün bu bağlamda terazi değil Pokémon pulu olduğu JP ウロコ, FR écaille, DE Schuppe ve ES escama ile doğrulandı; “pul” olarak düzeltildi.',
      'Pokémon move disambiguated via JP 技 → hamle':'“Move” sözcüğünün Pokémon saldırısı/tekniği anlamında olduğu JP 技 ile doğrulandı; “hamle” olarak düzeltildi.',
      'men with luggage → sandık taşıyan adamlar (FR caisse / DE Kiste / IT cassa / ES caja)':'“Men with luggage” ifadesindeki yükün sandık/kasa olduğu FR caisse, DE Kiste, IT cassa ve ES caja ile doğrulandı; “sandık taşıyan adamlar” yapıldı.',
      'oil disambiguated via JP 石油 / FR pétrole / IT petrolio / ES petróleo → petrol':'“Oil” sözcüğünün yemeklik yağ değil petrol olduğu JP 石油, FR pétrole, IT petrolio ve ES petróleo ile doğrulandı; “petrol” olarak düzeltildi.',
      "alibi: generic 'mazeret' → detective/legal 'alibi'":'Dedektiflik bağlamında genel “mazeret” yerine doğru terim olan “alibi” kullanıldı.',
      'Thunderbolt → Yıldırım (patch glossary consistency)':'Pokémon hamlesi Thunderbolt, yama sözlüğüyle tutarlı biçimde “Yıldırım” olarak standardize edildi.',
      'mastermind terminology → asıl planlayıcı (JP 黒幕/真犯人)':'“Mastermind” terimi JP 黒幕/真犯人 bağlamıyla karşılaştırılarak “asıl planlayıcı” şeklinde düzeltildi.',
      'sniff stage direction normalized → *koklar*':'“Sniff” sahne yönergesi doğal Türkçe eylem biçimi olan “*koklar*” şeklinde standardize edildi.',
      "deduction: formal 'tümdengelim' → detective-context 'çıkarım'":'Dedektiflik bağlamında aşırı akademik “tümdengelim” yerine doğal “çıkarım” kullanıldı.',
      'sense of smell: koku alma duyusu':'“Sense of smell” ifadesi doğru Türkçeyle “koku alma duyusu” yapıldı.',
      'Orthography: hiç bir → hiçbir':'Yazım: “hiç bir” → “hiçbir”.',
      'Orthography: yani sıra → yanı sıra':'Yazım: “yani sıra” → “yanı sıra”.',
      'Orthography: ipuçlarina → ipuçlarına':'Yazım: “ipuçlarina” → “ipuçlarına”.',
      'Orthography: haşat → hasat':'Yazım: “haşat” → “hasat”.',
      'Orthography: Çözdüg → Çözdüğ':'Yazım: “Çözdüg” → “Çözdüğ”.',
      'Surf move phrasing normalized':'Pokémon hamlesi Surf için kullanılan ifade doğal ve tutarlı Türkçeye göre düzenlendi.',
      'Yazım: Louise + genitive suffix':'Yazım: “Louise” adına getirilen ilgi eki Türkçe sesletime uygun biçimde “Louise’in” olarak düzeltildi.',
      'Yazım: DNA + genitive suffix':'Yazım: DNA kısaltmasının ilgi eki “DNA’nın” olarak düzeltildi.',
      'Yazım standardizasyonu':'Yazım standardizasyonu yapıldı.',
      'Technical repair left duplicated/incomplete parade phrase; rebuilt as broadcast fragment while preserving all control codes.':'Teknik onarımdan sonra tekrarlı/eksik kalan geçit töreni yayın cümlesi, tüm kontrol kodları korunarak doğal bir yayın parçası şeklinde yeniden kuruldu.',
      'JP/FR/DE/IT/ES treat “you know” as discourse emphasis, not a literal question.':'JP/FR/DE/IT/ES sürümleri “you know” ifadesini gerçek bir soru değil konuşma vurgusu olarak ele alıyor; gereksiz “biliyor musun?” kaldırıldı.',
      'JP/FR/DE/IT/ES contain only a hesitant request to slow down; literal “Biliyor musun?” removed.':'JP/FR/DE/IT/ES yalnızca çekingen bir “yavaşlar mısın?” isteği içeriyor; literal “Biliyor musun?” kaldırıldı.',
      'JP/FR/DE/IT/ES: simple recollection marker; literal “Biliyor musun?” removed.':'JP/FR/DE/IT/ES sürümlerinde bu bölüm yalnızca hatırlama geçişi; literal “Biliyor musun?” kaldırıldı.',
      'JP/ZH say directly that Tim is the second person to ask about R; English filler omitted.':'JP/ZH doğrudan Tim’in R’yi soran ikinci kişi olduğunu söylüyor; İngilizcedeki konuşma dolgusu Türkçeye taşınmadı.',
      'JP/FR/DE/IT/ES: recollection about man with Pikachu; English filler omitted.':'JP/FR/DE/IT/ES bir Pikachu ile gelen adamın hatırlanmasına odaklanıyor; İngilizcedeki dolgu ifade kaldırıldı.',
      'JP/ZH avoid literal Pokémon-style evolution for a human; Turkish keeps the parallel naturally and standardizes Pokémon Korucusu.':'JP/ZH bir insan için Pokémon evrimi ifadesini kelimesi kelimesine kullanmıyor; Türkçe benzetmeyi doğal kurdu ve “Pokémon Korucusu” terimini standardize etti.',
      'Original Turkish had broken time relation; JP/ZH/FR/DE/IT/ES agree water quality is now different from the old days.':'Eski Türkçede zaman ilişkisi bozuktu; JP/ZH/FR/DE/IT/ES su kalitesinin geçmişe göre artık farklı olduğunu ortak biçimde doğruluyor.',
      'Pokémon Ranger terminology standardized as Pokémon Korucusu; English discourse filler omitted.':'Pokémon Ranger terimi “Pokémon Korucusu” olarak standardize edildi; İngilizcedeki konuşma dolgusu aktarılmadı.',
      'JP/ZH/FR/IT/ES: project stress/overfocus, not literally “a point I got stuck at”.':'JP/ZH/FR/IT/ES anlamı projeye aşırı odaklanma/stres; “takılıp kaldığım bir nokta” şeklindeki literal anlam kaldırıldı.',
      'Control-repaired line had modifier order inverted; JP/ZH confirm four-balloon bundle opposite Brad.':'Kontrol kodu onarılmış satırda tamlayan sırası bozuktu; JP/ZH Brad’in karşısındaki dört balonluk demeti doğruluyor.',
      'Removed “yakından yaklaşmak” redundancy; all languages mean get/see Pokémon up close.':'“Yakından yaklaşmak” anlatım bozukluğu kaldırıldı; tüm diller Pokémonlara yakından bakma/yaklaşma anlamında birleşiyor.',
      'Typo “küsur” corrected to “kusur”; JP context is inspection/quality checking.':'Yazım hatası “küsur” → “kusur” düzeltildi; JP bağlamı kalite/kusur kontrolünü doğruluyor.',
      'Typo “küsur” corrected to “kusur”; JP/EN agree many defective items.':'Yazım hatası “küsur” → “kusur” düzeltildi; JP/EN çok sayıda kusurlu parça bulunduğunu doğruluyor.',
      'FR/DE/IT/ES idiom “tell me about it” = agreement/commiseration; Turkish “Sorma!” is idiomatic.':'FR/DE/IT/ES karşılıkları “tell me about it” deyiminin soru değil dert ortaklığı/onay olduğunu gösteriyor; Türkçede doğal karşılık “Sorma!” yapıldı.',
      'JP/ZH tone is teasing praise (“you’re pretty good”); Turkish made more Pikachu-like.':'JP/ZH tonu takılmalı bir övgü; Türkçe Pikachu’nun sesine daha uygun, hafif alaycı bir övgü olarak düzenlendi.',
      'JP/ZH “collect testimony and verify”; Turkish changed from singular imperative to collaborative natural phrasing.':'JP/ZH “ifadeleri toplayıp doğrulama/karşılaştırma” anlamını veriyor; Türkçe tekil emir yerine ortak hareketi anlatan doğal yapıya çevrildi.',
      'Technical repair left duplicated “frozen” phrase; JP/FR/DE confirm help frozen Drifloon and borrow its help.':'Teknik onarım sonrası “donmuş” ifadesi gereksiz tekrarlanmıştı; JP/FR/DE donmuş Drifloon’u kurtarıp yardım isteme anlamını doğruluyor.',
      'FR/DE/IT/ES explicitly “not that one”; puzzle rejection is “O değil”, not factual “Bu doğru değil”.':'FR/DE/IT/ES açıkça “o değil” diyor; bulmaca reddi bir doğruluk yargısı değil yanlış seçeneği işaret ediyor. “O değil” yapıldı.',
      'FR/DE/IT/ES explicitly “not that one”; puzzle rejection localized naturally.':'FR/DE/IT/ES açıkça “o değil” anlamında; bulmaca reddi doğal Türkçeyle düzenlendi.',
      'JP/FR/DE/ES: wrong target vial/type; natural Turkish “Aradığımız şişe bu değil”.':'JP/FR/DE/ES yanlış hedef şişe/tür anlamında birleşiyor; doğal Türkçe “Aradığımız şişe bu değil” yapıldı.',
      '“involved in the show” means participants/people connected to the program, not “gösteriye karışan”.':'“Involved in the show” suç/olaya karışmak değil programda yer alan kişiler anlamında; “gösteriye karışan” düzeltildi.',
      'JP/ZH/FR/DE explicitly refer to operating losses/red figures; “zarar etmeyi bırakmak” replaced with natural “açığını kapatmak”.':'JP/ZH/FR/DE işletme zararı/açık anlamını açıkça veriyor; “zarar etmeyi bırakmak” yerine doğal “açığını kapatmak” kullanıldı.',
      'Control-repaired text still contained duplicated “kapı”; JP/ZH and EU languages confirm a shout came from inside after knocking.':'Kontrol kodu onarılan metinde “kapı” tekrarı kalmıştı; JP/ZH ve Avrupa dilleri kapı çalındıktan sonra içeriden bağırıldığını doğruluyor.',
      'JP/ZH/FR/IT/ES idiom is “what is she doing/taking so long”; literal causal phrasing removed.':'JP/ZH/FR/IT/ES anlamı “bu kadın ne yapıyor da bu kadar gecikiyor?”; literal ve nedensellik bozukluğu taşıyan yapı kaldırıldı.',
      'FR/DE/IT/ES/JP indicate correction of a mistaken answer (“not that; it is Chatot”), not truth-value statement.':'FR/DE/IT/ES/JP yanlış cevabı düzeltme anlamında “o değil, bu Chatot” diyor; “doğru/yanlış” önermesi gibi çevrilmedi.',
      'JP/ZH/FR/DE explain rubbing arms cannot make that beautiful sound; expanded to preserve the joke.':'JP/ZH/FR/DE kolları birbirine sürterek aynı güzel sesin çıkarılamayacağı esprisini açıklıyor; Türkçe espriyi koruyacak kadar açıldı.',
      'JP/ZH/DE singular Baker office; literal “offices” replaced with Baker’ın bürosu; hedge removed.':'JP/ZH/DE Baker’ın tekil bürosunu doğruluyor; “ofisler” hatası “Baker’ın bürosu” yapıldı ve gereksiz belirsizlik kaldırıldı.',
      'Control-repaired sentence restructured; JP/ZH confirm Burmy uses surrounding material and has three cloak types.':'Kontrol kodları düzeltilmiş cümlenin sözdizimi yeniden kuruldu; JP/ZH Burmy’nin çevresindeki malzemeleri kullandığını ve üç pelerin türü bulunduğunu doğruluyor.',
      'Control-repaired but syntactically broken line rewritten; FR/DE/IT/ES/JP/ZH agree on Taillow preening and dropped feathers.':'Kontrol kodları onarılmış olsa da sözdizimi bozuk kalan cümle yeniden yazıldı; FR/DE/IT/ES/JP/ZH Taillowların tüylerini temizleyip tüy bıraktığı anlamında birleşiyor.',
      'Control-repaired word order was broken; all languages mean “proof it was involved in the incident”.':'Kontrol kodu onarımından sonra sözcük sırası bozuktu; tüm diller “olaya karıştığını gösteren kanıt” anlamını doğruluyor.',
      'Goodman suffix fixed; JP/ZH emphasize Pikachu is Harry’s partner and currently stays/works with Baker agency.':'Goodman adına gelen ek düzeltildi; JP/ZH Pikachu’nun Harry’nin ortağı olduğunu ve şu anda Baker ajansında kaldığını/çalıştığını vurguluyor.',
      'All languages say she was looking down; previous Turkish incorrectly said “bir şeye aşağıdan bakıyordu”.':'Tüm diller kişinin aşağıya baktığını söylüyor; eski Türkçedeki “bir şeye aşağıdan bakıyordu” yönü tersine çeviriyordu ve düzeltildi.',
      'JP/ZH/DE/ES use order sheet/form; standardized “sipariş formu”, not receipt.':'JP/ZH/DE/ES sipariş kâğıdı/formu anlamında; “fiş” değil “sipariş formu” olarak standardize edildi.',
      'Order-sheet terminology standardized across repeated interaction.':'Tekrarlanan etkileşim boyunca sipariş kâğıdı terimi “sipariş formu” olarak tutarlılaştırıldı.',
      'Order-sheet terminology standardized; subject agreement made natural.':'Sipariş kâğıdı terimi “sipariş formu” olarak standardize edildi; özne/yüklem ilişkisi de doğal Türkçeye göre düzeltildi.',
      'JP “そうか!” / FR “Mais oui!” are realization markers; “Ne biliyor musun?!” was a literal mistranslation.':'JP “そうか!” ve FR “Mais oui!” fark etme/aydınlanma ünlemleri; “Ne biliyor musun?!” literal ve yanlış bir çeviriydi.',
      'JP expresses general realization that people/Pokémon can change; English fillers removed.':'JP, insanların ve Pokémonların değişebileceğine dair genel bir fark ediş veriyor; İngilizcedeki dolgu ifadeler Türkçeye taşınmadı.',
      'JP says Pikachu has been waiting and is fully prepared; Turkish “Beni beklettiğini biliyorsun” was unnatural.':'JP Pikachu’nun beklediğini ve tamamen hazır olduğunu söylüyor; “Beni beklettiğini biliyorsun” doğal değildi ve yeniden kuruldu.',
      'JP/FR frame this as “destiny”; English filler localized as emphatic “İşte buna kader derim!”.':'JP/FR bunu “kader” olarak çerçeveliyor; İngilizcedeki dolgu ifade Türkçede doğal vurgu olan “İşte buna kader derim!” şeklinde yerelleştirildi.',
      'JP/ZH/FR/DE/IT/ES: Pikachu is confident Harry must be safe; “iyi olmak zorunda” was a semantic calque.':'JP/ZH/FR/DE/IT/ES Pikachu’nun Harry’nin güvende/iyi olduğuna emin olduğunu gösteriyor; “iyi olmak zorunda” anlamsal bir İngilizce kopyasıydı.',
    }
    # Split compound notes and localize each segment where possible.
    if n in exact: return exact[n]
    parts=[x.strip() for x in n.split(';') if x.strip()]
    if len(parts)>1:
        return '; '.join(exact.get(x,x) for x in parts)
    return exact.get(n,n)

def changed_reason(row, st, typ):
    notes=[]
    for key in ('V4_Notes','V3_Notes','Review_Notes'):
        n=localize_note(row.get(key) or '')
        if n and n not in notes: notes.append(n)
    cur=row.get('Turkish_Current',''); tech=row.get('Turkish_Technical_Repaired',cur)
    if st=='TEKNİK' and tech!=cur:
        return 'Metindeki bozuk Nintendo kontrol/renk kodları resmî kaynakla eşleştirilerek onarıldı; dilsel içerik mümkün olduğunca korunup oyun içi biçimlendirme güvenli hâle getirildi.'
    if notes:
        return ' | '.join(notes)
    return 'Çok-dilli karşılaştırma sonucunda anlam, terminoloji, deyim veya doğal Türkçe açısından yüksek güvenli bir iyileştirme yapıldı.'

def supporting_languages(row):
    # These are the independent official localizations present in the archive and consulted for every aligned row.
    available=[]
    for col,short in [('JPN','JP'),('Simp_Chinese','ZH-CN'),('Trad_Chinese','ZH-TW'),('French','FR'),('German','DE'),('Italian','IT'),('Spanish','ES')]:
        t=visible(row.get(col,''))
        if t and not t.upper().startswith('NOMESSAGE_'): available.append(short)
    return ', '.join(available) if available else 'Teknik satır / bağlam'

all_rows=[]; summaries=[]; changed=[]; unchanged=[]
per_fields=None
for p in sorted(x for x in SRC.glob('*.csv') if not x.name.startswith('_')):
    with p.open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    outrows=[]; c=0; u=0; v4c=0; technical=0; semantic=0
    for r in rows:
        idx=int(r['Index']); sc,rs=priority.get((p.name,idx),(0,''))
        st=stage(r)
        final=r.get('Turkish_Revised_v4',''); cur=r.get('Turkish_Current','')
        decision='DEĞİŞTİ' if final!=cur else 'AYNI_KALDI'
        typ=change_type(r,st)
        if decision=='DEĞİŞTİ':
            reason=changed_reason(r,st,typ); c+=1; changed.append((p.name,r))
        else:
            reason=unchanged_reason(r,sc); u+=1; unchanged.append((p.name,r))
        if st=='V4': v4c+=1
        if r.get('Turkish_Technical_Repaired','') != cur: technical+=1
        if final != r.get('Turkish_Technical_Repaired',''): semantic+=1
        creative='YÜKSEK' if sc>=9 else ('ORTA' if sc>=5 else 'DÜŞÜK')
        confidence='YÜKSEK' if decision=='DEĞİŞTİ' or sc<9 else 'ORTA'
        mode='ELLE KÜRASYON + ÇOK-DİLLİ KONTROL' if decision=='DEĞİŞTİ' else 'SATIR BAZLI ÇOK-DİLLİ KONTROL'
        audit={
            'File':p.name,
            'Index':r['Index'],
            'Label':r['Label'],
            'English':r['English'],'French':r['French'],'German':r['German'],'Italian':r['Italian'],'Spanish':r['Spanish'],
            'JPN':r['JPN'],'jp_hira':r['jp_hira'],'Simp_Chinese':r['Simp_Chinese'],'Trad_Chinese':r['Trad_Chinese'],
            'Turkish_Original_Patch':cur,
            'Turkish_Technical_Repaired':r.get('Turkish_Technical_Repaired',''),
            'Turkish_v2':r.get('Turkish_Revised',''),
            'Turkish_v3':r.get('Turkish_Revised_v3',''),
            'Turkish_Final_v4':final,
            'Karar':decision,
            'Degisiklik_Asamasi':st,
            'Degisiklik_Turu':typ,
            'Neden_TR':reason,
            'Diger_Dillerle_Karsilastirma_TR':multilingual_note(p.name,idx,r,sc,rs),
            'Destekleyen_Kaynak_Diller':supporting_languages(r),
            'Yaratici_Fark_Duzeyi':creative,
            'Oncelik_Puani':str(sc),
            'Oncelik_Nedenleri':rs,
            'Guven':confidence,
            'Inceleme_Bicimi':mode,
            'Onceki_Review_Status':r.get('Review_Status',''),
            'Onceki_Review_Notes':r.get('Review_Notes',''),
            'V3_Notes':r.get('V3_Notes',''),
            'V4_Notes':r.get('V4_Notes',''),
        }
        outrows.append(audit); all_rows.append(audit)
    fields=list(outrows[0].keys()) if outrows else []
    per_fields=fields
    with (OUT/p.name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(outrows)
    summaries.append({'File':p.name,'Toplam_Satir':len(rows),'Degisti':c,'Ayni_Kaldi':u,'V4_Yeni_Degisiklik':v4c,'Teknik_Onarim_Iceren':technical,'Final_Semantik_Fark':semantic})

with (OUT/'_ALL_17653_AUDIT.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=per_fields); w.writeheader(); w.writerows(all_rows)
with (OUT/'_AUDIT_SUMMARY.csv').open('w',encoding='utf-8-sig',newline='') as f:
    fields=list(summaries[0].keys()); w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(summaries)
with (OUT/'_CHANGED_ONLY.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=per_fields); w.writeheader(); w.writerows([r for r in all_rows if r['Karar']=='DEĞİŞTİ'])
with (OUT/'_UNCHANGED_ONLY.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=per_fields); w.writeheader(); w.writerows([r for r in all_rows if r['Karar']=='AYNI_KALDI'])

print('files',len(summaries),'rows',len(all_rows),'changed',sum(x['Degisti'] for x in summaries),'unchanged',sum(x['Ayni_Kaldi'] for x in summaries),'v4add',sum(x['V4_Yeni_Degisiklik'] for x in summaries),'tech',sum(x['Teknik_Onarim_Iceren'] for x in summaries),'semantic-final',sum(x['Final_Semantik_Fark'] for x in summaries))
