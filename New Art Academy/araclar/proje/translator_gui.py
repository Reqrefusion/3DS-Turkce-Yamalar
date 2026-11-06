#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Side-by-side multilingual TSV editor for New Art Academy localization."""
from __future__ import annotations
import csv
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

LANG_COLUMNS = [
    ("source_fr", "Français"),
    ("source_de", "Deutsch"),
    ("source_es", "Español"),
    ("source_it", "Italiano"),
    ("source_nl", "Nederlands"),
    ("source_pt", "Português"),
    ("source_ru", "Русский"),
]


def unescape_text(s):
    out=[]; i=0; mp={'n':'\n','r':'\r','t':'\t','0':'\0','\\':'\\'}
    while i<len(s):
        if s[i]=='\\' and i+1<len(s) and s[i+1] in mp:
            out.append(mp[s[i+1]]); i+=2
        else:
            out.append(s[i]); i+=1
    return ''.join(out)


def escape_text(s):
    out=[]
    for ch in s:
        out.append({'\\':'\\\\','\n':'\\n','\r':'\\r','\t':'\\t','\0':'\\0'}.get(ch,ch))
    return ''.join(out)


class App:
    def __init__(self, root, filename=None):
        self.root=root
        self.root.title('New Art Academy - Çok Dilli → Türkçe Çeviri Editörü')
        self.rows=[]; self.path=None; self.i=0; self.loading=False
        self.info=tk.StringVar(); self.search=tk.StringVar(); self.status=tk.StringVar()

        top=tk.Frame(root); top.pack(fill='x', padx=8, pady=6)
        tk.Button(top,text='TSV Aç',command=self.open_file).pack(side='left')
        tk.Button(top,text='Kaydet',command=self.save).pack(side='left',padx=4)
        tk.Button(top,text='Önceki',command=lambda:self.go(-1)).pack(side='left',padx=(18,2))
        tk.Button(top,text='Sonraki',command=lambda:self.go(1)).pack(side='left')
        tk.Button(top,text='Sonraki Boş',command=self.next_empty).pack(side='left',padx=4)
        tk.Entry(top,textvariable=self.search,width=28).pack(side='left',padx=(18,2),fill='x',expand=True)
        tk.Button(top,text='Ara',command=self.find).pack(side='left')

        tk.Label(root,textvariable=self.info,anchor='w').pack(fill='x',padx=8)

        body=tk.PanedWindow(root,orient='horizontal',sashrelief='raised',sashwidth=5)
        body.pack(fill='both',expand=True,padx=8,pady=6)

        lf=tk.LabelFrame(body,text='English / İngilizce kaynak (salt okunur)')
        mf=tk.LabelFrame(body,text='Diğer resmi diller (salt okunur)')
        rf=tk.LabelFrame(body,text='Türkçe — yalnız bu alanı düzenleyin')
        body.add(lf,stretch='always',minsize=280)
        body.add(mf,stretch='always',minsize=380)
        body.add(rf,stretch='always',minsize=320)

        self.src=tk.Text(lf,wrap='word',undo=False)
        self.src.pack(fill='both',expand=True)

        mid_wrap=tk.Frame(mf); mid_wrap.pack(fill='both',expand=True)
        self.refs=tk.Text(mid_wrap,wrap='word',undo=False)
        ref_scroll=tk.Scrollbar(mid_wrap,command=self.refs.yview)
        self.refs.configure(yscrollcommand=ref_scroll.set)
        self.refs.pack(side='left',fill='both',expand=True)
        ref_scroll.pack(side='right',fill='y')
        self.refs.tag_configure('lang',font=('TkDefaultFont',10,'bold'))

        self.tr=tk.Text(rf,wrap='word',undo=True)
        self.tr.pack(fill='both',expand=True)
        self.tr.bind('<<Modified>>',self.modified)

        bot=tk.Frame(root); bot.pack(fill='x',padx=8,pady=(0,8))
        tk.Label(bot,textvariable=self.status,anchor='w').pack(side='left',fill='x',expand=True)
        tk.Button(bot,text='Kaydet + Sonraki',command=self.save_next).pack(side='right')
        root.protocol('WM_DELETE_WINDOW',self.close)
        if filename and Path(filename).exists():
            self.load(Path(filename))

    def open_file(self):
        f=filedialog.askopenfilename(filetypes=[('TSV','*.tsv'),('All files','*.*')])
        if f: self.load(Path(f))

    def load(self,path):
        with path.open('r',encoding='utf-8-sig',newline='') as f:
            self.rows=list(csv.DictReader(f,delimiter='\t'))
        if not self.rows:
            messagebox.showerror('Hata','TSV boş veya okunamadı.'); return
        required={'file','id','source_en','tr'}
        if not required.issubset(self.rows[0].keys()):
            messagebox.showerror('Hata','TSV gerekli sütunları içermiyor: file, id, source_en, tr'); return
        self.path=path; self.i=0
        self.root.title(f'New Art Academy - Çok Dilli → TR — {path.name}')
        self.show()

    def store_current(self):
        if not self.rows or self.loading: return
        self.rows[self.i]['tr']=escape_text(self.tr.get('1.0','end-1c'))

    def show(self):
        if not self.rows: return
        self.loading=True
        r=self.rows[self.i]

        self.src.config(state='normal')
        self.src.delete('1.0','end')
        self.src.insert('1.0',unescape_text(r.get('source_en','')))
        self.src.config(state='disabled')

        self.refs.config(state='normal')
        self.refs.delete('1.0','end')
        available=0
        for col,label in LANG_COLUMNS:
            val=unescape_text(r.get(col,'') or '')
            self.refs.insert('end',label+'\n','lang')
            if val:
                available += 1
                self.refs.insert('end',val+'\n\n')
            else:
                self.refs.insert('end','— Bu satır/dosya için kaynak yok veya resmi çeviri boş. —\n\n')
        self.refs.config(state='disabled')

        self.tr.delete('1.0','end')
        self.tr.insert('1.0',unescape_text(r.get('tr','')))
        self.tr.edit_modified(False)

        done=sum(1 for x in self.rows if x.get('tr','').strip())
        self.info.set(
            f"{self.i+1}/{len(self.rows)}  |  {r.get('file')}  |  ID {r.get('id')}  |  "
            f"{r.get('format','')}  |  diğer dil referansı: {available}/7"
        )
        self.status.set(
            f"Çevrilen: {done}/{len(self.rows)} — [f2], [], %s gibi kontrol etiketlerini koruyun. "
            "Ç Ğ İ Ö Ş Ü ç ğ ı ö ş ü doğrudan yazılabilir."
        )
        self.loading=False

    def modified(self,event=None):
        if not self.loading:
            self.store_current(); self.tr.edit_modified(False)

    def go(self,delta):
        if not self.rows:return
        self.store_current(); self.i=max(0,min(len(self.rows)-1,self.i+delta)); self.show()

    def next_empty(self):
        if not self.rows:return
        self.store_current()
        for k in list(range(self.i+1,len(self.rows)))+list(range(0,self.i+1)):
            if not self.rows[k].get('tr','').strip():
                self.i=k; self.show(); return
        messagebox.showinfo('Tamam','Boş Türkçe satır kalmadı.')

    def find(self):
        q=self.search.get().casefold().strip()
        if not q or not self.rows:return
        self.store_current()
        cols=['file','source_en','tr']+[x[0] for x in LANG_COLUMNS]
        for k in list(range(self.i+1,len(self.rows)))+list(range(0,self.i+1)):
            r=self.rows[k]
            hay='\n'.join(unescape_text(r.get(c,'') or '') for c in cols).casefold()
            if q in hay:
                self.i=k; self.show(); return
        messagebox.showinfo('Arama','Eşleşme bulunamadı.')

    def save(self):
        if not self.path or not self.rows:return
        self.store_current(); fields=list(self.rows[0].keys())
        with self.path.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields,delimiter='\t'); w.writeheader(); w.writerows(self.rows)
        self.status.set('Kaydedildi: '+str(self.path))

    def save_next(self):
        self.save(); self.go(1)

    def close(self):
        if self.rows and messagebox.askyesno('Çıkış','Çıkmadan önce TSV kaydedilsin mi?'):
            self.save()
        self.root.destroy()


if __name__=='__main__':
    root=tk.Tk(); root.geometry('1540x760')
    default=sys.argv[1] if len(sys.argv)>1 else ('translations_tr.tsv' if Path('translations_tr.tsv').exists() else None)
    App(root,default); root.mainloop()
