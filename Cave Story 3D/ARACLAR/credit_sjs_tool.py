#!/usr/bin/env python3
"""Cave Story 3D credit.sjs translator.

The file contains a raw 0xC2 layout byte inside some bracket payloads.  It is
NOT treated as text: this tool preserves it byte-for-byte while replacing only
human-readable bracket payloads. Numeric/layout suffixes and all non-bracket
bytes remain identical to the English source.
"""
from pathlib import Path
import re, sys

SRC = Path('/mnt/data/cs3d_work/patch/data/credit.sjs')
DST = Path('/mnt/data/cs3d_work/final/000400000004D200/romfs/data/credit.sjs')
MARK='§'

T={
 f'{MARK}  CAST':f'{MARK}  KADRO',
 f' FROM THE SURFACE{MARK}  ':f' YERYÜZÜNDEN{MARK}  ',
 ' Looks up':' Ağabeyini', f'{MARK}  to her brother,':f'{MARK}  örnek alır,',
 ' Sometimes':' Bazen', f'{MARK}  reliable brother':f'{MARK}  güvenilir ağabey',
 " Sue's mom":" Sue'nun annesi", ' Sue\'s grandfather':" Sue'nun dede", f'{MARK}  figure':f'{MARK}  yerine koyduğu kişi',
 ' The Mimiga-like':' Mimigaya benzeyen', f'{MARK}  coward engineer':f'{MARK}  korkak mühendis',
 f'{MARK}  MIMIGA VILLAGE':f'{MARK}  MİMİGA KÖYÜ', ' Nice and':' Nazik ve', f'{MARK}  Courageous':f'{MARK}  cesur',
 ' The Leader':' Lider', ' Number-Two':' İkinci adam', ' Eats, eats, eats':' Yer, yer, yine yer',
 ' The angler':' Balıkçı', ' The Farmer':' Çiftçi',
 f'{MARK}  BUSHLANDS{MARK}  ':f'{MARK}  ÇALILIKLAR{MARK}  ', ' The cowardly':' Korkak', f'{MARK}  loner':f'{MARK}  yalnız kurt',
 ' The colorful':' Renkli', ' Power Supply Bot':' Güç Kaynağı Robotu',
 f'{MARK}  SAND ZONE':f'{MARK}  KUM BÖLGESİ', ' Mimiga Ally':' Mimiga Müttefiki', ' Mimiga kids':' Mimiga Çocukları',
 ' The Colons':' Colonlar', ' Keeper of':" Kum Bölgesi'nin", f'{MARK}  the Sand Zone':f'{MARK}  koruyucusu',
 " Jenka's puppies":" Jenka'nın yavruları",
 f'{MARK}  LABYRINTH':f'{MARK}  LABİRENT', ' Labyrinth':' Labirent', f'{MARK}  arms dealer':f'{MARK}  silahçısı',
 " Labyrinth's":" Labirent'in", f'{MARK}  local physician':f'{MARK}  doktoru', ' Dr. Gero':' Doktor Gero',
 ' I am a nurse!':' Ben hemşireyim!', ' Nurse Hasumi':' Hemşire Hasumi',
 f'{MARK}  PLANTATION':f'{MARK}  PLANTASYON', ' The little Mimiga':' Küçük Mimiga', ' The grandpa':' Yaşlı',
 ' Sprinkler manager':' Fıskiye sorumlusu', ' Followers of the':" Doktor'un", f'{MARK}  Doctor':f'{MARK}  takipçileri',
 ' The Shovel Crew':' Kürek Ekibi',
 f'{MARK}  VILLAINS':f'{MARK}  KÖTÜLER', ' VILLAINS':' KÖTÜLER', ' Drawn to the':' Tacın cazibesine', f'{MARK}  Crown':f'{MARK}  kapılan',
 ' The Doctor':' Doktor', ' Cursed by the':' Taç tarafından', ' A new friend':' Yeni bir dost',
 ' ALSO...':' DİĞERLERİ...', ' ALSO':' DİĞERLERİ',
 ' The Hermit':' Münzevi', f'{MARK}  Gunsmith':f'{MARK}  Silah Ustası', ' The Hermit Gunsmith':' Münzevi Silah Ustası',
 ' A tasty':' Lezzetli bir', f'{MARK}  mushroom':f'{MARK}  mantar', ' mushroom':' mantar',
 ' Living in':" Dış Duvar'da", f'{MARK}  the outer wall':f'{MARK}  yaşayan', ' the outer wall':' yaşayan',
 ' The Littles':' Little Ailesi', ' The enigmatic':' Gizemli', f'{MARK}  natives':f'{MARK}  yerliler', ' natives':' yerliler',
 ' The Sculptor':' Heykeltıraş', ' The sculptor':' Heykeltıraş',
 ' SEAL CHAMBER':' MÜHÜR ODASI', " Jenka's powerful":" Jenka'nın güçlü", ' younger brother':' küçük kardeşi',

 f'{MARK}  MONSTERS':f'{MARK}  CANAVARLAR',
 ' Leaps and hops: Critter':' Hoplayıp zıplar: Yaratık', ' For every cave a: Bat':' Her mağarada bir: Yarasa',
 ' Possessed: The Door':' Ele geçirilmiş: Kapı', ' Angry charger: Behemoth':' Öfkeli saldırgan: Behemoth',
 ' White mushroom: Pignon':' Beyaz mantar: Pignon', ' Worth eating: Giant Pignon':' Yenmeye değer: Dev Pignon',
 ' Only one: The Egg Fish':' Eşi benzeri yok: Yumurta Balığı', ' Slices you up: Gravekeeper':' Doğrar geçer: Mezarlık Bekçisi',
 ' Very Deadly: Basil':' Son derece ölümcül: Basil', ' A model insect: Beetle':' Örnek böcek: Böcek',
 ' The big flyer: Basu':' Büyük uçan: Basu', ' The crusher: Power Critter':' Ezici: Güçlü Yaratık',
 ' White mold ghost: Mannan':' Beyaz küf hayaleti: Mannan', ' Tiny frog: Petit':' Minik kurbağa: Petit',
 ' Big croaker: Frog':' Koca vıraklayan: Kurbağa', ' Floats about: Jelly':' Süzülüp durur: Jelly',
 ' Queen Jelly: Kurara':' Jöle kraliçesi: Kurara', ' Violent Mimiga: Ravil':' Vahşi Mimiga: Ravil',
 ' Instant deathtrap: Press':' Ani ölüm tuzağı: Pres', ' Sudden chomper: Sandcroc':' Aniden ısırır: Kum Timsahı',
 ' Wandering skull: Skullhead':' Gezgin kafatası: Skullhead', ' Sand runner: Skullstep':' Kum koşucusu: Skullstep',
 ' White foe: Skeleton':' Beyaz düşman: İskelet', ' Sand Zone hunter: Crow':' Kum Bölgesi avcısı: Karga',
 ' Tough missile: Armadillo':' Sert mermi: Armadillo', ' From one, many: Polish':' Birden çoğa: Polish',
 ' Scattering everywhere: Baby':' Her yana saçılır: Yavru', " Toroko's: Flowercub":" Toroko'nun: Çiçek Yavrusu",
 ' Labyrinth dweller: Gaudi':' Labirent sakini: Gaudi', ' Labyrinth warrior: Armor':' Labirent savaşçısı: Zırh',
 ' Labyrinth baby: Gaudi Egg':' Labirent yavrusu: Gaudi Yumurtası', ' Fiery fan: Fire Whirl':' Ateşli pervane: Ateş Girdabı',
 ' Unknown: Buyobuyo Base':' Bilinmeyen: Buyobuyo Üssü', ' And: Buyobuyo':' Ve: Buyobuyo',
 ' Gaudi spirit: Fuzz':' Gaudi ruhu: Fuzz', ' Spirit clump: Fuzz Core':' Ruh kümesi: Fuzz Çekirdeği',
 ' An old friend: Porcupine Fish':' Eski bir dost: Kirpi Balığı', ' Failed hatch: Dragon Zombie':' Çıkamayan yavru: Zombi Ejderha',
 ' Ticking: Time Bomb':' Tik tak: Zaman Bombası', " In the Outer wall: Night Ghost":" Dış Duvar'da: Gece Hayaleti",
 ' Jumps: Hoppy':' Zıplar: Hoppy', ' Photosynthetic foe: Midorin':' Fotosentetik düşman: Midorin',
 ' Born of earth: Droll':' Topraktan doğan: Droll', ' Stepping stone: Gunfish':' Basamak taşı: Silah Balığı',
 ' Mother bat: Orangebell':' Anne yarasa: Turuncu Çan', ' Plantation dragonfly: Stumpy':' Plantasyon yusufçuğu: Stumpy',
 " Hell's messenger: Bute":" Cehennemin habercisi: Bute", " Hell's messenger: Mesa":" Cehennemin habercisi: Mesa",
 ' Innocent demon: Green Devil':' Masum iblis: Yeşil Şeytan', ' Rolls along the walls: Rolling':' Duvarlarda yuvarlanır: Yuvarlanan',
 ' Blocks passage: Delete':' Yolu kapatır: Silici',

 f'{MARK}  BOSSES':f'{MARK}  BAŞ DÜŞMANLAR',
 ' Rabid Mimiga who':' Kuduz Mimiga;', ' kidnapped Sue':" Sue'yu kaçırdı",
 ' Misery transformed':" Misery'nin", ' Balrog into':' dönüştürdüğü Balrog',
 ' Machine-monster that':' Kumlarda gizlenen', ' lurks in the sand':' makine-canavar',
 ' Ate a red flower':' Kırmızı çiçek yedi', ' Ghost in':' Klinikteki', ' the clinic':' hayalet',
 ' Big boss in':' Labirentin', ' the labyrinth':' büyük patronu', ' Heart of the island':' Adanın kalbi',
 ' Big fish in the':' Adanın damarındaki', " island's artery":' büyük balık',
 ' Twin dragon surprise':' Sürpriz saldıran', ' attackers':' ikiz ejderhalar',
 ' True heroes meet the':' Gerçek kahramanların rakibi', ' Red Ogre':' Kızıl Ogre',
 ' The red crystal':' Kırmızı kristalin', ' runs wild':' çılgın gücü', ' Muscle Doctor':' Kaslı Doktor',
 ' The Doctor and the':' Doktor ve', " island's heart":' adanın kalbi', ' Undead Core':' Ölümsüz Çekirdek',
 ' The swollen mech':' Şişmiş makine', ' Heavy Press':' Ağır Pres', ' Hate and madness':' Nefret ve deliliğin', ' made flesh':' vücut bulmuş hâli',
 ' Monster X':' Canavar X', ' Core':' Çekirdek', ' Ironhead':' Demirkafa', ' Sisters':' Kız Kardeşler',

 f'{MARK}  CREDITS ':f'{MARK}  JENERİK ', '***PLACEHOLDER CREDITS***':'***GEÇİCİ JENERİK***',
 'Original Game Program':'Orijinal Oyun Programı', 'and Design':'ve Tasarımı', 'Executive Producer':'Yürütücü Yapımcı',
 'Producer':'Yapımcı', 'Associate Producer':'Yardımcı Yapımcı', 'Lead Programmer':'Baş Programcı',
 'Other Programmers':'Diğer Programcılar', 'Gameplay Design':'Oynanış Tasarımı', '3D Artists':'3D Sanatçıları',
 'Additional Artwork':'Ek Görsel Tasarım', 'Localization':'Yerelleştirme', 'Testing':'Test',
 'Production Director':'Yapım Yönetmeni', 'Package &':'Kutu ve', 'Manual Design':'Kılavuz Tasarımı',
 'Movie Trailer &':'Tanıtım Videosu ve', 'Ad Design':'Reklam Tasarımı', 'Web & Web Ad Design':'Web ve Çevrimiçi Reklam Tasarımı',
 'PR & Marketing':'Halkla İlişkiler ve Pazarlama', 'Very Special Thanks':'Çok Özel Teşekkürler',
 'Haruhi and Tamami, Mike Winfield':'Haruhi ve Tamami, Mike Winfield',
 "Mom, Miria, Tamy, the Saito's":'Anne, Miria, Tamy, Saito ailesi',
 'Max Fledler, Katy Coope and you!':'Max Fledler, Katy Coope ve sen!',
 '***END PLACEHOLDER CREDITS***':'***GEÇİCİ JENERİK SONU***',
 'Thank you very much!':'Çok teşekkürler!', 'Cave Story ~ The End':'Cave Story ~ SON',
}

