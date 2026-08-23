import sys,struct
sys.path.insert(0,'/mnt/data')
from decode_xi import parse_xi
from fnt01_parse import parse

def mask_for(v,cp):
 im,lin,meta=parse_xi(f'/mnt/data/font_scan/{v}/000.xi'); W=meta[3]
 f=parse(f'/mnt/data/font_scan/{v}/FNT.bin'); d={x['cp']:x for x in f['infos']}[cp]
 _,_,w,h=d['size']; sh=[11,6,1][d['idx']]
 m=[]
 for y in range(d['y'],d['y']+h):
  row=[]
  for x in range(d['x'],d['x']+w):
   vv=struct.unpack_from('<H',lin,(y*W+x)*2)[0]; row.append((vv>>sh)&31)
  m.append(row)
 return d,m

def pr(v,chars):
 print('\n###',v)
 for c in chars:
  try:d,m=mask_for(v,ord(c))
  except KeyError:continue
  print(c, d['size'],'adv',d['adv'],'xy',d['x'],d['y'],'ch',d['idx'])
  for row in m:
   print(''.join(' ' if a==0 else '.' if a<8 else '+' if a<16 else '*' if a<24 else '#' for a in row))

pr('eu_nrm','GgIiSsCÇcçÖöÏïÌÍÎÜü')
pr('eu_sml','GgIiSsCÇcçÖöÏïÌÍÎÜü')
