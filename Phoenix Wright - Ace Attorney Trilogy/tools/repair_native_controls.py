#!/usr/bin/env python3
"""Restore original EUR 3DS command operands in a separate translated candidate.
Only pages whose nonpresentation command order matches are edited.
"""
import argparse, hashlib, importlib.util, json, struct, re, os, tempfile
from pathlib import Path
from relocate_local_jumps import relocate

PRESENTATION = {1, 3, 4, 11, 12, 127}

def load_schema(path=None):
    path=Path(path) if path is not None else Path(__file__).with_name('opcodes_3ds.json')
    document=json.loads(path.read_text(encoding='utf-8'))
    raw=document.get('opcodes',document)
    schema={int(k):v for k,v in raw.items()}
    if set(schema)!=set(range(128)):
        raise ValueError('The reviewed opcode schema must define all 128 commands')
    for code,spec in schema.items():
        count=spec.get('count')
        if not isinstance(count,int) or isinstance(count,bool) or not 0<=count<=7:
            raise ValueError(f'Invalid argument count for opcode {code:#x}')
    for code,count in {0x33:5,0x55:2,0x60:4,0x69:2,0x6e:1,0x75:4,0x76:2,0x7f:0}.items():
        if schema[code]['count']!=count:
            raise ValueError('Outdated opcode schema: use opcodes_3ds.json from this tool set')
    digest=hashlib.sha256(bytes(schema[i]['count'] for i in range(128))).hexdigest()
    if digest!='c2ed8597abeeb71fc21728f73c7f116fdbc8df79025170fa66a1b05b87206167':
        raise ValueError('Outdated or unreviewed opcode argument table')
    return schema


def physical_page_limit(game,name,records,names):
    if game!='GS3' or not re.search(r'[bc]_text$',name):
        return None
    base_name=re.sub(r'[bc]_text$','_text',name)
    if base_name not in names:
        return None
    variant=records[2*names.index(name)+1]
    base=records[2*names.index(base_name)+1]
    n=struct.unpack_from('<I',variant)[0]
    if n!=struct.unpack_from('<I',base)[0]:
        return None
    no=struct.unpack_from('<'+'I'*n,variant,4)
    bo=struct.unpack_from('<'+'I'*n,base,4)
    k=n
    while k>0 and no[k-1]==bo[k-1]:
        k-=1
    return k if 0<k<n else None


def pages(data, schema, limit=None):
    if len(data) < 8 or len(data) % 2:
        raise ValueError('Invalid MDT size')
    n = struct.unpack_from('<I', data)[0]
    header = 4+4*n
    if not n or header > len(data):
        raise ValueError('Invalid MDT table')
    if limit is not None and (not isinstance(limit,int) or not 0<limit<=n):
        raise ValueError('Invalid physical page limit')
    offsets = struct.unpack_from('<'+'I'*n, data, 4)
    if limit is not None:
        offsets = offsets[:limit]
    starts = sorted({o for o in offsets if header <= o <= len(data)-2
                     and o % 2 == 0 and struct.unpack_from('<H', data, o)[0] == 0})
    ends = {o: starts[i+1] if i+1<len(starts) else len(data) for i,o in enumerate(starts)}
    if not starts:
        raise ValueError('MDT has no physical page starts')
    result = {}
    for page, start in enumerate(offsets):
        if start not in ends:
            continue
        pos, cmds = start, []
        while pos < ends[start]:
            code = struct.unpack_from('<H', data, pos)[0]
            if code >= 128:
                pos += 2
                continue
            if code not in schema:
                raise ValueError(f'Unknown opcode {code:#x} at {pos:#x}')
            count = schema[code]['count']
            end = pos+2+2*count
            if end > ends[start]:
                raise ValueError(f'Truncated opcode {code:#x} argc={count} at {pos:#x}, end={ends[start]:#x} in page {page}')
            args = struct.unpack_from('<'+'H'*count, data, pos+2) if count else ()
            cmds.append((code, args, pos))
            pos = end
        result[page] = cmds
    return n, result

