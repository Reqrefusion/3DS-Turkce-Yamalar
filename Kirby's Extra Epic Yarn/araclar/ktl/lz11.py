from __future__ import annotations
from collections import defaultdict, deque
import struct

def decompress(src: bytes) -> bytes:
    if not src or src[0] != 0x11:
        raise ValueError('LZ11 header missing')
    out_size = src[1] | (src[2] << 8) | (src[3] << 16)
    pos = 4
    if out_size == 0:
        out_size = struct.unpack_from('<I', src, pos)[0]
        pos += 4
    out = bytearray()
    while len(out) < out_size:
        flags = src[pos]; pos += 1
        for bit in range(8):
            if len(out) >= out_size: break
            if not (flags & (0x80 >> bit)):
                out.append(src[pos]); pos += 1
            else:
                b1, b2 = src[pos], src[pos+1]; pos += 2
                hi = b1 >> 4
                if hi == 0:
                    b3 = src[pos]; pos += 1
                    length = ((b1 & 0x0F) << 4 | (b2 >> 4)) + 0x11
                    disp = ((b2 & 0x0F) << 8 | b3) + 1
                elif hi == 1:
                    b3, b4 = src[pos], src[pos+1]; pos += 2
                    length = ((b1 & 0x0F) << 12 | b2 << 4 | (b3 >> 4)) + 0x111
                    disp = ((b3 & 0x0F) << 8 | b4) + 1
                else:
                    length = hi + 1
                    disp = ((b1 & 0x0F) << 8 | b2) + 1
                for _ in range(length):
                    out.append(out[-disp])
    return bytes(out[:out_size])

def _enc_match(length: int, disp: int) -> bytes:
    d = disp - 1
    if not (1 <= disp <= 0x1000): raise ValueError('bad disp')
    if 3 <= length <= 0x10:
        b1 = ((length - 1) << 4) | ((d >> 8) & 0xF)
        b2 = d & 0xFF
        return bytes((b1,b2))
    if 0x11 <= length <= 0x110:
        n = length - 0x11
        b1 = (n >> 4) & 0xF
        b2 = ((n & 0xF) << 4) | ((d >> 8) & 0xF)
        b3 = d & 0xFF
        return bytes((b1,b2,b3))
    if 0x111 <= length <= 0x10110:
        n = length - 0x111
        b1 = 0x10 | ((n >> 12) & 0xF)
        b2 = (n >> 4) & 0xFF
        b3 = ((n & 0xF) << 4) | ((d >> 8) & 0xF)
        b4 = d & 0xFF
        return bytes((b1,b2,b3,b4))
    raise ValueError('bad length')

def compress(data: bytes, max_candidates: int = 64) -> bytes:
    n = len(data)
    if n >= 0x1000000:
        out = bytearray((0x11,0,0,0)) + bytearray(struct.pack('<I',n))
    else:
        out = bytearray((0x11,n&0xFF,(n>>8)&0xFF,(n>>16)&0xFF))
    # 3-byte hash -> recent positions. 64 candidates is a good speed/ratio balance.
    hist: dict[bytes, deque[int]] = defaultdict(deque)
    pos = 0
    def add_pos(p: int):
        if p + 2 >= n: return
        k = data[p:p+3]
        q = hist[k]; q.append(p)
        # Remove positions outside 4K window and cap chain length.
        cutoff = p - 0x1000
        while q and q[0] < cutoff: q.popleft()
        while len(q) > max_candidates: q.popleft()
    while pos < n:
        flag_idx = len(out); out.append(0); flags=0
        for bit in range(8):
            if pos >= n: break
            best_len = 0; best_disp = 0
            if pos + 2 < n:
                k = data[pos:pos+3]
                q = hist.get(k)
                if q:
                    max_len = min(0x10110, n-pos)
                    # newest candidates first; nearby matches usually perform well
                    for cand in reversed(q):
                        disp = pos-cand
                        if disp <= 0 or disp > 0x1000: continue
                        l=3
                        # Overlapping matches are legal; compare against repeated source pattern.
                        while l < max_len and data[pos+l] == data[cand + (l % disp)]:
                            l += 1
                        if l > best_len:
                            best_len=l; best_disp=disp
                            if l == max_len: break
            if best_len >= 3:
                flags |= (0x80 >> bit)
                out += _enc_match(best_len,best_disp)
                old=pos; pos += best_len
                # Populate history for every consumed position so future matches stay strong.
                for p in range(old,pos): add_pos(p)
            else:
                out.append(data[pos]); add_pos(pos); pos += 1
        out[flag_idx]=flags
    return bytes(out)
