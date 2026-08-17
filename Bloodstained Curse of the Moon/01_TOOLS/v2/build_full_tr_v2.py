from __future__ import annotations
from pathlib import Path
import sys, struct, math, re, csv, shutil, zipfile, hashlib, textwrap
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont

KIT=Path('/mnt/data/bloodstained_tr_kit')
sys.path.insert(0,str(KIT))
from bloodstained_tr_tool import (unpack_container,pack_container,parse_osb,decode_osb_rgba4444,encode_osb_rgba4444,OSB_KEY,load_ttb,write_ttb,TTB_KEY,TtbTable)

ROM=Path('/mnt/data/bloodstain_work/romfs')
OUT=Path('/mnt/data/bloodstained_tr_full_v2')
TITLEID='00040000001D3C00'
OUTROM=OUT/'luma'/'titles'/TITLEID/'romfs'
PREV=OUT/'previews'
OUTROM.mkdir(parents=True,exist_ok=True); PREV.mkdir(parents=True,exist_ok=True)
FONT_PATH='/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'
FONT8=ImageFont.truetype(FONT_PATH,8)

# ---------------- OSB low-level ----------------
def rec(raw,h,i):
    return list(struct.unpack_from('<6I',raw,h[7]+4+i*24))

def vertex_abs(h,i,r):
    return h[7]+r[2]+((4+24*i)%80)

