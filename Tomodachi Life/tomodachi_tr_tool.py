from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from collections import OrderedDict, defaultdict
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from tomodachi_formats import (
    FormatError, DarcArchive, MsbtFile,
    lz11_decompress, lz11_compress
)

APP_TITLE = "Tomodachi Life TR Translation Tool v3"
LANGS = ["English", "French", "German", "Italian", "Spanish"]
PROJECT_VERSION = 1


def tr_key(archive_rel: str, inner: str, index: int) -> str:
    return f"{archive_rel}||{inner}||{index}"


def split_key(key: str):
    a, i, n = key.rsplit("||", 2)
    return a, i, int(n)


class LRUCache:
    def __init__(self, maxsize=12):
        self.maxsize = maxsize
        self.data = OrderedDict()

    def get(self, key, loader):
        if key in self.data:
            val = self.data.pop(key)
            self.data[key] = val
            return val
        val = loader()
        self.data[key] = val
        while len(self.data) > self.maxsize:
            self.data.popitem(last=False)
        return val

    def clear(self):
        self.data.clear()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1500x900")
        self.minsize(1050, 650)

        self.message_root: Path | None = None
        self.archive_paths: list[str] = []
        self.archive_msbt: dict[str, list[str]] = {}
        self.translations: dict[str, str] = {}
        self.project_path: Path | None = None
        self.dirty = False
        self.cache = LRUCache(10)
        self.current_archive: str | None = None
        self.current_inner: str | None = None
        self.current_msbt: MsbtFile | None = None
        self.current_lang_msbts: dict[str, MsbtFile | None] = {}
        self.current_msg_index: int | None = None
        self.filtered_indices: list[int] = []
        self._loading_target = False

        self.search_var = tk.StringVar()
        self.untranslated_only = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Bir message klasörü açın.")
        self.progress_var = tk.StringVar(value="")

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- UI ----------
    def _build_ui(self):
        top = ttk.Frame(self, padding=(8, 8, 8, 4))
        top.pack(fill="x")
        ttk.Button(top, text="Message klasörü aç", command=self.open_root).pack(side="left")
        ttk.Button(top, text="Proje aç", command=self.open_project).pack(side="left", padx=(6, 0))
        ttk.Button(top, text="Projeyi kaydet", command=self.save_project).pack(side="left", padx=(6, 0))
        ttk.Separator(top, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Label(top, text="English / French / German / Italian / Spanish / Türkçe yan yana").pack(side="left")
        ttk.Button(top, text="Çeviri klasörünü dışa aktar", command=self.export_csv).pack(side="right")
        ttk.Button(top, text="Çeviri klasörünü içe aktar", command=self.import_csv).pack(side="right", padx=(0, 6))
        ttk.Button(top, text="Yamayı oluştur", command=self.build_patch).pack(side="right", padx=(0, 6))

        paned = ttk.Panedwindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=8, pady=4)

        left = ttk.Frame(paned)
        center = ttk.Frame(paned)
        paned.add(left, weight=1)
        paned.add(center, weight=4)

        ttk.Label(left, text="Paket / MSBT").pack(anchor="w")
        self.file_tree = ttk.Treeview(left, show="tree", selectmode="browse")
        y = ttk.Scrollbar(left, orient="vertical", command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=y.set)
        self.file_tree.pack(side="left", fill="both", expand=True)
        y.pack(side="right", fill="y")
        self.file_tree.bind("<<TreeviewSelect>>", self.on_file_select)

        filterbar = ttk.Frame(center)
        filterbar.pack(fill="x", pady=(0, 4))
        ttk.Label(filterbar, text="Ara:").pack(side="left")
        ent = ttk.Entry(filterbar, textvariable=self.search_var)
        ent.pack(side="left", fill="x", expand=True, padx=(5, 8))
        self.search_var.trace_add("write", lambda *_: self.refresh_message_list())
        ttk.Checkbutton(filterbar, text="Sadece çevrilmemiş", variable=self.untranslated_only,
                        command=self.refresh_message_list).pack(side="left")
        ttk.Button(filterbar, text="İngilizceyi hedefe kopyala", command=self.copy_source).pack(side="right", padx=(8, 0))

        # Mesaj listesi: bütün diller aynı satırda yan yana.
        listframe = ttk.Frame(center)
        listframe.pack(fill="both", expand=True)
        cols = ("idx", "label", "English", "French", "German", "Italian", "Spanish", "Turkish")
        self.msg_tree = ttk.Treeview(listframe, columns=cols, show="headings", height=14, selectmode="browse")
        self.msg_tree.heading("idx", text="#")
        self.msg_tree.heading("label", text="Label")
        for lang in LANGS:
            self.msg_tree.heading(lang, text=lang)
        self.msg_tree.heading("Turkish", text="Türkçe")
        self.msg_tree.column("idx", width=55, stretch=False, anchor="e")
        self.msg_tree.column("label", width=190, stretch=False)
        for lang in LANGS:
            self.msg_tree.column(lang, width=300)
        self.msg_tree.column("Turkish", width=320)
        sy = ttk.Scrollbar(listframe, orient="vertical", command=self.msg_tree.yview)
        sx = ttk.Scrollbar(listframe, orient="horizontal", command=self.msg_tree.xview)
        self.msg_tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.msg_tree.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")
        listframe.rowconfigure(0, weight=1)
        listframe.columnconfigure(0, weight=1)
        self.msg_tree.bind("<<TreeviewSelect>>", self.on_message_select)

        # Alt bölümde de bütün diller yan yana.
        editors = ttk.Panedwindow(center, orient="horizontal")
        editors.pack(fill="both", expand=True, pady=(6, 0))
        self.lang_texts = {}
        for lang in LANGS:
            self.lang_texts[lang] = self._editor_panel(editors, lang, editable=False)
        self.source_text = self.lang_texts["English"]
        self.target_text = self._editor_panel(editors, "Türkçe (hedef)", editable=True)
        self.target_text.bind("<FocusOut>", lambda e: self.commit_current(silent=True))
        self.target_text.bind("<Control-s>", lambda e: (self.save_project(), "break"))

        status = ttk.Frame(self, padding=(8, 3, 8, 7))
        status.pack(fill="x")
        ttk.Label(status, textvariable=self.status_var).pack(side="left", fill="x", expand=True)
        ttk.Label(status, textvariable=self.progress_var).pack(side="right")

    def _editor_panel(self, parent, title, editable: bool):
        f = ttk.Frame(parent)
        parent.add(f, weight=1)
        if isinstance(title, tk.StringVar):
            ttk.Label(f, textvariable=title).pack(anchor="w")
        else:
            ttk.Label(f, text=title).pack(anchor="w")
        t = tk.Text(f, wrap="word", undo=editable, height=11)
        s = ttk.Scrollbar(f, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=s.set)
        t.pack(side="left", fill="both", expand=True)
        s.pack(side="right", fill="y")
        if not editable:
            t.configure(state="disabled")
        return t

    def set_readonly_text(self, widget: tk.Text, text: str):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    # ---------- Project/root ----------
    def open_root(self):
        d = filedialog.askdirectory(title="Tomodachi Life message klasörünü seç")
        if not d:
            return
        self.load_root(Path(d))

    def load_root(self, p: Path):
        # Parent seçildiyse message altına in.
        if (p / "message").is_dir() and not list(p.glob("*_EU_English_LZ.bin")):
            p = p / "message"
        archives = sorted(p.rglob("*_EU_English_LZ.bin"))
        if not archives:
            messagebox.showerror(APP_TITLE, "Seçilen klasörde *_EU_English_LZ.bin bulunamadı.")
            return
        if not self.commit_current(silent=False):
            return
        self.message_root = p
        self.cache.clear()
        self.archive_paths = []
        self.archive_msbt = {}
        self.file_tree.delete(*self.file_tree.get_children())
        self.current_archive = self.current_inner = None
        self.current_msbt = None
        self.current_lang_msbts = {}
        self.status_var.set(f"Taranıyor: {p}")
        self.update_idletasks()

        folder_nodes = {}
        total_msbt = 0
        errors = []
        for k, ap in enumerate(archives, 1):
            rel = ap.relative_to(p).as_posix()
            try:
                raw = ap.read_bytes()
                dec = lz11_decompress(raw)
                arc = DarcArchive.parse(dec)
                inner = [x for x in arc.files().keys() if x.lower().endswith('.msbt')]
                self.archive_paths.append(rel)
                self.archive_msbt[rel] = inner
                total_msbt += len(inner)
            except Exception as e:
                errors.append(f"{rel}: {e}")
                continue

            parent = ""
            parts = rel.split('/')
            if len(parts) > 1:
                folder = '/'.join(parts[:-1])
                if folder not in folder_nodes:
                    folder_nodes[folder] = self.file_tree.insert("", "end", text=folder, open=False, tags=("folder",))
                parent = folder_nodes[folder]
            aid = self.file_tree.insert(parent, "end", text=parts[-1], open=False, values=("archive", rel))
            for ip in inner:
                self.file_tree.insert(aid, "end", text=ip, values=("msbt", rel, ip))
            if k % 8 == 0:
                self.progress_var.set(f"{k}/{len(archives)}")
                self.update_idletasks()

        self.progress_var.set("")
        self.status_var.set(f"{len(self.archive_paths)} paket, {total_msbt} MSBT. 5 kaynak dil yan yana hazır.")
        if errors:
            messagebox.showwarning(APP_TITLE, f"{len(errors)} paket okunamadı. İlk hata:\n{errors[0]}")

    def open_project(self):
        f = filedialog.askopenfilename(title="Çeviri projesi aç", filetypes=[("Tomodachi TR project", "*.json"), ("JSON", "*.json")])
        if not f:
            return
        try:
            obj = json.loads(Path(f).read_text(encoding="utf-8"))
            if obj.get("version") != PROJECT_VERSION:
                raise ValueError("Desteklenmeyen proje sürümü")
            self.translations = {str(k): str(v) for k, v in obj.get("translations", {}).items()}
            self.project_path = Path(f)
            self.dirty = False
            hint = obj.get("root_hint")
            if self.message_root is None and hint and Path(hint).is_dir():
                self.load_root(Path(hint))
            self.status_var.set(f"Proje açıldı: {Path(f).name} — {len(self.translations)} çeviri")
            self.refresh_message_list()
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Proje açılamadı:\n{e}")

    def save_project(self):
        if not self.commit_current(silent=False):
            return False
        if self.project_path is None:
            f = filedialog.asksaveasfilename(title="Çeviri projesini kaydet", defaultextension=".json",
                                             filetypes=[("JSON", "*.json")], initialfile="tomodachi_tr_project.json")
            if not f:
                return False
            self.project_path = Path(f)
        obj = {
            "version": PROJECT_VERSION,
            "root_hint": str(self.message_root) if self.message_root else "",
            "translations": self.translations,
        }
        self.project_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        self.dirty = False
        self.status_var.set(f"Proje kaydedildi: {self.project_path.name} — {len(self.translations)} çeviri")
        return True

    # ---------- Loading ----------
    def _archive_path_for_lang(self, archive_rel: str, lang: str) -> Path:
        assert self.message_root is not None
        if lang == "English":
            rel = archive_rel
        else:
            rel = archive_rel.replace("_EU_English_LZ.bin", f"_EU_{lang}_LZ.bin")
        return self.message_root / Path(rel)

    def get_archive(self, archive_rel: str, lang: str) -> DarcArchive:
        key = (archive_rel, lang)
        def loader():
            p = self._archive_path_for_lang(archive_rel, lang)
            if not p.exists():
                raise FileNotFoundError(p)
            raw = p.read_bytes()
            dec = lz11_decompress(raw) if raw[:1] == b'\x11' else raw
            return DarcArchive.parse(dec)
        return self.cache.get(key, loader)

    def get_msbt(self, archive_rel: str, inner: str, lang: str) -> MsbtFile:
        arc = self.get_archive(archive_rel, lang)
        files = arc.files()
        if inner not in files:
            raise KeyError(f"{lang} içinde {inner} yok")
        return MsbtFile(files[inner])

    def on_file_select(self, _event=None):
        sel = self.file_tree.selection()
        if not sel:
            return
        vals = self.file_tree.item(sel[0], "values")
        if not vals or vals[0] != "msbt":
            return
        if not self.commit_current(silent=False):
            return
        archive_rel, inner = vals[1], vals[2]
        try:
            self.current_archive = archive_rel
            self.current_inner = inner
            self.current_msbt = self.get_msbt(archive_rel, inner, "English")
            self.load_all_languages()
            self.current_msg_index = None
            self.refresh_message_list()
            self.status_var.set(f"{archive_rel} → {inner} ({len(self.current_msbt.messages)} mesaj)")
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"MSBT açılamadı:\n{e}")

    def load_all_languages(self):
        """Seçili MSBT'nin mevcut bütün Avrupa dili karşılıklarını yükle."""
        self.current_lang_msbts = {"English": self.current_msbt}
        if not self.current_archive or not self.current_inner:
            return
        for lang in LANGS[1:]:
            try:
                self.current_lang_msbts[lang] = self.get_msbt(self.current_archive, self.current_inner, lang)
            except Exception:
                self.current_lang_msbts[lang] = None

    @staticmethod
    def _message_for_source(msbt: MsbtFile | None, source_msg):
        if msbt is None:
            return None
        if source_msg.index < len(msbt.messages):
            cand = msbt.messages[source_msg.index]
            if cand.label == source_msg.label:
                return cand
        for cand in msbt.messages:
            if cand.label == source_msg.label:
                return cand
        return msbt.messages[source_msg.index] if source_msg.index < len(msbt.messages) else None

    # ---------- Message list/editor ----------
    @staticmethod
    def preview(s: str, limit=120):
        s = s.replace('\r', ' ').replace('\n', ' ↵ ')
        return s if len(s) <= limit else s[:limit-1] + '…'

    def refresh_message_list(self):
        self.msg_tree.delete(*self.msg_tree.get_children())
        self.filtered_indices = []
        if not self.current_msbt or not self.current_archive or not self.current_inner:
            return
        q = self.search_var.get().strip().casefold()
        untranslated = self.untranslated_only.get()
        for m in self.current_msbt.messages:
            key = tr_key(self.current_archive, self.current_inner, m.index)
            target = self.translations.get(key, "")
            if untranslated and target:
                continue
            texts = {}
            for lang in LANGS:
                lm = self._message_for_source(self.current_lang_msbts.get(lang), m)
                texts[lang] = lm.source_markup if lm else ""
            hay = "\n".join([m.label, *texts.values(), target]).casefold()
            if q and q not in hay:
                continue
            self.filtered_indices.append(m.index)
            values = [m.index, m.label] + [self.preview(texts[lang]) for lang in LANGS] + [self.preview(target)]
            self.msg_tree.insert("", "end", iid=str(m.index), values=values)
        total = len(self.current_msbt.messages)
        done = sum(1 for m in self.current_msbt.messages if self.translations.get(tr_key(self.current_archive, self.current_inner, m.index), ""))
        self.progress_var.set(f"{done}/{total} çevrildi")

    def on_message_select(self, _event=None):
        sel = self.msg_tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if self.current_msg_index == idx:
            return
        if not self.commit_current(silent=False):
            return
        self.show_message(idx)

    def show_message(self, idx: int):
        if not self.current_msbt or not self.current_archive or not self.current_inner:
            return
        self.current_msg_index = idx
        msg = self.current_msbt.messages[idx]
        for lang in LANGS:
            lm = self._message_for_source(self.current_lang_msbts.get(lang), msg)
            self.set_readonly_text(self.lang_texts[lang], lm.source_markup if lm else "")

        key = tr_key(self.current_archive, self.current_inner, idx)
        target = self.translations.get(key, "")
        self._loading_target = True
        self.target_text.delete("1.0", "end")
        self.target_text.insert("1.0", target)
        self._loading_target = False

    def commit_current(self, silent=True) -> bool:
        if self.current_msg_index is None or not self.current_msbt or not self.current_archive or not self.current_inner:
            return True
        target = self.target_text.get("1.0", "end-1c")
        idx = self.current_msg_index
        key = tr_key(self.current_archive, self.current_inner, idx)
        if not target:
            if key in self.translations:
                self.translations.pop(key, None)
                self.dirty = True
            return True
        ok, why = self.current_msbt.validate_markup(idx, target)
        if not ok:
            if not silent:
                messagebox.showerror(APP_TITLE, f"Bu çeviri kaydedilemez:\n{why}\n\nKontrol kodlarını ({{TAG_1}} vb.) silmeyin; yerlerini değiştirebilirsiniz.")
            return False
        if self.translations.get(key) != target:
            self.translations[key] = target
            self.dirty = True
        # Listed row visible ise güncelle.
        iid = str(idx)
        if self.msg_tree.exists(iid):
            vals = list(self.msg_tree.item(iid, "values"))
            vals[-1] = self.preview(target)
            self.msg_tree.item(iid, values=vals)
        return True

    def copy_source(self):
        if self.current_msg_index is None or not self.current_msbt:
            return
        text = self.current_msbt.messages[self.current_msg_index].source_markup
        self.target_text.delete("1.0", "end")
        self.target_text.insert("1.0", text)
        self.commit_current(silent=True)

    # ---------- Validation/build ----------
    def validate_all(self) -> tuple[bool, str]:
        if not self.message_root:
            return False, "Önce message klasörünü açın."
        grouped = defaultdict(lambda: defaultdict(dict))
        for key, text in self.translations.items():
            a, inner, idx = split_key(key)
            grouped[a][inner][idx] = text
        for a, inners in grouped.items():
            try:
                arc = self.get_archive(a, "English")
                files = arc.files()
                for inner, mapping in inners.items():
                    if inner not in files:
                        return False, f"MSBT yok: {a} → {inner}"
                    m = MsbtFile(files[inner])
                    for idx, text in mapping.items():
                        if idx >= len(m.messages):
                            return False, f"Index sınır dışı: {a} → {inner} #{idx}"
                        ok, why = m.validate_markup(idx, text)
                        if not ok:
                            return False, f"{a} → {inner} #{idx}: {why}"
            except Exception as e:
                return False, f"{a}: {e}"
        return True, ""

    def build_patch(self):
        if not self.commit_current(silent=False):
            return
        if not self.translations:
            messagebox.showinfo(APP_TITLE, "Henüz kaydedilmiş Türkçe çeviri yok.")
            return
        ok, why = self.validate_all()
        if not ok:
            messagebox.showerror(APP_TITLE, f"Doğrulama başarısız:\n{why}")
            return
        outdir = filedialog.askdirectory(title="Yamalı message dosyalarının çıkış klasörü")
        if not outdir:
            return
        outroot = Path(outdir)
        grouped = defaultdict(lambda: defaultdict(dict))
        for key, text in self.translations.items():
            a, inner, idx = split_key(key)
            grouped[a][inner][idx] = text
        failures = []
        built_count = 0
        for k, (a, inners) in enumerate(sorted(grouped.items()), 1):
            try:
                src = self.message_root / Path(a)
                dec = lz11_decompress(src.read_bytes())
                arc = DarcArchive.parse(dec)
                files = arc.files()
                for inner, mapping in inners.items():
                    msbt = MsbtFile(files[inner])
                    arc.replace_file(inner, msbt.build(mapping))
                darc_blob = arc.build(alignment=0x20)
                lz_blob = lz11_compress(darc_blob)
                dst = outroot / Path(a)
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(lz_blob)
                # Üretileni hemen tekrar açarak bütünlük kontrolü.
                check = DarcArchive.parse(lz11_decompress(dst.read_bytes()))
                for inner in inners:
                    MsbtFile(check.files()[inner])
                built_count += 1
                self.progress_var.set(f"Yama: {k}/{len(grouped)}")
                self.update_idletasks()
            except Exception as e:
                failures.append(f"{a}: {e}")
        self.progress_var.set("")
        if failures:
            messagebox.showerror(APP_TITLE, f"{built_count} paket üretildi, {len(failures)} hata.\nİlk hata:\n{failures[0]}")
        else:
            messagebox.showinfo(APP_TITLE, f"Tamamlandı. {built_count} değiştirilmiş İngilizce paket üretildi.\n\nÇıkış: {outroot}\n\nBu dosyaları RomFS içindeki aynı message yollarına yerleştirin.")
            self.status_var.set(f"Yama oluşturuldu: {outroot}")

    # ---------- Klasör bazlı çeviri tabloları ----------
    @staticmethod
    def _export_relpath(archive_rel: str, inner: str) -> Path:
        """Klasör yapısını korur; gereksiz aynı-ad tekrarını kaldırır.

        Chat/Chat_EU_English_LZ.bin + ArcBase/X.msbt -> Chat/ArcBase/X.csv
        Drama/Drama_Confession_EU_English_LZ.bin + ArcBase/X.msbt
            -> Drama/Drama_Confession/ArcBase/X.csv
        """
        ap = Path(archive_rel)
        suffix = "_EU_English_LZ.bin"
        name = ap.name[:-len(suffix)] if ap.name.endswith(suffix) else ap.stem
        ip = Path(inner).with_suffix(".csv")
        if ap.parent.name == name:
            return ap.parent / ip
        return ap.parent / name / ip

    def export_csv(self):
        if not self.message_root:
            messagebox.showerror(APP_TITLE, "Önce message klasörünü açın.")
            return
        if not self.commit_current(silent=False):
            return
        outdir = filedialog.askdirectory(title="Çeviri klasörünün çıkış yerini seç")
        if not outdir:
            return
        outroot = Path(outdir)
        manifest = {
            "format": "tomodachi-tr-folder-project",
            "version": 3,
            "columns": ["index", "label", "English", "French", "German", "Italian", "Spanish", "Turkish"],
            "files": [],
        }
        rows = 0
        files_written = 0
        try:
            for ai, a in enumerate(self.archive_paths, 1):
                lang_files = {}
                for lang in LANGS:
                    try:
                        lang_files[lang] = self.get_archive(a, lang).files()
                    except Exception:
                        lang_files[lang] = {}

                for inner in self.archive_msbt.get(a, []):
                    em = MsbtFile(lang_files["English"][inner])
                    lang_msbts = {"English": em}
                    for lang in LANGS[1:]:
                        lang_msbts[lang] = MsbtFile(lang_files[lang][inner]) if inner in lang_files[lang] else None

                    # Yalnızca gerçekten metin içeren satırları dışa aktar.
                    # Bazı ArcVoice/yardımcı MSBT'lerde yüzlerce boş label/index vardır;
                    # bunlar çeviri dosyası olarak oluşturulursa CSV'ler boş görünür.
                    export_rows = []
                    for m in em.messages:
                        vals = []
                        for lang in LANGS:
                            lm = self._message_for_source(lang_msbts.get(lang), m)
                            vals.append(lm.source_markup if lm else "")
                        target = self.translations.get(tr_key(a, inner, m.index), "")
                        # Kaynakların hepsi boşsa ve mevcut bir Türkçe çeviri de yoksa
                        # bu satır çevrilebilir bir metin değildir.
                        if not any(v.strip() for v in vals) and not target.strip():
                            continue
                        export_rows.append((m.index, m.label, vals, target))

                    # Tamamen boş MSBT için CSV oluşturma.
                    if not export_rows:
                        continue

                    rel = self._export_relpath(a, inner)
                    dst = outroot / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    with dst.open("w", newline="", encoding="utf-8-sig") as fh:
                        w = csv.writer(fh)
                        w.writerow(["index", "label", *LANGS, "Turkish"])
                        for idx, label, vals, target in export_rows:
                            w.writerow([idx, label, *vals, target])
                            rows += 1
                    manifest["files"].append({
                        "path": rel.as_posix(),
                        "archive": a,
                        "msbt": inner,
                    })
                    files_written += 1
                self.progress_var.set(f"Klasör dışa aktar: {ai}/{len(self.archive_paths)}")
                self.update_idletasks()

            (outroot / "_tomodachi_tr_manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            messagebox.showinfo(
                APP_TITLE,
                f"Tamamlandı.\n\n{files_written} ayrı CSV dosyası\n{rows} metin satırı\n\n"
                f"Boş MSBT ve tamamen boş satırlar otomatik atlandı.\n"
                f"Her dosyada English / French / German / Italian / Spanish / Turkish yan yana.\n\nÇıkış: {outroot}"
            )
            self.status_var.set(f"Çeviri klasörü oluşturuldu: {outroot}")
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Klasör dışa aktarma hatası:\n{e}")
        finally:
            self.progress_var.set("")

    def import_csv(self):
        if not self.message_root:
            messagebox.showerror(APP_TITLE, "Önce message klasörünü açın.")
            return
        d = filedialog.askdirectory(title="Daha önce dışa aktarılan çeviri klasörünü seç")
        if not d:
            return
        root = Path(d)
        manifest_path = root / "_tomodachi_tr_manifest.json"
        if not manifest_path.exists():
            messagebox.showerror(APP_TITLE, "Bu klasörde _tomodachi_tr_manifest.json bulunamadı.\nAracın dışa aktardığı ana klasörü seçin.")
            return
        added = 0
        errors = []
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("format") != "tomodachi-tr-folder-project":
                raise ValueError("Geçersiz çeviri klasörü manifesti")
            msbt_cache = {}
            entries = manifest.get("files", [])
            for fi, ent in enumerate(entries, 1):
                rel = ent["path"]
                a = ent["archive"]
                inner = ent["msbt"]
                src = root / Path(rel)
                if not src.exists():
                    errors.append(f"Dosya yok: {rel}")
                    continue
                k = (a, inner)
                if k not in msbt_cache:
                    msbt_cache[k] = self.get_msbt(a, inner, "English")
                m = msbt_cache[k]
                with src.open("r", newline="", encoding="utf-8-sig") as fh:
                    r = csv.DictReader(fh)
                    required = {"index", "Turkish"}
                    if not required.issubset(set(r.fieldnames or [])):
                        errors.append(f"Sütun eksik: {rel}")
                        continue
                    for line_no, row in enumerate(r, 2):
                        target = row.get("Turkish", "")
                        if not target:
                            continue
                        try:
                            idx = int(row["index"])
                            ok, why = m.validate_markup(idx, target)
                            if not ok:
                                raise ValueError(why)
                            key = tr_key(a, inner, idx)
                            if self.translations.get(key) != target:
                                self.translations[key] = target
                                self.dirty = True
                            added += 1
                        except Exception as e:
                            errors.append(f"{rel}, satır {line_no}: {e}")
                if fi % 20 == 0:
                    self.progress_var.set(f"Klasör içe aktar: {fi}/{len(entries)}")
                    self.update_idletasks()
            self.refresh_message_list()
            # Açık olan satırı da içe aktarılan Türkçe değerle yenile;
            # aksi halde eski/boş editör değeri sonraki commit'te çeviriyi ezebilir.
            if self.current_msg_index is not None and self.current_msbt:
                self.show_message(self.current_msg_index)
            msg = f"{added} Türkçe çeviri içe aktarıldı."
            if errors:
                msg += f"\n{len(errors)} hata/atlanan kayıt. İlk hata: {errors[0]}"
            messagebox.showinfo(APP_TITLE, msg)
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Klasör içe aktarma hatası:\n{e}")
        finally:
            self.progress_var.set("")

    def on_close(self):
        if not self.commit_current(silent=False):
            return
        if self.dirty:
            if messagebox.askyesno(APP_TITLE, "Kaydedilmemiş çeviriler var. Projeyi kaydetmek ister misiniz?"):
                if not self.save_project():
                    return
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
