#!/usr/bin/env python3
"""Cave Story 3D TR v6 - elle yapılan sahne/satır kalite düzeltmeleri.

Bu araç otomatik çeviri yapmaz. İngilizce ROMFS ile Türkçe v5 satırları tek tek
karşılaştırılarak verilen kararları yeniden üretilebilir biçimde uygular.
SJS komutları değiştirilmez; yalnızca komutlar arasındaki görünür metin parçaları
ve açıkça seçilmiş terimler düzeltilir.
"""
from pathlib import Path
import re, sys

CMD = re.compile(r'<[A-Z0-9+\-]{3}(?:[0-9:+\-]+)?')
ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / '000400000004D200/romfs/data'

# file -> {split-text-index: manually reviewed Turkish body}
P = {
'armsitem.sjs': {
  9: 'YILAN\r\nDuvarların içinden ateş eder!\r\nChaba tarafından Labirent\r\nDükkânı’nda yapıldı.',
  33: 'KILIÇ\r\nTek vuruşluk bir mermi fırlatır.\r\nKing’in ruhunu taşır.',
  73: 'Jenka’nın köpeklerinden biri ve usta\r\nbir hazine avcısı. Sandıklara bayılır;\r\nbulduğu sandıklarda uyumayı ÇOK sever.',
  154: 'Can İksiri',
  202: 'Denetleyici',
  344: 'Kuşanmak ister misin?',
  356: 'Hasar aldığında kaybettiğin silah\r\nenerjisi yarıya iner.',
  373: 'Havadayken zıplama tuşuna basarak\r\ndört yönden birine doğru hızlanabilirsin.',
  494: 'Kuşanmak ister misin?',
  511: 'Kuşanmak ister misin?',
  523: 'Çıkarmak ister misin?',
  533: 'Çıkarmak ister misin?',
  543: 'Çıkarmak ister misin?',
  553: 'Çıkarmak ister misin?',
},
'stage/almond.sjs': {
  137: 'Almak ister misin?',
  179: 'Her yer patlama kapısıyla dolu.',
  180: 'Bunca güvenlik önleminin\r\narkasında bir şey olmalı.',
  201: 'Çekme Halatını kullanmak ister misin?',
  209: "Çekme Halatını Curly’nin etrafına sardın.",
  361: 'Beni çarpan cadı bu!',
  456: "Jenka’nın küçük bir erkek kardeşi\r\nolduğunu biliyor muydun?",
  458: 'Ablası gibi onun da hayal gücünü aşan\r\nbüyü güçleri vardı...',
},
'stage/ballo1.sjs': {
  41: 'Çok, çok uzun zaman önce,\r\nbüyü gücüne duyduğum hırsı\r\nhiçbir bedelden korkmadan',
  42: 'dizginsizce büyüttüm.',
  44: 'Öyle güçlü bir büyüydü ki\r\nonu yaratan ben bile\r\nkontrol edemiyordum...',
  46: 'Bu güç öylesine öfkeli ve\r\ndurdurulamazdı ki...',
  47: '...alevleri bana hayran olan\r\nçocuğu yuttu,',
  48: 've\r\nbeni seven eşimi...',
  50: 'Alevlerin içinde kaldılar ve\r\nkorkunç acılar çektiler.',
  51: '...Hepsi benim bencilce\r\ngünahım yüzünden.',
  55: 'O zaman elimden yalnızca gülmek geldi...',
  57: 'Jenka beni mühürledi;\r\nama büyüm geçen her dakika\r\ndaha da şiddetleniyordu.',
  59: 'Bunu çok uzun zamandır bekliyordum...',
  61: 'Bu korkunç büyü öfkeme\r\nson verecek kişiyi...',
},
'stage/ballo2.sjs': {
  40: 'Pek anlamıyorum ama...\r\nNeyse. Belki buradaki işimiz\r\nsonunda bitti.',
  54: 'SICAK... Ç--ÇOK SICAK...',
  95: 'İkimiz de burada\r\nezilip gideceğiz!',
  116: 'Sıkıca tutun!!',
  152: 'Biraz hırpalandı...',
},
'stage/barr.sjs': {
  137: "Sue ile ben iyi anlaşınca\r\nKing’in tepesi atıyor.",
  178: 'Usta bir tazı kadar\r\nkeskin burnum var!',
  189: 'Evet, hem köpek burnu VAR,\r\nhem de köpek beyni.',
  194: 'Onu önce ben buldum!',
  230: 'BEN SUE DEĞİLİM!',
  240: 'HEP ben ortalığı topluyorum!',
  247: 'Şu ufacık silahla\r\nbenimle dövüşmek mi istiyorsun?',
},
'stage/blcny2.sjs': {
  58: 'Hata ayıklamada iyi iş çıkardın!\r\nİlerisi hâlâ yapım aşamasında...',
  65: 'Buradan sonrası uçurum!',
},
'stage/cemet.sjs': {
  37: 'Herhalde ondandır;\r\nuzun zamandır eve gitmedim.',
},
'stage/cent.sjs': {
  254: 'Sen katil bir robotsun!!',
  417: 'Saklanmanın faydası yoktu.\r\nRoket de ben olmadan\r\nasla tamamlanamazdı!',
  487: "Lütfen rokete bin\r\nve Doktor’un tahtına doğru acele et.",
  492: 'Şiddetle su fışkırıyor.',
  501: 'Şiddetle su fışkırıyor.',
  564: 'Tüküren Silah Balığına dikkat!\r\nNot: Onları basamak olarak\r\nkullanabilirsin.',
},
'stage/chako.sjs': {
  103: "Şu ödlek Santa’yla\r\ntanıştın mı?",
  110: 'En büyüğünün peşine düş.',
},
'stage/clock.sjs': {
  39: "Sayaç 290'ı aldın.",
  48: 'Bu sayacı sana sunuyorum,\r\nmeydan okuyan kişi.',
  49: 'Kararlılığını görmek istiyorum.',
  51: 'Elinden geleni göster!',
},
'stage/comu.sjs': {
  71: 'Diğeri Mimiga\r\nMezarlığı’nın içinde.',
  78: 'Bu adanın korkunç yaratığı.\r\nMimigaları birbiri ardına\r\nyiyip bitirirdi...',
  84: 'Ada uğruna kendini tehlikeye\r\natması büyük cesaretti.',
  116: 'Baloncuk alındı.',
},
'stage/cthu.sjs': {
  39: 'Ne?\r\nHafızanı mı kaybettin?\r\nHeh heh...',
},
'stage/curly.sjs': {
  58: 'Lanet kalkmadan\r\nGüneş Taşlarını oynatamazsın.',
  64: 'Şöyle lezzetli bir balık yemek\r\nistiyorum.\r\nNyaa!',
  126: 'Tamamen zararsızlar!!',
  275: 'Sen de Mimigaların tarafındasın,\r\nöyle mi?',
},
'stage/curlys.sjs': {
  57: "Curly’nin İç Çamaşırını buldun.",
},
'stage/drain.sjs': {
  94: 'Anahtarı çevirdin.',
},
'stage/egg1.sjs': {
  34: 'Kimlik Kartını yerleştirdin.',
},
'stage/eggr2.sjs': {
  54: 'Soğuk bir esinti geçiyor...',
},
'stage/eggx.sjs': {
  139: 'Görünüşe göre bu yumurtayı\r\nçatlatmak için bir şifre lazım.',
  182: 'Uçan Ejderha Yumurtası No. 00\r\nKuluçka hazırlıkları tamamlandı.',
},
'stage/eggx2.sjs': {
  98: 'İhtiyacım olan Uçan Ejderha\r\nsağ salim yumurtadan çıksın diye.',
  111: 'Biliyorum... Yapacak bir şey yok.',
},
'stage/fall.sjs': {
  44: 'Barış sürüyor.',
  92: 'Misery ve ben artık kimsenin\r\nemrini dinlemek zorunda değiliz.',
  146: 'Nerede yaşayacağımızı\r\nsen seçebilirsin!',
},
'stage/frog.sjs': {
  102: 'Güzel. O zaman bu asker\r\nsenin işin.',
  106: 'Bu sefer kesin işini bitir,\r\nsonra geri gel.',
},
'stage/gard.sjs': {
  83: 'Yüce Doktor...',
  233: 'Sen, yüzeyden gelen\r\nşu inatçı askersin!',
  238: 'Hepsi senin.\r\nBenden küçük bir hediye!',
  282: 'Benim... intikamımı alır mısın?',
  295: 'Kılıcı aldın.',
},
'stage/hell1.sjs': {
  90: "Jenka’nın küçük bir erkek kardeşi\r\nolduğunu biliyor muydun?",
  92: 'Ablası gibi onun da hiçbir insanda\r\nbulunmayan büyü güçleri vardı.',
  102: 'Onu sever ve ona güvenirlerdi,',
},
'stage/tt_hell1.sjs': {
  90: "Jenka’nın küçük bir erkek kardeşi\r\nolduğunu biliyor muydun?",
  92: 'Ablası gibi onun da hiçbir insanda\r\nbulunmayan büyü güçleri vardı.',
  102: 'Onu sever ve ona güvenirlerdi,',
},
'stage/hell2.sjs': {
  54: 'Ballos, bu cezayla katıksız ve\r\nkontrol edilemez bir öfkeye sürüklendi.',
  56: 'Kral ve krallık, Ballos’un kontrolden\r\nçıkan büyü gücü tarafından yutuldu.',
},
'stage/tt_hell2.sjs': {
  54: 'Ballos, bu cezayla katıksız ve\r\nkontrol edilemez bir öfkeye sürüklendi.',
  56: 'Kral ve krallık, Ballos’un kontrolden\r\nçıkan büyü gücü tarafından yutuldu.',
},
'stage/hell3.sjs': {
  175: "Jenka’nın cadı kızı Misery,\r\nŞeytan Tacı’nın ortaya çıkmasının\r\nsorumlusudur...",
},
'stage/tt_hell3.sjs': {
  175: "Jenka’nın cadı kızı Misery,\r\nŞeytan Tacı’nın ortaya çıkmasının\r\nsorumlusudur...",
},
'stage/hell42.sjs': {
  131: "Şeytan Tacı, Ballos’un kalbi attığı\r\nsürece sonsuz kez\r\nyeniden oluşacak...",
},
'stage/tt_hell42.sjs': {
  131: "Şeytan Tacı, Ballos’un kalbi attığı\r\nsürece sonsuz kez\r\nyeniden oluşacak...",
},
'stage/jail1.sjs': {
  50: 'Süren deneylerinde\r\ndeneğe çevrilmek üzere.',
},
'stage/jail2.sjs': {
  60: "Doktor’un canı cehenneme!",
},
'stage/jenka1.sjs': {
  91: 'Ha!',
  140: 'Yine bir aptal\r\naynı şeyin peşinde demek.',
  148: 'Ama şu bacaklarım\r\npek güçsüz.',
  158: 'Kusura bakma,\r\nama kalanlarını da\r\nbulur musun?',
  202: 'Mimigaları savunmaya çalışan\r\ncesur insanları da\r\nöldürdüler.',
  205: '...köşeye sıkışan Mimigalar\r\ntamamen kudurdu.',
  248: 'Ancak o zaman\r\nrobot taburlarına\r\nkarşı koydular.',
  288: 'Benim köpeklerim de\r\nbaş belalarını sevmez...',
},
'stage/jenka2.sjs': {
  78: 'Kırmızı çiçeğin kudurttuğu\r\nMimigaları yeryüzüne salacaklar.',
  93: 'Kullanırsan canın tamamen yenilenir,',
  94: 'ama yalnızca bir kez.',
  103: 'Kırmızı çiçeğin kudurttuğu\r\nMimigaları yeryüzüne salacaklar.',
},
'stage/little.sjs': {
  32: 'Güzel kılıçmış.\r\nBenim şahane tabancamla\r\ntakas etmek ister misin?',
  37: 'Kılıcı ona verdin.',
  53: 'Tahmin etmiştim!',
  54: 'Bilmek güzel.',
  59: 'Peki, kılıcını geri al...',
  68: 'Kılıcı geri aldın!',
},
'stage/lounge.sjs': {
  35: 'Bunlar fıskiyeler.',
  87: 'Robotlar mı?!?\r\nUMURUMDA DEĞİL!!!',
},
'stage/malco.sjs': {
  45: 'Fan güç kaynağı devre dışı.',
  46: 'Malco güç kaynağı devre dışı.',
  48: 'Güç açılsın mı?',
  170: 'Beni kurtardığın için sağ ol!',
  172: 'Minnettarlığımı göstermek için\r\nsana bir şey yapmak istiyorum!',
  203: 'Bomba için şu malzemeleri bul:',
  254: 'Yine gel lütfen...',
  262: 'Burada yapayalnız kalıyorum.',
},
'stage/mapi.sjs': {
  43: 'Benimle işin falan yok!',
  104: 'Yakaladın!',
},
'stage/mazea.sjs': {
  54: 'Bu adanın dışını hiç gördün mü?',
  146: 'Hıh!!!',
  169: 'Turboşarj alındı.',
  174: 'Bedava, para istemiyorum.',
  210: 'Ama Gaudilerin hafızası zayıf;\r\nneyi koruduğumuzu bile unutuyoruz.\r\nÖzür!',
},
'stage/mazeb.sjs': {
  115: 'Belki de bu şanssızlığın\r\niçinden bir şans doğdu.',
  139: 'Havadayken zıplama tuşuna\r\nbasılı tutarak havada kalabilirsin.',
  141: "Booster’ı takıp çıkarmak için\r\nAlt Ekran’ı kullan.",
},
'stage/mazeo.sjs': {
  131: 'Sen bile onları\r\nyenemedin demek.',
  138: 'Kendimden hayal kırıklığına uğradım.',
  146: 'Şimdiye kadar bir şekilde\r\nhayatta kaldım ama...',
  140: 'Bu beden bu hâldeyken...',
  176: 'Silah Kalkanı alındı.',
},
'stage/mazes.sjs': {
  71: 'Bunca zamandır\r\nburaya gelmeni bekliyordum.',
  78: 'O zaman şu\r\nkayayı kenara çekelim.',
  91: 'Tabii ki korkmuyorsun!',
  184: 'Unutma, efendiye sen de\r\nbenim gibi karşı gelemezsin.',
  187: 'Bu işi burada bitiriyorum!',
  215: 'SİZ İKİNİZ BENİ HİÇ\r\nDİNLİYOR MUSUNUZ!?!?!?!?',
  241: 'Biraz daha uca yakın\r\ntutamaz mısın?',
},
'stage/mimi.sjs': {
  149: 'Her zaman keşfetme duygunu\r\nkoruduğun sürece,',
  267: 'Hayııır!',
  415: "Yukarı: Yamashita Çiftliği\r\nSol: Rezervuar   Sağ: Mezarlık\r\nAşağı: Arthur’un Evi",
},
'stage/momo.sjs': {
  74: 'Sevindim...',
  78: "Doktor’un yanında çalışmayı\r\ngöze aldım.",
  80: 'Beni apar topar adadan aşağı attılar.\r\nPek nazikçe sayılmaz...',
  152: 'Bir kahramandan da bu beklenir.',
  189: 'Roketi bitirebilmem için\r\nen azından biraz elektriğe ihtiyacım var.',
  197: 'Roketi bitirebilmem için\r\nen azından biraz elektriğe ihtiyacım var.',
  267: 'O burada bana yardım etmeden\r\nanaliz yapmak zor olacak.',
},
'stage/oside.sjs': {
  118: 'Kaçtıktan sonra sen ve Kazuma,\r\ndağların güvenli koynunda,\r\ngözlerden uzakta\r\nmütevazı bir hayat sürdünüz...',
  135: 'Sanırım sıradaki bölümü\r\nson bölüm yapacağım.',
},
'stage/pens1.sjs': {
  75: '"Kazuma: ama söyleyeyim, o noktaya\r\ngelirsem gerçekten yerim..."',
  334: 'Henüz ele geçiremedi,',
  335: 'ama ele geçirmesi\r\nan meselesi...',
  403: 'Adayı araştırmak için\r\naramızdaki en uygun kişi sensin.',
  420: 'Bunu şimdiye kadar\r\nhiç fark etmemiştim.',
},
'stage/pens2.sjs': {
  57: 'Sue: Neredeyse çatlayacak\r\nbir tane buldum.',
},
'stage/pixel.sjs': {
  72: 'Defteri açmak ister misin?',
  137: "Curly’deki suyu boşaltmak\r\nister misin?",
  155: 'Güvendesin!',
  163: 'Bu yüzden hava tüpümü sana verdim.\r\nİşe yaradı, değil mi?',
},
'stage/pole.sjs': {
  110: 'Saçmalamamı bağışla.',
  112: 'Şöyle yapalım,',
  140: 'Üretenlerle, başkalarının\r\nürettiklerinden yararlananlar arasında.',
  144: 'Şimdi, senin sayende bunu yaşadım.',
  152: '"Çıkış."',
},
'stage/pool.sjs': {
  55: 'Oradaki rezervuara düştü.',
  68: 'Bir şey ışıl ışıl parlıyor...',
  73: 'Gümüş Kolye alındı.',
},
'stage/prefa1.sjs': {
  35: 'Havada hareketi destekleyen bir cihaz\r\nolursa adayı daha ayrıntılı\r\nincelemek mümkün.',
  37: 'Bu amaçla Booster roketini\r\ngeliştirmeye başlayacağım.',
  39: 'Bu hava aracını iki aşamada\r\ngeliştireceğim: Booster v0.8 ve v2.0.',
  41: 'İlk hedefim, takılabilen ve havada\r\nitiş sağlayan v0.8’i tamamlamak.',
  44: 'v2.0 ise çok daha kullanışlı olacak.',
},
'stage/ring1.sjs': {
  154: 'Gerçekten inatçısın.',
  162: 'Bil ki, bu ada konusunda\r\nhiçbir pişmanlığım yok.',
},
'stage/ring2.sjs': {
  127: 'Sen o zamanki robotlardan birisin...',
  131: 'Dikkat!\r\nArkanda!!!',
},
'stage/ring3.sjs': {
  89: 'Bir robota göre insana özgü\r\nduyguların var.',
  157: 'Bu hâlim dehşet verici mi?',
},
'stage/sand.sjs': {
  103: 'Kum Bölgesi Deposu: DOĞU',
  131: 'Ama...\r\nBuraya kadar gelmiş olman\r\nbiraz can sıkıcı.',
  134: 'Benimle kapışmak mı istiyorsun?',
},
'stage/sande.sjs': {
  66: "Seni Labirent’e gönderiyorum.",
},
'stage/santa.sjs': {
  44: "Denizanası Suyu’nu\r\nkullanmak ister misin?",
  76: 'Sana bir şey vermek istiyorum.',
  108: 'Ardından sanki biri\r\nçığlık attı...',
},
'stage/shelt.sjs': {
  109: 'Demek Sue’nun yerine\r\nbeni almaya sen geldin.',
  329: 'Kazuma: Uçan Ejderha yumurtalarından\r\nçıkmaya hazır olan var mı?',
},
'stage/weed.sjs': {
  150: "Santa’nın Anahtarını aldın.",
  380: 'Su almaya gitmiştim ve\r\no canavarlar saldırdı.',
  420: 'Lütfen uğra.',
},
}

