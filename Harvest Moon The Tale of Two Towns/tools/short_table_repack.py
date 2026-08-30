import struct
import hm3ds_text as hm
DEL=0x270E; END=0x270F

def _enc(t,cmap):
    return b''.join(hm.p16(w) for w in hm.encode_text(t,'slots',cmap))

def _decode_ascii_content(b):
    return hm.decode_words([struct.unpack_from('<H',b,i)[0] for i in range(0,len(b),2)])

def repack_table(data:bytes,base:int,replacements:dict[str,str],cmap,label=''):
    out=bytearray(data); space=hm.p16(0x0800)
    o0=struct.unpack_from('<I',data,base)[0]
    if not (o0%4==0 and 4<=o0<=0x10000): raise RuntimeError((label,'bad table',hex(base),o0))
    n=o0//4
    offs=[struct.unpack_from('<I',data,base+4*i)[0] for i in range(n)]
    if offs[0]!=o0 or any(offs[i]>=offs[i+1] for i in range(n-1)): raise RuntimeError((label,'bad offsets'))
    starts=[base+v for v in offs]
    end=None
    for x in range(starts[-1],min(len(data)-1,starts[-1]+0x10000),2):
        if struct.unpack_from('<H',data,x)[0]==END: end=x; break
    if end is None or struct.unpack_from('<H',data,end-2)[0]!=DEL: raise RuntimeError((label,'end marker'))
    contents=[];names=[]
    for i,s in enumerate(starts):
        delim=(starts[i+1]-2) if i+1<n else end-2
        if struct.unpack_from('<H',data,delim)[0]!=DEL: raise RuntimeError((label,'delimiter',i))
        c=data[s:delim]; contents.append(bytearray(c)); names.append(_decode_ascii_content(c).rstrip(' '))
    replaced=set();report={}
    for old,new in replacements.items():
        idxs=[i for i,t in enumerate(names) if t==old]
        if not idxs: raise RuntimeError(f'{label}: {old!r} bulunamadı')
        for i in idxs: contents[i]=bytearray(_enc(new,cmap));replaced.add(i)
        report[old]={'new':new,'indices':idxs}
    original_total=sum((starts[i+1]-2 if i+1<n else end-2)-starts[i] for i in range(n))
    diff=sum(len(c) for c in contents)-original_total
    if diff>0:
        need=diff//2
        donors=sorted([i for i in range(n) if i not in replaced],key=lambda i:len(contents[i]),reverse=True)
        for i in donors:
            while need and len(contents[i])>=2 and bytes(contents[i][-2:])==space:
                del contents[i][-2:];need-=1
            if not need:break
        if need: raise RuntimeError((label,'padding yetersiz',need))
    elif diff<0:
        contents[-1].extend(space*((-diff)//2))
    if sum(len(c) for c in contents)!=original_total: raise RuntimeError((label,'size mismatch'))
    cur=o0
    for i,c in enumerate(contents):
        struct.pack_into('<I',out,base+4*i,cur);s=base+cur;out[s:s+len(c)]=c;cur+=len(c);out[base+cur:base+cur+2]=hm.p16(DEL);cur+=2
    if base+cur!=end: raise RuntimeError((label,'block size moved'))
    out[end:end+2]=hm.p16(END)
    return bytes(out),{'label':label,'base':hex(base),'end':hex(end),'replacements':report}

MES_SPECS = [
    (0xCF38, {'Cow':'İnek','Dog':'Köpek','Cat':'Kedi'}, 'Takvim hayvan etiketleri'),
    (0xEE9C, {'Yes':'Evet','No':'Hayır'}, 'StreetPass Evet/Hayır'),
    (0x293B4, {'Cow':'İnek','Dog':'Köpek','Cat':'Kedi'}, 'Festival hayvan etiketleri'),
    (0x453C8, {'Yes':'Evet','No':'Hayır','OK':'Tamam'}, 'Çok oyunculu onaylar'),
    (0x78F70, {'Yes':'Evet','No':'Hayır'}, 'Kayıt/yükleme onayları'),
    (0x7FD04, {'Cow':'İnek','Dog':'Köpek','Cat':'Kedi','Owl':'Baykuş','Dad':'Baba','Mum':'Anne','Spr':'Bahar','Sum':'Yaz','Aut':'Güz','Win':'Kış','Kira Bed.':'Kiralık Yatak'}, 'Takvim/veritabanı kısa etiketleri'),
    (0x2AEC8, {'Oil':'Yağ','Egg':'Yumurta','Eel':'Yılan Balığı','Pot':'Tencere','Hoe':'Çapa','Axe':'Balta'}, 'Kısa eşya adları'),
    (0x5D664, {'Süper Hoe':'Süper Çapa','Top Hoe':'Usta Çapa','Top Orak':'Usta Orak'}, 'Alet geliştirme etiketleri'),
    (0x654D4, {'Bed':'Yatak'}, 'Yatak etiketi'),
]
EVENT_SPEC = (0x7F2C, {'Cow':'İnek','Cat':'Kedi','Dog':'Köpek'}, 'Event festival hayvan etiketleri')

def apply_all(mes:bytes,event:bytes,cmap):
    reports=[]
    for b,r,l in MES_SPECS:
        mes,rep=repack_table(mes,b,r,cmap,l);reports.append(rep)
    b,r,l=EVENT_SPEC
    event,rep=repack_table(event,b,r,cmap,l);reports.append(rep)
    return mes,event,reports
