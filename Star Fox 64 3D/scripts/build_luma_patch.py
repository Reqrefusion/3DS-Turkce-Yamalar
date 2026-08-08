#!/usr/bin/env python3
from __future__ import annotations
import argparse, sys, zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
TOOLS=ROOT/'tools'
sys.path.insert(0, str(TOOLS))
from translation_common import control_tokens, load_jsonl, source_hash
import starfox64_3d_tr_tool as tool

TITLE_IDS={"EUR":"0004000000049100","USA":"0004000000049000"}

def fail(msg: str) -> None:
    raise SystemExit("HATA: "+msg)

def main() -> int:
    ap=argparse.ArgumentParser(description="Star Fox 64 3D Türkçe Luma3DS yaması oluştur")
    ap.add_argument("resources", help="Kendi oyununuzdan çıkardığınız Resources.zip veya Resources klasörü")
    ap.add_argument("--translation", default=str(ROOT/'translations'/'tr_TR.jsonl'))
    ap.add_argument("--region", choices=TITLE_IDS, default="EUR")
    ap.add_argument("--output", default=None)
    args=ap.parse_args()
    source=Path(args.resources)
    translation=Path(args.translation)
    output=Path(args.output) if args.output else ROOT/'dist'/f"StarFox64_3D_TR_Luma_{args.region}.zip"
    rows=load_jsonl(translation)
    rs=tool.open_resource_source(source)
    try:
        ok, errs=tool.self_test_source(rs)
        if errs: fail("Kaynak MSBT güvenlik testi başarısız: "+" | ".join(errs[:5]))
        available={tool.rel_key(rs,p):p for p in tool.find_msbt_files(rs)}
        parsed={}
        patches={}
        for row in rows:
            key=row['file']; idx=row['index']
            if key not in available: fail(f"Kaynakta gerekli MSBT yok: {key}")
            if key not in parsed: parsed[key]=tool.parse_msbt(available[key])
            msbt=parsed[key]
            if idx < 0 or idx >= len(msbt.entries): fail(f"{key}: geçersiz index {idx}")
            ent=msbt.entries[idx]
            if source_hash(ent.text) != row['source_sha256']:
                fail(f"{key}/{idx}: kaynak metin sürümü uyuşmuyor (SHA-256 farklı). Doğru oyun/bölge kaynaklarını kullanın.")
            if control_tokens(ent.text) != row['control_tokens']:
                fail(f"{key}/{idx}: kaynak kontrol tokenları meta verisiyle uyuşmuyor")
            if control_tokens(row['translation']) != row['control_tokens']:
                fail(f"{key}/{idx}: çeviri kontrol tokenları bozulmuş")
            patches.setdefault(key,{})[idx]=row['translation']
        changed=[]
        for key in sorted(patches):
            src=available[key]
            original=src.read_bytes()
            rebuilt=tool.rebuild_msbt(parsed[key], patches[key])
            tool.parse_msbt_bytes(rebuilt, key)
            if rebuilt != original: changed.append((key, rebuilt))
        if not changed: fail("Uygulanacak değişiklik bulunamadı")
        output.parent.mkdir(parents=True, exist_ok=True)
        title_id=TITLE_IDS[args.region]
        with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as zf:
            for key,data in changed:
                zf.writestr(f"luma/titles/{title_id}/romfs/Resources/{key}", data)
            zf.writestr('KURULUM.txt', f"""Star Fox 64 3D Türkçe yama\nBölge: {args.region}\nTitle ID: {title_id}\n\nZIP içeriğini SD kartın köküne çıkarın.\nLuma3DS yapılandırmasında 'Enable game patching' açık olmalı.\nOyunu İngilizce dilinde başlatın.\n""")
        with zipfile.ZipFile(output,'r') as zf:
            bad=zf.testzip()
            if bad: fail(f"ZIP CRC hatası: {bad}")
        print(f"OK: {ok} kaynak MSBT binary-identical testten geçti")
        print(f"OK: {len(rows)} çeviri kaydı kaynak SHA-256 ile doğrulandı")
        print(f"OK: {len(changed)} MSBT yamaya eklendi")
        print(f"Çıkış: {output}")
        return 0
    finally:
        rs.close()

if __name__ == '__main__': raise SystemExit(main())
