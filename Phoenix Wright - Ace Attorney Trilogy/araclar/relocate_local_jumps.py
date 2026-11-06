"""Relocate native page-local conditional jumps onto translated command anchors."""
import difflib
import struct

IGNORED = {1,3,4,11,12,127}

def relocate(native, translated, schema, limit, reader):
    old_count, old_pages = reader(native,schema,limit)
    new_count, new_pages = reader(translated,schema,limit)
    if old_count!=new_count or set(old_pages)!=set(new_pages):
        raise ValueError('Native and translated page tables are incompatible')
    count = struct.unpack_from('<I',native)[0]
    old_offsets = struct.unpack_from('<'+'I'*count,native,4)
    new_offsets = struct.unpack_from('<'+'I'*count,translated,4)
    fixed = bytearray(translated)
    checks, unresolved, edited = [], [], set()
    maps = {}
    for page in sorted(old_pages.keys() & new_pages.keys()):
        old, new = old_pages[page], new_pages[page]
        ac = [c for c in old if c[0] not in IGNORED]
        bc = [c for c in new if c[0] not in IGNORED]
        mapping = {}
        if [c[0] for c in ac] == [c[0] for c in bc]:
            mapping.update({a[2]:b for a,b in zip(ac,bc)})
        else:
            def signature(c):
                code,args,_ = c
                if code==53 and not args[0]&128:
                    return code,args[0]
                return code,args
            # Unique local conditions are hard boundaries. A global greedy
            # match can otherwise align repeated commands across the branch.
            hard=[]
            for i,c in enumerate(ac):
                if c[0]!=53 or c[1][0]&128:
                    continue
                old_hits=[k for k,x in enumerate(ac) if x[0]==53 and x[1][0]==c[1][0]]
                new_hits=[k for k,x in enumerate(bc) if x[0]==53 and x[1][0]==c[1][0]]
                if len(old_hits)==len(new_hits)==1:
                    hard.append((i,new_hits[0]))
            if any(a[1]>=b[1] for a,b in zip(hard,hard[1:])):
                raise ValueError(f'Reordered unique conditions in page {page}')
            borders=[(-1,-1),*hard,(len(ac),len(bc))]
            for (old_lo,new_lo),(old_hi,new_hi) in zip(borders,borders[1:]):
                aa=ac[old_lo+1:old_hi]
                bb=bc[new_lo+1:new_hi]
                matches=difflib.SequenceMatcher(None,list(map(signature,aa)),
                              list(map(signature,bb)),autojunk=False)
                for a,b,size in matches.get_matching_blocks():
                    mapping.update({aa[a+i][2]:bb[b+i] for i in range(size)})
            mapping.update({ac[a][2]:bc[b] for a,b in hard})
        # Presentation anchors are matched within neighboring control anchors.
        for k in range(len(ac)+1):
            left = ac[k-1] if k else None
            right = ac[k] if k<len(ac) else None
            if left and left[2] not in mapping:
                continue
            if right and right[2] not in mapping:
                continue
            lo = left[2] if left else -1
            hi = right[2] if right else 1<<60
            nlo = mapping[left[2]][2] if left else -1
            nhi = mapping[right[2]][2] if right else 1<<60
            aa = [c for c in old if lo<c[2]<hi and c[0] in IGNORED and c[0] not in {1,127}]
            bb = [c for c in new if nlo<c[2]<nhi and c[0] in IGNORED and c[0] not in {1,127}]
            if [c[0] for c in aa] == [c[0] for c in bb]:
                mapping.update({a[2]:b for a,b in zip(aa,bb)})
            else:
                sm = difflib.SequenceMatcher(None,[(c[0],c[1]) for c in aa],
                          [(c[0],c[1]) for c in bb],autojunk=False)
                for a,b,size in sm.get_matching_blocks():
                    mapping.update({aa[a+i][2]:bb[b+i] for i in range(size)})
        ordered=[mapping[pos][2] for pos in sorted(mapping)]
        if any(a>=b for a,b in zip(ordered,ordered[1:])):
            raise ValueError(f'Ambiguous/nonmonotonic command anchors in page {page}')
        maps[page]=mapping
        bypos = {c[2]:c for c in old}
        ends = {c[2]+2+2*len(c[1]):c for c in old}
        for code,args,pos in old:
            if code!=53 or args[0]&128:
                continue
            reason = None
            dst = old_offsets[page]+(args[1]&0xfffe)
            src_new = mapping.get(pos)
            mapped = mapping.get(dst)
            kind = 'command'
            if mapped:
                new_dst = mapped[2]
            elif dst in ends and ends[dst][2] in mapping:
                prev = mapping[ends[dst][2]]
                new_dst = prev[2]+2+2*len(prev[1])
                kind = 'text_start'
                if struct.unpack_from('<H',native,dst)[0]<128 or struct.unpack_from('<H',translated,new_dst)[0]<128:
                    reason = 'Text anchor does not lead to text'
            else:
                new_dst = None
                reason = 'Unmapped destination'
            if not src_new or src_new[0]!=53 or src_new[1][0]!=args[0]:
                reason = 'Unmapped or different condition'
            if reason:
                unresolved.append(dict(page=page,source_offset=pos-old_offsets[page],
                                       native_target=args[1],reason=reason))
                continue
            relative = new_dst-new_offsets[page]
            if relative<0 or relative>65534 or relative%2:
                raise ValueError('Relocated jump is outside the native operand range')
            value = relative | (args[1]&1)
            current = src_new[1][1]
            if kind=='command' and struct.unpack_from('<H',translated,new_dst)[0]!=bypos[dst][0]:
                raise AssertionError('Destination opcode differs from native anchor')
            if src_new[2] not in edited and current!=value:
                struct.pack_into('<H',fixed,src_new[2]+4,value)
                edited.add(src_new[2])
            checks.append(dict(page=page,source_offset=src_new[2]-new_offsets[page],
              native_target=args[1],previous_target=current,target=value,
              destination_kind=kind,destination_opcode=bypos[dst][0] if kind=='command' else None))
    aliases, alias_errors, alias_changes = [], [], 0
    indexes=range(limit if limit is not None else count)
    for index in indexes:
        if index in old_pages:
            continue
        value=old_offsets[index]
        parent=value>>16
        if parent not in old_pages:
            continue
        dst=old_offsets[parent]+(value&0xfffe)
        mapping=maps[parent]
        cmd=mapping.get(dst)
        kind='command'
        if cmd:
            new_dst=cmd[2]
        else:
            ends={c[2]+2+2*len(c[1]):c for c in old_pages[parent]}
            prev=ends.get(dst)
            if not prev or prev[2] not in mapping:
                alias_errors.append(dict(index=index,parent=parent,native_bias=value&0xfffe))
                continue
            newprev=mapping[prev[2]]
            new_dst=newprev[2]+2+2*len(newprev[1])
            if struct.unpack_from('<H',native,dst)[0]<128 or struct.unpack_from('<H',translated,new_dst)[0]<128:
                alias_errors.append(dict(index=index,parent=parent,native_bias=value&0xfffe))
                continue
            kind='text_start'
        bias=new_dst-new_offsets[parent]
        if not 0<=bias<=65534 or bias%2:
            raise ValueError('Alias bias is outside the native packed range')
        relocated=(parent<<16)|bias|(value&1)
        previous=new_offsets[index]
        if previous>>16 != parent:
            raise ValueError('Packed alias refers to a different parent page')
        if previous!=relocated:
            struct.pack_into('<I',fixed,4+4*index,relocated)
            alias_changes+=1
        aliases.append(dict(index=index,parent=parent,native_bias=value&0xfffe,
                      previous_bias=previous&0xfffe,bias=bias,destination_kind=kind))
    return bytes(fixed),dict(checked_jumps=len(checks),changed_jumps=len(edited),
                            unresolved=unresolved,jumps=checks,checked_aliases=len(aliases),
                            changed_aliases=alias_changes,unresolved_aliases=alias_errors,aliases=aliases)

