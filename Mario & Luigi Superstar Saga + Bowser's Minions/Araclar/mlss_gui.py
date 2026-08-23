#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from mlss_translate import export_project, seed_tr, build_project, font_report, extract_msg_from_zip, csv_project_check, LANGS

ROOT = Path(__file__).resolve().parent

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MLSS 3DS Türkçe Çeviri Aracı")
        self.geometry("900x650")
        self.minsize(760, 560)
        self.source = tk.StringVar(value="")
        self.csvdir = tk.StringVar(value=str(ROOT / "csv"))
        self.outdir = tk.StringVar(value=str(ROOT / "build"))
        self.base = tk.StringVar(value="EU_en")
        self.slot = tk.StringVar(value="EU_en")
        self.allow_tags = tk.BooleanVar(value=False)
        self._build_ui()

    def _build_ui(self):
        outer=ttk.Frame(self,padding=14);outer.pack(fill="both",expand=True)
        ttk.Label(outer,text="Kaynak oyundaki Msg klasörünü seçin. CSV'ler dil sütunları yan yana olacak şekilde üretilir; TR sütununu düzenleyip Build yapın.",wraplength=840).pack(anchor="w",pady=(0,10))
        form=ttk.Frame(outer);form.pack(fill="x")
        self._path_row(form,0,"Kaynak Msg:",self.source, self.pick_source)
        ttk.Button(form,text="ZIP’ten çıkar…",command=self.pick_zip_extract,width=13).grid(row=0,column=3,padx=(6,0),pady=3)
        self._path_row(form,1,"CSV klasörü:",self.csvdir, self.pick_csv)
        self._path_row(form,2,"Build çıktısı:",self.outdir, self.pick_out)
        opts=ttk.Frame(outer);opts.pack(fill="x",pady=10)
        ttk.Label(opts,text="Temel dil:").grid(row=0,column=0,sticky="w")
        ttk.Combobox(opts,textvariable=self.base,values=LANGS,state="readonly",width=12).grid(row=0,column=1,padx=(5,18))
        ttk.Label(opts,text="Oyunda değiştirilecek slot:").grid(row=0,column=2,sticky="w")
        ttk.Combobox(opts,textvariable=self.slot,values=LANGS,state="readonly",width=12).grid(row=0,column=3,padx=5)
        ttk.Checkbutton(opts,text="Kontrol kodu değişikliklerine izin ver",variable=self.allow_tags).grid(row=1,column=0,columnspan=4,sticky="w",pady=(6,0))
        actions=ttk.Frame(outer);actions.pack(fill="x",pady=(0,10))
        self.buttons=[]
        for text,cmd in [
            ("1) CSV'leri Oluştur / Güncelle", self.do_export),
            ("2) Boş TR'yi İngilizceyle Doldur", self.do_seed),
            ("3) Türkçe Build Oluştur", self.do_build),
            ("CSV Teknik Kontrol", self.do_csv_check),
            ("Font Raporu", self.do_font_report),
        ]:
            b=ttk.Button(actions,text=text,command=cmd);b.pack(side="left",pad=(0,8),pady=4);self.buttons.append(b)
        ttk.Label(outer,text="Önemli: <0E:...> ve <0F:...> etiketleri oyunun renk/ikon/akış kontrol kodlarıdır. Çevirirken silmeyin; yerlerini metne göre taşıyabilirsiniz.",wraplength=840).pack(anchor="w",pady=(0,8))
        logframe=ttk.LabelFrame(outer,text="İşlem günlüğü",padding=6);logframe.pack(fill="both",expand=True)
        self.logbox=tk.Text(logframe,wrap="word",height=18);self.logbox.pack(side="left",fill="both",expand=True)
        sb=ttk.Scrollbar(logframe,orient="vertical",command=self.logbox.yview);sb.pack(side="right",fill="y");self.logbox.configure(yscrollcommand=sb.set)
        self.log("Hazır. Önce Kaynak Msg klasörünü seçin.")

    def _path_row(self,parent,row,label,var,command):
        ttk.Label(parent,text=label,width=15).grid(row=row,column=0,sticky="w",pady=3)
        ttk.Entry(parent,textvariable=var).grid(row=row,column=1,sticky="ew",padx=5,pady=3)
        ttk.Button(parent,text="Seç…",command=command,width=8).grid(row=row,column=2,pady=3)
        parent.columnconfigure(1,weight=1)

    def pick_source(self):
        p=filedialog.askdirectory(title="Msg klasörünü seç")
        if p:self.source.set(p)

    def pick_zip_extract(self):
        z=filedialog.askopenfilename(title="Oyun dil ZIP dosyasını seç",filetypes=[("ZIP dosyası","*.zip"),("Tüm dosyalar","*.*")])
        if not z:
            return
        d=filedialog.askdirectory(title="Msg klasörünün çıkarılacağı klasörü seç")
        if not d:
            return
        try:
            msg=extract_msg_from_zip(Path(z),Path(d))
            self.source.set(str(msg))
            self.log(f"ZIP çıkarıldı: {msg}")
        except Exception as ex:
            messagebox.showerror("ZIP çıkarma hatası",str(ex))
    def pick_csv(self):
        p=filedialog.askdirectory(title="CSV klasörünü seç")
        if p:self.csvdir.set(p)
    def pick_out(self):
        p=filedialog.askdirectory(title="Build çıktı klasörünü seç")
        if p:self.outdir.set(p)

    def log(self,msg):
        self.after(0,lambda: (self.logbox.insert("end",str(msg)+"\n"),self.logbox.see("end")))

    def run_job(self,fn):
        for b in self.buttons:b.configure(state="disabled")
        def worker():
            try:
                fn()
            except Exception as ex:
                self.log("HATA: "+str(ex))
                self.after(0,lambda:messagebox.showerror("Hata",str(ex)))
            finally:
                self.after(0,lambda:[b.configure(state="normal") for b in self.buttons])
        threading.Thread(target=worker,daemon=True).start()

    def source_path(self):
        p=Path(self.source.get().strip())
        if not p.is_dir(): raise ValueError("Geçerli bir Msg klasörü seçin.")
        # User may select the directory above Msg.
        if p.name != "Msg" and (p/"Msg").is_dir(): p=p/"Msg"
        return p

    def do_export(self):
        def job():
            self.log("CSV dışa aktarma başladı…")
            c=export_project(self.source_path(),Path(self.csvdir.get()),True,self.log)
            font_report(self.source_path(),Path(self.csvdir.get())/"_font_report.csv",self.log)
            self.log(f"Tamamlandı: {sum(c.values())} satır, {len(c)} CSV.")
        self.run_job(job)

    def do_seed(self):
        def job():
            n=seed_tr(Path(self.csvdir.get()),"EU_en",True,self.log)
            self.log(f"TR sütununa {n} kaynak metin kopyalandı.")
        self.run_job(job)

    def do_build(self):
        def job():
            self.log("Build başladı…")
            r=build_project(self.source_path(),Path(self.csvdir.get()),Path(self.outdir.get()),self.base.get(),self.slot.get(),self.allow_tags.get(),True,self.log)
            self.log(f"Build tamamlandı: {r['changed']} çevrilmiş metin.")
            self.log(f"Çıktı: {r['output']}")
            if r['warnings']: self.log(f"Uyarı sayısı: {len(r['warnings'])}; build_report.txt dosyasına bakın.")
            self.after(0,lambda:messagebox.showinfo("Tamamlandı",f"Build tamamlandı.\nDeğiştirilen metin: {r['changed']}\nÇıktı: {r['output']}"))
        self.run_job(job)

    def do_csv_check(self):
        def job():
            self.log("CSV teknik kontrolü başladı…")
            total,problems=csv_project_check(Path(self.csvdir.get()),"EU_en")
            if problems:
                self.log(f"CSV teknik kontrolünde {len(problems)} sorun bulundu.")
                for x in problems[:100]: self.log(" - "+x)
                if len(problems)>100: self.log(f"... ve {len(problems)-100} ek sorun")
                self.after(0,lambda:messagebox.showwarning("CSV Teknik Kontrol",f"{len(problems)} sorun bulundu. Ayrıntılar işlem günlüğünde."))
            else:
                self.log(f"CSV teknik kontrolü başarılı: {total} satır temiz.")
                self.after(0,lambda:messagebox.showinfo("CSV Teknik Kontrol",f"Başarılı: {total} satır; şema, kontrol kodu, özel glif ve MSBT parse/render temiz."))
        self.run_job(job)

    def do_font_report(self):
        def job():
            out=Path(self.csvdir.get())/"_font_report.csv"
            font_report(self.source_path(),out,self.log)
        self.run_job(job)

if __name__=="__main__":
    App().mainloop()
