#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import io
import threading
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import sf4_tr_tool as core


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Street Fighter 3DS Türkçe Araçları")
        self.geometry("820x560")
        self.minsize(720, 480)

        self.source = tk.StringVar()
        self.workspace = tk.StringVar(value=str(Path.cwd() / "workspace"))
        self.output = tk.StringVar(value=str(Path.cwd() / "patched"))

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)
        frm.rowconfigure(5, weight=1)

        self._row(frm, 0, "Kaynak klasör / ZIP", self.source, self.pick_source)
        self._row(frm, 1, "Çalışma klasörü", self.workspace, self.pick_workspace)
        self._row(frm, 2, "Çıktı klasörü", self.output, self.pick_output)

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(10, 8))
        ttk.Button(btns, text="Kaynağı Kontrol Et", command=lambda: self.run("check")).pack(side="left", padx=4)
        ttk.Button(btns, text="Metin + Resim Çıkar", command=lambda: self.run("extract-all")).pack(side="left", padx=4)
        ttk.Button(btns, text="Türkçeyi Geri Yaz", command=lambda: self.run("build")).pack(side="left", padx=4)

        info = ttk.Label(
            frm,
            text="CSV'lerde tur sütununu, görsellerde *.tur.png dosyalarını düzenleyin. "
                 "Geri yazma işlemi İngilizce dosya adlarını ve ARC yapısını korur.",
            wraplength=760,
        )
        info.grid(row=4, column=0, columnspan=3, sticky="w", pady=(0, 8))

        self.text = tk.Text(frm, wrap="word", height=20)
        self.text.grid(row=5, column=0, columnspan=3, sticky="nsew")
        sb = ttk.Scrollbar(frm, orient="vertical", command=self.text.yview)
        sb.grid(row=5, column=3, sticky="ns")
        self.text.configure(yscrollcommand=sb.set)

    def _row(self, parent, row, label, var, cmd):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", pady=4)
        ttk.Button(parent, text="Seç...", command=cmd).grid(row=row, column=2, padx=(8, 0), pady=4)

    def pick_source(self):
        p = filedialog.askopenfilename(title="Kaynak ZIP seç", filetypes=[("ZIP", "*.zip"), ("Tümü", "*.*")])
        if not p:
            p = filedialog.askdirectory(title="Veya dil klasörlerini içeren klasörü seç")
        if p:
            self.source.set(p)

    def pick_workspace(self):
        p = filedialog.askdirectory(title="Çalışma klasörü")
        if p:
            self.workspace.set(p)

    def pick_output(self):
        p = filedialog.askdirectory(title="Çıktı klasörü")
        if p:
            self.output.set(p)

    def append(self, s):
        self.text.insert("end", s)
        self.text.see("end")

    def run(self, cmd):
        if not self.source.get().strip():
            messagebox.showerror("Eksik", "Kaynak klasör veya ZIP seçin.")
            return
        self.append(f"\n=== {cmd} ===\n")
        t = threading.Thread(target=self._worker, args=(cmd,), daemon=True)
        t.start()

    def _worker(self, cmd):
        argv = [cmd, self.source.get()]
        if cmd == "extract-all":
            argv += [self.workspace.get()]
        elif cmd == "build":
            argv += [self.workspace.get(), self.output.get()]
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                rc = core.main(argv)
            out = buf.getvalue()
            self.after(0, lambda: self.append(out))
            if rc == 0:
                self.after(0, lambda: messagebox.showinfo("Tamam", "İşlem tamamlandı."))
            else:
                self.after(0, lambda: messagebox.showerror("Hata", "İşlem hata ile bitti. Günlüğe bakın."))
        except Exception:
            out = buf.getvalue() + traceback.format_exc()
            self.after(0, lambda: self.append(out))
            self.after(0, lambda: messagebox.showerror("Hata", "Beklenmeyen hata oluştu. Günlüğe bakın."))


if __name__ == "__main__":
    App().mainloop()
