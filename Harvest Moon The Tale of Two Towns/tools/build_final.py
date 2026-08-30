#!/usr/bin/env python3
from pathlib import Path
import argparse,zipfile,shutil,sys,hashlib,subprocess
from release_info import RELEASE_NAME, TITLE_ID
TITLE=TITLE_ID
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import hm3ds_text as hm
import short_table_repack
EXPECTED={'romfs/mes_data.bin':'ba91cf4966c1b0c61ceab5b9025862c19da83965b2dbca51e8ba1c28ac70df80','romfs/event_mes_data.bin':'4a4686480a9eb5374368abe122dd7ada54f1ce2c9366d863039ae4ad1d216a9f','romfs/console_obj_data.bin':'8cb67fae2b6b3d97991e42098bd2e4b79d1c8652ccb1af9a0953815739547118'}
def sha(b):return hashlib.sha256(b).hexdigest()
def enc(t,c):return b''.join(hm.p16(w) for w in hm.encode_text(t,'slots',c))
def patch(d,o,n,c,count):
 ob=enc(o,c);nb=enc(n,c);assert d.count(ob)==count;assert len(nb)<=len(ob);nb+=enc(' ',c)*((len(ob)-len(nb))//2);return d.replace(ob,nb)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('rom_zip');ap.add_argument('-o','--output',default='build_final');a=ap.parse_args();out=Path(a.output);tmp=out/'_orig';rom=out/'luma'/'titles'/TITLE/'romfs'
 if out.exists():shutil.rmtree(out)
 tmp.mkdir(parents=True);rom.mkdir(parents=True)
 with zipfile.ZipFile(a.rom_zip) as z:
  for n,h in EXPECTED.items():
   b=z.read(n);assert sha(b)==h;(tmp/Path(n).name).write_bytes(b)
 c=hm.load_custom_charmap(str(ROOT/'tools'/'charmap_turkish_full.json'))
 for base in ['mes_data','event_mes_data']:
  patched,blank,too_long,errors,issues=hm.import_bin(tmp/f'{base}.bin',ROOT/'translations'/f'{base}.csv',tmp/f'{base}_tr.bin','slots',c,True)
  if too_long or errors or issues:
   raise RuntimeError(f'{base} import başarısız: patched={patched} blank={blank} too_long={too_long} errors={errors} issues={len(issues)}')
 mes=(tmp/'mes_data_tr.bin').read_bytes()
 for o,n,k in [('Request Beginner', 'Görev Acemisi', 1), ("{#2333} Save and go to bed.{BR} Go to bed without saving.{BR} Don't go to bed yet.", '{#2333} Kaydet ve uyu.{BR} Kaydetmeden uyu.{BR} Henüz uyuma.', 1), ('Saving.', 'Kayıt.', 1), ('Local Play', 'Yerel Oyun', 1), ("She's happy and healthy!", 'Mutlu ve sağlıklı!', 1), ('Upgrades!', 'Gelişim!', 1), ('Renovations?', 'Tadilat?', 1), ('Item Needed', 'Gerekli', 1), ('A Fine Axe!', 'İyi Balta!', 1), ('Money', 'Para', 2), ("I'm worried that my animals{BR}aren't doing well, so I'll{BR}be staying up all night to{BR}keep an eye on them.{BR}Could somebody please make{BR}me a midnight snack?", 'Hayvanlarım iyi görünmüyor.{BR}Bu yüzden bütün gece{BR}başlarında bekleyeceğim.{BR}Bana gece için bir şeyler{BR}hazırlayabilecek biri var mı?', 1), ('Midnight Snack?', 'Gece Yemeği?', 1), ('Help Wanted!', 'Yardım Lazım', 1), ('Touch screen', 'Ekrana dokun', 1), ('{#232F}{#206C}Unable to connect to{BR}Nintendo WFC. For help,{BR}check the software{BR}Instruction Booklet, or{BR}visit support.nintendo.com.{BR}Error code: {#1000}', '{#232F}{#206C}Nintendo WFC bağlantısı{BR}kurulamadı. Yardım için{BR}kılavuza bakın veya{BR}support.nintendo.com{BR}adresini ziyaret edin.{BR}Hata kodu: {#1000}', 1)]:mes=patch(mes,o,n,c,k)
 ev=(tmp/'event_mes_data_tr.bin').read_bytes()
 # Character picker is embedded in a control block and is not exported to CSV.
 ev=patch(ev,'{#232F}Please pick your character.{BR}{#2332} Male{BR} Female','{#232F}Karakterini seç.{BR}{#2332} Erkek{BR} Kadın',c,1)
 for o,n,k in [("We're here!{BR}This is your farm.", 'Geldik!{BR}Burası çiftliğin.', 1), ('This is the place!{BR}Your new farm!', 'İşte burası!{BR}Yeni çiftliğin!', 1), ('Where shall we go?', 'Nereye gidelim?', 4), ('Where do you wanna go?', 'Nereye gidelim?', 2), ('Stop! Sit! Heel!', 'Dur! Otur! Gel!', 1), ('{#2137}Talk about the request?{BR}{#2332} Yes{BR} No', '{#2137}İsteği konuşalım mı{BR}{#2332} Evet{BR} Hayır', 1)]:ev=patch(ev,o,n,c,k)
 mes,ev,_short_reports=short_table_repack.apply_all(mes,ev,c)
 for n in ['mes_data.bin','mes_data_fr_b.bin','mes_data_fr_g.bin','mes_data_ge.bin']:(rom/n).write_bytes(mes)
 for n in ['event_mes_data.bin','event_mes_data_fr_b.bin','event_mes_data_fr_g.bin','event_mes_data_ge.bin']:(rom/n).write_bytes(ev)
 console_out=tmp/'console_obj_data_tr.bin'
 subprocess.run([sys.executable,str(ROOT/'tools'/'console_obj_lib.py'),str(tmp/'console_obj_data.bin'),str(console_out)],check=True)
 cb=console_out.read_bytes()
 for n in ['console_obj_data.bin','console_obj_data_fr.bin','console_obj_data_ge.bin']:(rom/n).write_bytes(cb)
 payload=ROOT/'luma'/'titles'/TITLE/'romfs';text={'mes_data.bin','mes_data_fr_b.bin','mes_data_fr_g.bin','mes_data_ge.bin','event_mes_data.bin','event_mes_data_fr_b.bin','event_mes_data_fr_g.bin','event_mes_data_ge.bin','console_obj_data.bin','console_obj_data_fr.bin','console_obj_data_ge.bin'}
 for p in payload.rglob('*'):
  if p.is_file() and p.name not in text:
   q=rom/p.relative_to(payload);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
 shutil.rmtree(tmp);print(RELEASE_NAME, 'hazır:', out/'luma')
if __name__=='__main__':main()
