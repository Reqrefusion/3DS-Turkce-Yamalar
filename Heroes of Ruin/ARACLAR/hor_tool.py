#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

from hor_formats import (
    TURKISH_CHARS,
    blz_compress,
    blz_decompress,
    darc_extract,
    darc_inject,
    export_strl,
    font_report,
    import_strl,
    parse_strl_file,
    protected_tokens,
    extract_ui_text_candidates,
    build_ui_text_patches,
)

STRL_NAMES = ['buffs', 'characterparts', 'dialogues', 'names', 'quests', 'strings', 'weapons']
LANG_COLUMNS = [('en', '_UK'), ('fr', '_FR'), ('de', '_GE'), ('it', '_IT'), ('es', '_SP')]


def cmd_blz_dec(a):
    Path(a.output).write_bytes(blz_decompress(Path(a.input).read_bytes()))


def cmd_blz_enc(a):
    src = Path(a.input).read_bytes()
    out = blz_compress(src)
    if blz_decompress(out) != src:
        raise RuntimeError('BLZ round-trip validation failed')
    Path(a.output).write_bytes(out)
    print(f'{len(src)} -> {len(out)} bytes')


def cmd_strl_extract(a):
    export_strl(Path(a.input), Path(a.output))


def cmd_strl_pack(a):
    import_strl(Path(a.input), Path(a.output), a.allow_token_change)
    print(f'Wrote {a.output}')


