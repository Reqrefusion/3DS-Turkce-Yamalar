#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ocarina of Time 3D (EUR) QM/QBF Turkish localisation utility.

Designed around the EU eu.qm / ltn16.qbf files supplied by the user.
It is deliberately lossless for untouched languages and preserves every table field.
"""
from __future__ import annotations
import argparse,csv,json,struct,sys,re,unicodedata
from pathlib import Path
from collections import Counter

VERSION='1.3.0'
LANGS=['JP','US_EN','EU_EN','DE','EU_FR','US_FR','EU_ES','US_ES','IT','NL']
LANG_INDEX={x:i for i,x in enumerate(LANGS)}
CTRL_PARAM={0x00:0,0x01:0,0x02:1,0x03:2,0x04:0,0x05:0,0x06:0,0x07:0,0x08:1,0x0A:1,0x0B:0,0x0C:0,0x0E:5,0x0F:1,0x10:1,0x11:3,0x12:0,0x13:0,0x14:0,0x15:0,0x16:0,0x17:0,0x18:1,0x19:0,0x1A:4,0x1B:6,0x1C:0,0x1D:1,0x1E:0,0x23:1,0x24:1,0x25:3,0x26:1,0x27:0,0x28:0,0x29:0,0x2A:0,0x2B:0}
CTRL_NAMES={0x00:'END',0x01:'WAIT',0x02:'SPACE',0x03:'GOTO',0x04:'INSTANT_ON',0x05:'INSTANT_OFF',0x06:'SHOP',0x07:'EVENT',0x08:'DELAY',0x0A:'CLOSE',0x0B:'PLAYER',0x0C:'OCARINA',0x0E:'SOUND',0x0F:'ITEM',0x10:'SPEED',0x11:'BG',0x12:'VAR12',0x13:'VAR13',0x14:'VAR14',0x15:'VAR15',0x16:'VAR16',0x17:'VAR17',0x18:'VAR',0x19:'UNSKIP',0x1A:'CHOICE2',0x1B:'CHOICE3',0x1C:'NL',0x1D:'COLOR',0x1E:'CENTER',0x23:'CTRL23',0x24:'BTN',0x25:'CREDIT',0x26:'FLAG',0x27:'ELSE',0x28:'ENDIF',0x29:'IF_NOT_MQ',0x2A:'ELSE_MQ',0x2B:'ENDIF_MQ'}
NAME_CTRL={v:k for k,v in CTRL_NAMES.items()}
# Readable Turkish aliases used by earlier community tools/exports.
NAME_CTRL.update({'RENK':0x1D,'OYUNCU':0x0B})
# Controls that affect game flow / variables and should normally survive translation.
SEMANTIC={0x00,0x01,0x03,0x06,0x07,0x08,0x0A,0x0B,0x0C,0x0E,0x0F,0x11,0x12,0x13,0x14,0x15,0x16,0x17,0x18,0x19,0x1A,0x1B,0x23,0x24,0x25,0x26,0x27,0x28,0x29,0x2A,0x2B}


# IMPORTANT: Python Unicode re.IGNORECASE is unsafe for Turkish text: it treats
# i/I/İ/ı as case-insensitive matches.  All Turkish case-insensitive operations
# in this tool therefore use these one-codepoint mappings and literal matching.
_TR_LOWER={'I':'ı','İ':'i','Ç':'ç','Ğ':'ğ','Ö':'ö','Ş':'ş','Ü':'ü'}
_TR_UPPER={'i':'İ','ı':'I','ç':'Ç','ğ':'Ğ','ö':'Ö','ş':'Ş','ü':'Ü'}
def tr_lower(s:str)->str:
 return ''.join(_TR_LOWER.get(ch,ch.lower()) for ch in s)
def tr_upper(s:str)->str:
 return ''.join(_TR_UPPER.get(ch,ch.upper()) for ch in s)
def tr_ci_equal(a:str,b:str)->bool: return tr_lower(a)==tr_lower(b)
def tr_ci_find(haystack:str,needle:str)->int: return tr_lower(haystack).find(tr_lower(needle))

def nfc_text(s:str)->str: return unicodedata.normalize('NFC',s)

# Conservative review candidates only; never auto-rewritten.  These are common
# legacy ASCII/font-era spellings seen in Turkish game patches.
TR_MIX_SUSPECT_RE=re.compile(
 r"\b(?:acilm\w*|açil\w*|çalacaksin|kahkahadir|sadik|usak\w*|davranilir|"
 r"çadir\w*|sıkışip|unvanina|atlatmani|zamanina|çıkarayim|kiymetli|"
 r"kulaklariyla|adamimdir|seçilmis|açgözlülüge|degil|simdi|hayir\w*|sey|"
 r"karsilig\w*|ogren\w*|gunes\w*|dogru\w*|yanlis\w*|muhur\w*|isgal\w*|"
 r"yetis\w*|geçmis\w*|yakışmis\w*|alindi\w*|açini|almani|antrenmani|ekipmani|ayağiyla)\b")
TR_CONTEXT_SUSPECT_RE=(
 ('TR_TAKIP_TAKIP', re.compile(r'\btakıp(?:\s|⏎)+(?:et|ed)\w*')),
 ('TR_MIS_SUFFIX', re.compile(r'\b[A-Za-zÇĞİÖŞÜçğıöşü]+mis\b')),
 ('TR_MAN_I_SUFFIX', re.compile(r'\b[A-Za-zÇĞİÖŞÜçğıöşü]+mani\b')),
)
TR_ALLCAP_I_SUSPECT={'yine':'YİNE','kimseye':'KİMSEYE','bilgeler':'BİLGELER','iyi':'İYİ','ikinci':'İKİNCİ','ileri':'İLERİ'}

def turkish_text_audit(text:str):
 issues=[]
 if text!=nfc_text(text): issues.append(('NON_NFC','Unicode text is not NFC-normalized'))
 if any(unicodedata.category(ch).startswith('M') for ch in text): issues.append(('COMBINING_MARK','Combining Unicode mark present'))
 folded=tr_lower(text)
 for m in TR_MIX_SUSPECT_RE.finditer(folded): issues.append(('TR_CHAR_MIX_CANDIDATE',m.group(0)))
 for typ,rx in TR_CONTEXT_SUSPECT_RE:
  for m in rx.finditer(text):
   # These rules only report review candidates; they never rewrite text.
   issues.append((typ,m.group(0)))
 for w in re.findall(r'\b[A-ZÇĞİÖŞÜ]{3,}\b',text):
  lw=tr_lower(w)
  if lw in TR_ALLCAP_I_SUSPECT and w!=TR_ALLCAP_I_SUSPECT[lw]:
   issues.append(('TR_UPPERCASE_I_CANDIDATE',f'{w} -> {TR_ALLCAP_I_SUSPECT[lw]}'))
 return issues

class QM:
 def __init__(self,path:Path):
  self.path=Path(path); self.data=self.path.read_bytes()
  if self.data[:4]!=b'QM\0\0': raise ValueError('Not a QM file')
  self.count=struct.unpack_from('<I',self.data,8)[0]
  self.table_end=16+self.count*0x60
  if self.table_end>len(self.data): raise ValueError('Truncated QM table')
  self.rows=[]
  for i in range(self.count):
   pos=16+i*0x60; row=bytearray(self.data[pos:pos+0x60]); mid=struct.unpack_from('<I',row,0)[0]
   pairs=[struct.unpack_from('<II',row,0x10+j*8) for j in range(10)]
   self.rows.append({'id':mid,'row':row,'pairs':pairs})
 def text(self,i,lang='EU_EN'):
  off,ln=self.rows[i]['pairs'][LANG_INDEX[lang]]; return self.data[off:off+ln] if off and ln else b''
 def rebuild_replace(self,replacements:dict[int,bytes],lang='EU_EN'):
  """Rebuild by appending all language payloads compactly; table values preserved except offsets/lengths."""
  # Keep 16-byte header + exact table rows, regenerate payloads in row/language order.
  head=bytearray(self.data[:16]); rows=[bytearray(r['row']) for r in self.rows]
  payload=bytearray(); cursor=16+self.count*0x60; li=LANG_INDEX[lang]
  # Preserve 4-byte alignment used by the source file.
  for i,r in enumerate(self.rows):
   for j in range(10):
    raw=replacements.get(i,self.text(i,lang)) if j==li else self.text(i,LANGS[j])
    if not raw:
     struct.pack_into('<II',rows[i],0x10+j*8,0,0); continue
    pad=(-cursor)&3
    if pad: payload.extend(b'\0'*pad); cursor+=pad
    struct.pack_into('<II',rows[i],0x10+j*8,cursor,len(raw)); payload.extend(raw); cursor+=len(raw)
  return bytes(head)+b''.join(bytes(r) for r in rows)+bytes(payload)

def repair_extra_7f_utf8(raw:bytes)->tuple[bytes,int]:
 out=bytearray(); i=0; nfix=0
 while i<len(raw):
  if raw[i]==0x7f and i+2<len(raw) and 0xC2<=raw[i+1]<=0xF4:
   lead=raw[i+1]; n=2 if lead<0xE0 else 3 if lead<0xF0 else 4
   seq=raw[i+1:i+1+n]
   try: seq.decode('utf-8')
   except UnicodeDecodeError: pass
   else: out.extend(seq); i+=1+n; nfix+=1; continue
  out.append(raw[i]); i+=1
 return bytes(out),nfix

def tokenize(raw:bytes):
 raw,_=repair_extra_7f_utf8(raw); out=[]; text=bytearray(); i=0
 def flush():
  if text:
   out.append(('text',bytes(text))); text.clear()
 while i<len(raw):
  if raw[i]==0x7f and i+1<len(raw):
   flush(); cmd=raw[i+1]; n=CTRL_PARAM.get(cmd)
   if n is None:
    out.append(('ctrl',cmd,b'')); i+=2; continue
   payload=raw[i+2:i+2+n]; out.append(('ctrl',cmd,payload)); i+=2+n
  else: text.append(raw[i]); i+=1
 flush(); return out

def visible(raw:bytes)->str:
 chunks=[]
 for t in tokenize(raw):
  if t[0]=='text': chunks.append(t[1].decode('utf-8','replace'))
  else:
   _,cmd,p=t
   if cmd==0x1c: chunks.append('⏎')
   elif cmd==0x0b: chunks.append('{PLAYER}')
   else:
    name=CTRL_NAMES.get(cmd,f'CTRL{cmd:02X}'); chunks.append('{'+name+((':'+p.hex().upper()) if p else '')+'}')
 return ''.join(chunks)

def parse_markup(s:str)->bytes:
 """Convert export markup back to raw message bytes."""
 s=nfc_text(s)
 out=bytearray(); pos=0
 pat=re.compile(r'(⏎|\{[A-Z0-9_]+(?::[0-9A-Fa-f]*)?\})')
 for m in pat.finditer(s):
  out.extend(s[pos:m.start()].encode('utf-8'))
  tok=m.group(0)
  if tok=='⏎': out.extend(b'\x7f\x1c')
  else:
   inner=tok[1:-1]
   name,_,hx=inner.partition(':')
   if name not in NAME_CTRL: raise ValueError(f'Unknown control token: {tok}')
   cmd=NAME_CTRL[name]; need=CTRL_PARAM.get(cmd,0); p=bytes.fromhex(hx) if hx else b''
   if len(p)!=need: raise ValueError(f'{tok}: expected {need} parameter bytes, got {len(p)}')
   out.extend((0x7f,cmd)); out.extend(p)
  pos=m.end()
 out.extend(s[pos:].encode('utf-8'))
 return bytes(out)

def controls(raw:bytes,semantic_only=False):
 seq=[]
 for t in tokenize(raw):
  if t[0]=='ctrl':
   _,cmd,p=t
   if semantic_only and cmd not in SEMANTIC: continue
   seq.append((cmd,p))
 return seq

def cmd_export(a):
 qm=QM(Path(a.qm)); other=QM(Path(a.compare)) if a.compare else None
 fields=['index','id']+LANGS+(['CURRENT_TR'] if other else [])
 with open(a.output,'w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
  for i,r in enumerate(qm.rows):
   row={'index':i,'id':f"{r['id']:04X}"}
   for l in LANGS: row[l]=visible(qm.text(i,l))
   if other: row['CURRENT_TR']=visible(other.text(i,a.lang))
   w.writerow(row)
 print(f'Exported {qm.count} rows -> {a.output}')

def cmd_inject(a):
 qm=QM(Path(a.qm)); repl={}
 with open(a.csv,encoding='utf-8-sig',newline='') as f:
  for row in csv.DictReader(f):
   if not row.get(a.column): continue
   i=int(row['index']); markup=nfc_text(row[a.column])
   if getattr(a,'strict_turkish',False):
    plain=re.sub(r'(⏎|\{[A-Z0-9_]+(?::[0-9A-Fa-f]*)?\})',' ',markup)
    problems=turkish_text_audit(plain)
    if problems:
     raise ValueError(f'Row {i} Turkish audit failed: {problems[:8]}')
   repl[i]=parse_markup(markup)
 out=qm.rebuild_replace(repl,a.lang); Path(a.output).write_bytes(out)
 print(f'Injected {len(repl)} rows -> {a.output}')

def cmd_repair(a):
 qm=QM(Path(a.qm)); repl={}; fixes=0; msgs=0
 for i in range(qm.count):
  raw=qm.text(i,a.lang); rr,n=repair_extra_7f_utf8(raw)
  if n: repl[i]=rr; fixes+=n; msgs+=1
 Path(a.output).write_bytes(qm.rebuild_replace(repl,a.lang))
 print(json.dumps({'messages_fixed':msgs,'bogus_0x7f_removed':fixes,'output':a.output},ensure_ascii=False,indent=2))

def qbf_read(path):
 b=bytearray(Path(path).read_bytes());
 if b[:4]!=b'QBF1': raise ValueError('Not QBF1')
 cc,gc=struct.unpack_from('<HH',b,4); bpp,w,h,unk=struct.unpack_from('<BBBB',b,12); mo=16; go=mo+cc*8; gs=w*h*bpp//8
 meta=[list(struct.unpack_from('<HHBBH',b,mo+i*8)) for i in range(cc)]
 return b,cc,gc,bpp,w,h,unk,meta,go,gs

def qbf_add_turkish(src,out):
 b,cc,gc,bpp,w,h,unk,meta,go,gs=qbf_read(src)
 if (bpp,w,h)!=(4,16,16): raise ValueError('Expected 4bpp 16x16 QBF')
 by={m[0]:m for m in meta}; need='ĞğİıŞş'
 if all(ord(c) in by for c in need): Path(out).write_bytes(b); return {'already_present':True,'output':str(out)}
 def dec(gid):
  raw=b[go+gid*gs:go+(gid+1)*gs]; p=[]
  for x in raw:p.extend((x>>4,x&15))
  return [p[y*w:(y+1)*w] for y in range(h)]
 def enc(a):
  p=[v&15 for row in a for v in row]; z=bytearray()
  for i in range(0,len(p),2): z.append((p[i]<<4)|p[i+1])
  return bytes(z)
 def cp(c): return by[ord(c)][1]
 def copy(c): return [r[:] for r in dec(cp(c))]
 Cc,bc=dec(cp('Ç')),dec(cp('C')); cc2,bc2=dec(cp('ç')),dec(cp('c'))
 def diff(a,b): return [[a[y][x] if a[y][x]>b[y][x] else 0 for x in range(w)] for y in range(h)]
 cedU,cedL=diff(Cc,bc),diff(cc2,bc2)
 def breve(a,y0=1,x0=5):
  for x,y,v in [(x0,y0,11),(x0+4,y0,11),(x0+1,y0+1,15),(x0+2,y0+1,15),(x0+3,y0+1,15)]: a[y][x]=max(a[y][x],v)
  return a
 specs=[('Ğ','G',breve(copy('G'))),('ğ','g',breve(copy('g')))]
 ai=copy('I')
 for x,y,v in [(7,1,15),(8,1,15),(7,2,15),(8,2,15)]: ai[y][x]=max(ai[y][x],v)
 specs.append(('İ','I',ai)); ai=copy('i')
 for y in range(0,5):
  for x in range(w): ai[y][x]=0
 specs.append(('ı','i',ai))
 for ch,base,mask in [('Ş','S',cedU),('ş','s',cedL)]:
  a=copy(base)
  for y in range(h):
   for x in range(w): a[y][x]=max(a[y][x],mask[y][x])
  specs.append((ch,base,a))
 used={m[1] for m in meta}; free=[g for g in range(gc) if g not in used]
 missing=[sp for sp in specs if ord(sp[0]) not in by]
 if len(free)<len(missing): raise ValueError(f'Need {len(missing)} free glyph slots, have {len(free)}')
 glyph=bytearray(b[go:go+gc*gs]); new=[]
 for (ch,base,a),gid in zip(missing,free):
  bm=by[ord(base)]; new.append([ord(ch),gid,bm[2],bm[3],0]); glyph[gid*gs:(gid+1)*gs]=enc(a)
 meta2=sorted(meta+new,key=lambda m:m[0]); head=bytearray(b[:16]); struct.pack_into('<H',head,4,len(meta2)); blob=b''.join(struct.pack('<HHBBH',*m) for m in meta2)
 Path(out).write_bytes(head+blob+glyph)
 return {'already_present':False,'added':[(chr(m[0]),m[1]) for m in new],'char_count':len(meta2),'glyph_count':gc,'output':str(out)}

def cmd_qbf_info(a):
 b,cc,gc,bpp,w,h,unk,meta,go,gs=qbf_read(a.qbf); cps={m[0] for m in meta}; by={m[0]:m for m in meta}
 core='ÇçĞğİıÖöŞşÜüÂâÎîÛû'; imap={}
 for c in 'Iİiı':
  if ord(c) in by:
   cp,gid,adv,bear,flags=by[ord(c)]; imap[c]={'codepoint':f'U+{cp:04X}','glyph_id':gid,'advance':adv,'bearing':bear}
 print(json.dumps({'path':a.qbf,'char_count':cc,'glyph_count':gc,'bpp':bpp,'glyph_width':w,'glyph_height':h,'bitmap_offset':go,'glyph_size':gs,
  'duplicate_codepoints':len(meta)-len({m[0] for m in meta}),'duplicate_glyph_ids':len(meta)-len({m[1] for m in meta}),
  'turkish_core':{c:(ord(c) in cps) for c in core},'i_family':imap,
  'i_family_distinct_glyph_ids':len({x['glyph_id'] for x in imap.values()})==len(imap)},ensure_ascii=False,indent=2))

def cmd_qbf_add(a): print(json.dumps(qbf_add_turkish(a.qbf,a.output),ensure_ascii=False,indent=2))

def cmd_validate(a):
 base=QM(Path(a.base)); tr=QM(Path(a.tr)); issues=[]; stats=Counter(); font_cps=None
 if a.font:
  *_,meta,_,_=qbf_read(a.font); font_cps={m[0] for m in meta}
 for i,(br,trr) in enumerate(zip(base.rows,tr.rows)):
  b=base.text(i,a.lang); t=tr.text(i,a.lang); rr,n=repair_extra_7f_utf8(t)
  if n: issues.append((i,trr['id'],'bogus_7f_utf8',str(n))); stats['bogus_7f_msgs']+=1; stats['bogus_7f_count']+=n
  try:
   txt=b''.join(x[1] for x in tokenize(t) if x[0]=='text').decode('utf-8')
  except UnicodeDecodeError as e:
   issues.append((i,trr['id'],'invalid_utf8',str(e))); stats['invalid_utf8']+=1; txt=''
  bs=controls(b,True); ts=controls(t,True)
  # Layout/page breaks may legitimately differ; semantic sequence should not.
  if bs!=ts: issues.append((i,trr['id'],'semantic_control_mismatch',f'base={[(x,p.hex()) for x,p in bs]} tr={[(x,p.hex()) for x,p in ts]}')); stats['semantic_mismatch']+=1
  if b and t==b: stats['unchanged_from_english']+=1
  if font_cps is not None:
   miss=sorted({ord(ch) for ch in txt if ord(ch)>=32 and ord(ch) not in font_cps})
   if miss: issues.append((i,trr['id'],'missing_glyphs',' '.join(f'U+{x:04X}' for x in miss))); stats['missing_glyph_msgs']+=1
 stats['entries']=base.count; stats['issues']=len(issues)
 if a.report:
  with open(a.report,'w',encoding='utf-8',newline='') as f:
   w=csv.writer(f); w.writerow(['index','id','type','details']); w.writerows(issues)
 print(json.dumps(stats,ensure_ascii=False,indent=2))


def cmd_turkish_audit(a):
 qm=QM(Path(a.qm)); issues=[]; counts=Counter()
 for i,r in enumerate(qm.rows):
  raw=qm.text(i,a.lang); rr,n=repair_extra_7f_utf8(raw)
  if n:
   issues.append((i,f"{r['id']:04X}",'BOGUS_7F_UTF8',str(n))); counts['BOGUS_7F_UTF8']+=1
  try:
   txt=''.join(t[1].decode('utf-8') for t in tokenize(raw) if t[0]=='text')
  except UnicodeDecodeError as e:
   issues.append((i,f"{r['id']:04X}",'INVALID_UTF8',str(e))); counts['INVALID_UTF8']+=1; continue
  for typ,detail in turkish_text_audit(txt):
   issues.append((i,f"{r['id']:04X}",typ,detail)); counts[typ]+=1
 if a.report:
  with open(a.report,'w',encoding='utf-8-sig',newline='') as f:
   w=csv.writer(f); w.writerow(['index','id','type','details']); w.writerows(issues)
 print(json.dumps({'entries':qm.count,'issue_count':len(issues),'counts':dict(counts),
  'python_ignorecase_turkish_trap':bool(re.match('i','ı',re.IGNORECASE)),
  'report':a.report},ensure_ascii=False,indent=2))

def cmd_self_test(a):
 checks={
  'tr_lower_I':tr_lower('I')=='ı',
  'tr_lower_İ':tr_lower('İ')=='i',
  'tr_upper_i':tr_upper('i')=='İ',
  'tr_upper_ı':tr_upper('ı')=='I',
  'safe_i_dotless_distinct':not tr_ci_equal('i','ı'),
  'nfc_normalization':nfc_text('I\u0307')=='İ',
  'markup_nfc_roundtrip':visible(parse_markup('İ ı Ş ş Ğ ğ'))=='İ ı Ş ş Ğ ğ',
 }
 obj={'version':VERSION,'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,
      'python_re_ignorecase_turkish_trap':bool(re.match('i','ı',re.IGNORECASE))}
 print(json.dumps(obj,ensure_ascii=False,indent=2))

def main():
 ap=argparse.ArgumentParser(description='OoT3D EUR Türkçe QM/QBF aracı'); ap.add_argument('--version',action='version',version=VERSION); sp=ap.add_subparsers(dest='cmd',required=True)
 p=sp.add_parser('qm-export'); p.add_argument('qm'); p.add_argument('output'); p.add_argument('--compare'); p.add_argument('--lang',default='EU_EN',choices=LANGS); p.set_defaults(func=cmd_export)
 p=sp.add_parser('qm-inject'); p.add_argument('qm'); p.add_argument('csv'); p.add_argument('output'); p.add_argument('--column',default='TR_REVISED'); p.add_argument('--lang',default='EU_EN',choices=LANGS); p.add_argument('--strict-turkish',action='store_true',help='Şüpheli Türkçe karakter karışımlarında enjeksiyonu durdur'); p.set_defaults(func=cmd_inject)
 p=sp.add_parser('qm-repair-legacy'); p.add_argument('qm'); p.add_argument('output'); p.add_argument('--lang',default='EU_EN',choices=LANGS); p.set_defaults(func=cmd_repair)
 p=sp.add_parser('qm-validate'); p.add_argument('base'); p.add_argument('tr'); p.add_argument('--font'); p.add_argument('--report'); p.add_argument('--lang',default='EU_EN',choices=LANGS); p.set_defaults(func=cmd_validate)
 p=sp.add_parser('qm-turkish-audit'); p.add_argument('qm'); p.add_argument('--report'); p.add_argument('--lang',default='EU_EN',choices=LANGS); p.set_defaults(func=cmd_turkish_audit)
 p=sp.add_parser('qbf-info'); p.add_argument('qbf'); p.set_defaults(func=cmd_qbf_info)
 p=sp.add_parser('qbf-add-turkish'); p.add_argument('qbf'); p.add_argument('output'); p.set_defaults(func=cmd_qbf_add)
 p=sp.add_parser('self-test'); p.set_defaults(func=cmd_self_test)
 a=ap.parse_args(); a.func(a)


if __name__ == "__main__":
 main()
