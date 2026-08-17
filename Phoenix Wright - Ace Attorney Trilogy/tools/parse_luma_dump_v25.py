#!/usr/bin/env python3
from pathlib import Path
from struct import unpack_from
import argparse
NAMES=[*(f'r{i}' for i in range(13)),'sp','lr','pc','cpsr','dfsr','ifsr','far','fpexc','fpinst','fpinst2']
EX=('FIQ','undefined instruction','prefetch abort','data abort')
FAULT={1:'Alignment',4:'Instruction cache maintenance operation fault',12:'External Abort on translation - First-level',14:'External Abort on translation - Second-level',5:'Translation - Section',7:'Translation - Page',3:'Access bit - Section',6:'Access bit - Page',9:'Domain - Section',11:'Domain - Page',13:'Permission - Section',15:'Permission - Page',8:'Precise External Abort',22:'Imprecise External Abort',2:'Debug event'}
def parse(path):
 b=Path(path).read_bytes()
 if unpack_from('<2I',b)!=(0xdeadc0de,0xdeadcafe): raise SystemExit('Not a Luma3DS exception dump')
 ver,proc,exc,_,nbr,codesz,stacksz,addsz=unpack_from('<8I',b,8); n=nbr//4; regs=unpack_from('<%dI'%n,b,40); proc,core=proc&0xffff,proc>>16
 print(f'Format: {ver>>16}.{ver&0xffff}')
 print('Processor:', 'Arm9' if proc==9 else f'Arm11 (core {core})')
 print('Exception:', EX[exc] if exc<len(EX) else f'unknown({exc})')
 if proc==11 and exc>=2:
  xfsr=regs[18] if exc==2 else regs[17];print('Fault status:',FAULT.get(xfsr&0xf,'Unknown'),f'(0x{xfsr:08X})')
 if addsz:
  off=40+n*4+codesz+stacksz; ad=b[off:off+addsz]
  if proc==11: print('Process:',ad[:8].rstrip(b'\0').decode('ascii','replace'),f'({unpack_from("<Q",ad,8)[0]:016X})')
 print('Registers:')
 for name,val in zip(NAMES,regs): print(f'  {name:<6} 0x{val:08X}')
 thumb=bool(regs[16]&0x20); co=40+n*4; code=b[co:co+codesz]; addr=regs[15]-codesz+(2 if thumb else 4)
 print(f'Code dump address: 0x{addr:08X}, size={len(code)}')
 print(f'Stack size: {stacksz}')
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('dump');parse(ap.parse_args().dump)