def restore(original, translated, schema, limit=None):
    # The HD opcode 7F has one operand, but the native 3DS handler at
    # 0x182B28 consumes no operand. Convert the entire HD pair into two
    # native no-ops before walking the native command stream.
    legacy_schema={k:dict(v) for k,v in schema.items()}
    legacy_schema[127]['count']=1
    _, legacy_pages=pages(translated,legacy_schema,limit)
    normalized=bytearray(translated)
    compat=[]
    seen=set()
    for page,cmds in legacy_pages.items():
        for code,args,pos in cmds:
            if code!=127 or pos in seen:
                continue
            if args==(127,):
                seen.add(pos)
                continue
            if args not in [(0,),(2,),(3,)]:
                raise ValueError(f'Unrecognized HD 7F operand at {pos:#x}: {args}')
            normalized[pos+2:pos+4]=b'\x7f\x00'
            seen.add(pos)
            compat.append(dict(page=page,offset=pos,hd_operand=args[0]))
    nc,native=pages(original,schema,limit)
    tc,target=pages(bytes(normalized),schema,limit)
    if nc!=tc:
        raise ValueError('MDT table count differs')
    fixed=bytearray(normalized)
    changes,skipped,pending,allowed,patched=[],[],[],set(),set()
    recode={161:197,236:198,154:194,147:205,155:219,
            228:202,158:201,304:220,163:192}
    for page in sorted(native.keys() & target.keys()):
        a=[c for c in native[page] if c[0] not in PRESENTATION]
        b=[c for c in target[page] if c[0] not in PRESENTATION]
        if [c[0] for c in a]!=[c[0] for c in b]:
            skipped.append(page)
            continue
        for (code,args,_),(_,current,pos) in zip(a,b):
            if args==current or pos in patched:
                continue
            # 48 writes native message x/y fields at structure +44/+46.
            layout=(code==72 and args==(0,142) and
                    current in [(48,167),(85,167),(93,167)])
            repaired=list(current)
            for i,(old,value) in enumerate(zip(args,current)):
                if old==value:
                    continue
                if layout or recode.get(old)==value:
                    repaired[i]=old
                    allowed.update([pos+2+2*i,pos+3+2*i])
                else:
                    pending.append(dict(page=page,offset=pos,opcode=code,
                       argument=i,native_value=old,translated_value=value))
            if tuple(repaired)==current:
                continue
            struct.pack_into('<'+'H'*len(repaired),fixed,pos+2,*repaired)
            patched.add(pos)
            changes.append(dict(page=page,offset=pos,opcode=code,
                name=schema[code]['name'],translated_args=list(current),
                repaired_args=repaired,native_args=list(args),
                reason='native_screen_coordinates' if layout else 'numeric_recode'))
    for c in compat:
        allowed.update([c['offset']+2,c['offset']+3])
    if len(fixed)!=len(translated) or not all(
            a==b or i in allowed for i,(a,b) in enumerate(zip(translated,fixed))):
        raise AssertionError('Changed bytes outside approved fields')
    return bytes(fixed),dict(changed_commands=len(changes),changes=changes,
        compatibility_nops=compat,pending_operands=pending,skipped_pages=skipped,
        native_only_pages=sorted(native.keys()-target.keys()),
        translated_only_pages=sorted(target.keys()-native.keys()))

def _glyphs(data,schema,limit,hd=False):
    counts={code:spec['count'] for code,spec in schema.items()}
    if hd:
        counts[127]=1
    dialect={code:dict(spec,count=counts[code]) for code,spec in schema.items()}
    _,decoded=pages(data,dialect,limit)
    starts=sorted({cmds[0][2] for cmds in decoded.values()})
    glyphs={}
    for i,start in enumerate(starts):
        end=starts[i+1] if i+1<len(starts) else len(data)
        pos=start
        while pos<end:
            code=struct.unpack_from('<H',data,pos)[0]
            if code>=128:
                glyphs[pos]=code
                pos+=2
            else:
                pos+=2+2*counts[code]
        if pos!=end:
            raise ValueError('Script decoding crossed a page boundary')
    return glyphs


def repair_scenario(original,translated,schema=None,limit=None):
    schema=load_schema() if schema is None else schema
    fixed,info=restore(original,translated,schema,limit)
    fixed,flow=relocate(original,fixed,schema,limit,pages)
    if flow['unresolved'] or flow['unresolved_aliases']:
        raise ValueError('Unresolved control-flow anchors')
    if info['native_only_pages'] or info['translated_only_pages']:
        raise ValueError('Native and translated physical pages differ')
    if len(fixed)!=len(translated):
        raise ValueError('Scenario size changed')
    before=_glyphs(translated,schema,limit,hd=True)
    after=_glyphs(fixed,schema,limit)
    if before!=after:
        raise ValueError('Repair changed translated glyphs')
    old_dialect={code:dict(spec) for code,spec in schema.items()}
    old_dialect[127]['count']=1
    _,old_pages=pages(translated,old_dialect,limit)
    _,new_pages=pages(fixed,schema,limit)
    if set(old_pages)!=set(new_pages):
        raise ValueError('Repair changed physical page coverage')
    count=struct.unpack_from('<I',translated)[0]
    old_offsets=struct.unpack_from('<'+'I'*count,translated,4)
    new_offsets=struct.unpack_from('<'+'I'*count,fixed,4)
    for page in old_pages:
        if old_offsets[page]!=new_offsets[page]:
            raise ValueError('Repair moved a physical page')
        old_codes=[(code,pos) for code,args,pos in old_pages[page] if code!=127]
        new_codes=[(code,pos) for code,args,pos in new_pages[page] if code!=127]
        if old_codes!=new_codes:
            raise ValueError('Repair changed native opcode positions')
    info.update(relocation=flow,physical_page_limit=limit,
                validation=dict(text_equal=True,preserved_glyph_words=len(after),
                                size_equal=True,physical_pages_equal=True))
    return fixed,info


