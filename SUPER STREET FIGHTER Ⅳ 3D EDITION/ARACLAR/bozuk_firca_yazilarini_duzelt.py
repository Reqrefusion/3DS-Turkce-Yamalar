"""Replace damaged vertical-striped brush lettering in two game textures.

Run from ARACLAR: python bozuk_firca_yazilarini_duzelt.py
The edits are made both to the editable PNGs and the packaged ARC entries.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import sf4_tr_tool as sf4

ROOT = Path(__file__).resolve().parent.parent
FONT = str(Path(__file__).resolve().parent / "fonts/NimbusSansNarrow-BoldOblique.otf")


def lettering(lines, rows, size=(128, 128)):
    """Antialiased hand-painted style, fitted to the original brush text slots."""
    scale = 4
    result = Image.new("RGBA", size, (255, 255, 255, 0))
    for label, (top, bottom) in zip(lines, rows):
        max_h = bottom - top
        font = ImageFont.truetype(FONT, 24 * scale)
        bbox = font.getbbox(label, stroke_width=0)
        source = Image.new("L", (bbox[2] - bbox[0] + 12 * scale,
                                 bbox[3] - bbox[1] + 12 * scale), 0)
        draw = ImageDraw.Draw(source)
        draw.text((6 * scale - bbox[0], 6 * scale - bbox[1]), label,
                  font=font, fill=255, stroke_width=0)
        box = source.getbbox()
        source = source.crop(box)
        # Preserve slot size and leave at least two pixels between rows.
        factor = min((size[0] - 8) / source.width, (max_h - 2) / source.height)
        w, h = max(1, round(source.width * factor)), max(1, round(source.height * factor))
        source = source.resize((w, h), Image.Resampling.LANCZOS)
        # A restrained soft edge resembles the source brush asset at 3DS scale.
        source = source.filter(ImageFilter.GaussianBlur(0.20))
        layer = Image.new("RGBA", (w, h), (255, 255, 255, 0))
        layer.putalpha(source)
        result.alpha_composite(layer, ((size[0] - w) // 2, top + (max_h - h) // 2))
    return result


def write_asset(arc_name, entry, asset_name, lines, rows, size):
    image_path = ROOT / "CALISMA_ALANI/images/_GUI/_id/_common" / arc_name / (asset_name + ".tur.png")
    image = lettering(lines, rows, size)
    assert image.size == Image.open(image_path).size
    image.save(image_path)
    arc_path = ROOT / "YAMA/_eng/_GUI/_id/_common" / arc_name
    arc = sf4.ArcFile(arc_path.read_bytes())
    tex = sf4.png_to_tex_bytes(image_path, arc.unpack(entry))
    arc_path.write_bytes(arc.rebuild({entry: tex}))
    check = sf4.ArcFile(arc_path.read_bytes())
    assert sf4.tex_to_png_bytes(check.unpack(entry))
    print(f"Updated {arc_name}/{asset_name} ({len(lines)} labels)")


def left_aligned_labels(lines, rows):
    """Recreate the eleven compact results labels without damaged stripes."""
    result = Image.new("RGBA", (128, 256), (255, 255, 255, 0))
    font_path = str(Path(__file__).resolve().parent / "fonts/DejaVuSans-Bold.ttf")
    for label, (top, bottom) in zip(lines, rows):
        font = ImageFont.truetype(font_path, 48)
        bbox = font.getbbox(label)
        mask = Image.new("L", (bbox[2] - bbox[0] + 4, bbox[3] - bbox[1] + 4), 0)
        ImageDraw.Draw(mask).text((2 - bbox[0], 2 - bbox[1]), label, font=font, fill=255)
        mask = mask.crop(mask.getbbox())
        factor = min(76 / mask.width, (bottom - top) / mask.height)
        mask = mask.resize((round(mask.width * factor), round(mask.height * factor)), Image.Resampling.LANCZOS)
        layer = Image.new("RGBA", mask.size, (255, 255, 255, 0))
        layer.putalpha(mask)
        result.alpha_composite(layer, (0, top))
    return result


def write_exact(arc_name, entry, asset_name, image):
    image_path = ROOT / "CALISMA_ALANI/images/_GUI/_id/_common" / arc_name / (asset_name + ".tur.png")
    assert image.size == Image.open(image_path).size
    image.save(image_path)
    arc_path = ROOT / "YAMA/_eng/_GUI/_id/_common" / arc_name
    arc = sf4.ArcFile(arc_path.read_bytes())
    arc_path.write_bytes(arc.rebuild({entry: sf4.png_to_tex_bytes(image_path, arc.unpack(entry))}))
    print(f"Updated {arc_name}/{asset_name}")


def result_score_labels():
    path = ROOT / "CALISMA_ALANI/images/_GUI/_id/_common/battle.arc/002_d_u_text_ID.eng.png"
    result = Image.open(path).convert("RGBA")
    font_path = str(Path(__file__).resolve().parent / "fonts/DejaVuSans-Bold.ttf")
    replacements = [
        ((113, 0, 143, 12), "GALİP"),
        ((0, 16, 72, 29), "YÜKSEK SKOR"),
        ((112, 16, 150, 28), "GALİBİYET"),
        ((0, 30, 45, 42), "SKOR"),
        ((198, 12, 256, 26), "OYUNCU 2"),
        ((186, 26, 253, 39), "OYUNCU 1"),
        ((13, 43, 83, 55), "SEVİYE K.O."),
        ((13, 55, 83, 64), "SEVİYE K.O."),
    ]
    for (left, top, right, bottom), label in replacements:
        result.paste((255, 255, 255, 0), (left, top, right, bottom))
        font = ImageFont.truetype(font_path, 40)
        bbox = font.getbbox(label)
        mask = Image.new("L", (bbox[2] - bbox[0] + 4, bbox[3] - bbox[1] + 4), 0)
        ImageDraw.Draw(mask).text((2 - bbox[0], 2 - bbox[1]), label, font=font, fill=255)
        mask = mask.crop(mask.getbbox())
        factor = min((right - left - 1) / mask.width, (bottom - top - 2) / mask.height)
        mask = mask.resize((round(mask.width * factor), round(mask.height * factor)), Image.Resampling.LANCZOS)
        layer = Image.new("RGBA", mask.size, (255, 255, 255, 0))
        layer.putalpha(mask)
        result.alpha_composite(layer, (left, top + 1))
    return result


if __name__ == "__main__":
    write_asset("battle.arc", 1, "001_resultWinLose_ID",
                ["GALİP", "MAĞLUP"], [(3, 28), (35, 60)], (128, 64))
    write_asset("worldmap.arc", 1, "001_next_stage_ID",
                ["İLK AŞAMA", "SONRAKİ AŞAMA", "SON AŞAMA", "EK AŞAMA"],
                [(1, 23), (25, 48), (49, 71), (73, 95)], (128, 128))
    labels = ["CAN", "SÜRE", "TAMAMLAMA", "KUSURSUZ", "TOPLAM", "SKOR",
              "HÜCUM", "SAVUNMA", "TEKNİK", "SALDIRI", "VARİL"]
    slots = [(4, 15), (20, 31), (36, 48), (52, 64), (67, 80),
             (83, 96), (100, 112), (116, 128), (132, 145),
             (148, 160), (164, 176)]
    write_exact("battle.arc", 0, "000_resultText_ID", left_aligned_labels(labels, slots))
    ready_path = ROOT / "CALISMA_ALANI/images/_GUI/_id/_common/menu.arc/002_ready_ID.eng.png"
    write_exact("menu.arc", 2, "002_ready_ID", Image.open(ready_path).convert("RGBA"))
    level = lettering(["SEVİYE"], [(1, 21)], (128, 64))
    write_exact("menu.arc", 3, "003_lv_jpn_ID", level)
    write_exact("battle.arc", 2, "002_d_u_text_ID", result_score_labels())
