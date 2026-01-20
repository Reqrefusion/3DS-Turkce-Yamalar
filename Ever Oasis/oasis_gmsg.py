# oasis_gmsg.py
# Ever Oasis .gmsg export/import (Python port of oasis.lua)
# Usage:
#   python oasis_gmsg.py export main.gmsg main.md
#   python oasis_gmsg.py import main.gmsg main.md main_new.gmsg

import argparse
import os
import re
import struct

COMMANDS_LENGTH = {
    0x04: 2,
    0x05: 2,
    0x06: 2,
    0x08: 2,
    0x0A: 2,
    0x0B: 0,
    0x0C: 0,
    0x0E: 2,
    0x0F: 2,
    0x09: 2,
    0x10: 2,
    0x11: 2,
    0x12: 2,
    0x13: 2,
    0x14: 2,
    0x15: 0,
    0x16: 0,
    0x17: 0,
    0x18: 0,
}

def align_to(pos: int, n: int) -> int:
    r = pos % n
    return pos if r == 0 else pos + (n - r)

def read_u8(b: bytes, pos: int):
    return b[pos], pos + 1

def read_u16le(b: bytes, pos: int):
    return struct.unpack_from("<H", b, pos)[0], pos + 2

def read_i32le(b: bytes, pos: int):
    return struct.unpack_from("<i", b, pos)[0], pos + 4

def read_u32le(b: bytes, pos: int):
    return struct.unpack_from("<I", b, pos)[0], pos + 4

class BinWriter:
    def __init__(self, initial: bytes = b""):
        self.buf = bytearray(initial)
        self.pos = len(self.buf)

    def seek(self, pos: int):
        self.pos = pos

    def tell(self) -> int:
        return self.pos

    def _ensure(self, nbytes: int):
        need = self.pos + nbytes
        if need > len(self.buf):
            self.buf.extend(b"\x00" * (need - len(self.buf)))

    def write_bytes(self, data: bytes):
        self._ensure(len(data))
        self.buf[self.pos:self.pos+len(data)] = data
        self.pos += len(data)

    def write_u8(self, v: int):
        self._ensure(1)
        self.buf[self.pos] = v & 0xFF
        self.pos += 1

    def write_u16(self, v: int):
        self._ensure(2)
        struct.pack_into("<H", self.buf, self.pos, v & 0xFFFF)
        self.pos += 2

    def write_i16(self, v: int):
        self._ensure(2)
        struct.pack_into("<h", self.buf, self.pos, v)
        self.pos += 2

    def write_u32(self, v: int):
        self._ensure(4)
        struct.pack_into("<I", self.buf, self.pos, v & 0xFFFFFFFF)
        self.pos += 4

    def write_i32(self, v: int):
        self._ensure(4)
        struct.pack_into("<i", self.buf, self.pos, v)
        self.pos += 4

def write_align2_codepoint(bw: BinWriter, code: int):
    # same logic as oasis.lua:
    # if position is odd -> write 1 byte; else write 2 bytes
    if (bw.tell() % 2) == 1:
        bw.write_u8(code)
    else:
        bw.write_u16(code)

