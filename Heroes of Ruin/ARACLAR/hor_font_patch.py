from __future__ import annotations

import argparse
import struct
from pathlib import Path

try:
    from hor_formats import blz_compress, blz_decompress
except ImportError as exc:
    raise SystemExit('hor_formats.py bu dosyayla ayni klasorde olmali.') from exc

# Bu arac, kullanicinin sagladigi Heroes of Ruin demo_font.bcfnt_ dosyasinin
# CFNT 0x03000000 / A8 / 9x13 yapisini koruyarak ceviride gereken ek glifleri ekler.

EXTRA_GLYPHS = ['Â','Ç','Ö','Ü','â','ç','é','î','ö','û','ü','Ğ','ğ','İ','ı','Ş','ş','…','⇒']
FALLBACK_MAP = {
    0x00A0: ' ',   # no-break space
    0x2013: '-',   # en dash
    0x2014: '-',   # em dash
    0x2019: "'",   # right single quote
    0x201C: '"',   # left double quote
    0x201D: '"',   # right double quote
}
TURKISH = 'ÇĞİÖŞÜçğıöşü'


def _align4(n: int) -> int:
    return (n + 3) & ~3


def _looks_blz_font(data: bytes) -> bool:
    if len(data) < 0x14 or data[:4] not in (b'CFNT', b'CFNU', b'FFNT'):
        return False
    declared = struct.unpack_from('<I', data, 0x0C)[0]
    return declared > len(data)


def _raw_font(data: bytes) -> bytes:
    if _looks_blz_font(data):
        return blz_decompress(data)
    return data


