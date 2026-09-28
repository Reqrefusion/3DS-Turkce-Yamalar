"""Correct both artwork and text alignment in seven red title atlases.

Run after dort_unvan_atlasini_yenile.py, because title014 is shared.
All translations are matched by row to the English source atlas.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import sf4_tr_tool as sf4

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FONT = HERE / 'fonts/NimbusSansNarrow-BoldOblique.otf'
LABELS = {
    # Rush / Brave / Pinch / Crisis / Buster / Smash are kept consistent.
    '009': ('Hücum Valesi', 'Cesur Vale', 'Köşeye Sıkışmış Vale'),
    '010': ('Kriz Valesi', 'Ezici Kız', 'Yıkım Kızı'),
    '011': ('Hücum Kızı', 'Cesur Kız', 'Köşeye Sıkışmış Kız'),
    '012': ('Kriz Kızı', 'Ezici Kral', 'Yıkım Kralı'),
    '013': ('Hücum Kralı', 'Cesur Kral', 'Köşeye Sıkışmış Kral'),
    '014': ('Kriz Kralı', 'Ezici As', 'Yıkım Ası'),
    '015': ('Hücum Ası', 'Cesur As', 'Köşeye Sıkışmış As'),
}


def draw_one(number):
    folder = ROOT / f'CALISMA_ALANI/images/_GUI/_id/_title/title{number}.arc'
    reference = next(folder.glob('*.spa.png'))
    pixels = np.asarray(Image.open(reference).convert('RGBA')).copy()
    # Each reference keeps a long red stripe at the same vertical position.
    # Replace the source glyph region by uncovered translucent red on the
    # same scan line, including native alpha and top/bottom borders.
    for top in (0, 37, 75):
        for y in range(top + 11, top + 28):
            strip = pixels[y, 21:169]
            clean = strip[(strip[:, 0] > 200) & (strip[:, 1] < 125) &
                          (strip[:, 2] < 125) & (strip[:, 3] < 165)]
            if len(clean) > 10:
                pixels[y, 28:163] = np.median(clean, axis=0).astype('uint8')
    image = Image.fromarray(pixels, 'RGBA').resize((1024, 512), Image.Resampling.NEAREST)
    draw = ImageDraw.Draw(image)
    for row, label in enumerate(LABELS[number]):
        font = ImageFont.truetype(str(FONT), 64)
        stroke = 5
        while True:
            bbox = draw.textbbox((0, 0), label, font=font, stroke_width=stroke)
            if bbox[2] - bbox[0] <= 585:
                break
            font = ImageFont.truetype(str(FONT), font.size - 1)
        x = 4*19 + (585 - (bbox[2]-bbox[0]))//2 - bbox[0]
        y = 4*(7+37*row) + (94-(bbox[3]-bbox[1]))//2 - bbox[1]
        draw.text((x,y), label, font=font, fill=(255,251,245,255),
                  stroke_width=stroke, stroke_fill=(155,27,48,255))
    target = next(folder.glob('*.tur.png'))
    image.resize((256,128), Image.Resampling.LANCZOS).save(target)
    arc_path = ROOT / f'YAMA/_eng/_GUI/_id/_title/title{number}.arc'
    arc = sf4.ArcFile(arc_path.read_bytes())
    arc_path.write_bytes(arc.rebuild({0: sf4.png_to_tex_bytes(target, arc.unpack(0))}))
    assert sf4.ArcFile(arc_path.read_bytes()).unpack(0)[:4] == sf4.TEX_MAGIC


if __name__ == '__main__':
    for number in LABELS:
        draw_one(number)
        print(f'title{number}: üç satır kaynakla eşleştirildi')
