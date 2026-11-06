#!/usr/bin/env python3
"""Minimal Lua 5.1 binary chunk reader used for VLR diagnostics."""
import struct

class R:
    def __init__(self,b):
        self.b=b;self.o=0
        if b[:4]!=b'\x1bLua' or len(b)<12: raise ValueError('Lua chunk değil')
        self.o=4; self.version=self.u8(); self.fmt=self.u8(); self.endian=self.u8();
        self.intsz=self.u8();self.sizetsz=self.u8();self.instrsz=self.u8();self.numsz=self.u8();self.integral=self.u8()
        self.pref='<' if self.endian==1 else '>'
        if self.version!=0x51: raise ValueError(f'Lua 5.1 değil: 0x{self.version:02x}')
    def u8(self):v=self.b[self.o];self.o+=1;return v
    def raw(self,n):v=self.b[self.o:self.o+n];self.o+=n;return v
    def uint(self,n):return int.from_bytes(self.raw(n),'little' if self.endian==1 else 'big')
    def cint(self):return self.uint(self.intsz)
    def szt(self):return self.uint(self.sizetsz)
    def string(self):
        n=self.szt()
        if n==0:return None
        x=self.raw(n)
        return x[:-1] if x.endswith(b'\0') else x
    def proto(self):
        p={'source':self.string(),'linedefined':self.cint(),'lastlinedefined':self.cint(),
           'nups':self.u8(),'numparams':self.u8(),'is_vararg':self.u8(),'maxstack':self.u8()}
        nc=self.cint();p['code']=[self.raw(self.instrsz) for _ in range(nc)]
        nk=self.cint();const=[]
        for _ in range(nk):
            t=self.u8()
            if t==0:v=None
            elif t==1:v=bool(self.u8())
            elif t==3:v=self.raw(self.numsz)
            elif t==4:v=self.string()
            else: raise ValueError(f'Bilinmeyen constant type {t} @ {self.o-1}')
            const.append((t,v))
        p['constants']=const
        np=self.cint();p['protos']=[self.proto() for _ in range(np)]
        nl=self.cint();p['lineinfo']=[self.cint() for _ in range(nl)]
        nv=self.cint();p['locvars']=[(self.string(),self.cint(),self.cint()) for _ in range(nv)]
        nu=self.cint();p['upvalues']=[self.string() for _ in range(nu)]
        return p

def load(path):
    b=open(path,'rb').read();r=R(b);p=r.proto();return r,p

def walk(p):
    yield p
    for q in p['protos']: yield from walk(q)
