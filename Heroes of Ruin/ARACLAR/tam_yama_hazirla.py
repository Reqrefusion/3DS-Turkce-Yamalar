from pathlib import Path
import sys,shutil
TITLE="0004000000074000"
if len(sys.argv)<2:
 print("Kullanim: python tam_yama_hazirla.py <tam_RomFS_klasoru> [cikti]");raise SystemExit(2)
rom=Path(sys.argv[1]); out=Path(sys.argv[2]) if len(sys.argv)>2 else Path("HeroesOfRuin_Turkce_Luma")
base=Path(__file__).resolve().parents[1]
srcpatch=base/"YAMA_HAZIR/luma/titles"/TITLE/"romfs"
dst=out/"luma/titles"/TITLE/"romfs"
if dst.exists():shutil.rmtree(dst)
shutil.copytree(srcpatch,dst)
hits=[p for p in rom.rglob("demo_font.bcfnt_") if p.is_file()]
if len(hits)==1:
 rel=hits[0].relative_to(rom); target=dst/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(base/"FONT/demo_font.bcfnt_",target);print("Font eklendi:",rel)
elif len(hits)==0: print("UYARI: demo_font.bcfnt_ RomFS içinde bulunamadı; metin+sinema yaması hazır, fontu elle doğru konuma kopyalayın.")
else: print("UYARI: Birden fazla demo_font.bcfnt_ bulundu; font otomatik eklenmedi.")
print("Hazir:",out)
