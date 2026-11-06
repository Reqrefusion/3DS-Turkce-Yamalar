from __future__ import annotations
import csv, io, json, os, re, shutil, tempfile, zipfile
from pathlib import Path
from typing import Dict, List, Tuple
from .msbt import MsbtFile, control_tokens
from .bffnt import missing_chars

LANG_ORDER = [
    "EU_English", "US_English", "EU_French", "US_French", "EU_German",
    "EU_Italian", "EU_Spanish", "US_Spanish", "JP_Japanese", "KR_Korean"
]


def read_zip_languages(zip_path: str | Path, basename: str = "fluff.msbt") -> Tuple[List[str], List[dict]]:
    zip_path = Path(zip_path)
    with zipfile.ZipFile(zip_path, "r") as z:
        names = set(z.namelist())
        langs = []
        parsed: Dict[str, MsbtFile] = {}
        for lang in LANG_ORDER:
            n = f"message/{lang}/{basename}"
            if n in names:
                langs.append(lang)
                parsed[lang] = MsbtFile.from_bytes(z.read(n))
        if not langs:
            raise ValueError(f"message/*/{basename} bulunamadı")
        base = parsed[langs[0]]
        for lang in langs[1:]:
            cur = parsed[lang]
            if cur.labels != base.labels:
                raise ValueError(f"Etiket hizası farklı: {lang}")
        rows = []
        for i, label in enumerate(base.labels):
            row = {"Index": i, "Label": label}
            for lang in langs:
                row[lang] = parsed[lang].texts[i]
            row["Turkish"] = ""
            row["Status"] = "TODO"
            row["Notes"] = ""
            rows.append(row)
        return langs, rows


def export_csv(zip_path: str | Path, csv_path: str | Path, basename: str = "fluff.msbt") -> Tuple[List[str], int]:
    langs, rows = read_zip_languages(zip_path, basename)
    fields = ["Index", "Label"] + langs + ["Turkish", "Status", "Notes"]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return langs, len(rows)


def load_translation_csv(csv_path: str | Path) -> List[dict]:
    with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def validate_rows(rows: List[dict], source_col: str = "EU_English") -> List[str]:
    errors: List[str] = []
    for r in rows:
        label = r.get("Label", "?")
        src = r.get(source_col, "")
        tr = r.get("Turkish", "")
        if not tr and src:
            errors.append(f"{label}: Turkish boş")
            continue
        if sorted(control_tokens(src)) != sorted(control_tokens(tr)):
            errors.append(f"{label}: kontrol kodları korunmamış")
    return errors


def layout_risk(src: str, tr: str, peer_texts: List[str]) -> str:
    if not tr:
        return "EMPTY"
    src_lines = src.splitlines() or [src]
    tr_lines = tr.splitlines() or [tr]
    max_peer_lines = max([len((p or "").splitlines()) for p in peer_texts] + [len(src_lines)])
    peer_max_chars = max([max([len(x) for x in (p or "").splitlines()] or [0]) for p in peer_texts] + [1])
    tr_max = max([len(x) for x in tr_lines] or [0])
    if len(tr_lines) > max_peer_lines + 1:
        return "HIGH_LINES"
    if tr_max > peer_max_chars * 1.35 + 4:
        return "HIGH_WIDTH"
    if tr_max > peer_max_chars * 1.15 + 2:
        return "MEDIUM_WIDTH"
    return "OK"


