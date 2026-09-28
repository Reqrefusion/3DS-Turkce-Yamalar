"""Rebuild portrait title atlases in five source language color families."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import numpy as np
import sf4_tr_tool as sf4
ROOT=Path(__file__).resolve().parent.parent;HERE=Path(__file__).resolve().parent
BASE=ROOT/'CALISMA_ALANI/images/_GUI/_id/_title'
CLEAN=ROOT/'CALISMA_ALANI/temiz_zeminler';CLEAN.mkdir(parents=True,exist_ok=True)
LABELS={
61:('Her Yerde Uyur','Karateci','Fasulye Ezmesini Severim'),
62:('Ev Yok, İş Yok','Samuray Dövüşçü','Aç Dövüşçü'),
63:('Savaşın Yüreği','Satsui Ryu','Rüzgârın Yumrukları'),
64:('Kızıl Savaşçı','Dövüşçü Çapkın','Sevgilim Eliza'),
65:('Masters Varisi','Shoryureppa!','Hazırım, Gel!'),
66:('Hadi Gel!','Alevli Ejder','Zirveyi Hedefle'),
67:('Ateş Yumrukları','Cennet Tekmeleri','Saç Topuzları'),
68:('Çin Elbisesi','En Güçlü Kadın','Sıradan Kız'),
69:('Umarım Hazırsındır!','Üzgünüm!','Çelik Bacaklar'),
70:('Güzel Dedektif','Efsane Bacaklar','Ateşli Sumo'),
71:('Ağır Vurucu','Çılgın Sumo','Sumo Güreşçisi'),
72:('Chanko Güveci','Banyo Vakti','Ozeki'),
73:("Chanko'ya Bayılırım",'Kırmızı Fundoshi','Sumo Ezicisi'),
74:('Orman Savaşçısı','Ayak Bileği Avcısı','Elektrik Adam'),
75:('Vahşi Çocuk','Yüksek Voltaj','Orman Çocuğu'),
76:('Şortumu Beğendin mi?',"Pirarucu'ya Bayılırım","Samantha'nın Oğlu"),
77:('Jimmy','Taş Gibi Vücut','Kazak Dansçısı'),
79:('Bir Daha Döndür','Demir Kaslar','Sonsuza Dek Kas'),
80:('Mermilerden Nefret Ederim','Kızıl Kasırga','Hava Biçen'),
81:('İntikam Peşinde','Saça Bak Sen',"Charlie'yi Arıyor"),
82:('Karar Vermek Zor','Adaletin İntikamcısı','Sert Adam'),
83:('Sonic Flaş','Kaybeden Gider','Aile Babası'),
84:('Meditasyon Ustası','Alevli Yogi','Esne!'),
85:('Oğlum İçin','Merhametli Adam','Nihai Yogi'),
86:('Zafer Kaderdir','Sınırsız Menzil','Her Şeyin Üstünde'),
87:('Ateşli Tip','Çelik Kollar','Yumruk Sarhoşu'),
88:('Tekme Atamaz','Kuduz Köpek','Bir Zamanlar Şampiyon'),
89:('Yumrukla Zafer','Çabuk Zengin Ol','Tek Kol Arkada'),
90:('Azgın Bufalo','Şampiyon Benim!','Kanlı Pençe'),
91:('Güzellik Her Şeydir','Narsist','Kendine Âşık'),
92:('İspanyol Ninja','Maskeli Asilzade','İspanyol Yılanı'),
93:('Akrobat Dansçı','Yılan Dövmesi','Maske ve Pençe'),
94:('Azimli Kral','Parola: Tiger','Göz Bandı'),
95:('Muay Thai Kralı','Geri Dönüş Kralı','Anti-Shoryuken'),
96:('Kaplan','Tek Gözlü Savaşçı','Yara İzli Göğüs'),
97:('Yenilmez Kaplan','Cehennemden İblis','Psycho Power'),
98:('Yeni Beden Arıyor','Geri Taranmış Saç','Süper Psycho'),
99:('Bana Denk Değilsin','Shadaloo Hükümdarı','Karanlığın Kralı'),
100:('Adam Aranıyor','Karanlığın Hükümdarı','Bayan Mükemmel'),
101:('Oyun Bitti','Şık','Teknoloji Ustası'),
102:('İş Kadını','Sigarayı Bırakmalı','Yıldırım ve Ateş'),
103:("Lauren'ı Seviyorum",'Güzel Gözlük','Ölümcül Güzellik'),
104:('Devasa Karizma','Saçıma Bak','Tombik'),
105:('Çılgın Motorcu','Daracık Tulum','Ter Atıyor'),
106:('Şekere Bayılırım','Ahmak','Kung-Food'),
107:('Bir Numara Benim','Kasırga','Lezzet Güçtür'),
108:('Maskeli Adam','Acılı Dövüşçü','Lucha!'),
109:('Amigo','Tadı Harika!','Çifte Hayat'),
110:('Koş! Koş! Koş!','Viva Mexico!','Geçmişsiz Adam'),
111:('Mix-Up Ustası','Değişen Göz Rengi','Dikiş Meraklısı'),
112:('Yabancı','Fena Emo','Gi ve Şort'),
113:('Yalnız','Köpekleri Severim','Keşke Ailem Olsaydı'),
114:('Kukla Ustası','Tüm Hareketlerin Ustası','Tandem Motoru Hükmediyor'),
115:('Mide Bana Göre Değil','Kendini Geliştiren','CEO'),
116:('Çıplak ve Kaba','Sonuna Hazır Ol!','Nihai Biyo-Silah'),
117:('Ölümün Hükümdarı','Nihai İblis','Acıya Hazır mısın?'),
118:('Ani Ölüm','Budala','Satsui no Hado'),
119:('Messatsu!','Kem Göz','En Yüce Benim'),
120:('Shin Akuma','Göksel Semalar','Bilge Hoca'),
121:('Namıdiğer Shen Long','Varını Yoğunu Ortaya Koy','Nafile!'),
122:('Yeniden Meydanda','Aslında Ölmedi','Kaş Adam'),
123:('Öfkeli Ölüm','Görüşmeyeli Uzun Oldu','Herkesin Üstünde'),
124:('Katil Arı','Kalçalar Fora','Çift Örgülü'),
125:('Kedileri Severim','Casus Ajan','Delta Red'),
126:('Hedef Kilitlendi','Görev Başladı','Yalnız Değil'),
127:('Sarışın Ok','Achachachacha!','Yükselen Yıldız'),
128:('Gözü Kara','Dövüş Ruhu','Aksiyon Yıldızı'),
129:('Hitenryu Kung Fu','Disiplinli','Hisset, Düşünme'),
130:('Kendin Ol','Gösterişli Dövüşçü','Kiraz Çiçeği'),
131:('Aşk Profesörü','Tokyolu','Kendi Sınıfımdayım'),
132:('Taklitçi','Zafer İçin Pilav','Oyunlarda Berbat'),
133:('Yine Geç Kaldım','Pek Aşçı Sayılmam','Liseli Kız'),
134:('Kader Kartı','Soul Power','Düşük Tansiyon'),
135:('Gösterişli Saç','Uzun Şal','Zehir Kokusu'),
136:('Cilveli','Seksi','Psişik Tanrıça'),
137:('Gizemli Tilki','Sessiz Suikastçı','Ölümüne Dövüş'),
138:('Kurnaz','Etli Çörek Severim','İki Stil'),
139:('Ölümün Dişleri','Ölümle Savaşılmaz','Ölümcül Tekmeler'),
140:('Karanlıktan Vuruş','Kan Davası','Saikyo Yolu'),
141:('Yersiz Gurur',"Sakura'nın Hocası",'Saikyo!'),
142:("Jimmy'nin Kankası",'Alay Ustası','Topal Ördek'),
143:('Turp Gibiyim!','Yarım Pişmiş','Üçüncü Sınıf Dövüşçü'),
144:('Gururlu Dövüşçü','Dev Dövüşçü','Yıldırım Ayak Şefi'),
145:('Saç Süsü','Ruh Gezgini','Sevgilisi Var'),
146:('Kutsal Dua','Toprakla Bir','Sessiz Olan'),
147:('Meksika Tayfunu','Marakas Dövüşçüsü','Neşeli Tekmeci'),
148:('Ritmik Dövüşçü','Müzikal Tekmeci','Rahatlama Ustası'),
149:('Müzik Ustası','Dert Yok!','Her Şey Harika!'),
151:('Çevik Dövüşçü','Metro City Ninjası','Spor Ayakkabılı Ninja'),
152:('Sessiz Saldırgan','Bushinryu Ustası','Ninja Filozof'),
153:('Bir Çay Daha, Lütfen!','Bushinryu Dövüşçüsü','Sessiz Takipçi'),
154:('Kimse Bilmez','Duvar Yıkan','Yalnız Mahkûm'),
155:('Bahtsız','Emo Karamsar','Karanlık Kahraman'),
156:('Defol Git','Hadi Yakala Beni','Mahpus Kahraman'),
157:('Metro City Kavgacısı','Hayalperest Ninja','Aşk Arıyor'),
158:('Arkadaş Arıyor','Okul Halleri','İştahlı'),
159:('Don-Chan Hayranı','Orman Ninjası','Yine mi Antrenman?'),
160:('Hızlı Yiyen','Kunoichi','Al Bunu!'),
161:('Tosalı Kız','Siyah Kuşaklı Kız','Sıkı Antrenman'),
162:('Karateci Kız','Aile Kızı','Saç Bantlı Kız'),
163:('Hafta Sonu Marangozu','Fakir Kız','Dinlenmek Yok!'),
164:('Centilmen Yumrukçu','Kibar Beyefendi','Kıvrık Bıyık'),
165:("İngiltere'nin Gururu",'Milyoner','Otomobil Tutkunu'),
166:('Askı Seven','Zengin Çapkın',"Bay Gotch'un Patronu"),
167:('Dikenli Gül','Aç Jaguar','Muay Thai Efsanesi'),
168:('Yeni Kral','Majesteleri','Jaguar Dişi'),
169:('Jaguar Azı Dişi',"Sagat'ın Çırağı",'Gaspçı'),
170:('Tahtın Varisi','Hepinize Göstereceğim','Yağ Adam'),
171:('Kaçışsız Tutuş','Türk Dağı',"Türkiye'nin Gururu"),
172:('Ateşle Yaklaşma','Islakken Kaygandır','Gururlu Baba'),
173:('Yağlı Güreşçi',"Türkiye'nin Savaşçısı",'Türk Güreşçisi'),
174:('Deli Kız','Katil','Kontrolden Çıkmış'),
175:('Koreli Dövüşçü','Tekvandocu','Öldün Sen'),
176:('Hadi Oradan!','Son!','Deli Göz'),
177:('Sihirli Göz',"Gi'yle Uyur",'Gösterişli Dövüşçü'),
178:('Başardım!','Bir Göz At','Annemi Seviyorum'),
179:('Muhteşem Kaslar','Saç Spreyi Kullanır','Köri Aromalı'),
180:('Para Düşkünü','Güzellik Prensi','Nihai Düşman'),
181:('Kötülük Âşığı','Anne İzinli','Bozuk Fermuar'),
182:('Tarif Yok','Hata Yok','Sadece İnsan mı?'),
183:('Yok Edilemez!','Hayatın Güzel Yanları','Gözünü Ödülden Ayırma'),
184:('Kung Fu Aksiyonu','Selam, Ryu!','UV Engelleyici'),
185:('Her Gün Antrenman','Herkes Gelsin!','Hayvan Dostu'),
187:('Ninja Adayı',"Tosa'nın Gururu",'Eldivenli Sürücü'),
188:('Bangkok Kavgacısı','Yağın Gücü!','Kötü Kız'),
189:('Efsane Dövüşçü','Efsane Shoryuken','Efsane Bacaklar'),
190:('Efsane Sumo','Efsane Canavar','Efsane Rus'),
191:('Efsane Flaş','Efsane Yoga','Efsane Bufalo'),
192:('Efsane Pençe','Efsane Kral','Efsane Tiran'),
193:('Efsane Ajan','Efsane Göbek','Efsane Luchador'),
194:('Efsane Paralı Asker','Efsane CEO','Efsane Savaşçı'),
195:('Efsane Hoca','Efsane Katil Arı','Efsane Ejder'),
196:('Efsane Liseli','Efsane Medyum','Efsane Suikastçı'),
197:('Efsane Şaka','Efsane Tomahawk','Efsane Müzisyen'),
198:('Efsane Ninja','Efsane Haydut','Efsane Kunoichi'),
199:('Efsane Karateci Kız','Efsane Boksör','Efsane Jaguar'),
200:('Efsane Yağ Adam','Efsane Göz','Akuma Avcısı'),
}
COLORS={61:'WWW',62:'WMM',63:'MMM',64:'WWW',65:'WWM',66:'MMM',67:'MWW',68:'WWW',69:'MMM',70:'MMW',
        71:'WWW',72:'WMM',73:'MMM',74:'WWW',75:'WWM',76:'MMM',77:'MWW',
        79:'MMM',80:'MMW',81:'WWW',82:'WMM',83:'MMM',84:'WWW',85:'WWM',86:'MMM',87:'MWW',88:'WWW',89:'MMM',90:'MMW',
        91:'WWW',92:'WMM',93:'MMM',94:'WWW',95:'WWM',96:'MMM',97:'MWW',98:'WWW',99:'MMM',100:'MMW',101:'WWW',102:'WMM',
        103:'MMM',104:'WWW',105:'WWM',106:'MMM',107:'MWW',108:'WWW',109:'MMM',110:'MMW',111:'WWW',112:'WMM',
        113:'MMM',114:'WWW',115:'WWM',116:'MMM',117:'MWW',118:'WWW',119:'MMM',120:'MMW',121:'WWW',122:'WMM',
        123:'MMM',124:'WWW',125:'WWM',126:'MMM',127:'MWW',128:'WWW',129:'MMM',130:'MMW',131:'WWW',132:'WMM',
        133:'MMM',134:'WWW',135:'WWM',136:'MMM',137:'MWW',138:'WWW',139:'MMM',140:'MMW',141:'WWW',142:'WMM',
        143:'MMM',144:'WWW',145:'WWM',146:'MMM',147:'MWW',148:'WWW',149:'MMM',151:'WWW',152:'WMM',
        153:'MMM',154:'WWW',155:'WWM',156:'MMM',157:'MWW',158:'WWW',159:'MMM',160:'MMW',161:'WWW',162:'WMM',
        163:'MMM',164:'WWW',165:'WWM',166:'MMM',167:'MWW',168:'WWW',169:'MMM',170:'MMW',171:'WWW',172:'WMM',
        173:'MMM',174:'WWW',175:'WWM',176:'MMM',177:'MGG',178:'GGG',179:'GGG',180:'GGG',181:'GGG',182:'GGG',
        183:'GGG',184:'GGG',185:'GGG',187:'GGG',188:'GGG',
        189:'RRR',190:'RRR',191:'RRR',192:'RRR',193:'RRR',194:'RRR',195:'RRR',196:'RRR',197:'RRR',198:'RRR',199:'RRR',200:'RRR'}
SOURCE=Image.open(HERE/'sourceplates/title061_102_brush_textless.png').convert('RGBA')

def plate(n):
    folder=BASE/f'title{n:03}.arc'
    originals=np.stack([np.asarray(Image.open(next(folder.glob(f'*.{s}.png'))).convert('RGBA'))
                        for s in ('eng','fre','ger','ita','spa')])
    luma=(originals[:,:,:,:3].astype('float32')*np.array([.22,.65,.13])).sum(axis=3)
    idx=luma.argmin(axis=0)
    portrait=np.take_along_axis(originals,idx[None,:,:,None],axis=0)[0]
    out=np.zeros((128,256,4),dtype='uint8')
    for row,(lo,hi,y) in enumerate(((17,300,0),(315,600,37),(615,887,75))):
        ribbon=np.array(SOURCE.crop((47,lo,1704,hi)).resize((180,35),Image.Resampling.LANCZOS))
        # Native magenta brushes retain their color family; white brushes
        # are less saturated than the high-resolution redrawn source.
        if COLORS[n][row]=='M':
            ribbon[:,:,1]=(ribbon[:,:,1].astype(float)*.58).astype('uint8')
            ribbon[:,:,2]=np.minimum(255,ribbon[:,:,2].astype(float)*.85+25).astype('uint8')
        elif COLORS[n][row]=='G':
            ribbon[:,:,0]=(ribbon[:,:,0].astype(float)*.78).astype('uint8')
            ribbon[:,:,1]=(ribbon[:,:,1].astype(float)*.73).astype('uint8')
            ribbon[:,:,2]=(ribbon[:,:,2].astype(float)*.44).astype('uint8')
        elif COLORS[n][row]=='R':
            ribbon[:,:,0]=(ribbon[:,:,0].astype(float)*.97).astype('uint8')
            ribbon[:,:,1]=(ribbon[:,:,1].astype(float)*.59).astype('uint8')
            ribbon[:,:,2]=(ribbon[:,:,2].astype(float)*.59).astype('uint8')
        else:
            ribbon[:,:,0]=(ribbon[:,:,0].astype(float)*.92).astype('uint8')
            ribbon[:,:,1]=np.minimum(255,ribbon[:,:,1].astype(float)*.84+17).astype('uint8')
            ribbon[:,:,2]=np.minimum(255,ribbon[:,:,2].astype(float)*.84+17).astype('uint8')
        out[y:y+35,:180]=ribbon
    for x in range(36):
        t=max(0,min(1,(x-22)/14))
        out[:,x]=np.uint8((1-t)*portrait[:,x]+t*out[:,x])
    image=Image.fromarray(out,'RGBA')
    image.save(CLEAN/f'title{n:03}_textless.png')
    return image

def write(n):
    image=plate(n).resize((1024,512),Image.Resampling.NEAREST)
    draw=ImageDraw.Draw(image);fontpath=HERE/'fonts/DejaVuSans-Bold.ttf'
    for row,label in enumerate(LABELS[n]):
        size=56
        while True:
            font=ImageFont.truetype(str(fontpath),size)
            box=draw.textbbox((0,0),label,font=font,stroke_width=4)
            if box[2]-box[0]<=548:break
            size-=1
        x=4*37+(548-(box[2]-box[0]))//2-box[0]
        y=4*(4+37*row)+(100-(box[3]-box[1]))//2-box[1]
        draw.text((x,y),label,font=font,fill=(255,249,240,255),stroke_width=4,stroke_fill=(129,21,41,255))
    folder=BASE/f'title{n:03}.arc';path=next(folder.glob('*.tur.png'))
    image.resize((256,128),Image.Resampling.LANCZOS).save(path)
    arcpath=ROOT/f'YAMA/_eng/_GUI/_id/_title/title{n:03}.arc'
    arc=sf4.ArcFile(arcpath.read_bytes());arcpath.write_bytes(arc.rebuild({0:sf4.png_to_tex_bytes(path,arc.unpack(0))}))
if __name__=='__main__':
    for n in LABELS:write(n);print(n)
