"""Rebuild four reviewed Turkish title atlases from the multilingual source plates.

The textless PNGs in sourceplates are required. Run from any directory with
``python dort_unvan_atlasini_yenile.py``. This changes exactly four ARC files.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from scipy import ndimage
import sf4_tr_tool as sf4

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
FONT = HERE / 'fonts/NimbusSansNarrow-BoldOblique.otf'
TITLES = {
    '014': ('Kriz Kralı', 'Ezici As', 'Yıkım Ası'),
    '078': ('Kaslarıma Bak', 'Mohikanlı Güreşçi', 'Bir Tur At'),
    '150': ('Ritim Ustası', 'Işıl Işıl Dişler', 'Kırmızı Ninja'),
    '186': ('Sonsuza Dek Marakas', 'Spor Ayakkabı Adam', 'Kural Yok'),
}
ROW_MAP = {
    '014': (((12, 41), (4, 33)), ((49, 78), (42, 71)), ((87, 115), (80, 109))),
    '078': (((4, 44), (0, 36)), ((45, 84), (38, 74)), ((85, 123), (76, 112))),
    '150': (((4, 42), (0, 36)), ((45, 82), (38, 74)), ((85, 122), (76, 112))),
    '186': (((5, 36), (2, 34)), ((44, 74), (39, 72)), ((82, 112), (77, 110))),
}


def image_for(index: str) -> Image.Image:
    if index == '014':
        reference = next((ROOT / 'CALISMA_ALANI/images/_GUI/_id/_title/title014.arc').glob('*.spa.png'))
        pixels = np.asarray(Image.open(reference).convert('RGBA')).copy()
        # Five sources share the same translucent horizontal stripes. The
        # Spanish lettering differs; restore each internal scan line using
        # existing uncovered red pixels from that line, retaining alpha.
        for top in (0, 37, 75):
            for y in range(top+11, top+28):
                strip = pixels[y, 25:165]
                clean = strip[(strip[:, 0] > 200) & (strip[:, 1] < 120) &
                              (strip[:, 2] < 120) & (strip[:, 3] < 160)]
                if len(clean) < 12:
                    continue
                pixels[y, 29:161] = np.median(clean, axis=0).astype('uint8')
        aligned = Image.fromarray(pixels, 'RGBA')
    else:
        aligned = Image.open(ROOT / 'CALISMA_ALANI/temiz_zeminler'/f'title{index}_textless.png').convert('RGBA')
    base = aligned.resize((1024, 512), Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(base)
    for row, label in enumerate(TITLES[index]):
        font = ImageFont.truetype(str(FONT), 66)
        # The reference language labels all end within pixel 175; fit each
        # translation to the same brush without changing its height radically.
        width = 590 if index == '014' else 570
        stroke = 5 if index != '186' else 6
        while True:
            bbox = draw.textbbox((0, 0), label, font=font, stroke_width=stroke)
            if bbox[2] - bbox[0] <= width:
                break
            font = ImageFont.truetype(str(FONT), font.size - 1)
        x = (4 * (19 if index == '014' else 34)) + (width - (bbox[2] - bbox[0])) // 2 - bbox[0]
        y = 4 * (7 + 37 * row) + (94 - (bbox[3] - bbox[1])) // 2 - bbox[1]
        rim = (130, 56, 27, 255) if index == '186' else (157, 30, 53, 255)
        draw.text((x, y), label, font=font, fill=(255, 251, 245, 255),
                  stroke_width=stroke, stroke_fill=rim)
    return base.resize((256, 128), Image.Resampling.LANCZOS)


def update(index: str) -> None:
    directory = ROOT / f'CALISMA_ALANI/images/_GUI/_id/_title/title{index}.arc'
    destination = next(directory.glob('*.tur.png'))
    image_for(index).save(destination)
    target = ROOT / f'YAMA/_eng/_GUI/_id/_title/title{index}.arc'
    arc = sf4.ArcFile(target.read_bytes())
    original = arc.unpack(0)
    assert sf4.parse_tex_info(original).width == 256
    target.write_bytes(arc.rebuild({0: sf4.png_to_tex_bytes(destination, original)}))
    assert sf4.ArcFile(target.read_bytes()).unpack(0)[:4] == sf4.TEX_MAGIC


if __name__ == '__main__':
    for index in TITLES:
        update(index)
        print(f'title{index}.arc hazır')
