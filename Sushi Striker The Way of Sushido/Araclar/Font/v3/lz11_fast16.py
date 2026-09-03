from collections import deque

def compress(data):
    n=len(data)
    if n<0x1000000: out=bytearray([0x11,n&255,(n>>8)&255,(n>>16)&255])
    else: out=bytearray([0x11,0,0,0])+n.to_bytes(4,'little')
    hist={}
    def add(i):
        if i+2>=n:return
        k=data[i:i+3]; q=hist.get(k)
        if q is None: q=deque(maxlen=8); hist[k]=q
        q.append(i)
    pos=0
    while pos<n:
        fp=len(out);out.append(0);flags=0
        for bit in range(8):
            if pos>=n:break
            bestl=bestd=0
            if pos+2<n:
                q=hist.get(data[pos:pos+3])
                if q:
                    maxl=min(16,n-pos)
                    for prev in reversed(q):
                        d=pos-prev
                        if not 0<d<=4096: continue
                        l=3
                        while l<maxl and data[pos+l]==data[prev+(l%d)]:l+=1
                        if l>bestl:bestl,bestd=l,d
                        if l==maxl:break
            if bestl>=3:
                flags|=0x80>>bit; x=bestd-1
                out.extend(bytes([((bestl-1)<<4)|((x>>8)&15),x&255]))
                for j in range(bestl):add(pos+j)
                pos+=bestl
            else:
                out.append(data[pos]);add(pos);pos+=1
        out[fp]=flags
    return bytes(out)
