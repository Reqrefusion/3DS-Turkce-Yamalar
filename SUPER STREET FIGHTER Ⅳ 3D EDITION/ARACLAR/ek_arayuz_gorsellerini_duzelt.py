"""Recreate the damaged rank texture and restore the cursor icon sheet.

Run from ARACLAR: python ek_arayuz_gorsellerini_duzelt.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import sf4_tr_tool as sf4

ROOT = Path(__file__).resolve().parent.parent
FONT = Path(__file__).resolve().parent / "fonts/NimbusSansNarrow-BoldOblique.otf"


def ranks():
    size = (256, 128)
    out = Image.new("RGBA", size, (255, 255, 255, 0))
    for text, bounds in (("BÜYÜK USTA", (18, 4, 170, 53)),
                         ("USTA", (17, 64, 170, 102))):
        x0, y0, x1, y1 = bounds
        font = ImageFont.truetype(str(FONT), 80)
        box = font.getbbox(text)
        mask = Image.new("L", (box[2] - box[0] + 8, box[3] - box[1] + 8), 0)
        ImageDraw.Draw(mask).text((4 - box[0], 4 - box[1]), text, font=font, fill=255)
        mask = mask.crop(mask.getbbox())
        factor = min((x1 - x0 - 6) / mask.width, (y1 - y0 - 12) / mask.height)
        mask = mask.resize((round(mask.width * factor), round(mask.height * factor)), Image.Resampling.LANCZOS)
        x = x0 + (x1 - x0 - mask.width) // 2
        y = y0 + (y1 - y0 - mask.height) // 2
        glow = mask.filter(ImageFilter.GaussianBlur(3))
        halo = Image.new("RGBA", mask.size, (255, 255, 255, 0))
        halo.putalpha(glow.point(lambda v: round(v * .46)))
        out.alpha_composite(halo, (x, y))
        core = Image.new("RGBA", mask.size, (255, 255, 255, 0))
        core.putalpha(mask)
        out.alpha_composite(core, (x, y))
    return out


def versus_rank_sheet():
    """Keep the native rank chart, replacing the two English rank names."""
    base = ROOT / "CALISMA_ALANI/images/_GUI/_id/_common/battle_vs.arc/000_netRslt00_BM_HQ_NOMIP.eng.png"
    translated = ROOT / "CALISMA_ALANI/images/_GUI/_id/_common/battle_vs.arc/000_netRslt00_BM_HQ_NOMIP.tur.png"
    native = Image.open(base).convert("RGBA")
    out = Image.open(translated).convert("RGBA")
    out.paste(native.crop((0, 160, 256, 256)), (0, 160))
    draw = ImageDraw.Draw(out)
    body = Path(__file__).resolve().parent / "fonts/DejaVuSans-Bold.ttf"
    for text, bounds in (("USTA", (58, 212, 128, 234)),
                         ("BÜYÜK USTA", (0, 236, 128, 256))):
        x0, y0, x1, y1 = bounds
        draw.rectangle(bounds, fill=(0, 0, 0, 255))
        font = ImageFont.truetype(str(body), 13)
        while draw.textbbox((0, 0), text, font=font, stroke_width=1)[2] > x1 - x0 - 4:
            font = ImageFont.truetype(str(body), font.size - 1)
        bb = draw.textbbox((0, 0), text, font=font, stroke_width=1)
        x = x0 + (x1 - x0 - (bb[2] - bb[0])) // 2 - bb[0]
        y = y0 + (y1 - y0 - (bb[3] - bb[1])) // 2 - bb[1]
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 255),
                  stroke_width=1, stroke_fill=(234, 53, 108, 255))
    return out


def update(arc_name, entry, asset_name, image):
    image_path = ROOT / "CALISMA_ALANI/images/_GUI/_id/_common" / arc_name / (asset_name + ".tur.png")
    assert Image.open(image_path).size == image.size
    image.save(image_path)
    arc_path = ROOT / "YAMA/_eng/_GUI/_id/_common" / arc_name
    arc = sf4.ArcFile(arc_path.read_bytes())
    arc_path.write_bytes(arc.rebuild({entry: sf4.png_to_tex_bytes(image_path, arc.unpack(entry))}))
    assert sf4.ArcFile(arc_path.read_bytes()).unpack(entry)[:4] == sf4.TEX_MAGIC
    print(f"Updated {arc_name}/{asset_name}")


if __name__ == "__main__":
    update("worldmap.arc", 3, "003_class_jpn_kor_ID", ranks())
    p = ROOT / "CALISMA_ALANI/images/_GUI/_id/_common/menu.arc/006_cs_cursor_ID.eng.png"
    update("menu.arc", 6, "006_cs_cursor_ID", Image.open(p).convert("RGBA"))
    update("battle_vs.arc", 0, "000_netRslt00_BM_HQ_NOMIP", versus_rank_sheet())
