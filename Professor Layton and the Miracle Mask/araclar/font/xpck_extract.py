import struct,os,sys
sys.path.insert(0,'/mnt/data')
from xfsa_extract import level5_dec

def parse(path,outroot):
 b=open(path,'rb').read()
 magic=b[:4]; assert magic==b'XPCK'
 fc1,fc2=b[4],b[5]
 tmp1,tmp2,tmp3,tmp4,tmp5=struct.unpack_from('<5H',b,6)
 tmp6=struct.unpack_from('<I',b,16)[0]
 fc=((fc2&0xf)<<8)|fc1
 fio=tmp1<<2; nto=tmp2<<2; datao=tmp3<<2; fis=tmp4<<2; nts=tmp5<<2
 print('header',fc,hex(fio),hex(nto),hex(datao),fis,nts,tmp6<<2)
 names=level5_dec(b,nto)
 os.makedirs(outroot,exist_ok=True)
 out=[]
 for i in range(fc):
  off=fio+i*12
  crc,nameoff,tmp,tmp2z,tmpZ,tmp2Z=struct.unpack_from('<IHHHBB',b,off)
  fileoff=(((tmpZ<<16)|tmp)<<2)
  size=(tmp2Z<<16)|tmp2z
  end=names.find(b'\0',nameoff); name=names[nameoff:end].decode('ascii','replace')
  d=os.path.join(outroot,name);open(d,'wb').write(b[datao+fileoff:datao+fileoff+size])
  out.append((name,datao+fileoff,size,off))
  print(i,name,hex(datao+fileoff),size)
 return out
if __name__=='__main__':
 for p in sys.argv[1:]:
  parse(p,'/mnt/data/xpck_out/'+os.path.basename(p))
