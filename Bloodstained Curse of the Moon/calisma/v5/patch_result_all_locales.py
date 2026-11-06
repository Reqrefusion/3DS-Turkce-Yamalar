from pathlib import Path
import sys
sys.path.insert(0,'/mnt/data/v4work/kit1/bloodstained_tr_kit')
from bloodstained_tr_tool import load_ttb,write_ttb
p=Path('/mnt/data/bloodstained_tr_v5_complete/luma/titles/00040000001D3C00/romfs/Result.ttb')
t=load_ttb(p)
def enc(s): return s.replace('ğ','Ă').replace('ı','Ć').replace('İ','Č')
patch={}
def setmany(indices,text):
 for i in indices: patch[i]=enc(text)
# All non-Japanese localization slots are overwritten with Turkish so locale-slot selection cannot expose another language.
setmany([2,29,30,34,35,37,38,39],'HIZLI')
setmany([4,5,6,7,8,10,13,14],'MAKS. CP')
setmany([3,12,15,16,17,19,22,24],'BÖLÜM PUANI')
setmany([31,32,40,41,42,43,48,49],'<emoji/Decide> SONRAKİ  <emoji/BtnY> DETAYLAR')
setmany([1,46,51,52,54,55,57,58,182,183,184,185,187,190,191,192],'<emoji/Decide> SONRAKİ')
setmany([61,62,63,64,65,67,70,71],'EK BONUS')
setmany([60,69,72,73,74,76,79,81],'TEKRAR SAYISI')
setmany([59,75,80,83,84,85,86,92],'MAKS. BURST KOMBO')
setmany([90,91,93,94,95,96,97,99],'ZORLUK')
setmany([102,103,107,108,109,111,113,114],'KALAN YİYECEKLER')
setmany([115,170,174,176,177,178,179,181],'HASARSIZ')
setmany([118,119,123,124,125,126,129,131],'BİTİRME SÜRESİ')
setmany([116,132,139,140,141,142,148,149],'ÖNCEKİ REKOR')
setmany([145,146,153,154,155,156,158,161,162],'NORMAL')
setmany([159,160,163,164,165,166,168,169,171],'ZOR')
setmany([195,196,197,198,200,204,205,206],'CEZA')
setmany([201,202,207,210,211,212,213,218],'BİTİRME BONUSU')
setmany([216,217,219,220,221,222,223,225],'TOPLAM PUAN')
write_ttb(p,t,patch)
# Re-open and validate exact content
v=load_ttb(p)
for i,s in patch.items():
 if v.text_for_record(i)!=s: raise RuntimeError((i,v.text_for_record(i),s))
print('patched result slots',len(patch))
