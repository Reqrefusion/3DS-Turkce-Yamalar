CSV-only araç kullanım özeti

1) Export:
python yww_csv_tool.py export oyun.zip merino.csv

2) QA:
python yww_csv_tool.py qa oyun.zip merino.csv --out qa.json

3) Build:
python yww_csv_tool.py build oyun.zip merino.csv cikti.zip

4) Verify:
python yww_csv_tool.py verify oyun.zip cikti.zip merino.csv --out verify.json

GUI yoktur. Harici Python paketi gerekmez.
