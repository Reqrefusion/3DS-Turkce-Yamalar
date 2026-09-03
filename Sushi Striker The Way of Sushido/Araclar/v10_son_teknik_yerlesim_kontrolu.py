from pathlib import Path
import csv,re,math,shutil,subprocess,sys,zipfile,hashlib,py_compile
from functools import lru_cache

ROOT=Path('/mnt/data/sushi_work'); R=ROOT/'review_v10'; CSV=R/'csv'; TOOL=R/'Araclar'/'sushi_msbt_csv_flat.py'; SOURCE=ROOT/'review_v09_source'/'msgstudio'
files={}; rows={}
for p in CSV.glob('*.csv'):
    with p.open(encoding='utf-8-sig',newline='') as f:
        rs=list(csv.DictReader(f)); fields=list(rs[0].keys())
    files[p.name]=(fields,rs)
    for r in rs:rows[(p.name,r['label'])]=r

def readcsv(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def writecsv(p,fields,data):
    with Path(p).open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(data)

change_fields=['round','category','file','label','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
changes=readcsv(R/'V10_YENI_DEGISIKLIKLER.csv'); cmap={(x['file'],x['label']):x for x in changes}
master=readcsv(R/'TUM_10676_SATIR_DURUMU.csv'); mmap={(x['file'],x['label']):x for x in master}
review=readcsv(R/'V10_DERIN_KALITE_VE_TEKNIK_INCELEME.csv'); rvmap={(x['file'],x['label']):x for x in review}
combined=readcsv(R/'INCELEME_DEGISIKLIKLERI.csv')
prev_combined_count=len(combined)

def setv(fn,lab,new,reason,category):
    r=rows[(fn,lab)];old=r['tur']
    if old==new:return False
    r['tur']=new;k=(fn,lab)
    if k in cmap:
        c=cmap[k];c['new_tur']=new
        if reason not in c['reason']:c['reason']+=' Ek: '+reason
    else:
        c={'round':'v0.10','category':category,'file':fn,'label':lab,'eng':r['eng'],'deu':r['deu'],'esp':r['esp'],'fra':r['fra'],'ita':r['ita'],'nld':r['nld'],'old_tur':old,'new_tur':new,'reason':reason}
        changes.append(c);cmap[k]=c;combined.append(c.copy())
    # If existing combined already had v10 key, update its newest matching entry rather than duplicate
    for x in reversed(combined):
        if x['round']=='v0.10' and (x['file'],x['label'])==k:
            x['new_tur']=new
            if reason not in x['reason']:x['reason']+=' Ek: '+reason
            break
    if k in mmap:
        m=mmap[k];m['review_status']='DERİN+TEKNİK_v0.10';m['decision']='DEĞİŞTİ';m['current_tur']=new;m['reason']=cmap[k]['reason']
    # review row
    if k in rvmap:
        v=rvmap[k];v['decision']='DEĞİŞTİ';v['new_tur']=new;v['reason']=cmap[k]['reason']
    else:
        pm=mmap[k]
        v={'round':'v0.10','file':fn,'label':lab,'index':r['index'],'previous_review_status':pm.get('review_status',''),'previous_decision':pm.get('decision',''),
           'decision':'DEĞİŞTİ','eng':r['eng'],'deu':r['deu'],'esp':r['esp'],'fra':r['fra'],'ita':r['ita'],'nld':r['nld'],'old_tur':old,'new_tur':new,'reason':reason}
        review.append(v);rvmap[k]=v
    return True

# ------------------------------------------------------------------
# M/F same-source: Turkish is gender-neutral here; normalize all 47 manually reviewed pairs.
# ------------------------------------------------------------------
mf_reason="ENG metni M/F varyantlarında birebir aynı ve Türkçede cinsiyete bağlı bir dilbilgisi ayrımı yok. İlk geçişlerde iki etiket farklı sürümlerde kalmıştı; sahne bağlamı tekrar okunup daha doğal olan tek Türkçe iki varyanta da uygulandı."
mf={
('chapterBeginM003.csv','CharaSerif_27'):'Off... Şu “olgunluk” lafların\\nhiç de ince değil, haberin olsun!',
('chapterBeginM005.csv','CharaSerif_24'):'Bu... bizim için hiç iyi değil.',
('chapterBeginM008.csv','CharaSerif_06'):'Beni dinleyin. İçeri tek başıma gireceğim!',
('chapterBeginM009.csv','CharaSerif_11'):'Off.',
('database_movieSerif_5A.csv','MovieSerifText_5a_0046'):"Cumhuriyet'in safında\\nsavaştın!",
('database_movieSerif_5C.csv','MovieSerifText_5c_0017'):"Tamamdır! Hadi, İmparatorluk Ordusu'nu\\npataklayalım!",
('database_movieSerif_7C.csv','MovieSerifText_7c_0017'):'Sana olan borcumu ödemek istedim,\\no yüzden...',
('database_movieSerif_7C.csv','MovieSerifText_7c_0022'):'Çocuklara suşi yedireceğiz...',
('database_movieSerif_7C.csv','MovieSerifText_7c_0023'):'her ülkede, tüm\\ndünyada!',
('database_movieSerif_9A.csv','MovieSerifText_9a_0023'):'Bunu sana milyon kere sordum...',
('database_movieSerif_9B.csv','MovieSerifText_9b_0034'):'Burada konuşuyoruz!',
('database_movieSerif_9B.csv','MovieSerifText_9b_0037'):'Beni duydun mu?!',
('homeSushibar.csv','homeSushibar_15_a_06'):'Teşekkürler. İlk fırsatta buna bakacağım!',
('scene_puzzlebattle.csv','Enemy_StgWin_009'):'Uzun süren saldırıya\\ndayanamayacağını biliyordum!',
('scene_puzzlebattle.csv','Player_Chr001_HpLow25'):'Hadi, toparlan!',
('scene_puzzlebattle.csv','Player_Chr001_HpLow50'):'Şimdi iş ciddiye bindi!',
('scene_puzzlebattle.csv','Player_Chr001_HpLow75'):'Bu iş bende!',
('scene_puzzlebattle.csv','Player_StgWin_003'):'Sadece sende olmadığı için sinirlisin,\\nKojiro!',
('scene_puzzlebattle.csv','Player_StgWin_008'):'ŞİMDİ bana çocuk muamelesi\\nyapmayı bırakacak mısın?!',
('scene_puzzlebattle.csv','Player_StgWin_021'):'Bırak da geçeyim! O kızı\\nyeniden görmem gerek!',
('scene_puzzlebattle.csv','Player_StgWin_025'):"Umarım Celia'ya yavaş yavaş\\nulaşabiliyorumdur...",
('scene_puzzlebattle.csv','Player_StgWin_030'):'Ben aptal değilim! Sadece\\nbir dakika beni dinle!',
('scene_puzzlebattle.csv','Player_StgWin_036'):'Bu işin püf noktasını\\nkapıyorum! İyi suş, dostum!',
('scene_puzzlebattle.csv','Player_StgWin_053'):'En iyilerin en iyisi denilen\\nadam bu mu?',
('scene_puzzlebattle.csv','Player_StgWin_056'):'Uyarı için sağ ol,\\nbeyefendi!',
('scene_puzzlebattle.csv','Player_StgWin_078'):'Suş? Spor mu? Kafamı\\nağrıttın...',
('scene_puzzlebattle.csv','Player_StgWin_084'):'Anlaşılan Purrsilla hanım ona\\nhiç suşi vermiyor...',
('scene_puzzlebattle.csv','Player_StgWin_086'):'İnat etmeyi bırak da\\nbiraz ye artık!',
('scene_puzzlebattle.csv','Player_StgWin_110'):"Franklin'i kurtarmama izin ver,\\nsonra başından giderim!",
('scene_puzzlebattle.csv','Player_StgWin_112'):'G-gerçekten mi? Neyse,\\nmoralini bozma.',
('scene_puzzlebattle.csv','Player_StgWin_131'):'Suşiye olan sevgimi\\ngösterebildiğime sevindim!',
('scene_puzzlebattle.csv','Player_StgWin_140'):'Yani neredeyse vardık mı?\\nHadi, baba!',
('scene_puzzlebattle.csv','Player_StgWin_224'):'Sun-o zaten benimle\\ndaha mutlu olur!',
('scene_puzzlebattle.csv','Player_StgWin_233'):'Sana demiştim—Purrsilla artık\\nburada bile değil.',
('scene_puzzlebattle.csv','Player_StgWin_239'):'İyi deneme, ama sanırım\\nileride bir tapınak görüyorum!',
('scene_puzzlebattle.csv','Player_StgWin_252'):'Beni kandırabilirsin ama suşi\\nustalığımı aşamazsın!',
('scene_puzzlebattle.csv','Player_StgWin_258'):'Yapacağım, sağ ol!',
('scene_puzzlebattle.csv','Player_StgWin_271'):'Çünkü ben suşiye odaklanırım,\\npsişik zırvalıklara değil!',
('scene_puzzlebattle.csv','Player_StgWin_295'):'Benim kadar şımarıksın,\\nhem de bahanen yok!',
('scene_puzzlebattle.csv','Player_VsWin_Closely'):'Kıl payıydı! Bir rövanş\\nyapalım, ha?',
('scene_puzzlebattle.csv','TxtPuzzleSettlementSerifPlayer00'):'Ahh... Hep panikleyip\\nkafam karışıyor...',
('scene_puzzlebattle.csv','TxtPuzzleSettlementSerifPlayer04'):'Sağ ol! Dur, daha da mı zorlaşıyor?',
('scene_puzzlebattle.csv','TxtPuzzleSettlementSerifPlayer05'):'İyi bir bulmacayı çözmenin\\nkeyfi gibisi yok!',
('scene_puzzlebattle.csv','TxtPuzzleSettlementSerifPlayer09'):'Az kaldı; kusursuza\\nulaşacağım, merak etme!',
('stageBeginM008.csv','stageBeginM009_26'):'\\u000E\\u0000\\u0002\\u0002\\u0096Bu komik değil!\\u000E\\u0000\\u0002\\u0002d',
('stageEndM111.csv','CharaSerif_05'):'Dövüş bitti, Kodiak. Gel, otur da\\nbenimle biraz suşi ye.',
('stageEndM131.csv','CharaSerif_04'):'Benim için bu, babamla suşi\\npaylaşmaktan ibaretti.',
('stageBeginArea01Ex001.csv','CharaSerif_05'):'Şöyle yapalım—onun için seninle kapışayım!',
('stageBeginArea06sub010.csv','CharaSerif_05'):'Suşi çarpıştırıcısı mı?! Ne YAPIYORLAR?!',
('stageBeginM008.csv','stageBeginM009_03'):'Burası üssünüz mü? Peki... siz kimsiniz?',
}
for (fn,base),val in mf.items():
    for lab in [base+'_M',base+'_F',base,base+'_f']:
        if (fn,lab) in rows and rows[(fn,lab)]['eng']:
            setv(fn,lab,val,mf_reason,'TEKNİK/M-F-tutarlılık')

# ------------------------------------------------------------------
# 33 strings too verbose to fit the maximum official-language line count at 48 chars: manually shorten first.
# ------------------------------------------------------------------
def style_replace(fn,lab,new):setv(fn,lab,new,"48 karakterlik yerleşim risk taramasında bu metin, altı resmî dilin kullandığı satır sayısına sığmıyordu. Anlam/terim ve tüm kontrol kodları korunarak Türkçe kısaltıldı; dikey satır sayısı artırılmadı.",'TEKNİK/UI-yerleşim')
manual={
('stageBeginM083.csv','CharaSerif_11_M'):'Onun \\u000E\\u0000\\u0003\\u0004ﾑ＞İki Ucu Küvetli\\u000E\\u0000\\u0003\\u0004\\u0000\uff00 yeteneği\\nşeritlerini dandik küvetlerle tıkar!',
('stageEndArea08002.csv','CharaSerif_01_M'):'Geçit her gün başka bir dünyaya bağlanır.\\nHer gün yeni, zorlu bir dövüş seni bekler!',
('stageEndM126.csv','CharaSerif_03_M'):"Suşi ideallerine öyle bağlıydık ki\\nonunla İmparatorluk'a gittik!",
('stageEndM046.csv','CharaSerif_41_M'):'Bir ruh bunu kullanınca suşini kızartıp\\n\\u000E\\u0000\\u0003\\u0004ﾑ＞kalite yükseltmesi\\u000E\\u0000\\u0003\\u0004\\u0000\uff00 sağlar!',
('stageEndM093.csv','CharaSerif_01_M'):'Bu da bana bir borcun daha, Musashi!\\nSenden nefret ediyorum! Nefret! Nefret!',
('stageEndM057.csv','CharaSerif_45_M'):'Başını dik tut, Musashi! Bir hayalin var!\\nSomurtarak vakit kaybedemezsin!',
('stageBeginM041.csv','CharaSerif_11_M'):'Onun \\u000E\\u0000\\u0003\\u0004ﾑ＞İki Ucu Küvetli \\u000E\\u0000\\u0003\\u0004\\u0000\uff00yeteneği\\nşeritlerini ıvır zıvır küvetlerle tıkar!',
('stageEndM019.csv','CharaSerif_06_M'):'Bugün iyi iş çıkardın; büyük zafer bizim.\\nAma birliklerin dinlenmesi gerek.',
('homeSushibar.csv','homeSushibar_05_stone_06_M'):'Evet, sürekli! Denizde bir şey yapıyor.\\nTuhaf; orada hiçbir şey yaşamıyor, değil mi?',
('homeSushibar.csv','homeSushibar_06_b_03_M'):"Masa'ya göre senin yaşında en iyisi,\\nistediğini yapmana izin vermek.",
('homeSushibar.csv','homeSushibar_08_a_01_M'):'Sana anlattığım o \\u000E\\u0000\\u0003\\u0004ﾑ＞garip yuvarlak taş\\u000E\\u0000\\u0003\\u0004\\u0000\uff00 var ya;\\nüstünde çiçek deseni varmış. Çok güzelmiş.',
('homeSushibar.csv','homeSushibar_12_d_04_M'):'Belki de fikrimi değiştirme vakti geldi.\\nBir ton balığı! İnsana karakter kazandırır!',
('chapterBeginM007.csv','CharaSerif_04_M'):'Hrrrh. Sıkı saklanan bir sır gerçekten.\\nNereden başlayacağımı ben bile bilmiyorum.',
('database_cmn.csv','StarGet_WinLastAtk'):'Bitirici saldırıyla en az %d hasar verip kazan.',
('database_cmn.csv','StarGet_WinAutoShootLess'):'En fazla %d otoatış saldırısıyla kazan.',
('stageBeginM062.csv','CharaSerif_02_M'):'Hıh. Büyük, daha iyi demek değil.\\nİmparatorluk gibi bunu da parçalayacağım!',
('stageBeginM062.csv','CharaSerif_02_F'):'Hıh. Büyük, daha iyi demek değil.\\nİmparatorluk gibi bunu da parçalayacağım!',
('stageEndM001.csv','stageEndM001_06_M'):'Hayır. Katalog, listeler derlemesidir.\\nBurada suşi ruhlarıyla suşiler listelenir.',
('stageBeginArea06sub010.csv','CharaSerif_05_F'):'Suşi çarpıştırıcısı mı?! Ne YAPIYORLAR?!',
('ShrineGetMode.csv','Catten_AlreadyFriend1_M'):"Öyle mi? Bu ruh çooook tanıdık...\\nYerine \\u000E\\u0000\\u0003\\u0004쳿ＯSuşi Özü \\u000E\\u0000\\u0003\\u0004\\u0000\uff00'ümü vereyim.",
('homeKoziin.csv','homeKoziin_useful_00_03_M'):'Onlarla hemen kullanacağın bir suşi ruhuna\\nseviye atlatabilirsin.',
('stageBeginM008.csv','stageBeginM009_03_F'):'Burası üssünüz mü? Peki... siz kimsiniz?',
('eventBeginM002.csv','CharaSerif_11_M'):"Tüm suşi ruhları İmparatorluk'un!\\nBirini öylece yanında gezdiremezsin!",
('stageEndM092.csv','CharaSerif_03_M'):'Purrsilla bir zamanlar somon ve ton balığı\\ngibi kırmızı etli suşilere bayılırdı.',
('stageEndM092.csv','CharaSerif_06_M'):'Yaralanınca Purrsilla, eskiden sevdiği\\nsomonla ton balığına bakamaz oldu.',
('stageBeginM003.csv','stageBeginM004_04B_M'):"Franklin'i mi arıyorsun? Boşuna.\\nŞimdiye İmparatorluğun yarı yolundadır!",
('stageBeginM003.csv','stageBeginM004_11_M'):"O dangalağı ispiyonlayıp İmparatorluk\\nOrdusu'na girdim! Peki ne alıyorlar?",
('stageEndM051.csv','CharaSerif_01_M'):'Ucuz bir zafer kazandın, ne olmuş?!\\nNumaralarını çözdüm. Bir dahaki sefere benimsin!',
('stageBeginM013.csv','CharaSerif_08_M'):'Fikrini değiştirmek için geç değil.\\nİmparatorluğun insana hep ihtiyacı var.',
('stageBeginM121.csv','CharaSerif_03_M'):'Duvardaki sayı! Hasar vermek için\\n\\u000E\\u0000\\u0003\\u0004쳿Ｏen az o kadar yüksek\\u000E\\u0000\\u0003\\u0004\\u0000\uff00 bir yığın fırlat!',
('stageBeginArea01Ex001.csv','CharaSerif_05_F'):'Şöyle yapalım—onun için seninle kapışayım!',
('stageEndM083.csv','CharaSerif_01_M'):'Bugün KAZANMANA İZİN verdiğim için kazandın.\\nBir daha bu kadar nazik olmam!',
('database_sushiInfo.csv','SushiInfo_Tamago'):'Kat kat omlet dilimleri, nazikçe\\npofuduk pirinç yastıklarına konar.',
('stageEndM126.csv','CharaSerif_02_M'):"Biz Elit Birlik askerleri, General'e\\nJubay olduğu günlerden beri hizmet ederiz.",
('stageBeginM011.csv','CharaSerif_04_M'):'Takım arkadaşlarımla aynı\\n\\u000E\\u0000\\u0003\\u0004ﾑ＞Gizli Tabak Hilesi\\u000E\\u0000\\u0003\\u0004\\u0000\uff00 bende de var.',
('stageEndM003.csv','stageEndM004_22_M'):"Kojiro'nun raporu yayılacak; beni sınamak\\nisteyen İmparatorluk askerleri gelecek.",
('stageEndM078.csv','CharaSerif_05_M'):'Vay, ne sıkı aşıklardı! Bazı mengeneler bile\\nbu kadar sıkı tutmaz!',
('homeSushibar.csv','homeSushibar_10_in_02_M'):'Son zamanlarda burası dar geliyordu.\\nYine genişletme vakti!',
('homeSushibar.csv','homeSushibar_11_f_03_M'):"Duyduğuma göre gizli aşamalarda bulup\\nBulmaca Maçları'nda kazanabiliyorsun.",
('chapterBeginM007.csv','CharaSerif_14_M'):'Şaka değil! Hem orada beyni yıkananlar\\nyalnız askerler değilmiş, anlıyor musun?',
('chapterEndM003.csv','CharaSerif_26_M'):'Ama oraya varmak için İmparatorluğun üç\\ngeneralinden birinin toprağından geçmeliyiz.',
('stageBeginM136.csv','CharaSerif_04_M'):'Ta buralara, bizim gibi küçük insanlarla\\noyun oynamaya mı geldin? Zahmet etmezdin!',
('stageBeginArea06Ex006.csv','CharaSerif_05_M'):'Hıyah! Madem öyle, birkaç tekrar yapayım.\\nKasıp şovun kötü zamanı olmaz!',
('chapterBeginM009.csv','CharaSerif_25_M'):'Savaşta hayalinin peşinden giderken\\nbabanın hayalini de unutma.',
('stageBeginArea01Ex004.csv','CharaSerif_03_M'):'Bağ kurarken yolundaki tüm tabakları\\nyok saymanı sağlayan harika bir yetenek!',
('stageEndM036.csv','CharaSerif_03_M'):'Sorduğuna ÇOOOK sevindim! Burası harika!\\nKepçebeyler ve cinhanımlar, karşınızda...',
('eventBattleM001.csv','EventBattleM001_17_M'):'Ama tabakları bağlamak için sadece 7 saniye.\\nSonra parmaklarından kayıp giderler.',
('stageEndM031.csv','CharaSerif_06_M'):"İnanılmaz efendim! İmparatorluk birlikleri\\nCumhuriyet'ten tamamen püskürtüldü!",
('eventBeginM002.csv','CharaSerif_15_M'):"Evet! Franklin'in yanındayım!\\nİmparatorluk ne isterse istesin, ben yokum!",
('stageBeginM021.csv','CharaSerif_07_M'):'...Yeteneğime göndermeydi. Onu\\n\\u000E\\u0000\\u0003\\u0004ﾑ＞Düşman Verisi ekranı\\u000E\\u0000\\u0003\\u0004\\u0000\uff00ndan görebilirsin. Pardon.',
('stageBeginM072.csv','CharaSerif_16_M'):"Gourai'yi İmparatorluk Majesteleri verdi.\\nGücü Jinrai'yle rahatça boy ölçüşür.",
('stageBeginM072.csv','CharaSerif_23_M'):"Efsaneye göre Gourai'yle Jinrai'yi tutan\\ndünyadaki tüm suşiyi kontrol eder.",
('stageBeginM130.csv','CharaSerif_09_M'):'Ama öbür yolun daha kötü olmasından korktum.\\nBenim hayatımın kurbanı olmanı istemedim.',
('stageEndArea05Ex004.csv','CharaSerif_02_M'):'Epey umut vadediyorsun. Karar vermeden önce\\nseni biraz daha dövüşürken göreyim!',
('stageBeginArea08002.csv','CharaSerif_06_M'):'Işık hızındaki suşileri çarpıştırıp enerjiyle\\nsuşi dünyasına kapı açmaya ÇALIŞTILAR.',
}
for k,v in manual.items():style_replace(*k,v)

# ------------------------------------------------------------------
# Rebalance line breaks in remaining >48 rows WITHOUT increasing maximum official-language line count.
# ------------------------------------------------------------------
ctrl=re.compile(r'\\u[0-9A-Fa-f]{4}')
def vis(s):
    s=ctrl.sub('',s);return ''.join(c for c in s if ord(c)>=32 and not 0xE000<=ord(c)<=0xF8FF and not 0xFF00<=ord(c)<=0xFFEF)
def vlen(s):return len(vis(s))

def partition(text,n,width=48):
    toks=text.replace('\\n',' ').split()
    if not toks:return text
    lens=[vlen(t) for t in toks]
    if max(lens)>width:return None
    # prefix visible including one space per join
    N=len(toks)
    @lru_cache(None)
    def dp(i,k):
        if i==N:return (0,[]) if k>=0 else None
        if k==0:return None
        best=None;line=''
        for j in range(i,N):
            cand=' '.join(toks[i:j+1]);L=vlen(cand)
            if L>width:break
            rem=dp(j+1,k-1)
            if rem is None:continue
            # minimize max line, then raggedness; allow fewer than k lines through base i==N
            cost=max(L,rem[0])
            score=(cost,abs(width-L)+(0 if not rem[1] else 0))
            val=(score[0],[cand]+rem[1])
            if best is None or (val[0],sum((width-vlen(x))**2 for x in val[1])) < (best[0],sum((width-vlen(x))**2 for x in best[1])):best=val
        return best
    z=dp(0,n)
    if z is None:return None
    return '\\n'.join(z[1])

layout_reason="Görünür metin 48 karakterlik güvenli satır eşiğini aşıyordu, fakat toplam metin resmî yerelleştirmelerin kullandığı satır sayısına sığıyor. Sözcükler ve kontrol kodları değiştirilmeden yalnız satır kırımları yeniden dengelendi; satır sayısı artırılmadı."
layout_count=0;failed=[]
for fn,(fields,rs) in files.items():
    for r in rs:
        cur=r['tur']; lines=cur.split('\\n')
        if max([vlen(x) for x in lines] or [0])<=48:continue
        n=max(len(lines),max(len((r[l] or '').split('\\n')) for l in ['deu','eng','esp','fra','ita','nld']))
        new=partition(cur,n,48)
        if new is None or max(vlen(x) for x in new.split('\\n'))>48:
            failed.append((fn,r['label'],max(vlen(x) for x in lines),n,cur))
        elif new!=cur:
            if setv(fn,r['label'],new,layout_reason,'TEKNİK/UI-satır-kırımı'):layout_count+=1

# Final strict layout check
remaining=[]
for fn,(fields,rs) in files.items():
    for r in rs:
        for i,line in enumerate(r['tur'].split('\\n'),1):
            if vlen(line)>48:remaining.append((fn,r['label'],i,vlen(line),line))
if failed or remaining:
    print('LAYOUT FAILED',len(failed),len(remaining));print(failed[:20]);print(remaining[:20]);raise SystemExit(3)

# Write CSVs
for fn,(fields,rs) in files.items():writecsv(CSV/fn,fields,rs)
# refresh reports
writecsv(R/'V10_YENI_DEGISIKLIKLER.csv',change_fields,changes)
review_fields=['round','file','label','index','previous_review_status','previous_decision','decision','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
writecsv(R/'V10_DERIN_KALITE_VE_TEKNIK_INCELEME.csv',review_fields,review)
master_fields=['file','label','index','review_status','decision','eng','deu','esp','fra','ita','nld','old_tur','current_tur','reason']
writecsv(R/'TUM_10676_SATIR_DURUMU.csv',master_fields,master)
# combined: rebuild from previous v09 + latest v10 changes to avoid duplicate v10 entries
prev9=readcsv(ROOT/'review_v09'/'INCELEME_DEGISIKLIKLERI.csv');combined=prev9+changes
writecsv(R/'INCELEME_DEGISIKLIKLERI.csv',change_fields,combined)
latest={}
for x in combined:latest[(x['file'],x['label'])]=x
writecsv(R/'INCELEME_SON_DURUM_ESSIZ.csv',change_fields,list(latest.values()))
# cumulative update
cum=readcsv(ROOT/'review_v09'/'SATIR_BAZLI_INCELEME_KUMULATIF.csv');cm={(x['file'],x['label']):x for x in cum}
for v in review:
    cm[(v['file'],v['label'])]={'round':'v0.10','file':v['file'],'label':v['label'],'index':v['index'],'decision':v['decision'],'eng':v['eng'],'deu':v['deu'],'esp':v['esp'],'fra':v['fra'],'ita':v['ita'],'nld':v['nld'],'old_tur':v['old_tur'],'new_tur':v['new_tur'],'reason':v['reason']}
cum_fields=['round','file','label','index','decision','eng','deu','esp','fra','ita','nld','old_tur','new_tur','reason']
writecsv(R/'SATIR_BAZLI_INCELEME_KUMULATIF.csv',cum_fields,list(cm.values()))
# new-change warning should now be 0
writecsv(R/'V10_YENI_DEGISIKLIK_UZUNLUK_UYARILARI.csv',['file','label','line_no','visible_len','line'],[])
# M/F consistency detail report will be regenerated after build

# Rebuild cleanly
newreb=R/'rebuilt_title_final'
if newreb.exists():shutil.rmtree(newreb)
subprocess.run([sys.executable,str(TOOL),'import','--csv',str(CSV),'--patch',str(R/'rebuilt_title'),'--out',str(newreb)],check=True)
subprocess.run([sys.executable,str(TOOL),'validate','--source',str(SOURCE),'--patch',str(newreb)],check=True)
newverify=R/'verify_csv_final'
if newverify.exists():shutil.rmtree(newverify)
subprocess.run([sys.executable,str(TOOL),'export','--source',str(SOURCE),'--patch',str(newreb),'--out',str(newverify)],check=True)
# exact compare
mis=[];total=0
for p in CSV.glob('*.csv'):
 with p.open(encoding='utf-8-sig',newline='') as f1,(newverify/p.name).open(encoding='utf-8-sig',newline='') as f2:
  aa=list(csv.DictReader(f1));bb={x['label']:x for x in csv.DictReader(f2)}
  for r in aa:
   total+=1;x=bb.get(r['label'])
   if not x or x['tur']!=r['tur']:mis.append((p.name,r['label']))
if mis:raise SystemExit('roundtrip mismatch '+str(mis[:10]))
# replace dirs
shutil.rmtree(R/'rebuilt_title');newreb.rename(R/'rebuilt_title')
shutil.rmtree(R/'verify_csv');newverify.rename(R/'verify_csv')
# Copy finalize tool
shutil.copy2(Path(__file__),R/'Araclar'/'v10_son_teknik_yerlesim_kontrolu.py');py_compile.compile(str(R/'Araclar'/'v10_son_teknik_yerlesim_kontrolu.py'),doraise=True)

# Rebuild bundle from scratch
bundle=R/'bundle'
if bundle.exists():shutil.rmtree(bundle)
bundle.mkdir();shutil.copytree(CSV,bundle/'CSV');shutil.copytree(R/'Araclar',bundle/'Araclar',ignore=shutil.ignore_patterns('__pycache__'))
shutil.copytree(R/'rebuilt_title',bundle/'LayeredFS'/'00040000001C1D00')
rap=bundle/'Raporlar';rap.mkdir()
for name in ['V10_DERIN_KALITE_VE_TEKNIK_INCELEME.csv','V10_YENI_DEGISIKLIKLER.csv','V10_YENI_DEGISIKLIK_UZUNLUK_UYARILARI.csv','SATIR_BAZLI_INCELEME_KUMULATIF.csv','TUM_10676_SATIR_DURUMU.csv','INCELEME_DEGISIKLIKLERI.csv','INCELEME_SON_DURUM_ESSIZ.csv']:
 shutil.copy2(R/name,rap/name)
readme=(bundle/'README_TR.txt')
readme.write_text(f'''Sushi Striker Türkçe yama v0.10 — derin kalite + teknik bütünlük FINAL\n\n- 243 MSBT / 243 çok dilli CSV\n- 10.676 satır master karar/gerekçe raporu\n- Bağımsız MSBT teknik doğrulayıcı\n- Kontrol komutu, runtime değişkeni, surrogate parametresi, görünür-boş satır ve M/F tutarlılık onarımları\n- UI satır-kırımı güvenlik geçişi: 48 görünür karakter üstü satır bırakılmadı; resmî dillerin satır kapasitesine göre yeniden dengelendi.\n- v0.10 toplam değişen benzersiz satır: {len(changes)}\n''',encoding='utf-8')
# zips
layer=R/'Sushi_Striker_TR_v10_LayeredFS.zip';tools=R/'Sushi_Striker_TR_v10_Araclar.zip';full=R/'Sushi_Striker_TR_v10_FULL.zip'
with zipfile.ZipFile(layer,'w',zipfile.ZIP_DEFLATED) as z:
 for p in (R/'rebuilt_title').rglob('*'):
  if p.is_file():z.write(p,Path('LayeredFS')/'00040000001C1D00'/p.relative_to(R/'rebuilt_title'))
with zipfile.ZipFile(tools,'w',zipfile.ZIP_DEFLATED) as z:
 for p in (R/'Araclar').rglob('*.py'):z.write(p,p.relative_to(R/'Araclar'))
# preliminary manifest/full for validator full check
manifest=[]
for p in sorted(bundle.rglob('*')):
 if p.is_file() and p.name!='DOSYA_MANIFESTOSU_SHA256.txt':manifest.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(bundle)).replace('\\','/'))
(bundle/'DOSYA_MANIFESTOSU_SHA256.txt').write_text('\n'.join(manifest)+'\n',encoding='utf-8')
with zipfile.ZipFile(full,'w',zipfile.ZIP_DEFLATED) as z:
 for p in bundle.rglob('*'):
  if p.is_file():z.write(p,p.relative_to(bundle))
# final validator
validator=R/'Araclar'/'msbt_technical_validator.py';trep=R/'V10_TEKNIK_DOGRULAMA.csv';tsum=R/'V10_TEKNIK_DOGRULAMA_OZETI.txt'
subprocess.run([sys.executable,str(validator),'--source',str(SOURCE),'--patch',str(R/'rebuilt_title'),'--csv',str(CSV),'--roundtrip',str(R/'verify_csv'),'--layer-zip',str(layer),'--full-zip',str(full),'--report',str(trep),'--summary',str(tsum)],check=True)
shutil.copy2(trep,rap/trep.name);shutil.copy2(tsum,rap/tsum.name)
# roundtrip summary
summ=f'CSV/MSBT dosyaları: 243\nToplam etiket: {total}\nv0.10 toplam değişen satır: {len(changes)}\nCSV→MSBT→CSV farkı: {len(mis)}\n48+ görünür satır: {len(remaining)}\n'
(R/'ROUNDTRIP_DOGRULAMA.txt').write_text(summ,encoding='utf-8');shutil.copy2(R/'ROUNDTRIP_DOGRULAMA.txt',rap/'ROUNDTRIP_DOGRULAMA.txt')
# final manifest and full zip
manifest=[]
for p in sorted(bundle.rglob('*')):
 if p.is_file() and p.name!='DOSYA_MANIFESTOSU_SHA256.txt':manifest.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(bundle)).replace('\\','/'))
(bundle/'DOSYA_MANIFESTOSU_SHA256.txt').write_text('\n'.join(manifest)+'\n',encoding='utf-8')
with zipfile.ZipFile(full,'w',zipfile.ZIP_DEFLATED) as z:
 for p in bundle.rglob('*'):
  if p.is_file():z.write(p,p.relative_to(bundle))
print('FINAL DONE',len(changes),'layout reflow',layout_count,'roundtrip',len(mis),'remaining long',len(remaining))
