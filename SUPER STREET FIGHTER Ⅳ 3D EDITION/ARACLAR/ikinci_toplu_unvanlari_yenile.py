"""Restore title039-054 from five source languages and write Turkish titles.

Uses the documented per-language text mask and ARC/TEX writer in the
previous batch's toplu_unvanlari_yenile.py.
"""
import toplu_unvanlari_yenile as batch
LABELS={
39:('Sınıfın Birincisi','Başkan','Şarap ve Ziyafet'),
40:('Yumruk Kralı','Bambaşka Soy','Çeyrek Adam'),
41:('Akrobat','Genç Kız','Sürpriz Üstüne Sürpriz'),
42:('İblis Kralı','Savaş Görmüş','Yönetim Kurulu Başkanı'),
43:('Estetisyen','İmparator','Gerçek Savaşçı'),
44:('Sana Fazla Havalı','Zamanlama Ustası','Gönülçelen'),
45:('Eksiksiz Paket','Bolluk İçinde','Makineli Tüfekçi'),
46:('Başkanların Başkanı','Çok Ciddi','En İyilerin En İyisi'),
47:('Efsane Dövüşçü','Efsane Kaybeden','Soykırımcı'),
48:('Aşk Elçisi','Erkenci Kuş','Burjuva'),
49:('Tek Ölümcül Darbe','Emekli','Elimden Geleni Yapacağım'),
50:('Günlük Görev','Tek Bir Hedef','15 Dakikalık Şöhret'),
51:('Tek Vuruşluk Harika','Her İşin Ustası','Sefaletten Servete'),
52:('Yükselip Alçalmak','Çalışkan','Kıl Payı'),
53:('Yanılmaz','Kudretli Savaşçı','Tek Hamlede'),
54:('Ya Bat Ya Çık','Tetikte','Gordion Düğümü'),
}
if __name__=='__main__':
    batch.LABELS=LABELS
    for n in LABELS:
        batch.draw(n,batch.clean(n))
        print(n)