GLOBAL = {
    'Maksimum can': 'Azami can',
    'Ooh, evet!!': 'Oleyyy!!',
    'Kontrol Cihazı alındı.': 'Denetleyici alındı.',
    "Arthur'un evine ışınlan?": "Arthur'un evine\r\nışınlanmak ister misin?",
    "Plantasyon'a ışınlan?": "Plantasyon'a\r\nışınlanmak ister misin?",
    "Yumurta Koridoru'na ışınlan?": "Yumurta Koridoru'na\r\nışınlanmak ister misin?",
    "Çalılıklar'a ışınlan?": "Çalılıklar'a\r\nışınlanmak ister misin?",
    "Kum Bölgesi'ne ışınlan?": "Kum Bölgesi'ne\r\nışınlanmak ister misin?",
    "Labirent'e ışınlan?": "Labirent'e\r\nışınlanmak ister misin?",
}

def patch_file(rel, patches):
    p = ROOT / rel
    raw = p.read_bytes()
    text = raw.decode('cp1254','surrogateescape')
    cmds = CMD.findall(text)
    parts = CMD.split(text)
    changed = 0
    for idx, body in patches.items():
        if idx >= len(parts):
            raise RuntimeError(f'{rel}: parça {idx} yok')
        old = parts[idx]
        m1 = re.match(r'^\s*', old); m2 = re.search(r'\s*$', old)
        pre = m1.group(0); post = m2.group(0)
        # Eğer tüm parça boşsa bu bir hata olurdu; manuel patch'ler görünür metindir.
        parts[idx] = pre + body + post
        if parts[idx] != old: changed += 1
    out=[]
    for i,c in enumerate(cmds):
        out.append(parts[i]); out.append(c)
    out.append(parts[-1])
    new=''.join(out)
    for a,b in GLOBAL.items(): new=new.replace(a,b)
    p.write_bytes(new.encode('cp1254','surrogateescape'))
    return changed

def main():
    total=0
    for rel, patches in P.items():
        n=patch_file(rel, patches); total += n
        print(f'{rel}: {n} manuel parça')
    # Global terim düzeltmesini patch listesinde olmayan SJS'lere de uygula.
    for p in ROOT.rglob('*.sjs'):
        rel=p.relative_to(ROOT).as_posix()
        if rel in P: continue
        t=p.read_bytes().decode('cp1254','surrogateescape'); n=t
        for a,b in GLOBAL.items(): n=n.replace(a,b)
        if n!=t: p.write_bytes(n.encode('cp1254','surrogateescape'))
    print('Toplam manuel parça:', total)

if __name__=='__main__': main()