def cmd_language_extract(a):
    game = Path(a.game_dir)
    lang = game / a.lang
    out = Path(a.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = []
    for base in STRL_NAMES:
        src = lang / f'{base}.strl_'
        if not src.is_file():
            raise FileNotFoundError(src)
        dst = out / f'{base}.json'
        export_strl(src, dst)
        if a.csv:
            export_strl(src, out / f'{base}.csv')
        entries = parse_strl_file(src)
        report.append((base, len(entries), len({e.text for e in entries})))
        print(f'{base}: {len(entries)} entries -> {dst.name}')
    total = sum(x[1] for x in report)
    unique_sum = sum(x[2] for x in report)
    print(f'Total entries: {total}; per-file unique-text sum: {unique_sum}')



def _multilang_rows(game: Path, base: str) -> list[dict]:
    parsed = {}
    for col, folder in LANG_COLUMNS:
        src = game / folder / f'{base}.strl_'
        if not src.is_file():
            raise FileNotFoundError(src)
        parsed[col] = parse_strl_file(src)

    en = parsed['en']
    for col, _folder in LANG_COLUMNS[1:]:
        other = parsed[col]
        if len(other) != len(en):
            raise ValueError(f'{base}: {col} count {len(other)} != English count {len(en)}')
        for i, (a, b) in enumerate(zip(en, other)):
            if a.ident != b.ident:
                raise ValueError(
                    f'{base}: language ID mismatch at row {i}: '
                    f'EN=0x{a.ident:08X}, {col.upper()}=0x{b.ident:08X}'
                )

    rows = []
    for i, e in enumerate(en):
        rows.append({
            'index': i,
            'id': f'0x{e.ident:08X}',
            'en': parsed['en'][i].text,
            'fr': parsed['fr'][i].text,
            'de': parsed['de'][i].text,
            'it': parsed['it'][i].text,
            'es': parsed['es'][i].text,
            'tr': '',
        })
    return rows


def _write_multilang_file(path: Path, base: str, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == '.csv':
        with path.open('w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=['index', 'id', 'en', 'fr', 'de', 'it', 'es', 'tr'])
            w.writeheader()
            w.writerows(rows)
    else:
        payload = {
            'format': 'Heroes of Ruin STRL multi-language translation table',
            'file': f'{base}.strl_',
            'languages': {k: v for k, v in LANG_COLUMNS},
            'notes': [
                'Translate only the tr field. en/fr/de/it/es are side-by-side references.',
                'If tr is empty during build, English is used for that row.',
                'Protected control/variable tokens are validated against English.',
            ],
            'entries': rows,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def cmd_multilang_extract(a):
    game = Path(a.game_dir)
    out = Path(a.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    combined = []
    total = 0
    for base in STRL_NAMES:
        rows = _multilang_rows(game, base)
        _write_multilang_file(out / f'{base}.json', base, rows)
        if a.csv:
            _write_multilang_file(out / f'{base}.csv', base, rows)
        if a.combined_csv:
            for row in rows:
                combined.append({'file': base, **row})
        total += len(rows)
        print(f'{base}: {len(rows)} aligned rows (EN/FR/DE/IT/ES)')

    if a.combined_csv:
        combined_path = out / 'all_texts_multilang.csv'
        with combined_path.open('w', encoding='utf-8-sig', newline='') as f:
            fields = ['file', 'index', 'id', 'en', 'fr', 'de', 'it', 'es', 'tr']
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(combined)
        print(f'Combined CSV -> {combined_path.name}')
    print(f'Total aligned translation rows: {total}')

def cmd_language_build(a):
    srcdir = Path(a.translation_dir)
    out = Path(a.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for base in STRL_NAMES:
        inp = srcdir / f'{base}.{a.input_format}'
        if not inp.exists():
            raise FileNotFoundError(f'Missing {inp.name}')
        target = out / f'{base}.strl_'
        import_strl(inp, target, a.allow_token_change)
        print(f'{inp.name} -> {target.name}')


def cmd_darc_extract(a):
    m = darc_extract(Path(a.input), Path(a.output_dir))
    print(f'Extracted {len(m["files"])} files')


def cmd_darc_inject(a):
    notes = darc_inject(Path(a.original), Path(a.replacement_dir), Path(a.output))
    print('\n'.join(notes) if notes else 'No replacement files found; archive re-packed unchanged.')


def cmd_font_check(a):
    print(font_report(Path(a.input)))


def cmd_analyze(a):
    game = Path(a.game_dir)
    result = {'languages': {}, 'ui_font_references': [], 'code_markers': {}}
    for lang_dir in sorted(p for p in game.iterdir() if p.is_dir() and p.name.startswith('_')):
        row = {}
        for base in STRL_NAMES:
            p = lang_dir / f'{base}.strl_'
            if p.exists():
                es = parse_strl_file(p)
                row[base] = {'entries': len(es), 'unique_texts': len({e.text for e in es})}
        if row:
            result['languages'][lang_dir.name] = row

    ui = game / 'UI'
    if ui.is_dir():
        for p in sorted(ui.glob('*.arc_')):
            try:
                raw = blz_decompress(p.read_bytes())
            except Exception:
                continue
            count = raw.count(b'nintendo.bcfnt')
            if count:
                result['ui_font_references'].append({'file': p.name, 'nintendo.bcfnt_refs': count})

    code = game / 'code.bin'
    if code.is_file():
        b = code.read_bytes()
        for marker in [b'.STRL', b'DoCompressedLoad', b'nintendo.bcfnt', b'.bcfnt', b'Rom Font Viewer']:
            offs = []
            start = 0
            while True:
                q = b.find(marker, start)
                if q < 0:
                    break
                offs.append(f'0x{q:X}')
                start = q + 1
            result['code_markers'][marker.decode('ascii')] = offs

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if a.output:
        Path(a.output).write_text(text, encoding='utf-8')
    else:
        print(text)



def cmd_ui_text_extract(a):
    payload = extract_ui_text_candidates(Path(a.ui_dir), Path(a.output))
    from collections import Counter
    c = Counter(x['classification'] for x in payload['entries'])
    print(f"Extracted {len(payload['entries'])} non-empty txt1 entries from {payload['bclyt_files_scanned']} BCLYT files")
    for k, v in sorted(c.items()):
        print(f"  {k}: {v}")


def cmd_ui_text_build(a):
    rep = build_ui_text_patches(Path(a.ui_dir), Path(a.translation), Path(a.output_ui_dir), a.allow_token_change)
    print(f"Changed {rep['changed_text_entries']} text entries in {len(rep['archives_modified'])} UI archives")
    for x in rep['archives_modified']:
        print(f"  {x['archive']}: {x['changed_entries']} entries, packed {x['packed_size']} bytes")

def main():
    p = argparse.ArgumentParser(description='Heroes of Ruin (3DS) translation toolkit')
    sp = p.add_subparsers(dest='cmd', required=True)

    q = sp.add_parser('blz-decompress', help='Decompress a BLZ/backwards-LZ asset')
    q.add_argument('input'); q.add_argument('output'); q.set_defaults(func=cmd_blz_dec)
    q = sp.add_parser('blz-compress', help='Compress and round-trip validate a BLZ asset')
    q.add_argument('input'); q.add_argument('output'); q.set_defaults(func=cmd_blz_enc)

    q = sp.add_parser('strl-extract', help='Extract one .strl_ to JSON or CSV')
    q.add_argument('input'); q.add_argument('output'); q.set_defaults(func=cmd_strl_extract)
    q = sp.add_parser('strl-pack', help='Build one .strl_ from JSON or CSV')
    q.add_argument('input'); q.add_argument('output')
    q.add_argument('--allow-token-change', action='store_true')
    q.set_defaults(func=cmd_strl_pack)

    q = sp.add_parser('language-extract', help='Extract all seven STRL files for one language')
    q.add_argument('game_dir'); q.add_argument('output_dir')
    q.add_argument('--lang', default='_UK', help='Source language directory (default: _UK)')
    q.add_argument('--csv', action='store_true', help='Also create spreadsheet-friendly CSV files')
    q.set_defaults(func=cmd_language_extract)

    q = sp.add_parser('multilang-extract', help='Extract EN/FR/DE/IT/ES side-by-side with an editable TR column')
    q.add_argument('game_dir'); q.add_argument('output_dir')
    q.add_argument('--csv', action='store_true', help='Also create side-by-side CSV files')
    q.add_argument('--combined-csv', action='store_true', help='Also create one CSV containing all seven STRL tables')
    q.set_defaults(func=cmd_multilang_extract)

    q = sp.add_parser('language-build', help='Build all seven .strl_ files from translation JSON/CSV')
    q.add_argument('translation_dir'); q.add_argument('output_dir')
    q.add_argument('--input-format', choices=['json', 'csv'], default='json',
                   help='Which translation files to read (default: json)')
    q.add_argument('--allow-token-change', action='store_true')
    q.set_defaults(func=cmd_language_build)

    q = sp.add_parser('darc-extract', help='Decompress/extract one UI .arc_ DARC archive')
    q.add_argument('input'); q.add_argument('output_dir'); q.set_defaults(func=cmd_darc_extract)
    q = sp.add_parser('darc-inject', help='Replace DARC files in-place (size/capacity limited) and re-BLZ')
    q.add_argument('original'); q.add_argument('replacement_dir'); q.add_argument('output')
    q.set_defaults(func=cmd_darc_inject)

    q = sp.add_parser('font-check', help='Check Turkish glyph coverage in a raw BCFNT/shared-font dump')
    q.add_argument('input'); q.set_defaults(func=cmd_font_check)

    q = sp.add_parser('ui-text-extract', help='Extract non-empty BCLYT txt1 strings from all UI .arc_ files')
    q.add_argument('ui_dir'); q.add_argument('output'); q.set_defaults(func=cmd_ui_text_extract)
    q = sp.add_parser('ui-text-build', help='Build modified UI .arc_ files from edited BCLYT txt1 candidate JSON')
    q.add_argument('ui_dir'); q.add_argument('translation'); q.add_argument('output_ui_dir')
    q.add_argument('--allow-token-change', action='store_true')
    q.set_defaults(func=cmd_ui_text_build)

    q = sp.add_parser('analyze-game', help='Create a compact file/language/font-reference report')
    q.add_argument('game_dir'); q.add_argument('--output'); q.set_defaults(func=cmd_analyze)

    a = p.parse_args()
    try:
        a.func(a)
    except Exception as e:
        print(f'ERROR: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
