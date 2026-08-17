#!/usr/bin/env python3
"""
Ace Attorney Trilogy (3DS) language extractor/reinjector + Switch TR scenario porter.

Designed from the two user-supplied archives:
  * 3DS pack.dat: concatenated, 4-byte aligned Nintendo LZ11 streams.
  * GS1/GS2/GS3 language entries: mes_all-like table of LZ10-compressed MDT files.
  * MDT: u32 section count + u32 section offsets + 16-bit script stream.

The Switch HD script stores a rendered Unicode codepoint + 0x80 for text words.
The 3DS version uses a compact script character table. Control words/arguments are
left untouched; only known Switch text words are recoded.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import struct
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Iterable, List, Tuple, Dict, Optional

ALIGN = 4

GS1_NAMES = [
    "sc0_text","sc1_0_text","sc1_1_text","sc1_2_text","sc1_3_text",
    "sc2_0_text","sc2_1_text","sc2_2_text","sc2_3_text","sc2_4_text","sc2_5_text",
    "sc3_0_text","sc3_1_text","sc3_2_text","sc3_3_text","sc3_4_text","sc3_5_text",
    "sc4_0a_text","sc4_0b_text","sc4_1a_text","sc4_1b_text","sc4_1c_text",
    "sc4_2a_text","sc4_2b_text","sc4_2c_text","sc4_3a_text","sc4_3b_text","sc4_3c_text",
    "sc4_4a_text","sc4_4b_text","sc4_4c_text","sc4_5a_text","sc4_5b_text","sc4_5c_text",
    "sc4_5d_text","ev0_mes","sys_mes"
]
GS2_NAMES = [
    "sc0_0_text","sc0_1_text","sc1_0_text","sc1_1_0_text","sc1_1_1_text","sc1_2_text",
    "sc1_3_0_text","sc1_3_1_text","sc2_0_text","sc2_1_0_text","sc2_1_1_text","sc2_2_text",
    "sc2_3_0_text","sc2_3_1_text","sc3_0_0_text","sc3_0_1_text","sc3_1_0_text","sc3_1_1_text",
    "sc3_2_0_text","sc3_2_1_text","sc3_3_0_text","sc3_3_1_text","sys_mes"
]
GS3_NAMES = [
    "sc0_0_text","sc0_1_text","sc0_1b_text","sc1_0_text","sc1_0b_text","sc1_1_text",
    "sc1_1b_text","sc1_2_text","sc1_2b_text","sc1_2c_text","sc1_3_0_text","sc1_3_1_text",
    "sc1_3_1b_text","sc2_0_text","sc2_0b_text","sc2_1_text","sc2_1b_text","sc2_2_text",
    "sc2_2b_text","sc2_2c_text","sc2_3_0_text","sc2_3_1_text","sc2_3_1b_text",
    "sc3_0_0_text","sc3_0_0b_text","sc3_0_1_text","sc3_0_1b_text","sc4_0_0_text",
    "sc4_0_1_text","sc4_0_1b_text","sc4_1_0_text","sc4_1_1_text","sc4_2_0_text",
    "sc4_2_0b_text","sc4_2_1_text","sc4_2_1b_text","sc4_3_0_text","sc4_3_0b_text",
    "sc4_3_1_text","sc4_3_2_text","sc4_3_2b_text","sc4_3_2c_text","sys_mes"
]
GS_NAMES = {"GS1": GS1_NAMES, "GS2": GS2_NAMES, "GS3": GS3_NAMES}
EXPECTED_MES_COUNTS = {"GS1": 74, "GS2": 46, "GS3": 86}

# Switch Turkish patch custom *base* codepoints. Scenario MDT stores base+0x80.
SW_CUSTOM = {
    0x2191: "İ", 0x2193: "ı", 0x2208: "ş", 0x220B: "Ş", 0x2200: "ğ",
    0x2286: "ç", 0x2282: "Ç", 0x0426: "ü", 0x043B: "Ü",
    0x03B1: "ö", 0x03B5: "Ö",
}
SW_DIRECT = {0x2015:"―", 0x2018:"‘", 0x2019:"’", 0x201C:"“", 0x201D:"”", 0x2026:"…", 0x2606:"☆", 0x2605:"★", 0x00B0:"°"}

# 3DS script character codes.
# 0x80..0x89 0-9, 0x8A..0xA3 A-Z, 0xA4..0xBD a-z.
THREEDS_SPECIAL = {
    "!": 190, "?": 191,
    "É":192,"À":193,"È":194,"Ù":195,"Â":196,"Ê":197,"Î":198,"Ô":199,"Û":200,
    "Ë":201,"Ï":202,"Ü":203,"Ç":204,"Œ":205,"é":206,"à":207,"è":208,"ù":209,
    "â":210,"ê":211,"î":212,"ô":213,"û":214,"ë":215,"ï":216,"ü":217,"ç":218,"œ":219,
    "°":220,"€":221,";":222,"á":223,"ä":224,"å":225,"æ":226,"﹚":227,"ö":228,"ø":229,
    "ß":230,"ÿ":231,"Ä":232,"Å":233,"Æ":234,"﹙":235,"Ö":236,"Ø":237,"ì":238,"ò":239,
    "Ì":240,"Ò":241,"í":242,"ñ":243,"ó":244,"ú":245,"Á":246,"Í":247,"Ñ":248,"Ó":249,
    "Ú":250,"¿":251,"¡":252,
    "-":336, '"':337, "[":338,"]":339,"$":340,"#":341,">":342,"<":343,"=":344,
    ".":353,"(":357,")":358,":":365,"`":366,",":367,"+":368,"/":369,"*":370,"'":371,
    "%":375,"~":377,"«":378,"»":379,"&":380,"☆":381,"♪":382," ":383,
}
# Robust Turkish donor slots. 3DS scenario scripts use a compact character
# table which is independent from the FFNT Unicode CMAP and can vary by game.
# ASCII A-Z codes are stable in all three games, so six rare uppercase letters
# are repurposed as deterministic Turkish glyph slots. Ordinary occurrences of
# those donor capitals are emitted as their lowercase equivalents.
TURKISH_DONOR_CHARS = {"Ğ":"Q", "İ":"X", "Ş":"J", "ğ":"Z", "ı":"U", "ş":"R"}
TURKISH_DONOR_CODES = {tr: 0x8A + ord(d)-ord("A") for tr,d in TURKISH_DONOR_CHARS.items()}
GAME_SPECIAL = {"GS1":{"-":372}, "GS2":{"-":372}, "GS3":{"-":1665}}


def align4(n: int) -> int:
    return (n + 3) & ~3


def u16s(data: bytes) -> List[int]:
    return list(struct.unpack("<" + "H" * (len(data)//2), data[:len(data)//2*2]))


def lz11_info(data: bytes, pos: int = 0) -> Tuple[int, int]:
    """Return (compressed_bytes_consumed, decompressed_size) without materializing output."""
    start = pos
    if data[pos] != 0x11:
        raise ValueError(f"not LZ11 at 0x{pos:X}")
    out_size = data[pos+1] | (data[pos+2] << 8) | (data[pos+3] << 16)
    pos += 4
    if out_size == 0:
        out_size = struct.unpack_from("<I", data, pos)[0]
        pos += 4
    produced = 0
    while produced < out_size:
        flags = data[pos]; pos += 1
        for bit in range(8):
            if produced >= out_size: break
            if not (flags & (0x80 >> bit)):
                pos += 1; produced += 1
                continue
            b1 = data[pos]
            top = b1 >> 4
            if top == 0:
                b2 = data[pos+1]
                length = ((b1 & 0xF) << 4 | (b2 >> 4)) + 0x11
                pos += 3
            elif top == 1:
                b2, b3 = data[pos+1], data[pos+2]
                length = ((b1 & 0xF) << 12 | b2 << 4 | (b3 >> 4)) + 0x111
                pos += 4
            else:
                length = top + 1
                pos += 2
            produced += length
    return pos - start, out_size


def lz11_decompress(data: bytes, pos: int = 0) -> Tuple[bytes, int]:
    start = pos
    if data[pos] != 0x11: raise ValueError("not LZ11")
    out_size = data[pos+1] | data[pos+2]<<8 | data[pos+3]<<16
    pos += 4
    if out_size == 0:
        out_size = struct.unpack_from("<I", data, pos)[0]; pos += 4
    out = bytearray()
    while len(out) < out_size:
        flags = data[pos]; pos += 1
        for bit in range(8):
            if len(out) >= out_size: break
            if not (flags & (0x80 >> bit)):
                out.append(data[pos]); pos += 1; continue
            b1 = data[pos]; top=b1>>4
            if top == 0:
                b2,b3=data[pos+1],data[pos+2]; pos += 3
                length=((b1&0xF)<<4 | b2>>4)+0x11
                disp=((b2&0xF)<<8 | b3)+1
            elif top == 1:
                b2,b3,b4=data[pos+1],data[pos+2],data[pos+3]; pos += 4
                length=((b1&0xF)<<12 | b2<<4 | b3>>4)+0x111
                disp=((b3&0xF)<<8 | b4)+1
            else:
                b2=data[pos+1]; pos += 2
                length=top+1
                disp=((b1&0xF)<<8 | b2)+1
            src=len(out)-disp
            if src < 0: raise ValueError("invalid LZ11 backref")
            for _ in range(length):
                out.append(out[src]); src += 1
                if len(out) >= out_size: break
    return bytes(out), pos-start


def lz10_decompress(data: bytes, pos: int = 0) -> Tuple[bytes, int]:
    start=pos
    if data[pos] != 0x10: raise ValueError("not LZ10")
    out_size=data[pos+1] | data[pos+2]<<8 | data[pos+3]<<16; pos+=4
    out=bytearray()
    while len(out)<out_size:
        flags=data[pos];pos+=1
        for bit in range(8):
            if len(out)>=out_size: break
            if flags & (0x80>>bit):
                b1,b2=data[pos],data[pos+1];pos+=2
                length=(b1>>4)+3; disp=(((b1&0xF)<<8)|b2)+1
                src=len(out)-disp
                for _ in range(length):
                    out.append(out[src]);src+=1
                    if len(out)>=out_size:break
            else:
                out.append(data[pos]);pos+=1
    return bytes(out),pos-start


def _best_match(data: bytes, p: int, table: Dict[bytes, deque], max_len: int, max_candidates: int = 4) -> Tuple[int,int]:
    if p+3 > len(data): return 0,0
    key=data[p:p+3]
    q=table.get(key)
    if not q: return 0,0
    best_len=0;best_disp=0
    checked=0
    for prev in reversed(q):
        disp=p-prev
        if disp>4096: break
        checked+=1
        if checked>max_candidates: break
        lim=min(max_len,len(data)-p)
        l=3
        while l<lim and data[prev+l]==data[p+l]: l+=1
        if l>best_len:
            best_len=l;best_disp=disp
            if l==lim: break
    return best_len,best_disp


def _add_pos(table: Dict[bytes,deque], data: bytes, p: int):
    if p+3>len(data): return
    k=data[p:p+3]; q=table[k]; q.append(p)
    while q and p-q[0]>4096: q.popleft()


def lz10_compress(data: bytes) -> bytes:
    if len(data)>=0x1000000: raise ValueError("LZ10 size too large")
    out=bytearray([0x10,len(data)&255,(len(data)>>8)&255,(len(data)>>16)&255])
    table=defaultdict(deque); p=0
    while p<len(data):
        flag_pos=len(out);out.append(0); flags=0
        for bit in range(8):
            if p>=len(data): break
            l,disp=_best_match(data,p,table,18)
            if l>=3:
                flags |= 0x80>>bit
                d=disp-1
                out.extend((((l-3)<<4)|((d>>8)&0xF), d&0xFF))
                for j in range(l): _add_pos(table,data,p+j)
                p+=l
            else:
                out.append(data[p]);_add_pos(table,data,p);p+=1
        out[flag_pos]=flags
    return bytes(out)


def lz11_compress(data: bytes) -> bytes:
    if len(data)>=0x1000000:
        out=bytearray([0x11,0,0,0])+bytearray(struct.pack("<I",len(data)))
    else:
        out=bytearray([0x11,len(data)&255,(len(data)>>8)&255,(len(data)>>16)&255])
    table=defaultdict(deque);p=0
    while p<len(data):
        flag_pos=len(out);out.append(0);flags=0
        for bit in range(8):
            if p>=len(data):break
            l,disp=_best_match(data,p,table,0x10110)
            if l>=3:
                flags |= 0x80>>bit; d=disp-1
                if l<=0x10:
                    out.extend((((l-1)<<4)|((d>>8)&0xF),d&0xFF))
                elif l<=0x110:
                    x=l-0x11
                    out.extend((((x>>4)&0xF),((x&0xF)<<4)|((d>>8)&0xF),d&0xFF))
                else:
                    x=l-0x111
                    out.extend((0x10|((x>>12)&0xF),(x>>4)&0xFF,((x&0xF)<<4)|((d>>8)&0xF),d&0xFF))
                for j in range(l): _add_pos(table,data,p+j)
                p+=l
            else:
                out.append(data[p]);_add_pos(table,data,p);p+=1
        out[flag_pos]=flags
    return bytes(out)


def scan_pack(pack: bytes) -> List[dict]:
    entries=[]; p=0; idx=0
    while p < len(pack):
        if pack[p] != 0x11:
            # tolerate zero alignment/padding only
            q=p
            while q<len(pack) and pack[q]==0:q+=1
            if q>=len(pack):break
            if q-p>4 or pack[q]!=0x11:
                raise ValueError(f"pack scan lost sync at 0x{p:X}")
            p=q
        consumed,dec=lz11_info(pack,p)
        entries.append({"index":idx,"offset":p,"compressed":consumed,"decompressed":dec})
        p=align4(p+consumed);idx+=1
    for i,e in enumerate(entries):
        e["slot"]=(entries[i+1]["offset"] if i+1<len(entries) else len(pack))-e["offset"]
    return entries


def parse_pack_inc(data: bytes) -> List[dict]:
    """Parse the companion pack.inc table: <u64 offset, u32 decompressed, u32 compressed, u32 id/hash>."""
    if len(data) % 20:
        raise ValueError(f"pack.inc size {len(data)} is not a multiple of 20")
    out=[]
    for i in range(len(data)//20):
        off,dec,comp,ident=struct.unpack_from("<QIII",data,i*20)
        out.append({"index":i,"offset":off,"decompressed":dec,"compressed":comp,"ident":ident})
    return out


def validate_pack_inc(pack: bytes, inc_records: List[dict]) -> None:
    """Ensure pack.inc exactly describes the supplied pack.dat before rebuilding it."""
    scanned=scan_pack(pack)
    if len(scanned)!=len(inc_records):
        raise ValueError(f"pack/inc entry count mismatch: {len(scanned)} vs {len(inc_records)}")
    for a,b in zip(scanned,inc_records):
        if (a["offset"],a["decompressed"],a["compressed"]) != (b["offset"],b["decompressed"],b["compressed"]):
            raise ValueError(f"pack.inc mismatch at entry {a['index']}: pack={a}, inc={b}")


def rebuild_pack_with_inc(pack: bytes, inc_data: bytes, replacements: Dict[int,bytes]) -> Tuple[bytes,bytes,dict]:
    """
    Rebuild pack.dat with variable-sized replacement entries and regenerate every pack.inc offset.
    Unchanged entries are copied byte-for-byte in their original LZ11 form; only replacements are recompressed.
    The final 32-bit identifier/hash field is preserved because it is entry identity metadata, not size/offset data.
    """
    recs=parse_pack_inc(inc_data)
    validate_pack_inc(pack,recs)
    bad=sorted(i for i in replacements if i<0 or i>=len(recs))
    if bad: raise IndexError(f"replacement entry out of range: {bad}")
    out=bytearray(); new_inc=bytearray(); changed=[]
    for r in recs:
        i=r["index"]; new_off=len(out)
        if i in replacements:
            raw=replacements[i]; blob=lz11_compress(raw); dec=len(raw); comp=len(blob)
            changed.append({"entry":i,"old_offset":r["offset"],"new_offset":new_off,
                            "old_compressed":r["compressed"],"new_compressed":comp,
                            "decompressed":dec})
        else:
            start=r["offset"]; end=start+r["compressed"]
            blob=pack[start:end]; dec=r["decompressed"]; comp=r["compressed"]
            if len(blob)!=comp: raise ValueError(f"entry {i} runs past pack.dat")
        out.extend(blob)
        while len(out)%4: out.append(0)
        new_inc.extend(struct.pack("<QIII",new_off,dec,comp,r["ident"]))
    return bytes(out),bytes(new_inc),{"entries":changed,"old_pack_size":len(pack),"new_pack_size":len(out),"delta":len(out)-len(pack)}


def parse_mesall(data: bytes) -> List[bytes]:
    if len(data)<12: raise ValueError("mes_all too small")
    n=struct.unpack_from("<I",data,0)[0]
    if n<=0 or n>10000 or 4+8*n>len(data): raise ValueError("bad mes_all count")
    out=[]
    for i in range(n):
        off,size=struct.unpack_from("<II",data,4+i*8)
        if off+size>len(data) or data[off]!=0x10: raise ValueError("bad mes_all record")
        dec,_=lz10_decompress(data,off);out.append(dec)
    return out


def build_mesall(records: List[bytes]) -> bytes:
    n=len(records); header=4+8*n; body=bytearray(); meta=[]
    for rec in records:
        while (header+len(body))%4: body.append(0)
        off=header+len(body); comp=lz10_compress(rec)
        body.extend(comp); meta.append((off,len(comp)))
    out=bytearray(struct.pack("<I",n))
    for off,size in meta: out.extend(struct.pack("<II",off,size))
    out.extend(body)
    return bytes(out)


def parse_mdt(data: bytes) -> List[bytes]:
    if len(data)<8: raise ValueError("MDT too small")
    n=struct.unpack_from("<I",data,0)[0]
    if n<=0 or 4+4*n>len(data):raise ValueError("bad MDT count")
    offs=list(struct.unpack_from("<"+"I"*n,data,4))
    out=[]
    for i,o in enumerate(offs):
        end=offs[i+1] if i+1<n else len(data)
        if o<4+4*n or o>end or end>len(data): raise ValueError("bad MDT offsets")
        out.append(data[o:end])
    return out


def switch_word_to_char(v: int) -> Optional[str]:
    base=(v-0x80)&0xFFFF
    if 0xFF01<=base<=0xFF5E: return chr(base-0xFEE0)
    if base==0x3000:return " "
    if base in SW_CUSTOM:return SW_CUSTOM[base]
    if base in SW_DIRECT:return SW_DIRECT[base]
    return None


def char_to_3ds(ch: str, game: Optional[str]=None) -> List[int]:
    # Turkish letters first: use stable ASCII donor slots patched in FFNT.
    if ch in TURKISH_DONOR_CODES:
        return [TURKISH_DONOR_CODES[ch]]
    if "0"<=ch<="9":return [0x80+ord(ch)-ord("0")]
    if "A"<=ch<="Z":
        # Donor capitals themselves must remain usable in normal source text.
        # Render them via the corresponding lowercase glyph slot.
        if ch in TURKISH_DONOR_CHARS.values():
            return [0xA4+ord(ch.lower())-ord("a")]
        return [0x8A+ord(ch)-ord("A")]
    if "a"<=ch<="z":return [0xA4+ord(ch)-ord("a")]
    if game and ch in GAME_SPECIAL.get(game,{}):
        return [GAME_SPECIAL[game][ch]]
    if ch in THREEDS_SPECIAL:return [THREEDS_SPECIAL[ch]]
    # Typography normalization that the 3DS table can represent safely.
    if ch in ("’","‘"):return [THREEDS_SPECIAL["'"]]
    if ch in ("“","”"):return [THREEDS_SPECIAL['"']]
    if ch in ("―","–","—"):
        return [GAME_SPECIAL.get(game,{}).get("-",THREEDS_SPECIAL["-"])]
    if ch=="…":return [THREEDS_SPECIAL["."]]
    if ch=="★":return [THREEDS_SPECIAL["☆"]]
    raise KeyError(ch)


def convert_switch_mdt(data: bytes, game: Optional[str]=None) -> Tuple[bytes, dict]:
    """
    Recode recognized Switch text words without changing file size or offset table.

    MDT offset tables can also contain pointer entries, not only monotonically increasing
    file offsets. For a safe cross-version port we therefore preserve the table byte-for-byte
    and only rewrite 16-bit words in the payload area beginning at the smallest real offset.
    This is valid for files whose section-count/shape matches between Switch and 3DS.
    """
    if len(data)<8: raise ValueError("MDT too small")
    n=struct.unpack_from("<I",data,0)[0]
    header=4+4*n
    if n<=0 or header>len(data): raise ValueError("bad MDT header")
    offs=struct.unpack_from("<"+"I"*n,data,4)
    real=[o for o in offs if header<=o<len(data)]
    if not real: raise ValueError("MDT has no real payload offsets")
    payload=min(real)
    out=bytearray(data);converted=0;unknown_chars=set(); text_words=[]
    # All known characters used by this patch are 1 codeword -> 1 codeword after
    # normalization, so offsets remain valid. Keep the positions/chars that were
    # actually recognized as text; that lets us wrap only genuine text and never
    # guess whether an unknown control operand happens to look like a character.
    for pos in range(payload,len(data)-1,2):
        v=struct.unpack_from("<H",data,pos)[0]
        ch=switch_word_to_char(v)
        if ch is None: continue
        try: mapped=char_to_3ds(ch,game)
        except KeyError:
            unknown_chars.add(ch); continue
        if len(mapped)!=1:
            raise ValueError(f"length-changing mapping for {ch!r} is not safe in-place")
        struct.pack_into("<H",out,pos,mapped[0]);converted+=1
        text_words.append((pos,ch))

    # Switch/HD text boxes are wider than the 3DS dialogue box.  Original 3DS
    # English lines are overwhelmingly <= 29-30 glyphs.  Insert the native 3DS
    # line-break opcode (word 0x0001) at an existing space, so file size and every
    # pointer/offset remain unchanged.  Existing control words naturally split
    # runs and are never touched.
    wraps=0; max_line=33
    runs=[]; run=[]; prev=None
    for item in text_words:
        if prev is None or item[0]==prev+2:
            run.append(item)
        else:
            if run:runs.append(run)
            run=[item]
        prev=item[0]
    if run:runs.append(run)
    for run in runs:
        start=0
        while len(run)-start > max_line:
            hi=min(start+max_line, len(run)-1)
            # Prefer a reasonably full line but never split extremely early.
            candidates=[i for i in range(start+10,hi+1) if run[i][1]==' ']
            if not candidates:
                candidates=[i for i in range(start+1,hi+1) if run[i][1]==' ']
            if not candidates: break
            cut=candidates[-1]
            struct.pack_into("<H",out,run[cut][0],1)
            wraps+=1; start=cut+1
    return bytes(out), {"sections":n,"converted_words":converted,"unknown_chars":sorted(unknown_chars),"payload_offset":payload,"auto_linebreaks":wraps,"max_line_glyphs":max_line}




def rebuild_trimmed_switch_variant(swraw: bytes, original_3ds_variant: bytes, base_3ds: bytes, game: Optional[str]="GS3") -> Tuple[bytes, dict]:
    """
    Rebuild GS3 b/c variants which were trimmed by the HD/Switch port.

    On 3DS these variant MDTs keep the base file's full offset-table count N, but
    only the first K alternative pages are physically stored.  From page K onward
    the table is copied verbatim from the base MDT.  The HD port normalizes these
    files by dropping that inherited tail and writing a K-entry table instead.

    We restore the 3DS table shape, shift the K real Switch offsets by the extra
    header bytes, preserve the original 3DS inherited tail, and keep the converted
    Switch payload unchanged.
    """
    def header_info(data: bytes):
        if len(data) < 8: raise ValueError("MDT too small")
        n=struct.unpack_from("<I",data,0)[0]
        if n<=0 or 4+4*n>len(data): raise ValueError("bad MDT header")
        offs=list(struct.unpack_from("<"+"I"*n,data,4))
        return n,4+4*n,offs
    kn,kh,ko=header_info(swraw)
    nn,nh,no=header_info(original_3ds_variant)
    bn,bh,bo=header_info(base_3ds)
    if nn != bn:
        raise ValueError(f"variant/base table count differs: {nn} vs {bn}")
    if kn >= nn:
        raise ValueError(f"Switch variant is not trimmed: {kn} >= {nn}")
    # The decisive format invariant: the legacy 3DS variant inherits every tail
    # entry from the corresponding base file starting exactly at K.
    if no[kn:] != bo[kn:]:
        first=next((i for i,(a,b) in enumerate(zip(no[kn:],bo[kn:]),kn) if a!=b),None)
        raise ValueError(f"3DS variant tail does not match base from K={kn}; first mismatch={first}")
    # Switch trimmed variants contain K ordinary file offsets.
    if not all(kh <= o < len(swraw) for o in ko):
        raise ValueError("Switch trimmed variant contains non-file/pointer offsets")
    converted,stats=convert_switch_mdt(swraw,game)
    delta=nh-kh
    new_first=[o+delta for o in ko]
    # preserve all inherited/legacy tail values byte-for-byte
    out=bytearray(struct.pack("<I",nn))
    out.extend(struct.pack("<"+"I"*nn,*(new_first+no[kn:])))
    out.extend(converted[kh:])
    stats.update({
        "mode":"trimmed_variant_restore",
        "3ds_sections":nn,
        "switch_variant_pages":kn,
        "restored_tail_entries":nn-kn,
        "header_growth":delta,
    })
    return bytes(out),stats

def extract_language(mes_path: Path, out_dir: Path, names: Optional[List[str]]=None):
    recs=parse_mesall(mes_path.read_bytes());out_dir.mkdir(parents=True,exist_ok=True)
    manifest={"count":len(recs),"records":[]}
    for i,r in enumerate(recs):
        if names and len(recs)==2*len(names):
            base=names[i//2];lang="jp" if i%2==0 else "en";fn=f"{i:03d}_{base}_{lang}.mdt"
        else: fn=f"{i:03d}.mdt"
        (out_dir/fn).write_bytes(r);manifest["records"].append(fn)
    (out_dir/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")


def inject_language(folder: Path, out_path: Path):
    man=json.loads((folder/"manifest.json").read_text(encoding="utf-8"))
    recs=[(folder/x).read_bytes() for x in man["records"]]
    out_path.write_bytes(build_mesall(recs))


def find_language_entries(pack: bytes, entries: List[dict]) -> Dict[str, Tuple[int,bytes]]:
    found={}
    candidates=[e for e in entries if 1_500_000<=e["decompressed"]<=3_500_000]
    for e in candidates:
        dec,_=lz11_decompress(pack,e["offset"])
        try: recs=parse_mesall(dec)
        except Exception: continue
        for gs,cnt in EXPECTED_MES_COUNTS.items():
            if len(recs)==cnt: found[gs]=(e["index"],dec)
    return found


def find_ffnt_entries(pack: bytes, entries: List[dict]) -> List[Tuple[int,bytes]]:
    out=[]
    for e in entries:
        if not (800_000<=e["decompressed"]<=1_300_000):continue
        dec,_=lz11_decompress(pack,e["offset"])
        if dec[:4] in (b"FFNT",b"CFNT"):out.append((e["index"],dec))
    return out


def _parse_ffnt_cmap(font: bytes) -> Dict[int,int]:
    # FINF CMAP pointer is stored as block_start+8.
    finf=font.find(b"FINF")
    if finf<0:raise ValueError("FINF missing")
    cmap_ptr=struct.unpack_from("<I",font,finf+0x1C)[0]
    off=cmap_ptr-8; mapping={};seen=set()
    while off and off not in seen:
        seen.add(off)
        magic,size,start,end,typ,reserved,nextptr=struct.unpack_from("<4sI4HI",font,off)
        if magic!=b"CMAP":break
        p=off+20
        if typ==0:
            first=struct.unpack_from("<H",font,p)[0]
            for cp in range(start,end+1):mapping[cp]=first+cp-start
        elif typ==1:
            vals=struct.unpack_from("<"+"H"*(end-start+1),font,p)
            for cp,idx in zip(range(start,end+1),vals):
                if idx!=0xFFFF:mapping[cp]=idx
        elif typ==2:
            count=struct.unpack_from("<H",font,p)[0];p+=2
            for _ in range(count):
                cp,idx=struct.unpack_from("<HH",font,p);p+=4;mapping[cp]=idx
        off=nextptr-8 if nextptr else 0
    return mapping


def _ffnt_sheet_decode(font: bytes):
    t=font.find(b"TGLP")
    if t<0:raise ValueError("TGLP missing")
    # <4sI4BI6HI
    vals=struct.unpack_from("<4sI4BI6HI",font,t)
    _,size,cw,ch,baseline,maxw,sheet_size,sheet_count,fmt,cols,rows,w,h,data_off=vals
    if fmt!=8 or sheet_count<1:raise ValueError("font patcher currently expects A8, 1+ sheet FFNT")
    raw=font[data_off:data_off+sheet_size]
    bmp=bytearray(w*h)
    W=1<<(w-1).bit_length(); H=1<<(h-1).bit_length()
    # These fonts are already power-of-two; use exact 3DS 8x8 swizzle.
    for ty in range(H//8):
      for tx in range(W//8):
       for y in range(2):
        for x in range(2):
         for y2 in range(2):
          for x2 in range(2):
           for y3 in range(2):
            for x3 in range(2):
             px=x3+x2*2+x*4+tx*8; py=y3+y2*2+y*4+ty*8
             dx=x3+x2*4+x*16+tx*64; dy=y3*2+y2*8+y*32+ty*W*8
             if px<w and py<h and dx+dy<len(raw):bmp[px+py*w]=raw[dx+dy]
    return {"t":t,"cw":cw,"ch":ch,"cols":cols,"rows":rows,"w":w,"h":h,"data_off":data_off,"sheet_size":sheet_size,"bmp":bmp}


def _ffnt_sheet_encode(info) -> bytes:
    w,h=info["w"],info["h"];bmp=info["bmp"];raw=bytearray(info["sheet_size"])
    W=1<<(w-1).bit_length();H=1<<(h-1).bit_length()
    for ty in range(H//8):
      for tx in range(W//8):
       for y in range(2):
        for x in range(2):
         for y2 in range(2):
          for x2 in range(2):
           for y3 in range(2):
            for x3 in range(2):
             px=x3+x2*2+x*4+tx*8; py=y3+y2*2+y*4+ty*8
             dx=x3+x2*4+x*16+tx*64; dy=y3*2+y2*8+y*32+ty*W*8
             if px<w and py<h and dx+dy<len(raw):raw[dx+dy]=bmp[px+py*w]
    return bytes(raw)


def patch_font(font: bytes) -> Tuple[bytes,dict]:
    """Patch donor Western glyph cells to Ğ/İ/Ş/ğ/ı/ş; copy matching widths."""
    cmap=_parse_ffnt_cmap(font); info=_ffnt_sheet_decode(font)
    cw,ch,cols,w,h=info["cw"],info["ch"],info["cols"],info["w"],info["h"]
    pitchx=cw+1;pitchy=ch+1
    def cell(idx):
        x=(idx%cols)*pitchx; row=idx//cols; y=h-(row+1)*pitchy
        a=[[info["bmp"][(y+yy)*w+x+xx] for xx in range(cw)] for yy in range(ch)]
        a.reverse() # visual orientation
        return a
    def put(idx,a):
        a=[r[:] for r in a];a.reverse()
        x=(idx%cols)*pitchx;row=idx//cols;y=h-(row+1)*pitchy
        for yy in range(ch):
            for xx in range(cw):info["bmp"][(y+yy)*w+x+xx]=a[yy][xx]
    def over(a,b,yrange=None):
        ys=range(ch) if yrange is None else yrange
        for yy in ys:
            for xx in range(cw):a[yy][xx]=max(a[yy][xx],b[yy][xx])
    base={c:cell(cmap[ord(c)]) for c in "GI SgisÇç".replace(" ","")}
    # Generate visual glyphs.
    G=[r[:] for r in base['G']]; g=[r[:] for r in base['g']]
    # Simple breve matching the thin bitmap style.
    for a in (G,g):
        pts=[(5,1),(6,2),(7,3),(8,3),(9,3),(10,2),(11,1)]
        for x,y in pts:
            if 0<=x<cw and 0<=y<ch:a[y][x]=255
    Idot=[r[:] for r in base['I']]
    # use the real i-dot rather than inventing a weight
    for yy in range(min(5,ch)):
        for xx in range(cw):Idot[yy][xx]=max(Idot[yy][xx],base['i'][yy][xx])
    # Ensure the uppercase dotted-I dot remains visible even if the source i dot
    # falls on an atlas edge in this compact bitmap font.
    for yy in (1,2):
        for xx in (7,8):
            if yy<ch and xx<cw: Idot[yy][xx]=255
    dotless=[r[:] for r in base['i']]
    for yy in range(min(5,ch)):
        for xx in range(cw):dotless[yy][xx]=0
    Sced=[r[:] for r in base['S']]; sced=[r[:] for r in base['s']]
    over(Sced,base['Ç'],range(max(0,ch-5),ch)); over(sced,base['ç'],range(max(0,ch-5),ch))
    generated={'Ğ':G,'İ':Idot,'Ş':Sced,'ğ':g,'ı':dotless,'ş':sced}
    donors=TURKISH_DONOR_CHARS
    bases={'Ğ':'G','İ':'I','Ş':'S','ğ':'g','ı':'i','ş':'s'}
    for tr,img in generated.items():put(cmap[ord(donors[tr])],img)
    # CWDH: copy width metrics from base glyph to donor glyph.
    cwdh=font.find(b"CWDH"); patched=bytearray(font)
    if cwdh>=0:
        _,size,start,end,nextptr=struct.unpack_from("<4sI2HI",font,cwdh)
        p=cwdh+16
        for tr,donor in donors.items():
            di=cmap[ord(donor)]; bi=cmap[ord(bases[tr])]
            if start<=di<=end and start<=bi<=end:
                patched[p+(di-start)*3:p+(di-start)*3+3]=font[p+(bi-start)*3:p+(bi-start)*3+3]
    sheet=_ffnt_sheet_encode(info)
    patched[info["data_off"]:info["data_off"]+len(sheet)]=sheet
    return bytes(patched),{"patched_chars":list(generated),"donor_unicode":donors}


def port_switch(pack_path: Path, switch_root: Path, out_dir: Path, make_pack: bool=False, inc_path: Optional[Path]=None):
    out_dir.mkdir(parents=True,exist_ok=True)
    pack=pack_path.read_bytes();entries=scan_pack(pack)
    langs=find_language_entries(pack,entries)
    if set(langs)!=set(GS_NAMES):raise RuntimeError(f"could not locate all language entries; got {list(langs)}")
    report={"pack_entries":{},"games":{},"fonts":[],"warnings":[]}
    replacements={}
    for gs,names in GS_NAMES.items():
        idx,mes=langs[gs]; recs=parse_mesall(mes); new=list(recs)
        gsrep={"entry":idx,"files":[],"ported":0,"skipped":0}
        scen=switch_root/"Data"/"StreamingAssets"/gs/"scenario"
        if not scen.exists():
            # accept the root one level above Data, or extracted mod root
            matches=list(switch_root.rglob(f"{gs}/scenario"))
            if not matches: raise FileNotFoundError(f"cannot find {gs}/scenario under {switch_root}")
            scen=matches[0]
        for i,name in enumerate(names):
            sw=scen/(name+"_u.mdt")
            if not sw.exists():
                gsrep["files"].append({"name":name,"status":"missing_switch_file"});gsrep["skipped"]+=1;continue
            en_idx=2*i+1; original=recs[en_idx]
            swraw=sw.read_bytes(); sw_sections=struct.unpack_from("<I",swraw,0)[0]
            ds_sections=struct.unpack_from("<I",original,0)[0]
            if sw_sections==ds_sections:
                converted,stats=convert_switch_mdt(swraw,gs);new[en_idx]=converted
                gsrep["files"].append({"name":name,"status":"ported",**stats});gsrep["ported"]+=1
                continue
            # GS3 HD/Switch b/c variants are trimmed to their physically stored K pages.
            # Recover the corresponding base name and restore the legacy 3DS N-entry table.
            if gs=="GS3" and re.search(r"[bc]_text$",name):
                base_name=re.sub(r"[bc]_text$","_text",name)
                if base_name in names:
                    base_idx=2*names.index(base_name)+1
                    try:
                        converted,stats=rebuild_trimmed_switch_variant(swraw,original,recs[base_idx],gs)
                        new[en_idx]=converted
                        gsrep["files"].append({"name":name,"status":"ported_trimmed_variant",**stats});gsrep["ported"]+=1
                        continue
                    except Exception as ex:
                        gsrep["files"].append({"name":name,"status":"variant_restore_failed","3ds_sections":ds_sections,"switch_sections":sw_sections,"error":str(ex)})
                        gsrep["skipped"]+=1;continue
            gsrep["files"].append({"name":name,"status":"skipped_section_mismatch","3ds_sections":ds_sections,"switch_sections":sw_sections})
            gsrep["skipped"]+=1;continue
        newmes=build_mesall(new); (out_dir/f"{gs}_mes_all_tr.bin").write_bytes(newmes)
        replacements[idx]=newmes; report["pack_entries"][gs]=idx;report["games"][gs]=gsrep
    # Patch all FFNT entries that expose the expected Western cmap. Usually two relevant fonts in this pack.
    ffnts=find_ffnt_entries(pack,entries)
    for idx,font in ffnts:
        try:
            cmap=_parse_ffnt_cmap(font)
            needed=[ord(x) for x in "GI SgisÇçQXJZUR".replace(" ","")]
            if not all(x in cmap for x in needed):continue
            pf,meta=patch_font(font);(out_dir/f"font_entry_{idx:05d}_tr.ffnt").write_bytes(pf)
            replacements[idx]=pf;report["fonts"].append({"entry":idx,**meta})
        except Exception as ex:
            report["warnings"].append(f"font entry {idx}: {ex}")
    # Reinjection: with pack.inc we may safely grow entries and rebuild all following offsets.
    # Without pack.inc retain the older fixed-slot safety mode.
    pack_result={"requested":make_pack,"success":False,"entries":[],"mode":None}
    if make_pack and inc_path is not None:
        inc_data=inc_path.read_bytes()
        new_pack,new_inc,meta=rebuild_pack_with_inc(pack,inc_data,replacements)
        p=out_dir/"pack_tr_patched.dat"; q=out_dir/"pack_tr_patched.inc"
        p.write_bytes(new_pack);q.write_bytes(new_inc)
        # Final self-check catches offset/size or compressor mistakes before emitting success.
        validate_pack_inc(new_pack,parse_pack_inc(new_inc))
        pack_result.update({"success":True,"mode":"full_index_rebuild","path":p.name,"inc_path":q.name,**meta})
        pack_result["entries"]=meta["entries"]
    elif make_pack:
        patched=bytearray(pack);byidx={e["index"]:e for e in entries};ok=True
        pack_result["mode"]="fixed_slot"
        for idx,raw in sorted(replacements.items()):
            e=byidx[idx];comp=lz11_compress(raw);fits=len(comp)<=e["slot"]
            pack_result["entries"].append({"entry":idx,"new_compressed":len(comp),"slot":e["slot"],"fits":fits})
            if not fits:ok=False;continue
            patched[e["offset"]:e["offset"]+e["slot"]]=comp+b"\0"*(e["slot"]-len(comp))
        if ok:
            p=out_dir/"pack_tr_patched.dat";p.write_bytes(patched);pack_result["success"]=True;pack_result["path"]=p.name
        else:
            report["warnings"].append("One or more recompressed entries do not fit their original pack.dat slot; provide pack.inc and pass --inc so all following offsets can be rebuilt safely.")
    report["pack_reinjection"]=pack_result
    report["warnings"].append("Switch menu/text *.bin assets are HD/Unity-side text tables; 3DS menu resources still require separate identification/porting and are not injected by this build.")
    (out_dir/"port_report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    return report


def cmd_extract_games(a):
    pack_path=Path(a.pack); data=pack_path.read_bytes(); entries=scan_pack(data); langs=find_language_entries(data,entries)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True); manifest={"source":pack_path.name,"games":{}}
    for gs,names in GS_NAMES.items():
        if gs not in langs: raise RuntimeError(f"{gs} language entry not found")
        idx,mes=langs[gs]; mesname=f"{gs}_mes_all.bin"; (out/mesname).write_bytes(mes)
        extract_language(out/mesname,out/gs,names)
        manifest["games"][gs]={"pack_entry":idx,"mes_all":mesname,"folder":gs}
    (out/"pack_language_manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(manifest["games"],indent=2,ensure_ascii=False))

def cmd_inject_pack_entry(a):
    pack_path=Path(a.pack); data=pack_path.read_bytes(); entries=scan_pack(data); idx=int(a.entry)
    if idx<0 or idx>=len(entries): raise IndexError(idx)
    raw=Path(a.replacement).read_bytes(); comp=lz11_compress(raw); e=entries[idx]
    if len(comp)>e["slot"]:
        raise RuntimeError(f"replacement entry {idx} needs {len(comp)} bytes but fixed slot is {e['slot']} bytes; refusing to shift following pack offsets")
    patched=bytearray(data); patched[e["offset"]:e["offset"]+e["slot"]]=comp+b"\0"*(e["slot"]-len(comp))
    Path(a.out).write_bytes(patched); print(f"entry {idx}: {len(comp)}/{e['slot']} bytes -> {a.out}")

def cmd_scan(a):
    data=Path(a.pack).read_bytes(); entries=scan_pack(data)
    Path(a.out).write_text(json.dumps(entries,indent=2),encoding="utf-8")
    print(f"{len(entries)} entries -> {a.out}")

def cmd_extract_pack(a):
    data=Path(a.pack).read_bytes();entries=scan_pack(data);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    for e in entries:
        dec,_=lz11_decompress(data,e["offset"]);(out/f"{e['index']:05d}.bin").write_bytes(dec)
    (out/"pack_manifest.json").write_text(json.dumps(entries,indent=2),encoding="utf-8")

def cmd_extract_language(a):
    names=GS_NAMES.get(a.game.upper()) if a.game else None;extract_language(Path(a.mes),Path(a.out),names)

def cmd_inject_language(a):inject_language(Path(a.folder),Path(a.out))

def cmd_rebuild_pack(a):
    pack=Path(a.pack).read_bytes(); inc=Path(a.inc).read_bytes(); repl={}
    for spec in a.replace:
        if "=" not in spec: raise ValueError("--replace must be ENTRY=FILE")
        k,v=spec.split("=",1); repl[int(k,0)]=Path(v).read_bytes()
    new_pack,new_inc,meta=rebuild_pack_with_inc(pack,inc,repl)
    Path(a.out_pack).write_bytes(new_pack);Path(a.out_inc).write_bytes(new_inc)
    validate_pack_inc(new_pack,parse_pack_inc(new_inc))
    print(json.dumps(meta,indent=2,ensure_ascii=False))


def cmd_port(a):
    rep=port_switch(Path(a.pack),Path(a.switch_root),Path(a.out),a.make_pack,Path(a.inc) if a.inc else None)
    for gs in GS_NAMES:
        x=rep["games"][gs];print(f"{gs}: {x['ported']} ported, {x['skipped']} skipped")
    print(f"fonts patched: {len(rep['fonts'])}")
    if a.make_pack:print("pack.dat:","created" if rep["pack_reinjection"]["success"] else "not created (see report)")


def main():
    ap=argparse.ArgumentParser(description="Ace Attorney Trilogy 3DS language tool / Switch-TR scenario porter")
    sp=ap.add_subparsers(dest="cmd",required=True)
    p=sp.add_parser("extract-games");p.add_argument("pack");p.add_argument("out");p.set_defaults(func=cmd_extract_games)
    p=sp.add_parser("inject-pack-entry");p.add_argument("pack");p.add_argument("entry",type=int);p.add_argument("replacement");p.add_argument("out");p.set_defaults(func=cmd_inject_pack_entry)
    p=sp.add_parser("scan-pack");p.add_argument("pack");p.add_argument("-o","--out",default="pack_manifest.json");p.set_defaults(func=cmd_scan)
    p=sp.add_parser("extract-pack");p.add_argument("pack");p.add_argument("out");p.set_defaults(func=cmd_extract_pack)
    p=sp.add_parser("extract-language");p.add_argument("mes");p.add_argument("out");p.add_argument("--game",choices=["GS1","GS2","GS3"]);p.set_defaults(func=cmd_extract_language)
    p=sp.add_parser("inject-language");p.add_argument("folder");p.add_argument("out");p.set_defaults(func=cmd_inject_language)
    p=sp.add_parser("rebuild-pack");p.add_argument("pack");p.add_argument("inc");p.add_argument("out_pack");p.add_argument("out_inc");p.add_argument("--replace",action="append",default=[],metavar="ENTRY=FILE",help="replace a decompressed pack entry; may be repeated");p.set_defaults(func=cmd_rebuild_pack)
    p=sp.add_parser("port-switch");p.add_argument("pack");p.add_argument("switch_root");p.add_argument("out");p.add_argument("--make-pack",action="store_true",help="emit patched pack.dat; with --inc rebuilds offsets safely");p.add_argument("--inc",help="companion pack.inc; enables variable-size full index rebuild");p.set_defaults(func=cmd_port)
    a=ap.parse_args();a.func(a)
if __name__=="__main__":main()
