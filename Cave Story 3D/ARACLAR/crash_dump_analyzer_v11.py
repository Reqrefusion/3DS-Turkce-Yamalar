#!/usr/bin/env python3
from struct import unpack_from
import sys
p=sys.argv[1]
data=open(p,'rb').read()
if unpack_from('<2I',data)!=(0xdeadc0de,0xdeadcafe): raise SystemExit('Luma dump değil')
version,processor,etype,_,nreg_b,code_sz,stack_sz,add_sz=unpack_from('<8I',data,8)
nreg=nreg_b//4
regs=unpack_from('<%dI'%nreg,data,40)
names=tuple(f'r{i}' for i in range(13))+('sp','lr','pc','cpsr','dfsr','ifsr','far','fpexc','fpinst','fpinst2')
print('version',hex(version),'processor',processor&0xffff,'core',processor>>16,'exception',etype)
for n,v in zip(names,regs): print(f'{n:6s} {v:08X}')
if etype==3:
 print('access','WRITE' if regs[17]&(1<<11) else 'READ','FAR',f'{regs[19]:08X}')
