#!/usr/bin/env python3
from collections import Counter
from pathlib import Path
from translation_common import load_jsonl
rows=load_jsonl(Path('translations/tr_TR.jsonl'))
files=Counter(r['file'] for r in rows)
print(f"Toplam kayıt: {len(rows)}")
print(f"MSBT dosyası: {len(files)}")
print(f"Kontrol tokenlı kayıt: {sum(bool(r['control_tokens']) for r in rows)}")
print(f"Çok satırlı çeviri: {sum('\n' in r['translation'] for r in rows)}")
for f,n in sorted(files.items()): print(f"  {f}: {n}")
