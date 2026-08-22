from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from hor_formats import import_strl
from hor_font_patch import patch_font

TITLE_ID = '0004000000074000'
STRL_NAMES = ['buffs','characterparts','dialogues','names','quests','strings','weapons']


def copytree_contents(src: Path, dst: Path) -> None:
    for p in src.rglob('*'):
        rel = p.relative_to(src)
        q = dst / rel
        if p.is_dir():
            q.mkdir(parents=True, exist_ok=True)
        else:
            q.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, q)


def main() -> None:
    here = Path(__file__).resolve().parent
    root = here.parent
    ap = argparse.ArgumentParser(description='Heroes of Ruin Turkce yama paketleyici')
    ap.add_argument('--translations', default=str(root / 'CEVIRI' / 'translation_multilang'))
    ap.add_argument('--font', default=str(root / 'FONT' / 'demo_font_orijinal.bcfnt_'))
    ap.add_argument('--output', default=str(root / 'YAMA_YENIDEN_OLUSTURULDU'))
    ap.add_argument('--input-format', choices=['csv','json'], default='csv')
    ap.add_argument('--slot', default='_UK', help='Turkce ile degistirilecek dil klasoru; varsayilan _UK')
    ap.add_argument('--title-id', default=TITLE_ID)
    args = ap.parse_args()

    trans = Path(args.translations)
    font = Path(args.font)
    out = Path(args.output)
    if out.exists(): shutil.rmtree(out)
    generic = out / 'romfs'
    lang = generic / args.slot
    lang.mkdir(parents=True, exist_ok=True)

    total = 0
    for base in STRL_NAMES:
        inp = trans / f'{base}.{args.input_format}'
        if not inp.is_file(): raise FileNotFoundError(inp)
        target = lang / f'{base}.strl_'
        import_strl(inp, target)
        total += 1
        print(f'{inp.name} -> {target}')

    if font.is_file():
        raw, packed, _mapping = patch_font(font.read_bytes())
        # Yuklenen fontun asil RomFS yolu upload sirasinda korunmadigi icin
        # kok + UI ve ham + BLZ adlarini birlikte olusturuyoruz.
        for rel, blob in [
            ('demo_font.bcfnt_', packed), ('demo_font.bcfnt', raw),
            ('UI/demo_font.bcfnt_', packed), ('UI/demo_font.bcfnt', raw),
        ]:
            p = generic / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(blob)
        print('Font yamasi eklendi.')
    else:
        print('UYARI: Font dosyasi bulunamadi; yalnizca STRL yama olusturuldu.')

    luma = out / 'Luma3DS_SD_KOKUNE_KOPYALA' / 'luma' / 'titles' / args.title_id / 'romfs'
    azahar = out / 'Azahar_Citra_Mod_Klasorune_Kopyala' / 'romfs'
    copytree_contents(generic, luma)
    copytree_contents(generic, azahar)
    print(f'Tamamlandi: {out}')
    print(f'STRL: {total}/7')


if __name__ == '__main__':
    main()
