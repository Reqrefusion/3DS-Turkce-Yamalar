#!/usr/bin/env python3
"""Cave Story 3D TR V7 ikinci manuel geçiş + temel QA.

Kullanım:
  python v7_manual_pipeline.py <ingilizce_data> <v6_veya_v7_yerel_data> [--reports DIR]

Yerel data klasörünü yerinde günceller. manual_review_v7.py idempotenttir; V7 üzerinde
tekrar çalıştırıldığında veri değiştirmez. Ardından yapı, satır uzunluğu, terim ve
görsel biçim QA araçlarını çalıştırır.
"""
from pathlib import Path
import argparse, subprocess, sys

def run(cmd, out=None):
    print('+',' '.join(map(str,cmd)))
    r=subprocess.run([str(x) for x in cmd], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(r.stdout,end='')
    if out: Path(out).write_text(r.stdout,encoding='utf-8')
    if r.returncode: raise SystemExit(r.returncode)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('english_data'); ap.add_argument('localized_data'); ap.add_argument('--reports',default='V7_PIPELINE_RAPORLARI'); a=ap.parse_args()
    tools=Path(__file__).resolve().parent; en=Path(a.english_data); loc=Path(a.localized_data); rep=Path(a.reports); rep.mkdir(parents=True,exist_ok=True)
    run([sys.executable,tools/'manual_review_v7.py',loc],rep/'01_manual_review_v7.txt')
    run([sys.executable,tools/'sjs_structure_qa.py',en,loc],rep/'02_sjs_structure.txt')
    run([sys.executable,tools/'text_layout_qa.py',loc,'--limit','42','-o',rep/'03_text_layout.tsv'],rep/'03_text_layout_summary.txt')
    run([sys.executable,tools/'glossary_qa.py',loc,'-o',rep/'04_glossary.tsv'],rep/'04_glossary_summary.txt')
    run([sys.executable,tools/'image_format_qa.py',en,loc,'-o',rep/'05_image_format.tsv'],rep/'05_image_format_summary.txt')
    run([sys.executable,tools/'english_residue_scanner.py',en,loc,'-o',rep/'06_english_residue.tsv'],rep/'06_english_residue_summary.txt')
    run([sys.executable,tools/'english_residue_review.py',rep/'06_english_residue.tsv','-o',rep/'07_english_residue_review.tsv'],rep/'07_english_residue_review_summary.txt')
    print('V7 pipeline tamamlandı:',rep)
if __name__=='__main__': main()
