#!/usr/bin/env python3
import struct, wave, argparse
from pathlib import Path

def parse_riff(b):
    if b[:4] not in (b'RIFF',b'RIFX') or b[8:12]!=b'WAVE': raise ValueError('not RIFF WAVE')
    be=b[:4]==b'RIFX'; en='>' if be else '<'; o=12; chunks={}
    while o+8<=len(b):
        tag=b[o:o+4]; sz=struct.unpack_from(en+'I',b,o+4)[0]; chunks.setdefault(tag,[]).append((o+8,sz)); o+=8+sz+(sz&1)
    return be,chunks

def decode_wwise_dsp(src: bytes):
    be,ch=parse_riff(src); en='>' if be else '<'
    fo,fs=ch[b'fmt '][0]; do,ds=ch[b'data'][0]
    fmt=src[fo:fo+fs]
    format_tag,channels,rate,avg,block,bits=struct.unpack_from(en+'HHIIHH',fmt,0)
    if channels!=1: raise NotImplementedError('mono only currently')
    if format_tag!=2 or bits!=4: raise ValueError((format_tag,bits))
    extra=struct.unpack_from(en+'H',fmt,0x10)[0]
    expected=0x0c + channels*0x2e
    if extra!=expected: raise ValueError(f'not Wwise Nintendo DSP extra={extra:#x} expected={expected:#x}')
    num_samples=struct.unpack_from(en+'i',fmt,0x18)[0]
    h=fmt[0x1c:0x1c+0x2e]
    coefs=list(struct.unpack_from(en+'16h',h,0))
    hist1,hist2=struct.unpack_from(en+'hh',h,0x24)
    data=src[do:do+ds]
    out=[]
    def clamp(x): return -32768 if x < -32768 else 32767 if x > 32767 else x
    p=0
    while p+8<=len(data) and len(out)<num_samples:
        fr=data[p:p+8]; p+=8
        ps=fr[0]; pred=(ps>>4)&0xf; shift=ps&0xf
        if pred>=8: pred=0
        c1=coefs[pred*2]; c2=coefs[pred*2+1]
        for byte in fr[1:]:
            for nib in ((byte>>4)&0xf, byte&0xf):
                if nib>=8: nib-=16
                # Nintendo DSP ADPCM formula
                sample=((nib << shift) << 11) + 1024 + c1*hist1 + c2*hist2
                sample=clamp(sample >> 11)
                hist2,hist1=hist1,sample
                out.append(sample)
                if len(out)>=num_samples: break
            if len(out)>=num_samples: break
    return rate,out, {'num_samples':num_samples,'coefs':coefs,'hist_init':struct.unpack_from(en+'hh',h,0x24),'data_size':ds}

def write_wav(path,rate,samples):
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(struct.pack('<%dh'%len(samples),*samples))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('input'); ap.add_argument('output'); a=ap.parse_args()
    b=Path(a.input).read_bytes(); rate,s,info=decode_wwise_dsp(b); write_wav(a.output,rate,s)
    print(f'{len(s)} samples @ {rate} Hz = {len(s)/rate:.3f}s'); print(info)
if __name__=='__main__': main()
