#!/usr/bin/env python3
from pathlib import Path
import argparse,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import pck_extract as pck
import wwise_dsp_decode as dsp
MAP={
'cine_01_play': {'EN':530074701,'FR':640551614,'DE':333588774,'IT':277617787,'ES':694457760},
'cine_02_play': {'EN':1035949580,'FR':724461106,'DE':205748518,'IT':989779889,'ES':165710428},
'cine_03_play': {'EN':458275269,'FR':1043430724,'DE':230982475,'IT':243113847,'ES':697693468},
'cine_04_play': {'EN':176040585,'FR':664608501,'DE':163894193,'IT':572369826,'ES':714215364},
'cine_05_play': {'EN':300128645,'FR':336872009,'DE':830707770,'IT':519271768,'ES':632089718},
'cine_06_play': {'EN':718756994,'FR':190320171,'DE':619309545,'IT':989935442,'ES':840097407},
'cine_06b_play': {'EN':83354869,'FR':358296706,'DE':979766466,'IT':2138834,'ES':881180788},
}
PCK={'EN':'English.pck','FR':'French.pck','DE':'German.pck','IT':'Italian.pck','ES':'Spanish.pck'}
def main():
 ap=argparse.ArgumentParser(description='Heroes of Ruin 7 animatic sesini 5 dil PCK dosyasindan cikarir.')
 ap.add_argument('sounds_dir',type=Path,help='English.pck vb. bulunan Sounds klasoru')
 ap.add_argument('output',type=Path);a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 for lang,pfn in PCK.items():
  pp=a.sounds_dir/pfn
  if not pp.is_file(): print('atlanıyor:',pp);continue
  blob,langs,banks,sounds,ext=pck.parse_pck(pp); idx={x['id']:x for x in sounds};ld=a.output/lang;ld.mkdir(exist_ok=True)
  for event,ids in MAP.items():
   mid=ids[lang];e=idx[mid];raw=blob[e['offset']:e['offset']+e['size']]
   (ld/f'{event}__{mid}.wem').write_bytes(raw)
   rate,s,info=dsp.decode_wwise_dsp(raw);dsp.write_wav(ld/f'{event}.wav',rate,s)
   print(lang,event,mid,f'{len(s)/rate:.3f}s')
if __name__=='__main__':main()
