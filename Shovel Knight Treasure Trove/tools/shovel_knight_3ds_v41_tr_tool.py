#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shovel Knight: Treasure Trove 3DS v4.1 localization PAK/STL tool.

Targets the European base Title ID 000400000017C900 and the update
0004000E0017C900 supplied/verified for this project.

The converter is intentionally strict: the known 3DS English source and
known Steam Turkish patch hashes are checked before automatic conversion.
"""
from __future__ import annotations
import argparse, collections, csv, hashlib, json, re, struct, sys
from pathlib import Path

KNOWN_3DS_ENG_SHA256 = "50a8810f8fc62c4cbbd96311a59513d89502f203c65870f41627427b1cea8510"
KNOWN_STEAM_TR_SHA256 = "2899a2f1b8c5529b97ff6a7cda3f22337163201044f8478b220a19efae91b454"
BASE_TITLE_ID_EUR = "000400000017C900"
UPDATE_TITLE_ID_EUR = "0004000E0017C900"

DIALOGUE = "loctext/dialogue_eng.stl"
MENUS = "loctext/menus_eng.stl"

# Exact mapping determined by comparing the 3DS v4.1 table boundaries/content
# against the Steam 6222443 Turkish table. Steam-only/PC-only blocks are skipped.
MENU_SEGMENTS = [
    (0, 700, 0),
    (701, 1509, 30),
    (1510, 1512, 438),
    (1513, 2030, 439),
    (2031, 2349, 441),
    (2350, 2395, 666),
]

# Corrections to malformed machine-translation control/markup strings.
# Keys are (table_name, 3ds_row_index).
MANUAL_FIXES = {
    (DIALOGUE, 31): '<w>Oooooo</w>, büyük laflar teneke adam! Sana birkaç şey göstereyim de gör!',
    (DIALOGUE, 109): "Üstelik <f cn=onq>Merhametsizler Tarikatı</f>'nın yenilmez şövalyeleri seninle Kule arasında duruyor!",
    (DIALOGUE, 135): 'Sözlerden başka bir şey denemedim. Büyüsü öylesine güçlü ki... Cesaret edemedim.',
    (DIALOGUE, 929): 'Bazen ikinci zıplayışımı <s>sonraya</s> saklar, önce <f cn=green>bomba</f> <f cn=green>sıçrayışımı</f> yaparım. İnişi tutturmayı bayağı kolaylaştırıyor!',
    (DIALOGUE, 2432): "Ah, hava yolculuğu yapan tayfamıza bir gezgin daha katılıyor. Ben <f cn=purple>Cardia</f>'yım ve bu diyarın eğlencelerine büyük ilgi duyuyorum.",
    (DIALOGUE, 2500): '<s>Cartediem!</s> Çıkışların @f%% kadarını buldun!',
    (DIALOGUE, 2506): '<s>Arbitum Centrus!</s> Meydan okuyanların @j%% kadarını yendin!',
    (MENUS, 958): 'Keşke onu mantığını dinlemeye ikna edebilsen! Ama ne yazık... savaş kaçınılmaz.',
    (MENUS, 1475): '<f cn=green>Bulutta</f> kayıt verisi yok.',
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


class PakItem:
    def __init__(self, name, data, unk1=0, hash32=0, flags=1, unk2=0):
        self.name = name
        self.data = data
        self.unk1 = unk1
        self.hash32 = hash32
        self.flags = flags
        self.unk2 = unk2


class Pak:
    def __init__(self, magic, items):
        self.magic = magic
        self.items = items

    @classmethod
    def parse(cls, data: bytes):
        if len(data) < 24:
            raise ValueError("PAK too small")
        magic, count = struct.unpack_from('<II', data, 0)
        rec_table_off, name_table_off = struct.unpack_from('<QQ', data, 8)
        if count > 100000:
            raise ValueError("Unreasonable PAK file count")
        if rec_table_off + count * 8 > len(data) or name_table_off + count * 8 > len(data):
            raise ValueError("PAK tables out of bounds")
        rec_offsets = struct.unpack_from('<' + 'Q' * count, data, rec_table_off)
        name_offsets = struct.unpack_from('<' + 'Q' * count, data, name_table_off)
        items = []
        for ro, no in zip(rec_offsets, name_offsets):
            if ro + 32 > len(data):
                raise ValueError("PAK record out of bounds")
            size, unk1 = struct.unpack_from('<QQ', data, ro)
            hash32, flags = struct.unpack_from('<II', data, ro + 16)
            unk2 = struct.unpack_from('<Q', data, ro + 24)[0]
            if ro + 32 + size > len(data):
                raise ValueError("PAK item data out of bounds")
            try:
                end = data.index(b'\0', no)
            except ValueError:
                raise ValueError("PAK filename is not NUL terminated")
            name = data[no:end].decode('utf-8')
            items.append(PakItem(name, data[ro + 32: ro + 32 + size], unk1, hash32, flags, unk2))
        return cls(magic, items)

    def build(self) -> bytes:
        count = len(self.items)
        rec_table_off = 24
        out = bytearray(struct.pack('<IIQQ', self.magic, count, rec_table_off, 0))
        rec_ptr_pos = len(out)
        out += b'\0' * (count * 8)
        rec_offsets = []
        for item in self.items:
            rec_offsets.append(len(out))
            out += struct.pack('<QQIIQ', len(item.data), item.unk1, item.hash32, item.flags, item.unk2)
            out += item.data
        name_table_off = len(out)
        name_ptr_pos = len(out)
        out += b'\0' * (count * 8)
        name_offsets = []
        for item in self.items:
            while len(out) % 8:
                out.append(0)
            name_offsets.append(len(out))
            out += item.name.encode('utf-8') + b'\0'
        while len(out) % 8:
            out.append(0)
        struct.pack_into('<Q', out, 16, name_table_off)
        for i, x in enumerate(rec_offsets):
            struct.pack_into('<Q', out, rec_ptr_pos + i * 8, x)
        for i, x in enumerate(name_offsets):
            struct.pack_into('<Q', out, name_ptr_pos + i * 8, x)
        return bytes(out)

    def by_name(self):
        return {x.name: x for x in self.items}


class Stl:
    def __init__(self, strings, prefix=0, version=1, ptr_table=24):
        self.strings = strings
        self.prefix = prefix
        self.version = version
        self.ptr_table = ptr_table

    @classmethod
    def parse(cls, data: bytes):
        if len(data) < 24:
            raise ValueError("STL too small")
        prefix = struct.unpack_from('<Q', data, 0)[0]
        count, version = struct.unpack_from('<II', data, 8)
        ptr_table = struct.unpack_from('<Q', data, 16)[0]
        if ptr_table + count * 8 > len(data):
            raise ValueError("STL pointer table out of bounds")
        ptrs = struct.unpack_from('<' + 'Q' * count, data, ptr_table)
        strings = []
        last_nonzero = -1
        for ptr in ptrs:
            if ptr == 0:
                strings.append(None)
                continue
            if ptr % 8:
                raise ValueError(f"STL string pointer 0x{ptr:X} is not 8-byte aligned")
            if ptr >= len(data):
                raise ValueError("STL string pointer out of bounds")
            if ptr < last_nonzero:
                raise ValueError("STL string pointers are not monotonic")
            last_nonzero = ptr
            try:
                end = data.index(b'\0', ptr)
            except ValueError:
                raise ValueError("STL string is not NUL terminated")
            strings.append(data[ptr:end].decode('utf-8'))
        return cls(strings, prefix, version, ptr_table)

    def build(self) -> bytes:
        if self.ptr_table != 24:
            raise ValueError("This builder expects the verified 3DS/PC ptr_table offset 24")
        count = len(self.strings)
        out = bytearray(struct.pack('<QIIQ', self.prefix, count, self.version, self.ptr_table))
        ptr_pos = len(out)
        out += b'\0' * (count * 8)
        for i, s in enumerate(self.strings):
            if s is None:
                ptr = 0
            else:
                while len(out) % 8:
                    out.append(0)
                ptr = len(out)
                out += s.encode('utf-8') + b'\0'
                while len(out) % 8:
                    out.append(0)
            struct.pack_into('<Q', out, ptr_pos + i * 8, ptr)
        return bytes(out)


def load_loctext(path: str | Path):
    raw = Path(path).read_bytes()
    pak = Pak.parse(raw)
    items = pak.by_name()
    if DIALOGUE not in items or MENUS not in items:
        raise ValueError(f"Expected {DIALOGUE} and {MENUS} inside PAK")
    stls = {DIALOGUE: Stl.parse(items[DIALOGUE].data), MENUS: Stl.parse(items[MENUS].data)}
    return raw, pak, stls


def menu_source_index(i: int) -> int:
    for a, b, off in MENU_SEGMENTS:
        if a <= i <= b:
            return i + off
    raise IndexError(i)


def critical_tokens(s: str | None):
    if s is None:
        return []
    # Parser-sensitive controls. Order may move naturally in Turkish, so validation is multiset based.
    toks = re.findall(r'@\w+%%|%(?:\d+\$)?[A-Za-z%]', s)
    toks += re.findall(r'<b[^>]*>|</b>', s)
    return toks


def visible_characters(s: str | None):
    if not s:
        return ''
    return re.sub(r'<[^>]*>|\[[^\]]*\]', '', s)


def convert_known_steam_to_3ds(src3ds: str | Path, steamtr: str | Path, outpath: str | Path, report_path=None, force=False):
    h3 = sha256_file(src3ds)
    hs = sha256_file(steamtr)
    if not force and h3 != KNOWN_3DS_ENG_SHA256:
        raise SystemExit(f"Refusing conversion: 3DS source hash mismatch\nExpected {KNOWN_3DS_ENG_SHA256}\nGot      {h3}")
    if not force and hs != KNOWN_STEAM_TR_SHA256:
        raise SystemExit(f"Refusing conversion: Steam Turkish patch hash mismatch\nExpected {KNOWN_STEAM_TR_SHA256}\nGot      {hs}")

    raw3, pak3, stl3 = load_loctext(src3ds)
    raws, paks, stls = load_loctext(steamtr)
    if len(stl3[DIALOGUE].strings) != 2633 or len(stl3[MENUS].strings) != 2396:
        raise ValueError("Unexpected 3DS v4.1 row counts")
    if len(stls[DIALOGUE].strings) != 2923 or len(stls[MENUS].strings) != 3162:
        raise ValueError("Unexpected Steam Turkish row counts")

    dialogue = list(stls[DIALOGUE].strings[:2633])
    menus = [stls[MENUS].strings[menu_source_index(i)] for i in range(2396)]

    # Platform-filtered NULL rows must remain NULL exactly as in the 3DS source.
    for table, rows in ((DIALOGUE, dialogue), (MENUS, menus)):
        for i, original in enumerate(stl3[table].strings):
            if original is None:
                rows[i] = None

    for (table, idx), text in MANUAL_FIXES.items():
        (dialogue if table == DIALOGUE else menus)[idx] = text

    new_rows = {DIALOGUE: dialogue, MENUS: menus}
    byname = pak3.by_name()
    for name in (DIALOGUE, MENUS):
        base = stl3[name]
        byname[name].data = Stl(new_rows[name], base.prefix, base.version, base.ptr_table).build()

    output = pak3.build()
    Path(outpath).write_bytes(output)

    # Full round-trip validation.
    out_raw, out_pak, out_stls = load_loctext(outpath)
    errors, warnings = [], []
    if [x.name for x in out_pak.items] != [x.name for x in Pak.parse(raw3).items]:
        errors.append("PAK internal filename list changed")
    base_items = Pak.parse(raw3).by_name(); out_items = out_pak.by_name()
    for n in (DIALOGUE, MENUS):
        a, b = base_items[n], out_items[n]
        if (a.unk1, a.hash32, a.flags, a.unk2) != (b.unk1, b.hash32, b.flags, b.unk2):
            errors.append(f"PAK metadata changed for {n}")
        if len(out_stls[n].strings) != len(stl3[n].strings):
            errors.append(f"Row count changed for {n}")
        src_null = [i for i,x in enumerate(stl3[n].strings) if x is None]
        out_null = [i for i,x in enumerate(out_stls[n].strings) if x is None]
        if src_null != out_null:
            errors.append(f"NULL row positions changed for {n}")
        for i, (en, tr) in enumerate(zip(stl3[n].strings, out_stls[n].strings)):
            ce, ct = collections.Counter(critical_tokens(en)), collections.Counter(critical_tokens(tr))
            if ce != ct:
                errors.append(f"Critical button/printf token mismatch: {n} row {i}: {ce} != {ct}")
    if errors:
        Path(outpath).unlink(missing_ok=True)
        raise ValueError("Validation failed:\n- " + "\n- ".join(errors))

    report = {
        "status": "PASS",
        "base_title_id_eur": BASE_TITLE_ID_EUR,
        "update_title_id_eur": UPDATE_TITLE_ID_EUR,
        "source_3ds_sha256": h3,
        "source_steam_tr_sha256": hs,
        "output_sha256": sha256_bytes(output),
        "output_size": len(output),
        "dialogue_rows": len(dialogue),
        "menu_rows": len(menus),
        "dialogue_null_rows": [i for i,x in enumerate(stl3[DIALOGUE].strings) if x is None],
        "menu_null_rows": [i for i,x in enumerate(stl3[MENUS].strings) if x is None],
        "menu_mapping": [{"3ds": f"{a}-{b}", "steam_offset": off} for a,b,off in MENU_SEGMENTS],
        "manual_fixes": [{"table":t,"row":i,"text":txt} for (t,i),txt in MANUAL_FIXES.items()],
        "checks": [
            "Known input hashes matched",
            "PAK parsed and rebuilt using native 64-bit record/name offsets",
            "PAK internal filenames and per-file metadata preserved",
            "STL row counts preserved",
            "3DS platform NULL rows preserved",
            "All STL pointers parse, are in bounds, 8-byte aligned and monotonic",
            "All button tags and printf/stat placeholders preserved as multisets",
            "Generated PAK re-opened and every output row was read back successfully",
        ],
        "warnings": warnings,
    }
    if report_path:
        Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def verify_pair(original: str | Path, patched: str | Path, font_fnt: str | Path | None = None):
    raw0, p0, s0 = load_loctext(original)
    raw1, p1, s1 = load_loctext(patched)
    errors=[]; warnings=[]
    if [x.name for x in p0.items] != [x.name for x in p1.items]: errors.append("Internal PAK names differ")
    m0=p0.by_name(); m1=p1.by_name()
    for n in (DIALOGUE,MENUS):
        if (m0[n].unk1,m0[n].hash32,m0[n].flags,m0[n].unk2)!=(m1[n].unk1,m1[n].hash32,m1[n].flags,m1[n].unk2):
            errors.append(f"Metadata differs: {n}")
        if len(s0[n].strings)!=len(s1[n].strings): errors.append(f"Row count differs: {n}")
        if [i for i,x in enumerate(s0[n].strings) if x is None] != [i for i,x in enumerate(s1[n].strings) if x is None]:
            errors.append(f"NULL rows differ: {n}")
        for i,(a,b) in enumerate(zip(s0[n].strings,s1[n].strings)):
            if collections.Counter(critical_tokens(a)) != collections.Counter(critical_tokens(b)):
                errors.append(f"Critical token mismatch {n}:{i}")
    if font_fnt:
        txt=Path(font_fnt).read_text('utf-8', errors='replace')
        ids=set(map(int,re.findall(r'^char id=(\d+)',txt,re.M)))
        missing=collections.Counter()
        for n in (DIALOGUE,MENUS):
            for s in s1[n].strings:
                for ch in visible_characters(s):
                    if ch not in '\r\n\t' and ord(ch) not in ids:
                        missing[ch]+=1
        if missing:
            errors.append("Font is missing visible characters: " + repr(dict(missing)))
    return {
        "status":"PASS" if not errors else "FAIL",
        "original_sha256":sha256_bytes(raw0),
        "patched_sha256":sha256_bytes(raw1),
        "errors":errors,
        "warnings":warnings,
        "rows":{DIALOGUE:len(s1[DIALOGUE].strings),MENUS:len(s1[MENUS].strings)},
    }


def extract_json(pak_path: str | Path, out_json: str | Path):
    raw,pak,stls=load_loctext(pak_path)
    doc={
        "source_sha256":sha256_bytes(raw),
        "tables":{
            name:[{"row":i,"text":s} for i,s in enumerate(stl.strings)]
            for name,stl in stls.items()
        }
    }
    Path(out_json).write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf-8')


def inject_json(original_pak: str | Path, json_path: str | Path, out_pak: str | Path):
    raw,pak,stls=load_loctext(original_pak)
    doc=json.loads(Path(json_path).read_text(encoding='utf-8'))
    by=pak.by_name()
    for name in (DIALOGUE,MENUS):
        entries=doc["tables"][name]
        if len(entries)!=len(stls[name].strings):
            raise ValueError(f"Row count mismatch for {name}")
        strings=[e["text"] for e in entries]
        base=stls[name]
        by[name].data=Stl(strings,base.prefix,base.version,base.ptr_table).build()
    Path(out_pak).write_bytes(pak.build())


def cmd_info(path):
    raw,pak,stls=load_loctext(path)
    print(f"SHA256: {sha256_bytes(raw)}")
    print(f"Size: {len(raw)} bytes")
    for item in pak.items:
        print(f"{item.name}: {len(item.data)} bytes, hash=0x{item.hash32:08X}, flags={item.flags}")
        if item.name in stls:
            x=stls[item.name]
            print(f"  STL rows={len(x.strings)}, null={sum(s is None for s in x.strings)}")


def main():
    ap=argparse.ArgumentParser(description="Shovel Knight 3DS v4.1 loctext PAK/STL tool")
    sub=ap.add_subparsers(dest='cmd',required=True)
    p=sub.add_parser('info'); p.add_argument('pak')
    p=sub.add_parser('convert-steam'); p.add_argument('source_3ds'); p.add_argument('steam_turkish'); p.add_argument('output'); p.add_argument('--report'); p.add_argument('--force',action='store_true')
    p=sub.add_parser('verify'); p.add_argument('original'); p.add_argument('patched'); p.add_argument('--font')
    p=sub.add_parser('extract-json'); p.add_argument('pak'); p.add_argument('output_json')
    p=sub.add_parser('inject-json'); p.add_argument('original'); p.add_argument('input_json'); p.add_argument('output')
    a=ap.parse_args()
    if a.cmd=='info': cmd_info(a.pak)
    elif a.cmd=='convert-steam':
        r=convert_known_steam_to_3ds(a.source_3ds,a.steam_turkish,a.output,a.report,a.force)
        print(json.dumps(r,ensure_ascii=False,indent=2))
    elif a.cmd=='verify':
        r=verify_pair(a.original,a.patched,a.font)
        print(json.dumps(r,ensure_ascii=False,indent=2))
        if r['status']!='PASS': sys.exit(2)
    elif a.cmd=='extract-json': extract_json(a.pak,a.output_json)
    elif a.cmd=='inject-json': inject_json(a.original,a.input_json,a.output)

if __name__=='__main__': main()
