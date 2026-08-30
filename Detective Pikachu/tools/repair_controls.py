#!/usr/bin/env python3
from pathlib import Path
import argparse, sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from msbt_toolkit import parse_msbt, build_msbt


def ctrl_spans(raw: bytes):
    out=[]; i=0
    while i < len(raw):
        if raw[i] == 0x0E and i + 7 <= len(raw):
            arg_len = int.from_bytes(raw[i+5:i+7], 'little')
            end = i + 7 + arg_len
            if end <= len(raw):
                out.append((i, end, raw[i:end]))
                i=end; continue
        i += 1
    return out


def bad_utf8_roundtrip(ctrl: bytes) -> bytes:
    return ctrl.decode('utf-8', errors='replace').encode('utf-8')


def repair_row(en_raw: bytes, tr_raw: bytes):
    ec = ctrl_spans(en_raw)
    tc = ctrl_spans(tr_raw)
    if len(ec) != len(tc):
        raise ValueError(f'control count mismatch English={len(ec)} Turkish={len(tc)}')
    if not ec:
        return tr_raw, 0, 0
    out=bytearray(); prev=0; technical=0; semantic_ctrl=0
    for (ts,te,tseq),(es,ee,eseq) in zip(tc,ec):
        out += tr_raw[prev:ts]
        bad = bad_utf8_roundtrip(eseq)
        if tr_raw[ts:ts+len(bad)] == bad:
            consume_end = ts + len(bad)
            if bad != eseq:
                technical += 1
        else:
            consume_end = te
            if tseq != eseq:
                semantic_ctrl += 1
        out += eseq
        prev = consume_end
    out += tr_raw[prev:]
    return bytes(out), technical, semantic_ctrl


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('english_dir', type=Path)
    ap.add_argument('turkish_patch_dir', type=Path)
    ap.add_argument('out_dir', type=Path)
    args=ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stats=[]; tot_tech=tot_sem=0
    for ep in sorted(args.english_dir.glob('*.msbt')):
        tp=args.turkish_patch_dir/ep.name
        en=parse_msbt(ep); tr=parse_msbt(tp)
        if len(en['raws'])!=len(tr['raws']): raise ValueError(ep.name)
        new=[]; ft=fs=0
        for er,trr in zip(en['raws'],tr['raws']):
            rr,a,b=repair_row(er,trr); new.append(rr); ft+=a; fs+=b
        (args.out_dir/ep.name).write_bytes(build_msbt(tr,new))
        stats.append((ep.name,ft,fs)); tot_tech+=ft; tot_sem+=fs
    print(f'Repaired {len(stats)} MSBT files; corrupted control sequences fixed={tot_tech}; non-roundtrip control corrections={tot_sem}')
    for s in stats:
        if s[1] or s[2]: print(f'{s[0]}: utf8-corrupt={s[1]}, other-control={s[2]}')

if __name__=='__main__': main()
