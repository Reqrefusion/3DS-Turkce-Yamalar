#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Basit CSV çeviri arayüzü. Python Tkinter; CSV UTF-8 BOM ve satır sonları korunur."""
import csv,tkinter as tk
from tkinter import filedialog,messagebox,ttk
from pathlib import Path

class Editor:
    def __init__(self,window):
        self.w=window;self.w.title('Zeus Quest — Türkçe Çeviri Editörü');self.w.geometry('1050x780')
        self.rows=[];self.columns=[];self.filename=None;self.pos=0
        bar=ttk.Frame(window,padding=8);bar.pack(fill='x')
        for title,fn in [('CSV Aç',self.open),('Kaydet (Ctrl+S)',self.save),('Önceki',self.prev),('Sonraki',self.next),('Boş Çeviriye Git',self.next_empty)]:
            ttk.Button(bar,text=title,command=fn).pack(side='left',padx=4)
        line=ttk.Frame(window,padding=(10,6));line.pack(fill='x')
        ttk.Label(line,text='Ara:').pack(side='left');self.query=tk.StringVar()
        ttk.Entry(line,textvariable=self.query,width=60).pack(side='left',fill='x',expand=True,padx=6)
        ttk.Button(line,text='Bul',command=self.find).pack(side='left')
        self.status=ttk.Label(window,text='CSV seçin',padding=8);self.status.pack(anchor='w')
        ttk.Label(window,text='Kaynak metin (salt okunur)',padding=(10,7)).pack(anchor='w')
        self.source=tk.Text(window,height=11,wrap='word',font=('Arial',12));self.source.pack(fill='both',expand=True,padx=10)
        self.source.config(state='disabled')
        ttk.Label(window,text='Türkçe çeviri (düzenlenebilir)',padding=(10,7)).pack(anchor='w')
        self.target=tk.Text(window,height=11,wrap='word',font=('Arial',12));self.target.pack(fill='both',expand=True,padx=10,pady=(0,12))
        self.w.bind('<Control-s>',lambda e:self.save());self.w.bind('<Control-Right>',lambda e:self.next());self.w.bind('<Control-Left>',lambda e:self.prev())
        self.w.protocol('WM_DELETE_WINDOW',self.quit)
    def commit(self):
        if self.rows:self.rows[self.pos]['turkce']=self.target.get('1.0','end-1c')
    def show(self):
        if not self.rows:return
        r=self.rows[self.pos]
        self.status.config(text=f'{self.pos+1:,} / {len(self.rows):,}   |   {r.get("id","")}    |    {self.filename.name}')
        self.source.config(state='normal');self.source.delete('1.0','end');self.source.insert('1.0',r['kaynak_metin']);self.source.config(state='disabled')
        self.target.delete('1.0','end');self.target.insert('1.0',r.get('turkce',''))
    def open(self):
        f=filedialog.askopenfilename(filetypes=[('CSV', '*.csv')]);
        if not f:return
        if self.filename and not messagebox.askyesno('Dosya değiştirme','Değişiklikleri kaydettiğinizden emin misiniz?'):return
        try:
            with open(f,encoding='utf-8-sig',newline='') as stream:
                r=csv.DictReader(stream);self.rows=list(r);self.columns=r.fieldnames
            if not self.rows or not self.columns or not {'kaynak_metin','turkce'}.issubset(self.columns):
                raise ValueError('kaynak_metin ve turkce sütunları gerekli')
            self.filename=Path(f);self.pos=0;self.show()
        except Exception as e:messagebox.showerror('CSV açılamadı',str(e))
    def save(self):
        if not self.rows:return
        self.commit()
        try:
            with open(self.filename,'w',encoding='utf-8-sig',newline='') as out:
                wr=csv.DictWriter(out,fieldnames=self.columns,lineterminator='\r\n',extrasaction='ignore');wr.writeheader();wr.writerows(self.rows)
            self.status.config(text=self.status.cget('text')+' — KAYDEDİLDİ')
        except Exception as e:messagebox.showerror('Kaydedilemedi',str(e))
    def move(self,step):
        if not self.rows:return
        self.commit();self.pos=max(0,min(len(self.rows)-1,self.pos+step));self.show()
    def next(self):self.move(1)
    def prev(self):self.move(-1)
    def next_empty(self):
        if not self.rows:return
        self.commit()
        for i in list(range(self.pos+1,len(self.rows)))+list(range(0,self.pos+1)):
            if not self.rows[i].get('turkce','').strip():self.pos=i;self.show();return
        messagebox.showinfo('Bitti','Bütün satırlar doldurulmuş.')
    def find(self):
        if not self.rows:return
        self.commit();q=self.query.get().lower().strip()
        if not q:return
        for i in list(range(self.pos+1,len(self.rows)))+list(range(0,self.pos+1)):
            if q in self.rows[i]['kaynak_metin'].lower() or q in self.rows[i].get('turkce','').lower():
                self.pos=i;self.show();return
        messagebox.showinfo('Arama','Eşleşme bulunamadı.')
    def quit(self):
        if self.filename and not messagebox.askyesno('Çıkış','Değişiklikleri kaydettiğinizden emin misiniz?'):return
        self.w.destroy()

if __name__=='__main__':
    root=tk.Tk();Editor(root);root.mainloop()