def _decode_a8_sheet(buf: bytes, width: int, height: int) -> list[int]:
    if len(buf) != width * height:
        raise ValueError('A8 sheet boyutu beklenenden farkli.')
    bmp = [0] * (width * height)
    for tile_y in range(height // 8):
        for tile_x in range(width // 8):
            for y in range(2):
                for x in range(2):
                    for y2 in range(2):
                        for x2 in range(2):
                            for y3 in range(2):
                                for x3 in range(2):
                                    px = x3 + x2 * 2 + x * 4 + tile_x * 8
                                    py = y3 + y2 * 2 + y * 4 + tile_y * 8
                                    dx = x3 + x2 * 4 + x * 16 + tile_x * 64
                                    dy = y3 * 2 + y2 * 8 + y * 32 + tile_y * width * 8
                                    bmp[py * width + px] = buf[dx + dy]
    return bmp


def _encode_a8_sheet(bmp: list[int], width: int, height: int) -> bytes:
    if len(bmp) != width * height:
        raise ValueError('A8 bitmap boyutu beklenenden farkli.')
    data = bytearray(width * height)
    for tile_y in range(height // 8):
        for tile_x in range(width // 8):
            for y in range(2):
                for x in range(2):
                    for y2 in range(2):
                        for x2 in range(2):
                            for y3 in range(2):
                                for x3 in range(2):
                                    px = x3 + x2 * 2 + x * 4 + tile_x * 8
                                    py = y3 + y2 * 2 + y * 4 + tile_y * 8
                                    dx = x3 + x2 * 4 + x * 16 + tile_x * 64
                                    dy = y3 * 2 + y2 * 8 + y * 32 + tile_y * width * 8
                                    data[dx + dy] = bmp[py * width + px]
    return bytes(data)


def _parse_font(raw: bytes) -> dict:
    if len(raw) < 0x80 or raw[:4] != b'CFNT':
        raise ValueError('Beklenen CFNT fontu degil.')
    magic, bom, hsize, version, fsize, sections = struct.unpack_from('<4sHHIII', raw, 0)
    if bom != 0xFEFF or hsize != 0x14 or version != 0x03000000 or fsize != len(raw):
        raise ValueError('Desteklenmeyen CFNT basligi.')
    finf = list(struct.unpack_from('<4sI2BH4B3I4B', raw, 0x14))
    if finf[0] != b'FINF' or finf[1] != 0x20:
        raise ValueError('FINF bolumu bulunamadi.')
    tglp_start = finf[9] - 8
    tglp = list(struct.unpack_from('<4sI4BI6HI', raw, tglp_start))
    if tglp[0] != b'TGLP':
        raise ValueError('TGLP bolumu bulunamadi.')
    cell_w, cell_h = tglp[2], tglp[3]
    sheet_size, num_sheets, fmt = tglp[6], tglp[7], tglp[8]
    cols, rows, sw, sh, data_off = tglp[9], tglp[10], tglp[11], tglp[12], tglp[13]
    if fmt != 8 or sheet_size != sw * sh or sw % 8 or sh % 8:
        raise ValueError('Bu arac yalnizca A8 CFNT sheet yapisini destekliyor.')
    if (cell_w, cell_h, cols, rows, sw, sh) != (9, 13, 3, 2, 32, 32):
        raise ValueError(
            'Bu fontun hucre/sheet yapisi beklenen demo_font ile ayni degil: '
            f'{cell_w}x{cell_h}, {cols}x{rows}, {sw}x{sh}'
        )
    sheets = []
    for i in range(num_sheets):
        a = data_off + i * sheet_size
        b = a + sheet_size
        if b > len(raw):
            raise ValueError('TGLP sheet verisi dosya disina tasiyor.')
        sheets.append(_decode_a8_sheet(raw[a:b], sw, sh))

    cwdh_start = finf[10] - 8
    cmagic, csize, cstart, cend, cnext = struct.unpack_from('<4sI2HI', raw, cwdh_start)
    if cmagic != b'CWDH' or cnext != 0 or cend < cstart:
        raise ValueError('Beklenen tek CWDH bolumu bulunamadi.')
    count = cend - cstart + 1
    if cstart != 0 or cwdh_start + 0x10 + count * 3 > len(raw):
        raise ValueError('CWDH glif metrikleri gecersiz.')
    metrics = [struct.unpack_from('<bbb', raw, cwdh_start + 0x10 + i * 3) for i in range(count)]
    return {
        'raw': raw, 'header': (magic, bom, hsize, version, fsize, sections),
        'finf': finf, 'tglp_start': tglp_start, 'tglp': tglp,
        'cell_w': cell_w, 'cell_h': cell_h, 'sheet_size': sheet_size,
        'num_sheets': num_sheets, 'cols': cols, 'rows': rows,
        'sw': sw, 'sh': sh, 'data_off': data_off, 'sheets': sheets,
        'metrics': metrics,
    }


def _glyph(font: dict, idx: int) -> list[list[int]]:
    cap = font['cols'] * font['rows']
    sheet = idx // cap
    local = idx % cap
    if sheet >= len(font['sheets']):
        raise ValueError(f'Glif index sheet disinda: {idx}')
    col = local % font['cols']
    row = local // font['cols']
    sx = col * (font['cell_w'] + 1)
    sy = row * (font['cell_h'] + 1)
    bmp = font['sheets'][sheet]
    return [
        [bmp[(sy + y) * font['sw'] + (sx + x)] for x in range(font['cell_w'])]
        for y in range(font['cell_h'])
    ]


def _put_glyph(font: dict, idx: int, glyph: list[list[int]]) -> None:
    cap = font['cols'] * font['rows']
    sheet = idx // cap
    local = idx % cap
    while len(font['sheets']) <= sheet:
        font['sheets'].append([0] * (font['sw'] * font['sh']))
    col = local % font['cols']
    row = local // font['cols']
    sx = col * (font['cell_w'] + 1)
    sy = row * (font['cell_h'] + 1)
    bmp = font['sheets'][sheet]
    for y in range(font['cell_h']):
        for x in range(font['cell_w']):
            bmp[(sy + y) * font['sw'] + (sx + x)] = glyph[y][x]


def _set(g: list[list[int]], x: int, y: int, v: int = 255) -> None:
    if 0 <= y < len(g) and 0 <= x < len(g[0]):
        g[y][x] = max(g[y][x], v)


def _clear(g: list[list[int]], x: int, y: int) -> None:
    if 0 <= y < len(g) and 0 <= x < len(g[0]):
        g[y][x] = 0


def _make_glyph(font: dict, ch: str) -> tuple[list[list[int]], tuple[int, int, int]]:
    def base(c: str):
        idx = ord(c) - 32
        return [r[:] for r in _glyph(font, idx)], font['metrics'][idx]

    if ch == 'Â':
        g, m = base('A'); _set(g, 3, 0); _set(g, 5, 0); return g, m
    if ch == 'Ç':
        g, m = base('C'); _set(g, 4, 12); _set(g, 3, 12, 128); return g, m
    if ch == 'Ö':
        g, m = base('O'); _set(g, 2, 0); _set(g, 6, 0); return g, m
    if ch == 'Ü':
        g, m = base('U'); _set(g, 2, 0); _set(g, 6, 0); return g, m
    if ch == 'â':
        g, m = base('a'); _set(g, 3, 0); _set(g, 2, 1); _set(g, 4, 1); return g, m
    if ch == 'ç':
        g, m = base('c'); _set(g, 4, 12); _set(g, 3, 12, 128); return g, m
    if ch == 'é':
        g, m = base('e'); _set(g, 4, 1); _set(g, 3, 2); return g, m
    if ch == 'î':
        g, _m = base('i'); _clear(g, 1, 2); _set(g, 1, 0); _set(g, 0, 1); _set(g, 2, 1); return g, (0, 3, 3)
    if ch == 'ö':
        g, m = base('o'); _set(g, 2, 2); _set(g, 5, 2); return g, m
    if ch == 'û':
        g, m = base('u'); _set(g, 3, 0); _set(g, 2, 1); _set(g, 4, 1); return g, m
    if ch == 'ü':
        g, m = base('u'); _set(g, 2, 2); _set(g, 5, 2); return g, m
    if ch == 'Ğ':
        g, m = base('G'); _set(g, 2, 0); _set(g, 6, 0); _set(g, 3, 0, 128); _set(g, 5, 0, 128); return g, m
    if ch == 'ğ':
        g, m = base('g'); _set(g, 2, 1); _set(g, 5, 1); _set(g, 3, 2); _set(g, 4, 2); return g, m
    if ch == 'İ':
        g, m = base('I'); _set(g, 2, 0); return g, m
    if ch == 'ı':
        g, m = base('i'); _clear(g, 1, 2); return g, m
    if ch == 'Ş':
        g, m = base('S'); _set(g, 4, 12); _set(g, 3, 12, 128); return g, m
    if ch == 'ş':
        g, m = base('s'); _set(g, 4, 12); _set(g, 3, 12, 128); return g, m
    if ch == '…':
        g = [[0] * font['cell_w'] for _ in range(font['cell_h'])]
        for x in (1, 4, 7): _set(g, x, 11)
        return g, (0, 8, 8)
    if ch == '⇒':
        g = [[0] * font['cell_w'] for _ in range(font['cell_h'])]
        for x in range(1, 6):
            _set(g, x, 5); _set(g, x, 7)
        _set(g, 6, 4); _set(g, 7, 5); _set(g, 8, 6); _set(g, 7, 7); _set(g, 6, 8)
        return g, (0, 9, 9)
    raise ValueError(f'Bilinmeyen ek glif: {ch!r}')


def _cmap_codepoints(raw: bytes) -> set[int]:
    out: set[int] = set()
    pos = 0
    while True:
        pos = raw.find(b'CMAP', pos)
        if pos < 0:
            break
        if pos + 0x14 > len(raw):
            break
        size = struct.unpack_from('<I', raw, pos + 4)[0]
        begin, end, method, _ = struct.unpack_from('<HHHH', raw, pos + 8)
        if size < 0x14 or pos + size > len(raw):
            pos += 4; continue
        body = pos + 0x14
        if method == 0 and body + 4 <= pos + size:
            # HoR fontunda direct body: u16 entry-count/reserved + u16 indexOffset.
            for cp in range(begin, end + 1): out.add(cp)
        elif method == 1:
            count = end - begin + 1
            if body + count * 2 <= pos + size:
                vals = struct.unpack_from('<' + 'H' * count, raw, body)
                for i, val in enumerate(vals):
                    if val != 0xFFFF: out.add(begin + i)
        elif method == 2 and body + 2 <= pos + size:
            count = struct.unpack_from('<H', raw, body)[0]
            q = body + 2
            for _i in range(count):
                if q + 4 > pos + size: break
                cp, idx = struct.unpack_from('<HH', raw, q); q += 4
                if idx != 0xFFFF: out.add(cp)
        pos += 4
    return out


def patch_font(data: bytes) -> tuple[bytes, bytes, dict[int, int]]:
    raw = _raw_font(data)
    font = _parse_font(raw)
    if len(font['metrics']) != 95:
        raise ValueError(
            'Beklenen ASCII demo_font 95 glif icermeli. '
            f'Bu dosyada {len(font["metrics"])} glif var.'
        )

    # 0..94 = ASCII U+0020..U+007E. Yeni glifler ard arda eklenir.
    code_to_index: dict[int, int] = {cp: cp - 32 for cp in range(32, 127)}
    metrics = list(font['metrics'])
    for ch in EXTRA_GLYPHS:
        g, m = _make_glyph(font, ch)
        idx = len(metrics)
        _put_glyph(font, idx, g)
        metrics.append(m)
        code_to_index[ord(ch)] = idx

    for cp, base_char in FALLBACK_MAP.items():
        code_to_index[cp] = ord(base_char) - 32

    sheet_blob = b''.join(_encode_a8_sheet(b, font['sw'], font['sh']) for b in font['sheets'])
    tglp_start = font['tglp_start']
    data_off = font['data_off']
    cwdh_start = data_off + len(sheet_blob)

    cwdh_body = bytearray()
    for m in metrics:
        cwdh_body += struct.pack('<bbb', *m)
    cwdh_size = _align4(0x10 + len(cwdh_body))
    cwdh = bytearray(cwdh_size)
    struct.pack_into('<4sI2HI', cwdh, 0, b'CWDH', cwdh_size, 0, len(metrics) - 1, 0)
    cwdh[0x10:0x10 + len(cwdh_body)] = cwdh_body

    # Iki CMAP: orijinal ASCII direct map + ek Unicode scan map.
    cmap1_start = cwdh_start + cwdh_size
    cmap1_size = 0x18
    cmap2_start = cmap1_start + cmap1_size
    cmap1 = bytearray(cmap1_size)
    struct.pack_into('<4sI4HI', cmap1, 0, b'CMAP', cmap1_size, 32, 126, 0, 0, cmap2_start + 8)
    struct.pack_into('<HH', cmap1, 0x14, 0, 0)

    extras = sorted((cp, idx) for cp, idx in code_to_index.items() if not (32 <= cp <= 126))
    scan_body = bytearray(struct.pack('<H', len(extras)))
    for cp, idx in extras:
        if cp > 0xFFFF or idx > 0xFFFF:
            raise ValueError('CMAP UTF-16/index siniri asildi.')
        scan_body += struct.pack('<HH', cp, idx)
    cmap2_size = _align4(0x14 + len(scan_body))
    cmap2 = bytearray(cmap2_size)
    struct.pack_into('<4sI4HI', cmap2, 0, b'CMAP', cmap2_size, extras[0][0], extras[-1][0], 2, 0, 0)
    cmap2[0x14:0x14 + len(scan_body)] = scan_body

    final_size = cmap2_start + cmap2_size
    out = bytearray(final_size)
    struct.pack_into('<4sHHIII', out, 0, b'CFNT', 0xFEFF, 0x14, 0x03000000, final_size, 5)

    finf = list(font['finf'])
    finf[9] = tglp_start + 8
    finf[10] = cwdh_start + 8
    finf[11] = cmap1_start + 8
    struct.pack_into('<4sI2BH4B3I4B', out, 0x14, *finf)

    tglp = list(font['tglp'])
    tglp[1] = cwdh_start - tglp_start
    tglp[7] = len(font['sheets'])
    tglp[13] = data_off
    struct.pack_into('<4sI4BI6HI', out, tglp_start, *tglp)

    # TGLP header ile 0x80 sheet ofseti arasindaki orijinal paddingi koru.
    out[tglp_start + 0x20:data_off] = raw[tglp_start + 0x20:data_off]
    out[data_off:data_off + len(sheet_blob)] = sheet_blob
    out[cwdh_start:cwdh_start + len(cwdh)] = cwdh
    out[cmap1_start:cmap1_start + len(cmap1)] = cmap1
    out[cmap2_start:cmap2_start + len(cmap2)] = cmap2

    raw_out = bytes(out)
    # Yeniden parse ve kapsama kontrolu.
    _parse_font(raw_out)
    cps = _cmap_codepoints(raw_out)
    required = set(code_to_index)
    missing = sorted(required - cps)
    if missing:
        raise RuntimeError('Font CMAP dogrulamasi basarisiz: ' + ', '.join(f'U+{x:04X}' for x in missing))

    packed = blz_compress(raw_out)
    if blz_decompress(packed) != raw_out:
        raise RuntimeError('Font BLZ round-trip dogrulamasi basarisiz.')
    return raw_out, packed, code_to_index


def report(data: bytes) -> str:
    raw = _raw_font(data)
    font = _parse_font(raw)
    cps = _cmap_codepoints(raw)
    present = ''.join(ch for ch in TURKISH if ord(ch) in cps)
    missing = ''.join(ch for ch in TURKISH if ord(ch) not in cps)
    return '\n'.join([
        f'CFNT boyutu: {len(raw)} bayt',
        f'Glif metrigi: {len(font["metrics"])}',
        f'Sheet: {len(font["sheets"])} x {font["sw"]}x{font["sh"]} A8',
        f'CMAP kod noktasi: {len(cps)}',
        f'Turkce glifler mevcut: {present or "(yok)"}',
        f'Turkce glifler eksik: {missing or "(yok)"}',
    ])


def main() -> None:
    p = argparse.ArgumentParser(description='Heroes of Ruin demo_font BCFNT Turkce glif araci')
    sub = p.add_subparsers(dest='cmd', required=True)
    q = sub.add_parser('check', help='Font kapsamini kontrol et')
    q.add_argument('input')
    q = sub.add_parser('patch', help='Turkce/ceviri gliflerini ekle ve BLZ .bcfnt_ uret')
    q.add_argument('input')
    q.add_argument('output')
    q.add_argument('--raw-output', help='Istege bagli acilmis .bcfnt ciktisi')
    a = p.parse_args()

    src = Path(a.input).read_bytes()
    if a.cmd == 'check':
        print(report(src))
        return
    raw_out, packed, mapping = patch_font(src)
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_bytes(packed)
    if a.raw_output:
        Path(a.raw_output).write_bytes(raw_out)
    print(f'Yazildi: {a.output} ({len(packed)} bayt)')
    print(report(raw_out))


if __name__ == '__main__':
    main()