def build_patched_zip(source_zip: str | Path, csv_path: str | Path, out_zip: str | Path,
                      replace_locale: str = "EU_English", basename: str = "fluff.msbt",
                      strict: bool = True) -> dict:
    rows = load_translation_csv(csv_path)
    with zipfile.ZipFile(source_zip, "r") as zin:
        src_name = f"message/{replace_locale}/{basename}"
        if src_name not in zin.namelist():
            raise ValueError(f"Hedef locale bulunamadı: {src_name}")
        msbt = MsbtFile.from_bytes(zin.read(src_name))
        by_label = {r.get("Label", ""): r for r in rows}
        new_texts = []
        problems = []
        for i, label in enumerate(msbt.labels):
            r = by_label.get(label)
            if not r:
                problems.append(f"{label}: CSV satırı yok")
                new_texts.append(msbt.texts[i])
                continue
            tr = r.get("Turkish", "")
            if not tr and msbt.texts[i]:
                problems.append(f"{label}: Turkish boş")
                new_texts.append(msbt.texts[i])
                continue
            if sorted(control_tokens(msbt.texts[i])) != sorted(control_tokens(tr)):
                problems.append(f"{label}: kontrol kodu uyuşmuyor")
                new_texts.append(msbt.texts[i])
                continue
            new_texts.append(tr)
        if strict and problems:
            raise ValueError("Derleme durduruldu:\n" + "\n".join(problems[:50]) + (f"\n... +{len(problems)-50}" if len(problems)>50 else ""))
        patched = msbt.to_bytes(new_texts)
        with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = patched if info.filename == src_name else zin.read(info.filename)
                zout.writestr(info, data)
    return {"target": src_name, "rows": len(new_texts), "problems": problems}


def build_layeredfs(source_zip: str | Path, csv_path: str | Path, out_dir: str | Path,
                    title_id: str, replace_locale: str = "EU_English") -> dict:
    rows = load_translation_csv(csv_path)
    with zipfile.ZipFile(source_zip, "r") as z:
        src_name = f"message/{replace_locale}/fluff.msbt"
        msbt = MsbtFile.from_bytes(z.read(src_name))
        by_label = {r.get("Label", ""): r for r in rows}
        new = []
        for i, label in enumerate(msbt.labels):
            r = by_label.get(label)
            tr = (r or {}).get("Turkish", "")
            if not tr and msbt.texts[i]:
                raise ValueError(f"Eksik Türkçe: {label}")
            if sorted(control_tokens(msbt.texts[i])) != sorted(control_tokens(tr)):
                raise ValueError(f"Kontrol kodu uyuşmuyor: {label}")
            new.append(tr)
        target = Path(out_dir) / "luma" / "titles" / title_id / "romfs" / "message" / replace_locale
        target.mkdir(parents=True, exist_ok=True)
        (target / "fluff.msbt").write_bytes(msbt.to_bytes(new))
        # Project metadata is copied unchanged if present.
        msbp_name = f"message/{replace_locale}/fluff.msbp"
        if msbp_name in z.namelist():
            (target / "fluff.msbp").write_bytes(z.read(msbp_name))
        return {"path": str(target), "rows": len(new)}


def font_report_from_zip(zip_path: str | Path, texts: List[str]) -> dict:
    out = {}
    with zipfile.ZipFile(zip_path, "r") as z:
        for name in ["frame/font/GameFont1.bffnt", "frame/font/GameFont2.bffnt"]:
            if name not in z.namelist():
                continue
            with tempfile.NamedTemporaryFile(suffix=".bffnt", delete=False) as tf:
                tf.write(z.read(name)); temp = tf.name
            try:
                miss = missing_chars(temp, texts)
            finally:
                os.unlink(temp)
            out[name] = sorted(miss)
    return out


def asset_scan(zip_path: str | Path) -> List[dict]:
    sigs = [(b"\x89PNG\r\n\x1a\n", "PNG"), (b"JFIF", "JPEG/JFIF"), (b"CTPK", "CTPK"),
            (b"CLIM", "BCLIM"), (b"FLIM", "BFLIM"), (b"CGFX", "CGFX"), (b"BCH\x00", "BCH")]
    rows = []
    with zipfile.ZipFile(zip_path, "r") as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            data = z.read(info.filename)
            hits = []
            for sig, kind in sigs:
                positions = []
                start = 0
                while True:
                    p = data.find(sig, start)
                    if p < 0: break
                    positions.append(p); start = p + 1
                if positions:
                    hits.append({"kind": kind, "offsets": positions[:32]})
            if hits:
                rows.append({"file": info.filename, "size": info.file_size, "hits": hits})
    return rows
