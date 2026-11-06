#!/usr/bin/env python3
from pathlib import Path
import argparse,csv,hashlib,importlib.util,re,sys
def load_tool(path):
 spec=importlib.util.spec_from_file_location("rhm_v22_validate_tool",path); mod=importlib.util.module_from_spec(spec); sys.modules["rhm_v22_validate_tool"]=mod; spec.loader.exec_module(mod); return mod
def sha(p):
 h=hashlib.sha256();
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""): h.update(b)
 return h.hexdigest()
def clean(s): return re.sub(r"\[\[.*?\]\]","",s)
def main():
 ap=argparse.ArgumentParser(description="RHM TR v22 tam LayeredFS doğrulayıcı"); ap.add_argument("--base",type=Path,required=True); ap.add_argument("--new",type=Path,required=True); ap.add_argument("--project",type=Path,required=True); ap.add_argument("--rhm-tool",type=Path,required=True); a=ap.parse_args(); r=load_tool(a.rhm_tool); errors=[]
 bf={p.relative_to(a.base):p for p in a.base.rglob("*") if p.is_file()}; nf={p.relative_to(a.new):p for p in a.new.rglob("*") if p.is_file()}
 if set(bf)!=set(nf): errors.append("Oyun dosya seti değişti.")
 changed=[rel for rel in bf if rel in nf and sha(bf[rel])!=sha(nf[rel])]; expected=Path("romfs/EUENmessage/pajama.zlib")
 if changed != [expected]: errors.append("Yalnız pajama.zlib değişmeliydi: "+", ".join(map(str,changed)))
 sarc=r.Sarc(r.read_wrapped_zlib(a.new/expected)); files=sarc.files(); inj=unk=mis=tok=rt=long=phys=0
 for table in sorted(a.project.rglob("*.msbt.tsv")):
  parts=table.parts; k=parts.index("pajama_sarc"); internal="/".join(parts[k+1:])[:-4]
  with table.open("r",encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f,delimiter="\t"))
  for row in rows:
   if "\n" in row["Turkish"] or "\r" in row["Turkish"]: phys+=1
  if internal not in files: unk+=len(rows); continue
  b=files[internal]; entries=r.msbt_entries(b); emap={lab:text for _,lab,text in entries}; sec,_=r.msbt_sections(b); raws=r.parse_txt2_raw(b,sec)
  for (_,lab,text),raw in zip(entries,raws):
   try:
    if r.editable_to_raw(r.raw_to_editable(raw,sec),sec)!=raw: rt+=1
   except Exception: rt+=1
  for row in rows:
   if row["label"] not in emap: unk+=1; continue
   inj+=1; tr=row["Turkish"]; got=emap[row["label"]]
   if got!=tr: mis+=1
   if r.protected_tokens(got)!=r.protected_tokens(tr): tok+=1
   for line in clean(tr).split("\\n"):
    if len(line)>52: long+=1
 print("RHM TR v22 doğrulama"); print("Değişen oyun dosyası:",len(changed),[str(x) for x in changed]); print("Enjekte edilebilir:",inj,"referans-only:",unk); print("Metin farkı:",mis,"token farkı:",tok,"roundtrip:",rt,">52 satır:",long,"fiziksel TSV newline:",phys)
 if (inj,unk)!=(5715,2) or mis or tok or rt or long or phys or errors:
  for e in errors: print("HATA:",e)
  raise SystemExit(1)
 print("SONUÇ: TEMİZ")
if __name__=="__main__": main()
