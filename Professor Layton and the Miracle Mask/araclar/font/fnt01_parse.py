from pathlib import Path
import struct,sys
sys.path.insert(0, str(Path(__file__).parent))
from xfsa_extract import level5_dec

def parse(path):
 b=open(path,'rb').read(); assert b[:8].startswith(b'FNTC01')
 version=struct.unpack_from('<i',b,8)[0]
 lh,sh=struct.unpack_from('<hh',b,12); le,se=struct.unpack_from('<HH',b,16)
 cso,csc,lco,lcc,sco,scc=struct.unpack_from('<6h',b,0x1c)
 csraw=level5_dec(b,cso<<2)
 lcraw=level5_dec(b,lco<<2)
 scraw=level5_dec(b,sco<<2) if scc else b''
 sizes=[]
 for i in range(csc):
  ox,oy,w,h=struct.unpack_from('<bbBB',csraw,i*4); sizes.append((ox,oy,w,h))
 infos=[]
 for i in range(lcc):
  cp,sizeinfo,imginfo=struct.unpack_from('<HHI',lcraw,i*8)
  si=sizeinfo&0x3ff; adv=sizeinfo>>10; idx=imginfo&0xf; x=(imginfo>>4)&0x3fff; y=imginfo>>18
  infos.append({'cp':cp,'si':si,'adv':adv,'idx':idx,'x':x,'y':y,'size':sizes[si],'raw':lcraw[i*8:(i+1)*8]})
 return {'blob':b,'version':version,'lh':lh,'sh':sh,'le':le,'se':se,'sizes':sizes,'infos':infos,'cso':cso,'lco':lco,'sco':sco,'scraw':scraw}
if __name__=='__main__':
 for p in sys.argv[1:]:
  f=parse(p); print(p,'height',f['lh'],'sizes',len(f['sizes']),'infos',len(f['infos']))
  by={x['cp']:x for x in f['infos']}
  for c in 'AGISagisÇçÖöÜüĞğİıŞş':
   if ord(c) in by: print(c,by[ord(c)])