def _arguments():
    p = argparse.ArgumentParser(description=__doc__)
    here=Path(__file__).resolve().parent
    p.add_argument('--tool',type=Path,default=here/'aat3ds_tool.py')
    p.add_argument('--schema',type=Path,default=here/'opcodes_3ds.json')
    for key in ['original','translated','output']:
        p.add_argument('--'+key,required=True,type=Path)
    p.add_argument('--build-pack',action='store_true')
    args = p.parse_args()
    if args.output.resolve() in {args.original.resolve(),args.translated.resolve()}:
        p.error('Output must be separate from input folders')
    return args


def _run(args):
    spec=importlib.util.spec_from_file_location('aa',args.tool)
    aa=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(aa)
    schema=load_schema(args.schema)
    opack=(args.original/'pack.dat').read_bytes()
    tpack=(args.translated/'pack.dat').read_bytes()
    oi=aa.parse_pack_inc((args.original/'pack.inc').read_bytes())
    tidata=(args.translated/'pack.inc').read_bytes()
    ti=aa.parse_pack_inc(tidata)
    aa.validate_pack_inc(opack,oi)
    aa.validate_pack_inc(tpack,ti)
    if len(oi)!=len(ti):
        raise ValueError('Pack layouts differ')
    args.output.mkdir(parents=True,exist_ok=True)
    report=dict(issue='https://github.com/Reqrefusion/3DS-Turkce-Yamalar/issues/4',
      original_pack_sha256=hashlib.sha256(opack).hexdigest(),
      translated_pack_sha256=hashlib.sha256(tpack).hexdigest(),runtime_tested=False,games={})
    replacements={}
    for gs,index in [('GS1',58),('GS2',6786),('GS3',9622)]:
        if oi[index]['ident']!=ti[index]['ident']:
            raise ValueError('Pack asset IDs differ')
        ob,_=aa.lz11_decompress(opack,oi[index]['offset'])
        tb,_=aa.lz11_decompress(tpack,ti[index]['offset'])
        native,records=aa.parse_mesall(ob),aa.parse_mesall(tb)
        if len(native)!=len(records) or len(records)!=2*len(aa.GS_NAMES[gs]):
            raise ValueError('Language count differs')
        folder=args.output/'scenarios'/gs
        folder.mkdir(parents=True,exist_ok=True)
        game=[]
        for i,name in enumerate(aa.GS_NAMES[gs]):
            idx=2*i+1
            limit=physical_page_limit(gs,name,native,aa.GS_NAMES[gs])
            try:
                fixed,info=repair_scenario(native[idx],records[idx],schema,limit)
            except ValueError as e:
                raise ValueError(f'{gs}/{name}: {e}') from e
            records[idx]=fixed
            (folder/(name+'.mdt')).write_bytes(fixed)
            game.append(dict(name=name,**info))
        rebuilt=aa.build_mesall(records)
        if aa.parse_mesall(rebuilt)!=records:
            raise ValueError(f'{gs}: language archive round trip failed')
        replacements[index]=rebuilt
        (args.output/(gs+'_mes_all_control_fix.bin')).write_bytes(rebuilt)
        report['games'][gs]=game
        print(gs,'restored commands',sum(f['changed_commands'] for f in game),
              'HD pairs neutralized',sum(len(f['compatibility_nops']) for f in game),
              'unaligned pages',sum(len(f['skipped_pages']) for f in game),flush=True)
    if args.build_pack:
        pack,inc,meta=aa.rebuild_pack_with_inc(tpack,tidata,replacements)
        table=aa.parse_pack_inc(inc)
        aa.validate_pack_inc(pack,table)
        for index,raw in replacements.items():
            got,_=aa.lz11_decompress(pack,table[index]['offset'])
            if got!=raw:
                raise ValueError(f'Pack entry {index} failed its round trip')
        (args.output/'pack.dat').write_bytes(pack)
        (args.output/'pack.inc').write_bytes(inc)
        report['pack']=meta
        report['output_pack_sha256']=hashlib.sha256(pack).hexdigest()
    report['validation']={'text_equal':True,'preserved_glyph_words':sum(f['validation']['preserved_glyph_words'] for fs in report['games'].values() for f in fs),'checked_local_jumps':sum(f['relocation']['checked_jumps'] for fs in report['games'].values() for f in fs),'checked_aliases':sum(f['relocation']['checked_aliases'] for fs in report['games'].values() for f in fs)}
    (args.output/'control_fix_report.json').write_text(
       json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')


def main():
    args=_arguments()
    destination=args.output.resolve()
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError('Use a new or empty output folder; existing results are not overwritten')
    destination.parent.mkdir(parents=True,exist_ok=True)
    # Keep partial output private until every script and pack check succeeds.
    with tempfile.TemporaryDirectory(prefix='.aat_controls_',dir=destination.parent) as staging:
        args.output=Path(staging)
        _run(args)
        if destination.exists():
            destination.rmdir()  # Fails safely if anything appeared in it meanwhile.
        os.replace(staging,destination)


if __name__=='__main__':
    main()


