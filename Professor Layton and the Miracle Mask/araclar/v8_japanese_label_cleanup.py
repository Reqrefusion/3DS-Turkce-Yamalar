from pathlib import Path
import csv,json,re
ROOT=Path('/mnt/data/Layton_TR_Final_v8'); p=ROOT/'ceviri/layton_tr.csv'
MAP={
'レイトン':'Layton','ルーク':'Luke','レミ':'Emmy',
'ナゾーバ':'Elizabeth','バスカル':'Pascal','グロリア':'Gloria','パンチョン':'Waltham','マカロン':'Bonnie',
'フランキ':'Frankie','ラプンシュカ':'Rapunska','セレナ':'Serena','ユーミン':'Yuming','ヌーデン':'Mordaunt',
'コッペリア':'Coppelia','ポリス':'Polis','ヤッタイ':'Jean-Paul','タニア':'Tania','シャロア':'Angela',
'ニルス':'Nils','パック':'Puck','ジャグラー':'Juggles','ミカ':'Mika','オルトビルセン':'Rhys Williams',
'ブルーマイル':'Bloom','シバロフ':'Sheffield','グロスキー':'Grosky','オージー':'Beaufort','トリッキー':'Yukkles',
'コマーニ無':'Bungle','コマーニ有':'Bungle','ナルキス':'Narcisse','ギラン':'Drake','ダンチョー':'Sirk Müdürü',
'チルチル':'Hannibal','モミノキー':'Tannenbaum','ハインリヒ':'Heinrich','ローラン':'Roland','ダルストン':'Dalston',
'グスタフ':'Gustav','マーフィー':'Murphy','ハンナ':'Hannah','ヘンリー':'Henry','ブロネフ':'Bronev','デスコール':'Descole',
'アルダス':'Aldus','ルシール':'Lucille','ランド':'Randall','ランドの母':'Bayan Ascot',
'ヤングランド':'Genç Randall','ヤングシャロア':'Genç Angela','ヤングレイトン':'Genç Layton','ヤングヘンリー':'Genç Henry',
'ポリス②':'Polis 2','ポリス③':'Polis 3','アイテム':'Eşya','コイン':'İpucu Parası',
'茶ウサルーク':'Luke (Kahve)','白ウサルーク':'Luke (Beyaz)','９１０３・・・':'9103...','[不要/ふよう]':'[Kullanılmıyor]',
}
with p.open(encoding='utf-8-sig',newline='') as f:
 rd=csv.DictReader(f); fields=rd.fieldnames; rows=list(rd)
changes=[]
for r in rows:
 o=r['original']
 if o in MAP and r['translation']!=MAP[o]:
  b=r['translation']; r['translation']=MAP[o]
  changes.append({'file':r['file'],'id':r['id'],'source_label':o,'before':b,'after':MAP[o],
                  'reason':'İngilizce kaynak/diyalog içindeki resmi yerelleştirilmiş ad veya Türkçe UI etiketiyle tutarlılaştırıldı.'})
for out in [p,ROOT/'ceviri/CEVIRI_KOLAY.csv']:
 with out.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
with (ROOT/'ceviri/layton_tr.jsonl').open('w',encoding='utf-8') as f:
 for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
rep=ROOT/'raporlar/V8_JAPONCA_ETIKET_TEMIZLIGI.csv'
with rep.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['file','id','source_label','before','after','reason']);w.writeheader();w.writerows(changes)
print('changed labels/ui',len(changes),rep)
