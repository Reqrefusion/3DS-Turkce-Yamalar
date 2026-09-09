from pathlib import Path
import sys
sys.path.insert(0, '/mnt/data/FaceRaiders_TR')
sys.path.insert(0, '/mnt/data/faceraiders_work')
import faceraiders_localizer as fl
from tr_map import TR

inp = Path('/mnt/data/faceraiders.zip')
out = Path('/mnt/data/FaceRaiders_TR/StgFace_all_languages_TR.csv')
rom = fl.choose_romfs(inp, 'StgFace')
base_path = 'hal/msg/StgFace/StgFaceEU_English.msbt'
m = fl.MSBT(rom.get(base_path))
idx_to_label = {idx: labels[0] for idx, labels in m.index_to_labels.items() if labels}
missing_idx = [i for i in TR if i not in idx_to_label]
if missing_idx:
    raise SystemExit(f'Missing labels for indices: {missing_idx}')
tr_by_label = {idx_to_label[i]: s for i, s in TR.items()}
notes_idx = {
    11: 'Standart onay düğmesi. “Evet” doğal Türkçe karşılık; kaynak dillerden uzun olduğu için gerçek cihazda düğme genişliği görsel olarak doğrulanmalı.',
    12: 'Standart ret düğmesi. “Hayır” anlamı koruyan doğal karşılık; kaynak dillerden uzun olduğu için gerçek cihazda düğme genişliği görsel olarak doğrulanmalı.',
    189: 'EU “Share the Fun!”, US “Show a Friend!” ve Japonca işlev karşılaştırılarak kısa, oyunbaz ad seçildi: “Neşeyi Paylaş!”.',
    315: '“Sneaky/Surprise Snaps” özelliği, gizli çekim çağrışımını azaltıp işlevi anlatacak şekilde “Sürpriz Çekim” olarak yerelleştirildi.',
    364: '“Fresh Face” sözcük oyunu doğrudan “Taze Yüz” yerine oyun içindeki beklenmedik karşılaşmayı vurgulayan “Sürpriz Yüz” yapıldı.',
    377: 'Kısa kamera sesi “Snap!” Türkçede doğal ses efekti olarak “Çıt!” diye uyarlandı.',
    379: 'Sayfa çevirme onomatopesi diğer dillerdeki oyunbaz tona göre “Fırt fırt fırt!” olarak yeniden yaratıldı.',
    384: 'Dedikodu esprisi kelimesi kelimesine değil, Türkçedeki imalı anlatım ritmiyle “Ben demiyorum...” şeklinde uyarlandı.',
    396: 'Oyun adı marka/başlık olduğu için “Face Raiders” çevrilmeden korundu.',
    248: 'UFO’nun yüz “kaçırması”, uzaylı kaçırma şakasını korumak için bilinçli olarak “kaçıracak” diye çevrildi.',
}
notes = {idx_to_label[i]: s for i,s in notes_idx.items()}
n, langs, base = fl.export_csv(rom, 'StgFace', out, tr_by_label, notes)
print('rows', n, 'langs', len(langs), 'base', base, 'tr', len(tr_by_label), 'out', out)