BRACKET=re.compile(br'\[([^\]]*)\]')

def dec_payload(b:bytes)->str:
    return b.replace(b'\xC2', MARK.encode('utf-8')).decode('utf-8') if False else b.replace(b'\xC2', b'\x00').decode('ascii').replace('\x00',MARK)

def enc_payload(s:str)->bytes:
    # Encode text as Windows-1254 while restoring the layout marker as raw 0xC2.
    chunks=s.split(MARK)
    return b'\xC2'.join(c.encode('cp1254','strict') for c in chunks)

def translate(src=SRC,dst=DST):
    raw=src.read_bytes()
    out=bytearray(); pos=0; translated=0
    for m in BRACKET.finditer(raw):
        out += raw[pos:m.start(1)]
        payload=dec_payload(m.group(1))
        target=T.get(payload,payload)
        if target != payload: translated += 1
        out += enc_payload(target)
        pos=m.end(1)
    out += raw[pos:]
    dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_bytes(out)
    # Structural validation: remove payload bytes and require everything else identical.
    def skeleton(data:bytes): return BRACKET.sub(b'[]',data)
    assert skeleton(raw)==skeleton(bytes(out)), 'non-text structure changed'
    assert raw.count(b'\xC2')==bytes(out).count(b'\xC2')==32, '0xC2 marker count changed'
    print(f'translated payloads: {translated}; raw C2 preserved: 32; structure: OK')

if __name__=='__main__': translate()
