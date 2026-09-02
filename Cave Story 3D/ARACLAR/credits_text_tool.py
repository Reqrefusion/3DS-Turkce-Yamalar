#!/usr/bin/env python3
"""Polish the six animated credits text variants without touching control tags."""
from pathlib import Path
import re
ROOT=Path('/mnt/data/cs3d_work/final/000400000004D200/romfs/data')
TAG_RE=re.compile(r'(\[[^\]]*\])')

REPL={
    'Hayranlıkla bakar':'Ağabeyini','ağabeyine':'örnek alır,',
    'Bazen güvenilir':'Bazen','ağabeyi':'güvenilir ağabey',
    "Sue'nun büyükbabası":"Sue'nun dede",'gibi gördüğü kişi':'yerine koyduğu kişi',
    'Professor Booster':'Profesör Booster','Dr. Gero':'Doktor Gero','Nurse Hasumi':'Hemşire Hasumi',
    'Koruyucusu':"Kum Bölgesi'nin",'Kum Bölgesi':'koruyucusu',
    'Jenka\'nın Yavruları':"Jenka'nın yavruları",'Dede':'Yaşlı',
    'Lezzetli':'Lezzetli bir','- ALSO... -':'- DİĞERLERİ... -','- ALSO -':'- DİĞERLERİ -',
    'Ele geçirilmiş: The Door':'Ele geçirilmiş: Kapı',
    'Yemeye değer: Giant Pignon':'Yenmeye değer: Dev Pignon',
    'Eşi benzeri yok: The Egg Fish':'Eşi benzeri yok: Yumurta Balığı',
    'Ezici güç: Power Critter':'Ezici: Power Critter',
    'Red Ogre':'Kızıl Ogre','Muscle Doctor':'Kaslı Doktor','Undead Core':'Ölümsüz Çekirdek','Heavy Press':'Ağır Pres',
    'Core':'Çekirdek','Monster X':'Canavar X','Sisters':'Kız Kardeşler','Ironhead':'Demirkafa',
    'Critter':'Yaratık','Bat':'Yarasa','Gravekeeper':'Mezarlık Bekçisi','Beetle':'Böcek',
    'Power Critter':'Güçlü Yaratık','Frog':'Kurbağa','Press':'Pres','Sandcroc':'Kum Timsahı',
    'Skeleton':'İskelet','Crow':'Karga','Baby':'Yavru','Flowercub':'Çiçek Yavrusu','Armor':'Zırh',
    'Gaudi Egg':'Gaudi Yumurtası','Fire Whirl':'Ateş Girdabı','Buyobuyo Base':'Buyobuyo Üssü',
    'Fuzz Core':'Fuzz Çekirdeği','Porcupine Fish':'Kirpi Balığı','Dragon Zombie':'Zombi Ejderha',
    'Time Bomb':'Zaman Bombası','Night Ghost':'Gece Hayaleti','Gunfish':'Silah Balığı',
    'Orangebell':'Turuncu Çan','Green Devil':'Yeşil Şeytan','Rolling':'Yuvarlanan','Delete':'Silici',
    'Haruhi and Tamami':'Haruhi ve Tamami','Miria and Maxx':'Miria ve Maxx',
}

# Descriptive monster names occur as the suffix of a full visible line (e.g.
# "Tik tak: Time Bomb").  Replace only the suffix so the translated description
# and control tags remain untouched.
SUFFIX_REPL={
    'Critter':'Yaratık','Bat':'Yarasa','Gravekeeper':'Mezarlık Bekçisi','Beetle':'Böcek',
    'Power Critter':'Güçlü Yaratık','Frog':'Kurbağa','Press':'Pres','Sandcroc':'Kum Timsahı',
    'Skeleton':'İskelet','Crow':'Karga','Baby':'Yavru','Flowercub':'Çiçek Yavrusu','Armor':'Zırh',
    'Gaudi Egg':'Gaudi Yumurtası','Fire Whirl':'Ateş Girdabı','Buyobuyo Base':'Buyobuyo Üssü',
    'Fuzz Core':'Fuzz Çekirdeği','Porcupine Fish':'Kirpi Balığı','Dragon Zombie':'Zombi Ejderha',
    'Time Bomb':'Zaman Bombası','Night Ghost':'Gece Hayaleti','Gunfish':'Silah Balığı',
    'Orangebell':'Turuncu Çan','Green Devil':'Yeşil Şeytan','Rolling':'Yuvarlanan','Delete':'Silici',
}

def process(p:Path):
    txt=p.read_bytes().decode('cp1254','strict')
    out=[]
    for line in txt.splitlines(keepends=True):
        # Only replace display text outside [] control tags.
        parts=TAG_RE.split(line)
        for i in range(0,len(parts),2):
            body=parts[i]
            # Preserve whitespace/newlines around exact visible text.
            m=re.match(r'^(\s*)(.*?)(\s*(?:\r?\n)?)$',body,flags=re.S)
            if not m: continue
            lead,vis,trail=m.groups()
            if vis in REPL:
                vis=REPL[vis]
            else:
                for old_name,new_name in sorted(SUFFIX_REPL.items(), key=lambda kv: -len(kv[0])):
                    if vis.endswith(old_name):
                        vis=vis[:-len(old_name)]+new_name
                        break
            parts[i]=lead+vis+trail
        out.append(''.join(parts))
    p.write_bytes(''.join(out).encode('cp1254','strict'))

if __name__=='__main__':
    files=sorted(ROOT.glob('credits_text*.txt'))
    for p in files: process(p)
    print('processed',len(files),'credits text variants')
