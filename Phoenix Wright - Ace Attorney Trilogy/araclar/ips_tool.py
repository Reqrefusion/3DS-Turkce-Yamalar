#!/usr/bin/env python3
from pathlib import Path
import argparse
def create(old,new):
 if len(old)!=len(new): raise ValueError('same-size files required')
 out=bytearray(b'PATCH');i=0
 while i<len(old):
  if old[i]==new[i]: i+=1;continue
  s=i
  while i<len(old) and old[i]!=new[i] and i-s<0xffff:i+=1
  out+=s.to_bytes(3,'big')+(i-s).to_bytes(2,'big')+new[s:i]
 return bytes(out+b'EOF')
def apply(src,ips):
 if not ips.startswith(b'PATCH'): raise ValueError('bad IPS')
 b=bytearray(src);p=5
 while ips[p:p+3]!=b'EOF':
  o=int.from_bytes(ips[p:p+3],'big');n=int.from_bytes(ips[p+3:p+5],'big');p+=5
  if n: b[o:o+n]=ips[p:p+n];p+=n
  else:
   r=int.from_bytes(ips[p:p+2],'big');v=ips[p+2];p+=3;b[o:o+r]=bytes([v])*r
 return bytes(b)
def main():
 ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='cmd',required=True)
 c=sub.add_parser('create');c.add_argument('old');c.add_argument('new');c.add_argument('ips')
 a=sub.add_parser('apply');a.add_argument('src');a.add_argument('ips');a.add_argument('out')
 x=ap.parse_args()
 if x.cmd=='create':Path(x.ips).write_bytes(create(Path(x.old).read_bytes(),Path(x.new).read_bytes()))
 else:Path(x.out).write_bytes(apply(Path(x.src).read_bytes(),Path(x.ips).read_bytes()))
if __name__=='__main__':main()
