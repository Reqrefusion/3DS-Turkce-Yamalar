"""Refresh Turkish diacritics in the packaged, already translated _eng font ARCs.

This operates on the existing package: the original five-language ARC source
archive is not included. Run from ARACLAR with:
  python font_isaretlerini_yenile.py ../YAMA/_eng
"""
from pathlib import Path
import sys

import sf4_tr_tool as sf4


def update_arc(path: Path, gfd_indices):
    original = path.read_bytes()
    arc = sf4.ArcFile(original)
    changed = {}
    for gi in gfd_indices:
        size, pages, desc = sf4._parse_gfd_font(arc.unpack(gi))
        mapping = {d[6]: d for d in desc}
        atlas_index = sf4._font_page_base(gi)
        atlas = sf4._font_alpha_image(arc.unpack(atlas_index))
        for target, base in (("Ç", "C"), ("ç", "c"), ("Ş", "S"),
                             ("ş", "s"), ("Ğ", "G"), ("ğ", "g")):
            d = mapping[ord(target)]
            bd = mapping[ord(base)]
            assert d[0] == bd[0] == 0
            base_mask = atlas.crop((bd[2], bd[3], bd[2] + bd[1], bd[3] + size))
            improved = sf4._font_generated(base_mask, target)
            assert improved.width <= d[1] and improved.height == size
            from PIL import Image
            atlas.paste(Image.new("L", (d[1], size), 0), (d[2], d[3]))
            atlas.paste(improved, (d[2], d[3]))
        changed[atlas_index] = sf4._font_tex_with_alpha(arc.unpack(atlas_index), atlas)
    path.write_bytes(arc.rebuild(changed))
    verified = sf4.ArcFile(path.read_bytes())
    for gi in gfd_indices:
        assert verified.unpack(gi) == arc.unpack(gi)
        for target in "ÇçŞşĞğ":
            glyph, _ = sf4._font_crop_glyph(verified, gi, target)
            assert glyph.getbbox() is not None
            if target in "ÇçŞş":
                assert glyph.crop((0, glyph.height - 1, glyph.width, glyph.height)).getbbox()
    print(f"Updated {path} ({len(gfd_indices)} font sets)")


if __name__ == "__main__":
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "YAMA/_eng"
    update_arc(base / "_GUI/_font/menu.arc", (2, 5, 9))
    update_arc(base / "_GUI/_font/common.arc", (2,))
