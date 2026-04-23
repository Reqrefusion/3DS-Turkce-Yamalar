#!/usr/bin/env python3
from pathlib import Path
import json
REPLACEMENTS=[('Dreamy Chez Broque', 'Düşlü Şe Brok'), ('Rose Broquet', 'Brok Gülü'), ('Chez Broque', 'Şe Brok'), ('Massif Bros.', 'Kasif Kardeşler'), ('Massif Bros', 'Kasif Kardeşler'), ('Massif Kardeşler', 'Kasif Kardeşler'), ('Big Massif', 'Koca Kasif'), ("Li'l Massif", 'Küçük Kasif'), ('Little Massif', 'Küçük Kasif'), ('Ufak Massif', 'Ufak Kasif'), ('Büyük Massif', 'Koca Kasif'), ('Massif', 'Kasif'), ('Pajamaja', 'Pijamaca'), ('Luiginary', 'Luijiner'), ('Eldream', 'Düşdede'), ('Britta', 'Blokinda'), ('Sneezemore', 'Hapşırmor'), ('Snoozemore', 'Mışılmor'), ('Dozite', 'Mışılit'), ('Grobot', 'Mışılbot'), ('Hooraws', 'Hurralar'), ('Hooraw', 'Hurra'), ('Seadring', 'Düşatı'), ('Seadric', 'Düşerik'), ('Seatoon', 'Düştun'), ('Seabelle', 'Düşbel')]
FIELDS=("text","tokenized_text")
def apply_to_all_json(src_all_json:str,out_dir:str)->int:
    src=Path(src_all_json); out=Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    data=json.loads(src.read_text(encoding="utf-8")); changed=[]
    for fname,ents in data.items():
        for eid,rec in ents.items():
            before=rec.get("text",""); modified=False
            for field in FIELDS:
                if field in rec:
                    val=rec[field]; new=val
                    for old,new_val in REPLACEMENTS: new=new.replace(old,new_val)
                    if new!=val:
                        rec[field]=new; modified=True
            if modified: changed.append({"file":fname,"id":eid,"before":before,"after":rec["text"]})
    (out/"all.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    per=out/"per_msbt"; per.mkdir(exist_ok=True)
    for fname,ents in data.items():
        (per/f"{fname}.json").write_text(json.dumps(ents,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"changed_entries.json").write_text(json.dumps(changed,ensure_ascii=False,indent=2),encoding="utf-8")
    return len(changed)
if __name__=="__main__":
    import sys
    if len(sys.argv)!=3: raise SystemExit("usage: tr_name_localizer.py <all.json> <out_dir>")
    print(f"changed entries: {apply_to_all_json(sys.argv[1], sys.argv[2])}")