def write_align4_codepoint(bw: BinWriter, code: int) -> int:
    # same logic as oasis.lua:
    # if (pos/2) is odd -> write 2 bytes, else write 4 bytes
    if ((bw.tell() // 2) % 2) == 1:
        bw.write_u16(code)
        return 0
    else:
        bw.write_u32(code)
        return 2

def parse_bytes_string(msg_bytes: bytes) -> str:
    out = []
    pos = 0
    text_run = bytearray()

    def flush_text():
        nonlocal text_run
        if text_run:
            # decode as utf-8 if possible; fallback to latin-1 (keeps bytes 1:1)
            try:
                out.append(text_run.decode("utf-8"))
            except UnicodeDecodeError:
                out.append(text_run.decode("latin-1"))
            text_run = bytearray()

    while pos < len(msg_bytes):
        c1 = msg_bytes[pos]
        pos += 1

        if c1 == 0x7F:
            flush_text()

            if pos % 2 != 0:
                pos += 1

            r1, pos = read_u16le(msg_bytes, pos)

            if r1 == 0x0000:
                break
            elif r1 == 0x0001:
                out.append("<br>")
            elif r1 == 0x0002:
                out.append("<hr>")
            elif r1 == 0x0003:
                out.append("<waitbutton>")
            elif r1 == 0x000D:
                out.append("<playername>")
            elif r1 in COMMANDS_LENGTH:
                ln = COMMANDS_LENGTH[r1]
                if ln > 0:
                    pos = align_to(pos, 4)

                codes = [f"0x{r1:x}"]
                for _ in range(ln):
                    short, pos = read_u16le(msg_bytes, pos)
                    if short != 0x0000:
                        codes.append(f"0x{short:x}")

                out.append("[" + ", ".join(codes) + "]")
            elif r1 == 0x0019:
                pos = align_to(pos, 4)
                short1, pos = read_u16le(msg_bytes, pos)
                short2, pos = read_u16le(msg_bytes, pos)

                if short1 == 0xFFFF and short2 == 0xFFFF:
                    out.append("</span>")
                else:
                    out.append(f'<span class="color-{short1}">')
            else:
                out.append(f"[0x{r1:x}]")

        elif c1 == 0x00:
            flush_text()
            out.append("[0x0]")
        else:
            text_run.append(c1)

    flush_text()
    return "".join(out)

def export_gmsg(input_path: str, output_md: str):
    data = open(input_path, "rb").read()

    entry_count, _ = read_i32le(data, 0x0C)
    pos, _ = read_i32le(data, 0x10)

    msgs = []
    p = pos
    for _ in range(entry_count):
        mid, p = read_i32le(data, p)
        _, p = read_i32le(data, p)           # unknown
        off, p = read_i32le(data, p)
        ln, p = read_i32le(data, p)

        msg_bytes = data[off:off+ln]
        msgs.append((mid, msg_bytes))

    with open(output_md, "w", encoding="utf-8", newline="\n") as f:
        for mid, bts in msgs:
            txt = parse_bytes_string(bts)
            f.write(f"{mid}|{txt}|\n")

def find_next(chars, start, target):
    for j in range(start, len(chars)):
        if chars[j] == target:
            return j
    return -1

SPAN_RE = re.compile(r'span class="color\-([0-9]+)"')

def write_string_line(line_id: int, s: str, bw: BinWriter) -> int:
    chars = list(s)
    i = 0
    while i < len(chars):
        c = chars[i]

        if c == "[":
            j = find_next(chars, i, "]")
            if j == -1:
                raise ValueError(f"Error in line {line_id}: missing ']' in {s}")

            inside = "".join(chars[i+1:j]).strip()
            tokens = [t for t in re.split(r"[,\s]+", inside) if t]
            codes = [int(t, 16) for t in tokens]

            first_code = codes[0]
            if first_code == 0x0:
                bw.write_u8(0x00)
            else:
                write_align2_codepoint(bw, 0x7F)

                if first_code not in COMMANDS_LENGTH:
                    raise ValueError(f"unrecognized code in line id={line_id}: {inside}")

                ln = COMMANDS_LENGTH[first_code]
                args = codes[1:]

                if ln > 0:
                    write_align4_codepoint(bw, first_code)
                else:
                    bw.write_u16(first_code)

                if first_code == 0x09:
                    bw.write_u16(args[0] if len(args) > 0 else 0)
                    bw.write_u16(args[1] if len(args) > 1 else 0)
                else:
                    # match oasis.lua's weird packing: write (ln-1) int32 values
                    for k in range(ln - 1):
                        if k < len(args):
                            bw.write_u32(args[k])
                        else:
                            bw.write_u16(0x0000)
                            bw.write_u16(0x0000)

            i = j

        elif c == "<":
            j = find_next(chars, i, ">")
            if j == -1:
                raise ValueError(f"Error in line {line_id}: missing '>' in {s}")

            tag = "".join(chars[i+1:j])

            write_align2_codepoint(bw, 0x7F)

            if tag == "br":
                bw.write_u16(0x01)
            elif tag == "hr":
                bw.write_u16(0x02)
            elif tag == "waitbutton":
                bw.write_u16(0x03)
            elif tag == "playername":
                bw.write_u16(0x0D)
            elif tag.startswith('span '):
                m = SPAN_RE.search(tag)
                if not m:
                    raise ValueError(f'Invalid span tag in line {line_id}: <{tag}>')
                color = int(m.group(1))
                write_align4_codepoint(bw, 0x19)
                bw.write_u16(color)
                bw.write_u16(0x0000)
            elif "/span" in tag:
                write_align4_codepoint(bw, 0x19)
                bw.write_u16(0xFFFF)
                bw.write_u16(0xFFFF)
            else:
                raise ValueError(f"Invalid tag in line {line_id}: <{tag}>")

            i = j

        else:
            bw.write_bytes(c.encode("utf-8"))

        i += 1

    # terminator sequence
    write_align2_codepoint(bw, 0x7F)
    return write_align4_codepoint(bw, 0x00)

def import_gmsg(input_gmsg: str, input_md: str, output_gmsg: str):
    lines = {}
    with open(input_md, "r", encoding="utf-8", errors="strict") as f:
        for raw in f:
            raw = raw.rstrip("\n")
            if not raw:
                continue
            m = re.match(r"([^|]+)\|([^|]*)\|", raw)
            if not m:
                raise ValueError(f"Bad line format: {raw}")
            mid = int(m.group(1))
            text = m.group(2)
            lines[mid] = text

    data = open(input_gmsg, "rb").read()

    entry_count, _ = read_i32le(data, 0x0C)
    table_pos, _ = read_i32le(data, 0x10)

    header_and_table_size = (entry_count * 16) + table_pos
    bw = BinWriter(data[:header_and_table_size])

    p = table_pos
    for _ in range(entry_count):
        this_table_pos = p

        mid, p = read_i32le(data, p)
        unknown, p = read_i32le(data, p)
        _, p = read_i32le(data, p)  # old offset
        _, p = read_i32le(data, p)  # old length

        if mid not in lines:
            raise ValueError(f"Missing id {mid} in md file")

        s = lines[mid]
        if len(s) > 0:
            new_offset = bw.tell()
            align = write_string_line(mid, s, bw)
            end_pos = bw.tell()
            new_len = (end_pos - new_offset - align)

            # rewrite table entry
            cur = bw.tell()
            bw.seek(this_table_pos)
            bw.write_i32(mid)
            bw.write_i32(unknown)
            bw.write_i32(new_offset)
            bw.write_i32(new_len)
            bw.seek(cur)

    with open(output_gmsg, "wb") as f:
        f.write(bw.buf)

def resolve_in(path: str, exts):
    if os.path.exists(path):
        return path
    for ext in exts:
        p2 = path + ext
        if os.path.exists(p2):
            return p2
    return path  # let it error naturally later

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    ap_exp = sub.add_parser("export")
    ap_exp.add_argument("input", help="main.gmsg (or just main)")
    ap_exp.add_argument("output", help="main.md (or just main)")

    ap_imp = sub.add_parser("import")
    ap_imp.add_argument("input_gmsg", help="main.gmsg (or just main)")
    ap_imp.add_argument("input_md", help="main.md (or just main)")
    ap_imp.add_argument("output_gmsg", help="main_new.gmsg (or just main_new)")

    args = ap.parse_args()

    if args.cmd == "export":
        inp = resolve_in(args.input, [".gmsg"])
        out = args.output if args.output.lower().endswith(".md") else (args.output + ".md")
        export_gmsg(inp, out)
        print(f"OK: exported -> {out}")

    elif args.cmd == "import":
        inp_g = resolve_in(args.input_gmsg, [".gmsg"])
        inp_m = resolve_in(args.input_md, [".md"])
        out_g = args.output_gmsg if args.output_gmsg.lower().endswith(".gmsg") else (args.output_gmsg + ".gmsg")
        import_gmsg(inp_g, inp_m, out_g)
        print(f"OK: imported -> {out_g}")

if __name__ == "__main__":
    main()
