#!/usr/bin/env python3
from pathlib import Path
import sys, tempfile, shutil, subprocess, json
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'font'))
from xfsa_extract import parse
from xfsa_repack import repack

def extract_xs(fa,out):
    blob=Path(fa).read_bytes(); _,files=parse(str(fa)); c=0
    for name,pos,size,idx in files:
        n=name.replace('\\','/')
        if n.startswith('txt/uk/') and n.lower().endswith('.xs'):
            rel=n[len('txt/uk/'):]; dst=out/rel; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(blob[pos:pos+size]); c+=1
    if not c: raise SystemExit('txt/uk/*.xs bulunamadı; doğru lt5_uk.fa dosyasını seçin.')
    return c

def main():
    import argparse
    ap=argparse.ArgumentParser(description='XFSA lt5_uk.fa içine Türkçe XSCR projesini güvenli biçimde enjekte eder.')
    ap.add_argument('clean_fa'); ap.add_argument('project'); ap.add_argument('output_fa')
    ap.add_argument('--report',default=None)
    a=ap.parse_args()
    with tempfile.TemporaryDirectory(prefix='layton_tr_') as td:
        td=Path(td); src=td/'src'; out=td/'out'; src.mkdir()
        count=extract_xs(Path(a.clean_fa),src)
        cmd=[sys.executable,str(HERE/'xs'/'arac'/'layton_xs_tool.py'),'inject',str(src),str(a.project),str(out),'--compression','original','--encoding-policy','turkish-font','--report',str(td/'xs_report.json')]
        subprocess.run(cmd,check=True)
        reps={f'txt/uk/{p.relative_to(out).as_posix()}':p for p in out.rglob('*.xs')}
        stat=repack(str(a.clean_fa),reps,str(a.output_fa))
        # re-open and verify member count and replacement existence
        _,files=parse(str(a.output_fa)); names={x[0].replace('\\','/') for x in files}
        missing=[n for n in reps if n not in names]
        if missing: raise SystemExit(f'Yeniden paketleme doğrulaması başarısız: {missing[:3]}')
        report={'xs_files':count,'replaced':len(reps),'output':str(a.output_fa),'xfsa_files':len(files),'repack':stat,'xs_report':json.loads((td/'xs_report.json').read_text(encoding='utf-8'))}
        rp=Path(a.report) if a.report else Path(str(a.output_fa)+'.json')
        rp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'ok':True,'xs':count,'output':str(a.output_fa),'report':str(rp)},ensure_ascii=False))
if __name__=='__main__': main()