def node_quad_offsets(raw,h,i):
    r=rec(raw,h,i); a=vertex_abs(h,i,r)
    return [a+j*4*20 for j in range(r[4]//4)]

def quad_values(raw,qoff):
    return [struct.unpack_from('<5f',raw,qoff+k*20) for k in range(4)]

def quad_rect(raw,qoff):
    vs=quad_values(raw,qoff)
    xs=[v[0] for v in vs]; ys=[v[1] for v in vs]; us=[v[3] for v in vs]; vv=[v[4] for v in vs]
    return (min(xs),max(xs),min(ys),max(ys),min(us),max(us),min(vv),max(vv))

def is_glyph_quad(raw,qoff,tol=.15):
    q=quad_rect(raw,qoff)
    return abs((q[1]-q[0])-8)<tol and abs((q[3]-q[2])-8)<tol

def clone_overlaps(raw: bytes):
    """Detach later vertex buffers when node buffers overlap, without changing geometry."""
    raw=bytearray(raw); h=parse_osb(raw); n=h[9]; post=h[7]
    rs=[rec(raw,h,i) for i in range(n)]
    intervals=[]
    for i,r in enumerate(rs):
        a=vertex_abs(h,i,r); intervals.append((a,a+r[4]*20))
    clone=set()
    for i in range(1,n):
        a,b=intervals[i]
        for j in range(i):
            c,d=intervals[j]
            if max(a,c)<min(b,d):
                clone.add(i); break
    appended=bytearray()
    for i in sorted(clone):
        r=rs[i]; olda,oldb=intervals[i]; vb=bytes(raw[olda:oldb])
        shift=(4+24*i)%80
        current_rel=len(raw)+len(appended)-post
        rel0=(current_rel+15)//16*16
        appended += b'\0'*(rel0-current_rel)
        new_field2=rel0
        appended += b'\0'*shift
        assert post+new_field2+shift == len(raw)+len(appended)
        appended += vb
        struct.pack_into('<I',raw,post+4+i*24+8,new_field2)
    raw += appended
    struct.pack_into('<I',raw,24,len(raw)-post)
    # validation: every active vertex interval must be disjoint
    h2=parse_osb(raw); ranges=[]
    for i in range(h2[9]):
        r=rec(raw,h2,i); a=vertex_abs(h2,i,r); b=a+r[4]*20
        for c,d in ranges:
            if max(a,c)<min(b,d):
                raise AssertionError('vertex overlap remained after cloning')
        ranges.append((a,b))
    return raw, clone

def cell_range_for_uv(q,w,h):
    x0=int(round(q[4]*w)); x1=int(round(q[5]*w)); y0=int(round(q[6]*h)); y1=int(round(q[7]*h))
    out=set()
    for cy in range(max(0,y0//8),min(h//8,(y1+7)//8)):
        for cx in range(max(0,x0//8),min(w//8,(x1+7)//8)):
            out.add((cx,cy))
    return out

def allocate_glyph_cells(raw,h,patched_nodes,chars):
    """Use cells not needed by untouched nodes/non-text sprites; overwrite old text atlas cells safely."""
    w,hh=h[3],h[4]
    patched=set(patched_nodes); protected=set()
    for i in range(h[9]):
        for qoff in node_quad_offsets(raw,h,i):
            q=quad_rect(raw,qoff)
            if i not in patched or not is_glyph_quad(raw,qoff):
                protected |= cell_range_for_uv(q,w,hh)
    available=[(cx,cy) for cy in range(hh//8) for cx in range(w//8) if (cx,cy) not in protected]
    uniq=[]
    for ch in chars:
        if ch not in uniq and not ch.isspace(): uniq.append(ch)
    # blank is additional cell
    if len(available)<len(uniq)+1:
        raise RuntimeError(f'Not enough atlas cells: need {len(uniq)+1}, free {len(available)}')
    mapping={ch:available[k] for k,ch in enumerate(uniq)}
    blank=available[len(uniq)]
    return mapping,blank,protected

def draw_glyph_tile(atlas: Image.Image, cell, ch, fill=(255,255,255,255)):
    x,y=cell[0]*8,cell[1]*8
    atlas.paste((0,0,0,0),(x,y,x+8,y+8))
    if ch:
        tile=Image.new('RGBA',(8,8),(0,0,0,0)); d=ImageDraw.Draw(tile)
        bbox=d.textbbox((0,0),ch,font=FONT8)
        tw,th=bbox[2]-bbox[0],bbox[3]-bbox[1]
        # center; bias upward one pixel if diacritics would otherwise fall out
        tx=(8-tw)//2-bbox[0]
        ty=(8-th)//2-bbox[1]
        d.text((tx,ty),ch,font=FONT8,fill=fill)
        atlas.alpha_composite(tile,(x,y))

def set_quad(raw: bytearray,qoff,x0,x1,y0,y1,u0,u1,v0,v1):
    old=quad_values(raw,qoff)
    xs=[v[0] for v in old]; ys=[v[1] for v in old]; us=[v[3] for v in old]; vv=[v[4] for v in old]
    xmin,xmax=min(xs),max(xs); ymin,ymax=min(ys),max(ys); umin,umax=min(us),max(us); vmin,vmax=min(vv),max(vv)
    for k,(x,y,z,u,v) in enumerate(old):
        nx=x0 if abs(x-xmin)<=abs(x-xmax) else x1
        ny=y0 if abs(y-ymin)<=abs(y-ymax) else y1
        nu=u0 if abs(u-umin)<=abs(u-umax) else u1
        nv=v0 if abs(v-vmin)<=abs(v-vmax) else v1
        struct.pack_into('<5f',raw,qoff+k*20,nx,ny,z,nu,nv)

def uv_for_cell(cell,w,h):
    x,y=cell[0]*8,cell[1]*8
    # slight inset keeps bilinear edge bleed away while preserving almost all pixel area
    return ((x+0.02)/w,(x+7.98)/w,(y+0.02)/h,(y+7.98)/h)

def wrap_text(text,max_cols,max_lines=None):
    # Respect explicit newlines; wrap each paragraph to available character columns.
    lines=[]
    for para in text.split('\n'):
        if para=='':
            lines.append(''); continue
        lines += textwrap.wrap(para,width=max_cols,break_long_words=False,break_on_hyphens=False,replace_whitespace=False,drop_whitespace=True) or ['']
    if max_lines is not None and len(lines)>max_lines:
        # retry compactly by growing logical width slightly; geometry can extend a little beyond original bbox
        width=max_cols
        while len(lines)>max_lines and width<max_cols+14:
            width+=1; lines=[]
            for para in text.split('\n'):
                lines += textwrap.wrap(para,width=width,break_long_words=False,break_on_hyphens=False,replace_whitespace=False,drop_whitespace=True) or ['']
        if len(lines)>max_lines:
            raise ValueError(f'Text needs {len(lines)} lines but node has {max_lines}: {text}')
    return lines

def layout_for_node(raw,h,i,text,align='left',manual_lines=False):
    glyphs=[q for q in node_quad_offsets(raw,h,i) if is_glyph_quad(raw,q)]
    if not glyphs: return [],glyphs
    rects=[quad_rect(raw,q) for q in glyphs]
    minx=min(q[0] for q in rects); maxx=max(q[1] for q in rects)
    # source row top positions (higher y = visually higher)
    rowtops=sorted({round(q[3],3) for q in rects},reverse=True)
    max_cols=max(1,int(round((maxx-minx)/8)))
    lines=text.split('\n') if manual_lines else wrap_text(text,max_cols,len(rowtops))
    if len(lines)>len(rowtops): raise ValueError(f'node {i}: too many lines')
    needed=sum(1 for ch in '\n'.join(lines) if not ch.isspace())
    if needed>len(glyphs):
        raise ValueError(f'node {i}: {needed} chars > {len(glyphs)} glyphs: {text}')
    positions=[]
    # use original row spacing. For action labels with explicit fewer lines, keep at top rows.
    for li,line in enumerate(lines):
        y1=rowtops[li]; y0=y1-8
        width=len(line)*8
        if align=='center': start=(minx+maxx-width)/2
        elif align=='right': start=maxx-width
        else: start=minx
        x=start
        for ch in line:
            if not ch.isspace(): positions.append((ch,x,x+8,y0,y1))
            x+=8
    return positions,glyphs

def patch_osb_text_file(filename,node_texts,align='left',align_overrides=None,manual_nodes=None,out_name=None,colors=None):
    src=ROM/filename; raw0=unpack_container(src,OSB_KEY); raw,cloned=clone_overlaps(raw0); h=parse_osb(raw)
    nodes=sorted(node_texts)
    chars=''.join(node_texts.values())
    cmap,blank,protected=allocate_glyph_cells(raw,h,nodes,chars)
    atlas=decode_osb_rgba4444(raw)
    for ch,cell in cmap.items(): draw_glyph_tile(atlas,cell,ch)
    draw_glyph_tile(atlas,blank,'')
    w,hh=atlas.size
    for i,text in node_texts.items():
        al=(align_overrides or {}).get(i,align)
        pos,glyphs=layout_for_node(raw,h,i,text,al,i in (manual_nodes or set()))
        for k,qoff in enumerate(glyphs):
            if k<len(pos):
                ch,x0,x1,y0,y1=pos[k]; cell=cmap[ch]; u0,u1,v0,v1=uv_for_cell(cell,w,hh)
                set_quad(raw,qoff,x0,x1,y0,y1,u0,u1,v0,v1)
            else:
                q=quad_rect(raw,qoff); u0,u1,v0,v1=uv_for_cell(blank,w,hh)
                set_quad(raw,qoff,q[0],q[1],q[2],q[3],u0,u1,v0,v1)
    enc=encode_osb_rgba4444(atlas); data_size=h[1]; data_off=h[5]
    assert len(enc)==data_size; raw[data_off:data_off+data_size]=enc
    out=OUTROM/(out_name or filename); out.write_bytes(pack_container(bytes(raw),OSB_KEY))
    # structural verification after pack/decrypt
    vr=unpack_container(out,OSB_KEY); parse_osb(vr); decode_osb_rgba4444(vr)
    return out,len(cloned),len(cmap)

# Demo typewriter patch: use a final-node layout and reveal Turkish chars progressively.
def patch_demo(filename,groups,out_name=None):
    src=ROM/filename; raw0=unpack_container(src,OSB_KEY); raw,cloned=clone_overlaps(raw0); h=parse_osb(raw)
    all_nodes=[]; chars=''
    for start,end,text in groups:
        all_nodes += list(range(start,end+1)); chars+=text
    cmap,blank,protected=allocate_glyph_cells(raw,h,all_nodes,chars)
    atlas=decode_osb_rgba4444(raw); w,hh=atlas.size
    for ch,cell in cmap.items(): draw_glyph_tile(atlas,cell,ch)
    draw_glyph_tile(atlas,blank,'')
    for start,end,text in groups:
        finalpos,finalglyphs=layout_for_node(raw,h,end,text,'left',False)
        # node quads grow by one glyph at a time; map the prefix into translated layout.
        for i in range(start,end+1):
            glyphs=[q for q in node_quad_offsets(raw,h,i) if is_glyph_quad(raw,q)]
            reveal=min(len(glyphs),len(finalpos))
            for k,qoff in enumerate(glyphs):
                if k<reveal:
                    ch,x0,x1,y0,y1=finalpos[k]; u0,u1,v0,v1=uv_for_cell(cmap[ch],w,hh)
                    set_quad(raw,qoff,x0,x1,y0,y1,u0,u1,v0,v1)
                else:
                    q=quad_rect(raw,qoff); u0,u1,v0,v1=uv_for_cell(blank,w,hh)
                    set_quad(raw,qoff,q[0],q[1],q[2],q[3],u0,u1,v0,v1)
    enc=encode_osb_rgba4444(atlas); raw[h[5]:h[5]+h[1]]=enc
    out=OUTROM/(out_name or filename); out.write_bytes(pack_container(bytes(raw),OSB_KEY))
    vr=unpack_container(out,OSB_KEY); parse_osb(vr); decode_osb_rgba4444(vr)
    return out,len(cloned),len(cmap)

# ---------------- Turkish story text ----------------
opening={
0:"""Bir zamanlar iblislerin Ay Laneti'ne uğrattığı bir adam vardı.\nAdı Zangetsu'ydu.\nKızıl giysileri ve ateş gibi gözleriyle, kendisini lanetleyen iblislerin peşini acımasızca sürüyordu. Bir karanlıktan diğerine ilerlerken yoluna çıkan son iblisi de yok edene kadar durmayacaktı...\nBir gece büyük bir iblisin yaklaşan varlığını hissetti.\nTehditleri ne kadar büyük olursa olsun bütün iblisleri ortadan kaldırmaya yemin etti.\nAy ışığı altında haykırarak, uğursuz çeliğinde karanlığı yutan kılıcını çekti.\nO gece ya iblisler ya da Ay, onun kılıcının gazabını tadacaktı.""",
1:"""Yolun sonunda Zangetsu, karanlığa yenilmek pahasına dostlarını korudu. Onu durdurmak için dostları yeniden yola çıktı. Yoldaşlarının canını almak zorunda kalabilirler; peki ruhunu kurtarabilecekler mi...?"""
}

miriam=[
"Beni kurtardığın için sağ ol. O yaratığı iblis gücüyle mi mühürledin?",
"Sen... Bir Parçabağlayıcısın. O güç iblisleri çağırabilir! Buna izin veremem!",
"Bekle! Evet, bir Parçabağlayıcıyım. Ama bu gücü yalnızca doğru yolda kullanmaya yemin ettim. Kötülüğe alet olmayacağım!",
"Öyleyse kararlılığını savaşta kanıtla!",
"Miriam artık müttefik!",
]
alfred=[
"Bir iblise yenilmek... Ne büyük utanç. Ben Alfred, bir simyacıyım.",
"Simyacı... İblisleri dünyevi arzuların için kullanırsın!",
"Her başarı bir bedel ister. Bazen iblislerden yararlanmak gerekir. Senin de bir amacın var, değil mi? Gücüm sana da yarayabilir.",
"Varlığın beni huzursuz ediyor ama yeteneğin işe yarar. Şimdilik başın omuzlarında kalsın.",
"Alfred artık müttefik!",
]
gebel=[
"Lanetli Parçabağlayıcı. Sayısız iblisin gücü sende...",
"İyi gözlem. İntikamım için iblislerin gücüne ihtiyacım var. Şimdilik amaçlarımız aynı. Birlikte çalışmak ikimiz için de yararlı olur.",
"... Öyle olsun. Şimdilik yaşamana izin vereceğim.",
"Gebel artık müttefik!",
]

tutorial={
0:"Alt silahları Y tuşuyla kullanabiliyorum gibi.",
1:"Ama bunun için SİLAH puanı gerekiyor...",
2:"Lambaları kırarsam SİLAH puanını yenileyen bir iksir bulabilirim.",
3:"Renkli lambalar farklı alt silah verir. Yine de kılıcımdan vazgeçmem...",
4:"Yeni dostlarla L/R tuşlarıyla yer değiştirebilirim.",
5:"Yol ayrımında kısa yolu seçerim. Bulamazsam düşen maceracıların izlerini izlerim.",
6:"Her dostun ayrı dayanıklılığı var. Canı azalırsa hemen karakter değiştiririm.",
7:"Her alt silah yalnız bir kişiye aittir. Diğerleri onu alamaz...",
8:"Kimseye güvenmemeye yemin ettim ve yalnız savaştım. Ama sınırıma ulaştım.",
9:"Herkesin güçlü ve zayıf yanları var. Yalnız ilerlemek aptallık. Keşke güvenebileceğim bir dost olsa...",
10:"Güvenebileceğim biriyle karşılaşsam 'Birlikte savaşalım!' derdim. Hiçbir yetenek güvenilir bir dosttan üstün değildir!",
11:"Zamanın akışına karşı sürüklenmeye lanetlenmiş bir adam duydum. Böyle bir lanet varsa geçmişe dönüp yeniden başlayabilirim.",
12:"İçinde yeni bir Ruh Sanatı uyandı.",
13:"Hilal Kesisi\nHavada saldır",
14:"Kanlı Ay\nHavada saldır",
15:"Yeni Ay\nYöne iki kez bas",
16:"Kırbaç Darbesi",
17:"Yüksek Sıçra",
18:"Kayma\n↓+Zıpla",
19:"Yıkım Asası",
20:"Simya Kullan\n(SİLAH puanı harcar)",
21:"Karanlık Çağır",
22:"Ölümsüz Dönüşüm\n(SİLAH puanı harcar)",
23:"Kan Em\nDönüşümde\n(SİLAH puanı harcar)",
24:"Hızlı Yüksel\nDönüşümde\n(SİLAH puanı harcar)",
25:"Dönüşümü Bitir\nDönüşümde",
}

stages={
0:"BÖLÜM 1\nAy Işığı Ayartısı",
1:"BÖLÜM 2\nBuz Zindanı",
2:"BÖLÜM 3\nGörkemli Boşluk",
3:"BÖLÜM 4\nGöğe Küfür",
4:"BÖLÜM 4\nGeceyi Yar",
5:"BÖLÜM 5\nKıyım Trajedisi",
6:"BÖLÜM 6\nTabu Kirleticisi",
7:"BÖLÜM 7\nAyı Yar",
8:"BÖLÜM 8\nAya Lanet",
9:"BÖLÜM 8\nDüşen Ay Ağıdı",
}

common_open="İblis sürüleri yok edilmiş ve büyük kötülük yenilmişti. Mücadeleleri sayesinde ülkeye barış dönecekti. Kahramanlar gün ışığında gururla durdu. Yakında her biri kendi yoluna gidecekti."
ally_m="Savaş bitince Miriam, yaşamak için yeni bir neden aramak üzere ülkede dolaşmaya başladı."
ally_a="Simyada yeni olasılıklar gören Alfred, bu sanatı canlandırmak ve yeni gerçekler aramak için yola çıktı."
ally_g="İblis tehdidi sona erince, içi iblis gücüyle dolan Gebel yeniden boşlukta kayboldu."
common_close="Zangetsu başiblisi öldürmüştü ama içindeki sızı dinmedi. Savaşta huzursuzluk hissetmişti. Yendiği Gremory ona yalnızca bir gölge gibi gelmişti. Zangetsu'nun kızıl kılıcının ay ışığında yeniden parlayacağı başka bir kader gecesi kaçınılmazdı. SON"
ending={
1:"İblis sürüleri yok edilmiş, birçok bedel ödenmiş ve sonunda büyük kötülük yenilmişti. Ama savaş sırasında Zangetsu bir şeyi fark etti. Bu dünya ve içindeki her şey iblis Gremory tarafından yaratılmış, Ayın Laneti aracılığıyla yalnız ona gösterilmişti. Kale çökerken, dünya parçalanırken Zangetsu düşündü. Kendi tereddüdü yüzünden ne simyacıyı ne de Parçabağlayıcıları öldürebilmiş, onlarla birlik de kuramamıştı. Onlar canlarını tehlikeye atıp onu kurtardığında Zangetsu kendi zayıflığını gördü. O anda içinde bir şey değişmeye başladı. Yaklaşan savaşın sezgisiyle bir kez daha yayılan karanlığa daldı. SON",
2:"İblisleri yok edecek güçten başka hiçbir şey istemeyen adam, son günlerini sefilce geçirdi. Kalbi karanlığa teslim olan ona acıyacak ya da yas tutacak kimse kalmamıştı. Zangetsu artık yeni karanlık imparatordu. Ülkenin üzerine uzun ve korkunç bir gece çöktü. KÖTÜ SON",
3:common_open+' '+ally_m+' '+common_close,
4:common_open+' '+ally_a+' '+common_close,
5:common_open+' '+ally_g+' '+common_close,
6:common_open+' '+ally_m+' '+ally_a+' '+common_close,
7:common_open+' '+ally_m+' '+ally_g+' '+common_close,
8:common_open+' '+ally_a+' '+ally_g+' '+common_close,
9:"İblis sürüleri yok edilmiş ve büyük kötülük yenilmişti. Onun mücadelesi sayesinde ülkeye barış dönecekti. Parlak gün ışığında bile soluk bir gölge kalmıştı. Zangetsu başiblisi öldürmüştü ama içindeki sızı dinmedi. Savaşta bir huzursuzluk hissetmişti. Yendiği Gremory ona yalnızca bir gölge gibi gelmişti. Zangetsu'nun kızıl kılıcının ay ışığında yeniden parlayacağı başka bir kader gecesi kaçınılmazdı. SON",
10:"Zangetsu yaptıklarına şaşırmıştı. Bunu neden yapmıştı? İblisleri öldürmek ve intikam almak için yaşıyordu; ama unuttuğu duygular yeniden canlanmıştı. Artık bunun için çok geçti. Bilinci karanlıkta boğulurken Zangetsu yalnızca dostlarının güvende olması için dua edebildi...",
11:"Yeni karanlık imparatoru durdurmak için Zangetsu'nun dostları savaşa girdi. Onu öldürmek zorunda kalabilirlerdi; ama ruhunu kurtarabilecekler miydi...? DEVAM EDECEK",
12:"Böylece yeni karanlık çağ sona erdi. Ama dostlarını kurtaramamış olmak yüreklerine ağır geliyordu. Sonunda yalnızca onun ruhunu kurtaracak güçleri kalmıştı. Bu ülke ve onun ruhu gerçek huzura kavuşsun.",
13:"Zangetsu'nun ruhu geride kaldı ve öteki dünyaya uğurlandı.",
14:"SON\n?",
15:"BİTTİ!!!",
}

# ---------------- Build story OSBs ----------------
def nonspace(s): return sum(1 for c in s if not c.isspace())

def cap_report(filename,node_texts):
    raw=unpack_container(ROM/filename,OSB_KEY);h=parse_osb(raw); out=[]
    for i,t in node_texts.items():
        cap=sum(is_glyph_quad(raw,q) for q in node_quad_offsets(raw,h,i)); out.append((i,nonspace(t),cap))
    return out

print('Capacity checks:')
for fn,d in [('Openingext00_en.osbctr',opening),('TutorialText00_en.osbctr',tutorial),('GraphicText02_en.osbctr',stages),('EndingText00_en.osbctr',ending)]:
    bad=[]
    for i,n,c in cap_report(fn,d):
        if n>c: bad.append((i,n,c))
    print(fn,'bad',bad)
    if bad: raise SystemExit('translation capacity exceeded')

built=[]
built.append(patch_osb_text_file('Openingext00_en.osbctr',opening,align='center'))
built.append(patch_demo('DemoText00_en.osbctr',[(0,62,miriam[0]),(63,140,miriam[1]),(141,256,miriam[2]),(257,302,miriam[3]),(303,324,miriam[4])]))
built.append(patch_demo('DemoText01_en.osbctr',[(0,82,alfred[0]),(83,134,alfred[1]),(135,263,alfred[2]),(264,358,alfred[3]),(359,380,alfred[4])]))
# Demo02 starts with a tiny punctuation/transition node 0; keep it blanked by first group from node1.
built.append(patch_demo('DemoText02_en.osbctr',[(1,52,gebel[0]),(53,182,gebel[1]),(183,226,gebel[2]),(227,247,gebel[3])]))
built.append(patch_osb_text_file('TutorialText00_en.osbctr',tutorial,align='left',align_overrides={i:'center' for i in range(13,26)},manual_nodes=set(range(13,26))))
built.append(patch_osb_text_file('GraphicText02_en.osbctr',stages,align='center',manual_nodes=set(stages)))
built.append(patch_osb_text_file('EndingText00_en.osbctr',ending,align='center',manual_nodes={14,15}))
print('Story OSBs built:',[(p.name,c,g) for p,c,g in built])

# ---------------- TTB v2 ----------------
# Start from the tested first-pass translations and add/fix visible English labels/credits.
first=KIT/'translations_firstpass_tr.csv'
patches=defaultdict(dict)
with first.open(encoding='utf-8-sig',newline='') as f:
    for row in csv.DictReader(f):
        if row['translation_tr']:
            patches[row['file']][int(row['index'])]=row['translation_tr']
# Remove leftover English mode/attack labels in Turkish strings.
replacements={
('Announce.ttb',2):'KÂBUS MODU açıldı!',
('Announce.ttb',3):'NİHAİ MOD açıldı!',
('Announce.ttb',5):'PATRON SERİSİ MODU açıldı!',
('GameOver.ttb',4):'<emoji/Decide> RAHAT stile geç ve oyuna dön.',
('GameOver.ttb',8):'RAHAT stile geçmek istiyor musunuz?\n\n*Stil, bir oyun dosyası yüklenirken\ndeğiştirilebilir.',
('Option.ttb',31):'↑＋SALDIRI ile alt silah kullanımını etkinleştirir',
('PauseMenu.ttb',15):"<emoji/Decide> Onayla <emoji/Cancel> / <emoji/Start> Oyuna dön   AYIN LANETİ'ni etkinleştir",
('Result.ttb',146):'NORMAL',('Result.ttb',154):'NORMAL',('Result.ttb',155):'NORMAL',('Result.ttb',158):'NORMAL',('Result.ttb',162):'NORMAL',
}
for (fn,i),v in replacements.items(): patches[fn][i]=v
# Staff roll role labels: names/titles of games/company remain proper nouns.
roles={
'Scenario Supervisor':'Senaryo Sorumlusu','English Localization Director':'İngilizce Yerelleştirme Direktörü','Sound Engineer':'Ses Mühendisi','Director':'Yönetmen','Music':'Müzik','Programmer':'Programcı','Background Graphics':'Arka Plan Grafikleri','Sound Director':'Ses Direktörü','UI Designer':'Arayüz Tasarımcısı','QC':'Kalite Kontrol','Lead Character Graphics':'Baş Karakter Grafikçisi','Planner':'Planlama','Special Thanks':'Özel Teşekkürler','Sound Effects':'Ses Efektleri','Sound Producer':'Ses Yapımcısı','All INTI staff':'Tüm INTI çalışanları','Producer':'Yapımcı','Lead Programmer':'Baş Programcı','Lead Background Graphics':'Baş Arka Plan Grafikçisi','Character Graphics':'Karakter Grafikleri','Lead UI Graphics':'Baş Arayüz Grafikçisi','PR':'Halkla İlişkiler','ALL RIGHTS RESERVED.':'TÜM HAKLARI SAKLIDIR.'}
st=load_ttb(ROM/'StaffRoll.ttb')
for i in range(len(st.records)):
    s=st.text_for_record(i)
    plain=re.sub(r'<color(?:/cyan)?>','',s)
    if plain in roles:
        tr=roles[plain]
        if s.startswith('<color/cyan>'):
            tr='<color/cyan>'+tr+('<color>' if s.endswith('<color>') else '')
        patches['StaffRoll.ttb'][i]=tr
# Build all modified TTBs.
for fn,entries in sorted(patches.items()):
    tab=load_ttb(ROM/fn)
    write_ttb(OUTROM/fn,tab,entries)
    # verify parse and exact translated rows
    rt=load_ttb(OUTROM/fn)
    for i,v in entries.items():
        assert rt.text_for_record(i)==v,(fn,i)
print('TTB files built',len(patches),'strings',sum(len(x) for x in patches.values()))

# Write machine-readable translation list for audit.
csvout=OUT/'ttb_translations_tr_v2.csv'
with csvout.open('w',encoding='utf-8-sig',newline='') as f:
    wr=csv.writer(f);wr.writerow(['file','index','original','translation_tr'])
    for fn in sorted(patches):
        tab=load_ttb(ROM/fn)
        for i in sorted(patches[fn]): wr.writerow([fn,i,tab.text_for_record(i),patches[fn][i]])

# ---------------- README / report ----------------
report=[]
report.append('Bloodstained: Curse of the Moon (Nintendo 3DS) - Türkçe Yama v2')
report.append('Sürüm: Avrupa / CTR-N-BLMP / TitleID 00040000001D3C00')
report.append('')
report.append('Bu sürümde Türkçeleştirilen ana içerik:')
report.append('- TTB menü/sistem/kayıt/seçenek/sonuç/metinleri ve kredi rol başlıkları')
report.append('- Açılış hikâye anlatımı ve Nightmare giriş anlatımı')
report.append('- Miriam / Alfred / Gebel karşılaşma konuşmaları (typewriter animasyonu dahil)')
report.append('- Tutorial/anlatım ekranları ve yetenek açıklamaları')
report.append('- Bölüm başlık kartları')
report.append('- Ending / Bad End / devam ekranlarındaki anlatım metinleri')
report.append('')
report.append('Kurulum: ZIP içindeki luma klasörünü SD kart köküne birleştirin.')
report.append('Hedef yol: SD:/luma/titles/00040000001D3C00/romfs/')
report.append('Luma3DS game patching / LayeredFS etkin olmalıdır.')
report.append('')
report.append('Doğrulama: tüm üretilen TTB/OSBCTR dosyaları yeniden açılıp ayrıştırıldı; OSB texture verileri decode edildi; paylaşılan vertex blokları ayrıştırıldı.')
report.append('Not: gerçek 3DS/emülatör çalışma zamanı bu ortamda test edilemedi. Görsel taşma, özel efekt veya nadir bir İngilizce grafik kalıntısı görürseniz ekran görüntüsünü gönderin; o kaynağı da düzeltmek gerekir.')
(OUT/'README_TR.txt').write_text('\n'.join(report),encoding='utf-8')

# SHA sums
lines=[]
for p in sorted(OUTROM.iterdir()):
    if p.is_file(): lines.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name)
(OUT/'SHA256SUMS.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('DONE',OUT)

# ---------------- Graphical UI text ----------------
def node_composite_geometry(raw,h,node_idx,quad_indices=None):
    qoffs=node_quad_offsets(raw,h,node_idx)
    if quad_indices is not None: qoffs=[qoffs[i] for i in quad_indices]
    rects=[quad_rect(raw,q) for q in qoffs]
    return qoffs,(min(r[0] for r in rects),max(r[1] for r in rects),min(r[2] for r in rects),max(r[3] for r in rects))

def paste_canvas_into_node_uvs(atlas,raw,h,node_idx,canvas,quad_indices=None):
    qoffs=node_quad_offsets(raw,h,node_idx)
    if quad_indices is None: inds=list(range(len(qoffs)))
    else: inds=list(quad_indices)
    sel=[qoffs[i] for i in inds]; rects=[quad_rect(raw,q) for q in sel]
    minx,maxx=min(r[0] for r in rects),max(r[1] for r in rects); miny,maxy=min(r[2] for r in rects),max(r[3] for r in rects)
    aw,ah=atlas.size
    for qi,qoff in zip(inds,sel):
        r=quad_rect(raw,qoff)
        # geometry -> composite pixels (game y grows upward)
        cx0=int(round(r[0]-minx)); cx1=int(round(r[1]-minx)); cy0=int(round(maxy-r[3])); cy1=int(round(maxy-r[2]))
        piece=canvas.crop((cx0,cy0,cx1,cy1))
        ux0=int(round(r[4]*aw)); ux1=int(round(r[5]*aw)); uy0=int(round(r[6]*ah)); uy1=int(round(r[7]*ah))
        if piece.size!=(ux1-ux0,uy1-uy0): piece=piece.resize((ux1-ux0,uy1-uy0),Image.Resampling.LANCZOS)
        atlas.paste(piece,(ux0,uy0),piece)

def replace_text_node_inplace(filename,node_idx,text,font_size=18,fill=(255,255,255,255),stroke_fill=None,stroke_width=0,quad_indices=None,multiline=None):
    src=ROM/filename; raw=bytearray(unpack_container(src,OSB_KEY)); h=parse_osb(raw); atlas=decode_osb_rgba4444(raw)
    qoffs,b=node_composite_geometry(raw,h,node_idx,quad_indices); minx,maxx,miny,maxy=b
    W=max(1,int(round(maxx-minx))); H=max(1,int(round(maxy-miny)))
    canvas=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(canvas); font=ImageFont.truetype(FONT_PATH,font_size)
    lines=(multiline if multiline is not None else text.split('\n'))
    # center all lines vertically/horizontally
    boxes=[d.textbbox((0,0),ln,font=font,stroke_width=stroke_width) for ln in lines]
    heights=[bb[3]-bb[1] for bb in boxes]; total=sum(heights)+max(0,len(lines)-1)*1
    y=(H-total)//2
    for ln,bb,lh in zip(lines,boxes,heights):
        tw=bb[2]-bb[0]; x=(W-tw)//2-bb[0]
        d.text((x,y-bb[1]),ln,font=font,fill=fill,stroke_width=stroke_width,stroke_fill=stroke_fill or fill)
        y+=lh+1
    # overwrite exact UV regions; use direct paste including transparency so old English is removed
    # custom version of paste with no alpha mask
    inds=list(range(len(node_quad_offsets(raw,h,node_idx)))) if quad_indices is None else list(quad_indices)
    sel=[node_quad_offsets(raw,h,node_idx)[i] for i in inds]; rects=[quad_rect(raw,q) for q in sel]
    minx,maxx=min(r[0] for r in rects),max(r[1] for r in rects); miny,maxy=min(r[2] for r in rects),max(r[3] for r in rects)
    aw,ah=atlas.size
    for qoff in sel:
        r=quad_rect(raw,qoff); cx0=int(round(r[0]-minx));cx1=int(round(r[1]-minx));cy0=int(round(maxy-r[3]));cy1=int(round(maxy-r[2]))
        piece=canvas.crop((cx0,cy0,cx1,cy1))
        ux0=int(round(r[4]*aw));ux1=int(round(r[5]*aw));uy0=int(round(r[6]*ah));uy1=int(round(r[7]*ah))
        piece=piece.resize((ux1-ux0,uy1-uy0),Image.Resampling.LANCZOS)
        atlas.paste(piece,(ux0,uy0))
    raw[h[5]:h[5]+h[1]]=encode_osb_rgba4444(atlas)
    out=OUTROM/filename; out.write_bytes(pack_container(bytes(raw),OSB_KEY)); parse_osb(unpack_container(out,OSB_KEY))
    return out

def patch_graphictext01():
    fn='GraphicText01.osbctr'; raw0=unpack_container(ROM/fn,OSB_KEY); raw,cl=clone_overlaps(raw0); h=parse_osb(raw)
    atlas=Image.new('RGBA',(h[3],h[4]),(0,0,0,0)); W,H=atlas.size
    specs={
        0:('OYUN BİTTİ',(255,95,145,255)),
        2:('OYUN BİTTİ',(180,20,30,255)),
        3:('OYUN BİTTİ',(255,95,145,255)),
        4:('TEBRİKLER!',(255,120,20,255)),
        6:('TEBRİKLER!!',(190,30,30,255)),
        7:('TEBRİKLER!!',(255,110,20,255)),
    }
    blank=(248,248,256,256)
    atlas.paste((0,0,0,0),blank)
    strip_h=36
    for si,(node,(txt,col)) in enumerate(specs.items()):
        y0=si*strip_h; y1=y0+strip_h
        strip=Image.new('RGBA',(256,strip_h),(0,0,0,0)); d=ImageDraw.Draw(strip); font=ImageFont.truetype(FONT_PATH,22)
        bb=d.textbbox((0,0),txt,font=font,stroke_width=1); tw=bb[2]-bb[0]; th=bb[3]-bb[1]
        d.text(((256-tw)//2-bb[0],(strip_h-th)//2-bb[1]),txt,font=font,fill=col,stroke_width=1,stroke_fill=(255,200,180,255) if node in (0,3,4,7) else col)
        atlas.alpha_composite(strip,(0,y0))
        qoffs=node_quad_offsets(raw,h,node); rects=[quad_rect(raw,q) for q in qoffs]
        bx=(min(r[0] for r in rects),max(r[1] for r in rects),min(r[2] for r in rects),max(r[3] for r in rects))
        u0,u1,v0,v1=0,1,y0/H,y1/H
        set_quad(raw,qoffs[0],bx[0],bx[1],bx[2],bx[3],u0,u1,v0,v1)
        for qoff in qoffs[1:]:
            r=quad_rect(raw,qoff); set_quad(raw,qoff,r[0],r[1],r[2],r[3],blank[0]/W,blank[2]/W,blank[1]/H,blank[3]/H)
    # blank node1 too
    for node in (1,):
        for qoff in node_quad_offsets(raw,h,node):
            r=quad_rect(raw,qoff); set_quad(raw,qoff,r[0],r[1],r[2],r[3],blank[0]/W,blank[2]/W,blank[1]/H,blank[3]/H)
    raw[h[5]:h[5]+h[1]]=encode_osb_rgba4444(atlas)
    out=OUTROM/fn; out.write_bytes(pack_container(bytes(raw),OSB_KEY)); parse_osb(unpack_container(out,OSB_KEY)); return out

def patch_thank():
    fn='Thank00.osbctr'; raw=bytearray(unpack_container(ROM/fn,OSB_KEY));h=parse_osb(raw);atlas=decode_osb_rgba4444(raw)
    qoffs=node_quad_offsets(raw,h,0); chosen=[qoffs[2],qoffs[3]]; rs=[quad_rect(raw,q) for q in chosen]
    # Build the two 200x112 logo halves side-by-side from atlas.
    comp=Image.new('RGBA',(400,112),(0,0,0,0)); aw,ah=atlas.size
    for k,r in enumerate(rs):
        ux0=int(round(r[4]*aw));ux1=int(round(r[5]*aw));uy0=int(round(r[6]*ah));uy1=int(round(r[7]*ah))
        piece=atlas.crop((ux0,uy0,ux1,uy1)).resize((200,112),Image.Resampling.NEAREST); comp.alpha_composite(piece,(k*200,0))
    # Cover only the English thank-you line; keep the official game logo/subtitle around it.
    pix=comp.load(); xs=[];ys=[]
    for y in range(comp.height):
        for x in range(comp.width):
            r,g,b,a=pix[x,y]
            if a>100 and r>190 and g>190 and b>190: xs.append(x);ys.append(y)
    if xs:
        y0=max(0,min(ys)-3); y1=min(comp.height,max(ys)+4)
    else: y0,y1=38,70
    d=ImageDraw.Draw(comp); d.rectangle((0,y0,399,y1),fill=(0,0,0,255))
    txt='OYUN İÇİN TEŞEKKÜRLER!'; font=ImageFont.truetype(FONT_PATH,20); bb=d.textbbox((0,0),txt,font=font);tw=bb[2]-bb[0];th=bb[3]-bb[1]
    d.text(((400-tw)//2-bb[0],(y0+y1-th)//2-bb[1]),txt,font=font,fill=(255,255,255,255))
    for k,r in enumerate(rs):
        piece=comp.crop((k*200,0,(k+1)*200,112)); ux0=int(round(r[4]*aw));ux1=int(round(r[5]*aw));uy0=int(round(r[6]*ah));uy1=int(round(r[7]*ah))
        atlas.paste(piece.resize((ux1-ux0,uy1-uy0),Image.Resampling.NEAREST),(ux0,uy0))
    raw[h[5]:h[5]+h[1]]=encode_osb_rgba4444(atlas); out=OUTROM/fn;out.write_bytes(pack_container(bytes(raw),OSB_KEY));parse_osb(unpack_container(out,OSB_KEY));return out

# Standalone graphic labels.
replace_text_node_inplace('Clear00.osbctr',0,'BÖLÜM\nTAMAM',font_size=18,fill=(245,255,245,255),stroke_fill=(20,210,70,255),stroke_width=1,multiline=['BÖLÜM','TAMAM'])
# nodes use separate atlas variants; apply directly on source each time would overwrite previous output, so patch all three in one pass below.
def patch_clear_all():
    fn='Clear00.osbctr';raw=bytearray(unpack_container(ROM/fn,OSB_KEY));h=parse_osb(raw);atlas=decode_osb_rgba4444(raw);aw,ah=atlas.size
    for node in [0,1,2]:
        qoff=node_quad_offsets(raw,h,node)[0];r=quad_rect(raw,qoff); ux0=int(round(r[4]*aw));ux1=int(round(r[5]*aw));uy0=int(round(r[6]*ah));uy1=int(round(r[7]*ah))
        W=int(round(r[1]-r[0]));H=int(round(r[3]-r[2]));im=Image.new('RGBA',(W,H),(0,0,0,0));d=ImageDraw.Draw(im);font=ImageFont.truetype(FONT_PATH,18)
        lines=['BÖLÜM','TAMAM']; y=2
        for ln in lines:
            bb=d.textbbox((0,0),ln,font=font,stroke_width=1);tw=bb[2]-bb[0];th=bb[3]-bb[1];d.text(((W-tw)//2-bb[0],y-bb[1]),ln,font=font,fill=(245,255,245,255),stroke_width=1,stroke_fill=(20,210,70,255));y+=22
        atlas.paste(im.resize((ux1-ux0,uy1-uy0),Image.Resampling.LANCZOS),(ux0,uy0))
    raw[h[5]:h[5]+h[1]]=encode_osb_rgba4444(atlas);out=OUTROM/fn;out.write_bytes(pack_container(bytes(raw),OSB_KEY));parse_osb(unpack_container(out,OSB_KEY));return out
patch_clear_all()
replace_text_node_inplace('Start00.osbctr',0,'BAŞLA',font_size=22,fill=(255,230,80,255),stroke_fill=(150,60,0,255),stroke_width=1)
patch_graphictext01()
patch_thank()
# Copyright line variants in title screen.
def patch_title_copyright():
    fn='Title00.osbctr';raw=bytearray(unpack_container(ROM/fn,OSB_KEY));h=parse_osb(raw);atlas=decode_osb_rgba4444(raw);aw,ah=atlas.size
    for node in [2,3,4]:
        qoffs=node_quad_offsets(raw,h,node); rs=[quad_rect(raw,q) for q in qoffs]; minx,maxx=min(r[0] for r in rs),max(r[1] for r in rs); W=int(round(maxx-minx));H=8
        im=Image.new('RGBA',(W,H),(0,0,0,0));d=ImageDraw.Draw(im);txt='©INTI CREATES CO., LTD. 2018 TÜM HAKLARI SAKLIDIR.';font=ImageFont.truetype(FONT_PATH,8);bb=d.textbbox((0,0),txt,font=font);tw=bb[2]-bb[0]
        if tw>W: font=ImageFont.truetype(FONT_PATH,7);bb=d.textbbox((0,0),txt,font=font);tw=bb[2]-bb[0]
        d.text(((W-tw)//2-bb[0],-bb[1]),txt,font=font,fill=(245,245,245,255))
        # split using geometry width
        cursor=0
        for qoff,r in zip(qoffs,rs):
            gw=int(round(r[1]-r[0])); piece=im.crop((cursor,0,cursor+gw,H));cursor+=gw
            ux0=int(round(r[4]*aw));ux1=int(round(r[5]*aw));uy0=int(round(r[6]*ah));uy1=int(round(r[7]*ah));atlas.paste(piece.resize((ux1-ux0,uy1-uy0),Image.Resampling.LANCZOS),(ux0,uy0))
    # Node5's long strip is only the rights line; second quad is an icon.
    qoff=node_quad_offsets(raw,h,5)[0];r=quad_rect(raw,qoff); W=int(round(r[1]-r[0]));H=8;im=Image.new('RGBA',(W,H),(0,0,0,0));d=ImageDraw.Draw(im);txt='2018 TÜM HAKLARI SAKLIDIR.';font=ImageFont.truetype(FONT_PATH,8);bb=d.textbbox((0,0),txt,font=font);tw=bb[2]-bb[0];d.text(((W-tw)//2-bb[0],-bb[1]),txt,font=font,fill=(245,245,245,255));ux0=int(round(r[4]*aw));ux1=int(round(r[5]*aw));uy0=int(round(r[6]*ah));uy1=int(round(r[7]*ah));atlas.paste(im.resize((ux1-ux0,uy1-uy0),Image.Resampling.LANCZOS),(ux0,uy0))
    raw[h[5]:h[5]+h[1]]=encode_osb_rgba4444(atlas);out=OUTROM/fn;out.write_bytes(pack_container(bytes(raw),OSB_KEY));parse_osb(unpack_container(out,OSB_KEY));return out
patch_title_copyright()

# Generic small-pixel UI labels / loading / saving. Proper names and legal company names are preserved.
gt00={
15:'BİR TUŞA BAS',16:'OYUN AYARI',17:'PATRON',18:'PATRON',19:'AYAR',22:'TİTREŞİM',23:'',24:'HD TİTRE',25:'SES DİLİ',26:'DOSYA TAKAS',27:'SİL',28:'LANET DURAK',29:'AY LANETİ',30:'BİTİŞ AÇ',36:'CAN',37:'CANLAR',38:'PUAN',39:'SİLAH',41:'SİL',42:'BÜYÜ YOK',43:'KÂBUS',44:'SÜRE',45:'NİHAİ',46:'ORTA',47:'RAHAT',48:'USTA',49:'',50:'TÜR',51:'SÜRE YOK',52:'YENİ VERİ',53:'OYUNA DEVAM',54:'',55:'DEĞİŞ',56:'STİL',57:'AÇIK',58:'VUR',59:'ALT SİLAH',60:'KARAKTER SAĞ',61:'KARAKTER SOL',62:'KOMUT DEĞİŞ',63:'SİLAH',64:'KOMUT',65:'KOŞ',66:'VUR',67:'VUR',68:'ZIPLA',69:'',70:'',72:'R1',73:'RENK 2',74:'RENK 3',75:'JAPONCA',76:'TÜRKÇE',
}
for i in range(77,87): gt00[i]='YÜKLENİYOR'
gt00[87]='YÜKLE'
for i in range(88,91): gt00[i]='YÜKLENİYOR'
for i in range(91,100): gt00[i]='KAYDEDİYOR'
gt00[100]='KAYDET';gt00[101]='KAYDEDİYOR'
patch_osb_text_file('GraphicText00.osbctr',gt00,align='left')

# Refresh checksums now that graphical UI files were added.
lines=[]
for p in sorted(OUTROM.iterdir()):
    if p.is_file(): lines.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name)
(OUT/'SHA256SUMS.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('Graphical UI patching complete. Files in romfs:',len(list(OUTROM.iterdir())))
