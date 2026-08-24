from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from ktl.project import (
    build_patched_zip,
    build_layeredfs,
    load_translation_csv,
    validate_rows,
    font_report_from_zip,
)
from ktl.fullpatch import build_full_patched_zip, build_layeredfs_all

ROOT = Path(__file__).resolve().parent
DEFAULT_ZIP = ROOT / "input" / "source.zip"
DEFAULT_CSV = ROOT / "data" / "Kirby_TR_translated.csv"


def cli():
    ap = argparse.ArgumentParser(
        description="Kirby's Extra Epic Yarn - CSV tabanli Turkce MSBT araclari"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("validate", help="CSV ve kontrol kodlarini dogrula")
    p.add_argument("csv", nargs="?", default=str(DEFAULT_CSV))
    p.add_argument("--source", default="EU_English")

    p = sub.add_parser("build-zip", help="Turkceyi secilen dilin fluff.msbt dosyasina enjekte et")
    p.add_argument("zip", nargs="?", default=str(DEFAULT_ZIP))
    p.add_argument("csv", nargs="?", default=str(DEFAULT_CSV))
    p.add_argument("out", nargs="?", default=str(ROOT / "output" / "Kirby_TR_patched_EU_English.zip"))
    p.add_argument("--locale", default="EU_English")

    p = sub.add_parser("build-layeredfs", help="Luma3DS LayeredFS klasoru olustur")
    p.add_argument("zip", nargs="?", default=str(DEFAULT_ZIP))
    p.add_argument("csv", nargs="?", default=str(DEFAULT_CSV))
    p.add_argument("outdir", nargs="?", default=str(ROOT / "output" / "layeredfs"))
    p.add_argument("--locale", default="EU_English")
    p.add_argument("--title-id", default="00040000001D1F00")


    p = sub.add_parser("build-full", help="Tüm 10 dil klasörünü + HOME icon/code.bin başlığını Türkçeleştir; stilize bannerı orijinal bırak")
    p.add_argument("zip", nargs="?", default=str(DEFAULT_ZIP))
    p.add_argument("csv", nargs="?", default=str(DEFAULT_CSV))
    p.add_argument("out", nargs="?", default=str(ROOT / "output" / "Kirby_Extra_Epic_Yarn_TR_FINAL_SAFE.zip"))

    p = sub.add_parser("build-layeredfs-all", help="Tüm dil klasörleri için Türkçe LayeredFS RomFS oluştur")
    p.add_argument("zip", nargs="?", default=str(DEFAULT_ZIP))
    p.add_argument("csv", nargs="?", default=str(DEFAULT_CSV))
    p.add_argument("outdir", nargs="?", default=str(ROOT / "output" / "layeredfs_all"))
    p.add_argument("--title-id", default="00040000001D1F00")

    p = sub.add_parser("font-check", help="Turkce metindeki karakterlerin oyun fontlarinda bulunup bulunmadigini denetle")
    p.add_argument("zip", nargs="?", default=str(DEFAULT_ZIP))
    p.add_argument("csv", nargs="?", default=str(DEFAULT_CSV))

    a = ap.parse_args()
    if a.cmd == "validate":
        errs = validate_rows(load_translation_csv(a.csv), a.source)
        print("\n".join(errs) if errs else "OK - CSV ve kontrol kodlari gecerli.")
        raise SystemExit(1 if errs else 0)
    if a.cmd == "build-zip":
        print(json.dumps(build_patched_zip(a.zip, a.csv, a.out, a.locale, strict=True), ensure_ascii=False, indent=2))
        return
    if a.cmd == "build-layeredfs":
        print(json.dumps(build_layeredfs(a.zip, a.csv, a.outdir, a.title_id, a.locale), ensure_ascii=False, indent=2))
        return
    if a.cmd == "build-full":
        print(json.dumps(build_full_patched_zip(a.zip, a.csv, a.out), ensure_ascii=False, indent=2))
        return
    if a.cmd == "build-layeredfs-all":
        print(json.dumps(build_layeredfs_all(a.zip, a.csv, a.outdir, a.title_id), ensure_ascii=False, indent=2))
        return
    if a.cmd == "font-check":
        rows = load_translation_csv(a.csv)
        texts = [r.get("Turkish", "") for r in rows]
        print(json.dumps(font_report_from_zip(a.zip, texts), ensure_ascii=False, indent=2))
        return


if __name__ == "__main__":
    cli()
