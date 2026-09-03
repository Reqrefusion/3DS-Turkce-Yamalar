from collections import defaultdict, deque

def decompress(data):
 import struct
 if data[0]!=0x11:return data
 size=data[1]|data[2]<<8|data[3]<<16; pos=4
 if size==0:size=int.from_bytes(data[pos:pos+4],'little');pos+=4
 out=bytearray()
 while len(out)<size:
  flags=data[pos];pos+=1
  for bit in range(8):
   if len(out)>=size:break
   if not flags&(0x80>>bit):out.append(data[pos]);pos+=1
   else:
    b1=data[pos];pos+=1; hi=b1>>4
    if hi==0:
     b2,b3=data[pos],data[pos+1];pos+=2; length=((b1&15)<<4|(b2>>4))+0x11; disp=((b2&15)<<8|b3)+1
    elif hi==1:
     b2,b3,b4=data[pos],data[pos+1],data[pos+2];pos+=3; length=((b1&15)<<12|b2<<4|(b3>>4))+0x111; disp=((b3&15)<<8|b4)+1
    else:
     b2=data[pos];pos+=1;length=hi+1;disp=((b1&15)<<8|b2)+1
    for _ in range(length):out.append(out[-disp])
 return bytes(out[:size])

def compress(data, max_candidates=32):
 n=len(data)
 hdr=bytearray([0x11, n&0xff,(n>>8)&0xff,(n>>16)&0xff]) if n<0x1000000 else bytearray([0x11,0,0,0])+n.to_bytes(4,'little')
 out=bytearray(hdr)
 buckets=defaultdict(deque)
 def keyat(i):
  return (data[i]<<16)|(data[i+1]<<8)|data[i+2]
 def add(i):
  if i+2>=n:return
  k=keyat(i);q=buckets[k];q.append(i)
  while q and i-q[0]>0x1000:q.popleft()
 def best(pos):
  if pos+2>=n:return (0,0)
  k=keyat(pos);q=buckets.get(k)
  if not q:return (0,0)
  bestlen=0;bestdisp=0; maxlen=min(0x10110,n-pos)
  # newest candidates usually best
  checked=0
  for prev in reversed(q):
   disp=pos-prev
   if disp<=0 or disp>0x1000:continue
   checked+=1
   # quick fourth byte check when useful
   l=3
   # overlapping references are allowed; source bytes beyond pos repeat with period disp.
   while l<maxlen and data[pos+l]==data[prev+(l%disp)]:
    l+=1
   if l>bestlen:
    bestlen,bestdisp=l,disp
    if l>=maxlen:break
   if checked>=max_candidates:break
  return (bestlen,bestdisp) if bestlen>=3 else (0,0)
 pos=0
 while pos<n:
  flagpos=len(out);out.append(0);flags=0; group=[]
  for bit in range(8):
   if pos>=n:break
   l,d=best(pos)
   # small lazy match: if next is much better, emit literal now
   if l>=3 and pos+1<n:
    add(pos) # temporarily make current available so next matching normal stream state includes literal if chosen
    l2,d2=best(pos+1)
    # undo impossible cheaply: current stays in bucket even if match chosen, but dictionary should include it anyway after consumption
    if l2>l+1:
     l=0
    # We already added pos; mark so not add twice below
    already=True
   else: already=False
   if l>=3:
    flags|=(0x80>>bit); x=d-1
    if l<=0x10:
     out.extend(bytes([((l-1)<<4)|((x>>8)&0xf),x&0xff]))
    elif l<=0x110:
     y=l-0x11;out.extend(bytes([(y>>4)&0xf,((y&0xf)<<4)|((x>>8)&0xf),x&0xff]))
    else:
     y=l-0x111;out.extend(bytes([0x10|((y>>12)&0xf),(y>>4)&0xff,((y&0xf)<<4)|((x>>8)&0xf),x&0xff]))
    # add all consumed positions
    start=pos
    if not already:add(pos)
    for j in range(1,l):add(pos+j)
    pos+=l
   else:
    out.append(data[pos])
    if not already:add(pos)
    pos+=1
  out[flagpos]=flags
 return bytes(out)

if __name__=='__main__':
 import sys,time
 d=open(sys.argv[1],'rb').read();
 if d[:1]==b'\x11': d=decompress(d)
 t=time.time();c=compress(d);print(len(d),len(c),time.time()-t);assert decompress(c)==d
 open(sys.argv[2],'wb').write(c)
