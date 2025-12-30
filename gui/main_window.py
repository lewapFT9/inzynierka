import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import shutil

import utils.utils as utils
from downloader.google_downloader import download_images_google
from downloader.pexels_downloader import download_images_pexels
from downloader.pixabay_downloader import download_images_pixabay
from downloader.unsplash_downloader import download_images_unsplash
from downloader.openverse_downloader import download_images_openverse

from gui.cleaner_window import CleanerWindow
from splitter.splitter import split_images
from resizer.image_resizer import apply_resize_to_folder
from gui.source_selector import SourceSelector

from exceptions.exceptions import (
    RateLimitException,
    TooManyFormatFilteredException,
    TooManyResolutionFilteredException,
    SourceExhaustedException,
    TooManyFilesizeFilteredException,
    DownloadCancelledException
)
from gui.mode_selector import ModeSelectorWindow

import subprocess
import platform
import re

def measure_connection_quality():
    """
    Zwraca tuple:
        (latency_ms, status)
    gdzie status to: "good", "medium", "bad", "no_internet"
    """

    param = "-n" if platform.system().lower() == "windows" else "-c"
    command = ["ping", param, "1", "8.8.8.8"]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return (None, "no_internet")

        # --- PARSING PINGA ---
        out = result.stdout

        # Windows ─ "Average = 32ms"
        # Linux   ─ "time=32.5 ms"
        match = re.search(r"(\d+\.?\d*)\s*ms", out)

        if not match:
            return (None, "good")  # nie udało się odczytać → zakładamy ok

        latency = float(match.group(1))

        # --- OCENA ---
        if latency < 80:
            status = "good"
        elif latency < 200:
            status = "medium"
        else:
            status = "bad"

        return (latency, status)

    except Exception:
        return (None, "no_internet")



class ImageDownloaderGUI:

    def __init__(self, master):
        self.master = master
        master.title("PRACA INŻYNIERSKA")

        # =========================
        #   WYGLĄD / STAŁY ROZMIAR
        # =========================
        self.WINDOW_W = 420
        self.WINDOW_H = 700
        self.master.geometry(f"{self.WINDOW_W}x{self.WINDOW_H}")
        self.master.minsize(self.WINDOW_W, self.WINDOW_H)
        self.master.maxsize(self.WINDOW_W, self.WINDOW_H)
        self.master.resizable(False, False)

        # Kolory (spójnie w całej aplikacji)
        self.C_BG = "#f4f6fb"  # tło okna
        self.C_CARD = "#ffffff"  # tło "kart"
        self.C_ACCENT = "#1976d2"  # akcent (nagłówki)
        self.C_TEXT = "#1f2937"  # tekst
        self.C_MUTED = "#6b7280"  # tekst pomocniczy
        self.C_DANGER = "#d32f2f"  # ostrzegawczy

        self.master.configure(bg=self.C_BG)

        # ttk style
        try:
            style = ttk.Style()
            # na Windows "vista", na Linux/Mac różnie – ustawiamy delikatnie
            style.theme_use(style.theme_use())
            style.configure("TButton", padding=(10, 6))
            style.configure("Accent.TButton", padding=(10, 8))
            style.configure("TProgressbar", thickness=10)
        except Exception:
            pass

        # =========================
        #   STAN / LOGIKA (BEZ ZMIAN)
        # =========================
        self.source_selector_window = None
        self.stop_download = False
        self.download_in_progress = False
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        self.gui_alive = True

        # flaga formatu docelowego (None = brak wymuszonej konwersji)
        self.force_output_format = None
        self.tmp_dir = None

        # dane pobierania
        self.query = None
        self.class_name = None
        self.folder = None
        self.count = None

        # źródła i katalog tymczasowy
        self.available_sources = []
        self.tmp_dir = None
        self.source_selector_window = None

        # flagi sterujące
        self.stop_download = False
        self.download_in_progress = False
        self.gui_alive = True

        # format wyjściowy (konwersja)
        self.force_output_format = None

        # =========================
        #   SCROLLABLE MAIN FRAME
        # =========================
        self.canvas = tk.Canvas(master, bg=self.C_BG, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(master, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.C_BG)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # dopasowanie szerokości wnętrza do canvasa
        def _sync_width(event):
            self.canvas.itemconfig(self.canvas_window, width=event.width)

        self.canvas.bind("<Configure>", _sync_width)

        # przewijanie kółkiem myszy (Windows/Linux/macOS)
        def _on_mousewheel(event):
            if not self.gui_alive:
                return
            # Windows / macOS
            if hasattr(event, "delta") and event.delta:
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            else:
                # Linux (Button-4/Button-5)
                if event.num == 4:
                    self.canvas.yview_scroll(-3, "units")
                elif event.num == 5:
                    self.canvas.yview_scroll(3, "units")

        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.canvas.bind_all("<Button-4>", _on_mousewheel)
        self.canvas.bind_all("<Button-5>", _on_mousewheel)

        self.build_ui()

    # =========================
    #   UI
    # =========================
    def build_ui(self):
        f = self.scrollable_frame  # skrót

        # Helper do "kart" – tylko UI (nie dotyka logiki)
        def card(title: str, subtitle: str = None):
            outer = tk.Frame(f, bg=self.C_BG)
            outer.pack(fill="x", padx=12, pady=8)

            box = tk.Frame(outer, bg=self.C_CARD, padx=14, pady=12)
            box.pack(fill="x")

            tk.Label(
                box,
                text=title,
                font=("Segoe UI", 11, "bold"),
                fg=self.C_ACCENT,
                bg=self.C_CARD
            ).pack(anchor="w")

            if subtitle:
                tk.Label(
                    box,
                    text=subtitle,
                    font=("Segoe UI", 9),
                    fg=self.C_MUTED,
                    bg=self.C_CARD
                ).pack(anchor="w", pady=(2, 10))
            else:
                tk.Frame(box, bg=self.C_CARD, height=10).pack()

            return box

        # ----------------------------
        # GÓRA: POWRÓT
        # ----------------------------
        top = tk.Frame(f, bg=self.C_BG)
        top.pack(fill="x", padx=12, pady=(12, 6))

        self.back_button =  ttk.Button(top, text="Powrót", command=self.return_to_mode_selector)
        self.back_button.pack(fill="x", pady=10)

        # ----------------------------
        # PODSTAWOWE DANE
        # ----------------------------
        c = card("Pobieranie", "Uzupełnij dane wejściowe.")
        tk.Label(c, text="Hasło do wyszukiwania (query):", bg=self.C_CARD, fg=self.C_TEXT).pack(anchor="w")
        self.query_entry = tk.Entry(c, width=40)
        self.query_entry.pack(fill="x", pady=(2, 10))

        tk.Label(c, text="Liczba obrazów:", bg=self.C_CARD, fg=self.C_TEXT).pack(anchor="w")
        self.count_entry = tk.Entry(c, width=10)
        self.count_entry.pack(fill="x", pady=(2, 10))

        tk.Label(c, text="Nazwa klasy (folder):", bg=self.C_CARD, fg=self.C_TEXT).pack(anchor="w")
        self.class_entry = tk.Entry(c, width=20)
        self.class_entry.pack(fill="x", pady=(2, 10))

        self.select_button = ttk.Button(c, text="Wybierz folder docelowy", command=self.choose_folder)
        self.select_button.pack(fill="x", pady=(0, 6))

        self.folder_path = tk.StringVar()
        tk.Label(c, textvariable=self.folder_path, fg=self.C_MUTED, bg=self.C_CARD).pack(anchor="w")

        # ----------------------------
        # PODZIAŁ ZBIORU
        # ----------------------------
        c = card("Podział zbioru", "Wybierz podzbiory i ustaw procenty (suma 100%).")

        tk.Label(c, text="Wybierz podzbiory:", bg=self.C_CARD, fg=self.C_TEXT).pack(anchor="w")
        self.use_train = tk.BooleanVar(value=True)
        self.use_valid = tk.BooleanVar(value=True)
        self.use_test = tk.BooleanVar(value=True)

        def on_subset_toggle():
            # TRAIN
            if not self.use_train.get():
                self.train_scale.set(0)
                self.train_scale.config(state="disabled")
            else:
                self.train_scale.config(state="normal")

            # VALID
            if not self.use_valid.get():
                self.valid_scale.set(0)
                self.valid_scale.config(state="disabled")
            else:
                self.valid_scale.config(state="normal")

            # TEST
            if not self.use_test.get():
                self.test_scale.set(0)
                self.test_scale.config(state="disabled")
            else:
                self.test_scale.config(state="normal")

        tk.Checkbutton(c, text="train", variable=self.use_train, command=on_subset_toggle, bg=self.C_CARD).pack(
            anchor="w")
        tk.Checkbutton(c, text="valid", variable=self.use_valid, command=on_subset_toggle, bg=self.C_CARD).pack(
            anchor="w")
        tk.Checkbutton(c, text="test", variable=self.use_test, command=on_subset_toggle, bg=self.C_CARD).pack(
            anchor="w")

        tk.Label(c, text="Tryb podziału zbioru:", bg=self.C_CARD, fg=self.C_TEXT).pack(anchor="w", pady=(10, 0))
        self.split_mode = tk.StringVar(value="random")

        tk.Radiobutton(c, text="Losowy (random)", variable=self.split_mode, value="random", bg=self.C_CARD).pack(
            anchor="w")
        tk.Radiobutton(c, text="Priorytet kolejności (prioritize)", variable=self.split_mode, value="prioritize",
                       bg=self.C_CARD).pack(anchor="w")

        tk.Label(c, text="Udziały procentowe:", bg=self.C_CARD, fg=self.C_TEXT).pack(anchor="w", pady=(10, 0))

        self.train_scale = tk.Scale(c, from_=0, to=100, orient=tk.HORIZONTAL, label="Train (%)", bg=self.C_CARD)
        self.valid_scale = tk.Scale(c, from_=0, to=100, orient=tk.HORIZONTAL, label="Valid (%)", bg=self.C_CARD)
        self.test_scale = tk.Scale(c, from_=0, to=100, orient=tk.HORIZONTAL, label="Test (%)", bg=self.C_CARD)

        self.train_scale.set(70)
        self.valid_scale.set(20)
        self.test_scale.set(10)

        self.train_scale.pack(fill="x", pady=(4, 4))
        self.valid_scale.pack(fill="x", pady=(4, 4))
        self.test_scale.pack(fill="x", pady=(4, 0))

        # ----------------------------
        # FILTR ROZDZIELCZOŚCI WEJŚCIOWEJ
        # ----------------------------
        c = card("Filtr rozdzielczości (wejściowej)", "Ustaw minimalną i/lub maksymalną rozdzielczość obrazów.")

        # --- MINIMUM ---
        min_frame = tk.Frame(c, bg=self.C_CARD)
        min_frame.pack(fill="x")

        self.min_width_var = tk.StringVar(value="")
        self.min_height_var = tk.StringVar(value="")
        self.no_min_resolution = tk.BooleanVar(value=True)

        tk.Checkbutton(
            min_frame,
            text="Brak minimalnej",
            variable=self.no_min_resolution,
            command=self.update_resolution_fields,
            bg=self.C_CARD
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        tk.Label(min_frame, text="Min szerokość:", bg=self.C_CARD).grid(row=1, column=0, sticky="e", padx=5, pady=2)
        self.min_width_entry = tk.Entry(min_frame, textvariable=self.min_width_var, width=8)
        self.min_width_entry.grid(row=1, column=1, sticky="w")

        tk.Label(min_frame, text="Min wysokość:", bg=self.C_CARD).grid(row=2, column=0, sticky="e", padx=5, pady=2)
        self.min_height_entry = tk.Entry(min_frame, textvariable=self.min_height_var, width=8)
        self.min_height_entry.grid(row=2, column=1, sticky="w")

        # --- MAKSIMUM ---
        max_frame = tk.Frame(c, bg=self.C_CARD)
        max_frame.pack(fill="x", pady=(10, 0))

        self.max_width_var = tk.StringVar(value="")
        self.max_height_var = tk.StringVar(value="")
        self.no_max_resolution = tk.BooleanVar(value=True)

        tk.Checkbutton(
            max_frame,
            text="Brak maksymalnej",
            variable=self.no_max_resolution,
            command=self.update_resolution_fields,
            bg=self.C_CARD
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        tk.Label(max_frame, text="Max szerokość:", bg=self.C_CARD).grid(row=1, column=0, sticky="e", padx=5, pady=2)
        self.max_width_entry = tk.Entry(max_frame, textvariable=self.max_width_var, width=8)
        self.max_width_entry.grid(row=1, column=1, sticky="w")

        tk.Label(max_frame, text="Max wysokość:", bg=self.C_CARD).grid(row=2, column=0, sticky="e", padx=5, pady=2)
        self.max_height_entry = tk.Entry(max_frame, textvariable=self.max_height_var, width=8)
        self.max_height_entry.grid(row=2, column=1, sticky="w")

        self.update_resolution_fields()

        # ----------------------------
        # FILTR ROZMIARU PLIKU (MB)
        # ----------------------------
        c = card("Filtr rozmiaru pliku", "Ustaw minimalny i/lub maksymalny rozmiar pliku (w MB).")

        filesize_frame = tk.Frame(c, bg=self.C_CARD)
        filesize_frame.pack(fill="x")

        self.no_min_filesize = tk.BooleanVar(value=True)
        self.no_max_filesize = tk.BooleanVar(value=True)

        self.min_filesize_var = tk.StringVar(value="")
        self.max_filesize_var = tk.StringVar(value="")

        tk.Checkbutton(
            filesize_frame,
            text="Brak minimalnej",
            variable=self.no_min_filesize,
            command=lambda: self.update_filesize_fields(),
            bg=self.C_CARD
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        tk.Label(filesize_frame, text="Min (MB):", bg=self.C_CARD).grid(row=1, column=0, sticky="e", padx=5, pady=2)
        self.min_filesize_entry = tk.Entry(filesize_frame, textvariable=self.min_filesize_var, width=8)
        self.min_filesize_entry.grid(row=1, column=1, sticky="w")

        tk.Checkbutton(
            filesize_frame,
            text="Brak maksymalnej",
            variable=self.no_max_filesize,
            command=lambda: self.update_filesize_fields(),
            bg=self.C_CARD
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))

        tk.Label(filesize_frame, text="Max (MB):", bg=self.C_CARD).grid(row=3, column=0, sticky="e", padx=5, pady=2)
        self.max_filesize_entry = tk.Entry(filesize_frame, textvariable=self.max_filesize_var, width=8)
        self.max_filesize_entry.grid(row=3, column=1, sticky="w")

        self.update_filesize_fields()

        # ----------------------------
        # SCALING / CROP
        # ----------------------------
        c = card("Zmiana rozdzielczości (wyjściowej)", "Resize lub crop do zadanych wymiarów.")

        self.resize_enabled = tk.BooleanVar(value=True)
        tk.Checkbutton(
            c,
            text="Włącz skalowanie",
            variable=self.resize_enabled,
            command=self.update_resize_fields,
            bg=self.C_CARD
        ).pack(anchor="w")

        self.method_var = tk.StringVar(value="resize")

        self.resize_radio_resize = tk.Radiobutton(
            c, text="Zmień rozmiar", variable=self.method_var, value="resize", bg=self.C_CARD
        )
        self.resize_radio_resize.pack(anchor="w")

        self.resize_radio_crop = tk.Radiobutton(
            c, text="Wytnij środek", variable=self.method_var, value="crop", bg=self.C_CARD
        )
        self.resize_radio_crop.pack(anchor="w")

        size_frame = tk.Frame(c, bg=self.C_CARD)
        size_frame.pack(fill="x", pady=8)

        tk.Label(size_frame, text="Szerokość:", bg=self.C_CARD).grid(row=0, column=0, padx=5, sticky="e")
        self.width_entry = tk.Entry(size_frame, width=6)
        self.width_entry.insert(0, "224")
        self.width_entry.grid(row=0, column=1, sticky="w")

        tk.Label(size_frame, text="Wysokość:", bg=self.C_CARD).grid(row=0, column=2, padx=5, sticky="e")
        self.height_entry = tk.Entry(size_frame, width=6)
        self.height_entry.insert(0, "224")
        self.height_entry.grid(row=0, column=3, sticky="w")

        self.update_resize_fields()

        # ----------------------------
        # FORMATY WEJŚCIOWE
        # ----------------------------
        c = card("Formaty wejściowe", "Wybierz dozwolone formaty obrazów.")

        self.allow_all_formats = tk.BooleanVar(value=True)
        self.allow_jpg = tk.BooleanVar(value=True)
        self.allow_png = tk.BooleanVar(value=True)
        self.allow_gif = tk.BooleanVar(value=True)

        self.jpg_cb = tk.Checkbutton(
            c,
            text="JPG / JPEG",
            variable=self.allow_jpg,
            command=self.update_format_checkboxes,
            bg=self.C_CARD
        )
        self.jpg_cb.pack(anchor="w")

        self.png_cb = tk.Checkbutton(
            c,
            text="PNG",
            variable=self.allow_png,
            command=self.update_format_checkboxes,
            bg=self.C_CARD
        )
        self.png_cb.pack(anchor="w")

        self.gif_cb = tk.Checkbutton(
            c,
            text="GIF",
            variable=self.allow_gif,
            command=self.update_format_checkboxes,
            bg=self.C_CARD
        )
        self.gif_cb.pack(anchor="w")

        self.all_cb = tk.Checkbutton(
            c,
            text="Wszystkie formaty dozwolone",
            variable=self.allow_all_formats,
            command=self.update_format_checkboxes,
            bg=self.C_CARD
        )
        self.all_cb.pack(anchor="w", pady=(6, 0))

        self.update_format_checkboxes()

        # ----------------------------
        # PROGRESS + START
        # ----------------------------
        c = card("Start", "Kliknij, aby rozpocząć pobieranie.")

        self.progress = tk.IntVar()
        self.progress_bar = ttk.Progressbar(c, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.pack(fill="x", pady=(0, 10))

        self.download_button = ttk.Button(c, text="Pobierz obrazy", command=self.start_download)
        self.download_button.pack(fill="x", pady=(0, 8))

        self.stop_button = ttk.Button(c, text="Przerwij pobieranie", command=self.request_stop_download)
        self.stop_button.pack(fill="x")

        # mały odstęp na koniec, żeby dało się ładnie doscrollować
        tk.Frame(f, bg=self.C_BG, height=20).pack()

    # =========================
    #   FORMATY I ROZDZIELCZOŚĆ
    # =========================

    def return_to_mode_selector(self):

        # Zamknij bieżące okno
        self.master.destroy()

        # Utwórz nowe główne okno i pokaż selektor trybu
        new_root = tk.Tk()
        ModeSelectorWindow(new_root)
        new_root.mainloop()


    def validate_positive_int(self, entry_widget, field_name):
        """
        Waliduje dodatnią liczbę całkowitą.
        Zwraca:
            int   → poprawna wartość
            None  → pole puste
            "error" → błąd (wyświetlony komunikat)
        """
        value = entry_widget.get().strip()

        if value == "":
            return None

        try:
            num = int(value)
            if num <= 0:
                raise ValueError
            return num
        except:
            if self.gui_alive:
                self.master.after(0, lambda:
                    messagebox.showerror("Błąd danych",
                                 f"{field_name} musi być dodatnią liczbą całkowitą."))
            return "error"

    def cleanup_tmp_dir(self):
        if self.tmp_dir and os.path.exists(self.tmp_dir):
            try:
                shutil.rmtree(self.tmp_dir)
                print(f"[CLEANUP] Usunięto katalog tymczasowy: {self.tmp_dir}")
            except Exception as e:
                print(f"[CLEANUP] Nie udało się usunąć tmp_dir: {e}")

    def get_resolution_filter_val(self):
        result = {}

        # --- MIN ---
        min_w = min_h = None
        if not self.no_min_resolution.get():  # pole aktywne
            if not self.min_width_var.get().strip():
                if self.gui_alive:
                    self.master.after(0, lambda: messagebox.showerror("Błąd danych", "Pole 'Min szerokość' nie może być puste."))
                return "error"
            if not self.min_height_var.get().strip():
                if self.gui_alive:
                    self.master.after(0, lambda: messagebox.showerror("Błąd danych", "Pole 'Min wysokość' nie może być puste."))
                return "error"

            min_w = self.validate_positive_int(self.min_width_entry, "Minimalna szerokość")
            min_h = self.validate_positive_int(self.min_height_entry, "Minimalna wysokość")
            if min_w == "error" or min_h == "error":
                return "error"

            result["min_w"] = min_w
            result["min_h"] = min_h

        # --- MAX ---
        max_w = max_h = None
        if not self.no_max_resolution.get():  # pole aktywne
            if not self.max_width_var.get().strip():
                if self.gui_alive:
                    self.master.after(0, lambda: messagebox.showerror("Błąd danych", "Pole 'Max szerokość' nie może być puste."))
                return "error"
            if not self.max_height_var.get().strip():
                if self.gui_alive:
                    self.master.after(0, lambda: messagebox.showerror("Błąd danych", "Pole 'Max wysokość' nie może być puste."))
                return "error"

            max_w = self.validate_positive_int(self.max_width_entry, "Maksymalna szerokość")
            max_h = self.validate_positive_int(self.max_height_entry, "Maksymalna wysokość")
            if max_w == "error" or max_h == "error":
                return "error"

            result["max_w"] = max_w
            result["max_h"] = max_h

        # --- WALIDACJA min < max ---
        if min_w is not None and max_w is not None:
            if max_w <= min_w:
                if self.gui_alive:
                    self.master.after(0, lambda: messagebox.showerror("Błąd danych", "Maksymalna szerokość musi być większa niż minimalna."))
                return "error"

        if min_h is not None and max_h is not None:
            if max_h <= min_h:
                if self.gui_alive:
                    self.master.after(0, lambda: messagebox.showerror("Błąd danych", "Maksymalna wysokość musi być większa niż minimalna."))
                return "error"

        if not result:
            return None

        return result

    def get_filesize_filter_val(self):
        result = {}

        min_mb = max_mb = None

        # --- MIN ---
        if not self.no_min_filesize.get():  # jeśli pole aktywne
            raw = self.min_filesize_var.get().strip()
            if not raw:
                if self.gui_alive:
                    self.master.after(
                        0,
                        lambda: messagebox.showerror(
                            "Błąd danych",
                            "Minimalna waga (MB) nie może być pusta."
                        )
                    )
                return "error"

            try:
                raw = raw.replace(",", ".")
                min_mb = float(raw)
                if min_mb <= 0:
                    raise ValueError
            except ValueError:
                if self.gui_alive:
                    self.master.after(
                        0,
                        lambda: messagebox.showerror(
                            "Błąd danych",
                            "Minimalna waga (MB) musi być dodatnią liczbą (np. 0.5)."
                        )
                    )
                return "error"

            result["min_mb"] = min_mb

        # --- MAX ---
        if not self.no_max_filesize.get():  # jeśli pole aktywne
            raw = self.max_filesize_var.get().strip()
            if not raw:
                if self.gui_alive:
                    self.master.after(
                        0,
                        lambda: messagebox.showerror(
                            "Błąd danych",
                            "Maksymalna waga (MB) nie może być pusta."
                        )
                    )
                return "error"

            try:
                raw = raw.replace(",", ".")
                max_mb = float(raw)
                if max_mb <= 0:
                    raise ValueError
            except ValueError:
                if self.gui_alive:
                    self.master.after(
                        0,
                        lambda: messagebox.showerror(
                            "Błąd danych",
                            "Maksymalna waga (MB) musi być dodatnią liczbą (np. 2.5)."
                        )
                    )
                return "error"

            result["max_mb"] = max_mb

        # --- WALIDACJA min < max ---
        if min_mb is not None and max_mb is not None:
            if max_mb <= min_mb:
                if self.gui_alive:
                    self.master.after(
                        0,
                        lambda: messagebox.showerror(
                            "Błąd danych",
                            "Maksymalna waga (MB) musi być większa niż minimalna."
                        )
                    )
                return "error"

        if not result:
            return None

        return result

    def get_target_resize_size_val(self):
        """
        Zwraca (szerokość, wysokość) jeśli skalowanie jest włączone,
        None jeśli jest wyłączone, albo "error" jeśli walidacja nie przeszła.
        """
        if not self.resize_enabled.get():
            return None

        # najpierw sprawdzamy, czy pola nie są puste
        if not self.width_entry.get().strip():
            if self.gui_alive:
                self.master.after(0, lambda: messagebox.showerror("Błąd danych", "Szerokość docelowa nie może być pusta."))
            self.width_entry.focus_set()
            return "error"

        if not self.height_entry.get().strip():
            if self.gui_alive:
                self.master.after(0, lambda: messagebox.showerror("Błąd danych", "Wysokość docelowa nie może być pusta."))
            self.height_entry.focus_set()
            return "error"

        # a dopiero potem używamy wspólnej walidacji liczby dodatniej
        w = self.validate_positive_int(self.width_entry, "Szerokość docelowa")
        h = self.validate_positive_int(self.height_entry, "Wysokość docelowa")

        if w == "error" or h == "error":
            return "error"

        return (w, h)

    def update_format_checkboxes(self):
        if self.allow_all_formats.get():
            self.allow_jpg.set(True)
            self.allow_png.set(True)
            self.allow_gif.set(True)
            self.jpg_cb.config(state="disabled")
            self.png_cb.config(state="disabled")
            self.gif_cb.config(state="disabled")
        else:
            self.jpg_cb.config(state="normal")
            self.png_cb.config(state="normal")
            self.gif_cb.config(state="normal")

    def update_scales(self, changed):
        """Normalizacja trzech suwaków tak, aby suma wynosiła 100%."""
        t = self.train_scale.get()
        v = self.valid_scale.get()
        s = self.test_scale.get()

        total = t + v + s
        if total == 0:
            # zapobiega sytuacji 0/0/0 → ustaw train = 100
            self.train_scale.set(100)
            self.valid_scale.set(0)
            self.test_scale.set(0)
            return

        # Normalizacja — przeskalowanie wartości do 100%
        scale_factor = 100 / total
        t = int(t * scale_factor)
        v = int(v * scale_factor)
        s = 100 - t - v  # gwarancja braku błędów zaokrągleń

        # aby nie wywołać zapętlenia update_scales
        self.train_scale.set(t)
        self.valid_scale.set(v)
        self.test_scale.set(s)

    def get_allowed_input_formats(self):
        # jeśli wszystkie formaty są dozwolone → filtr WYŁĄCZONY
        if self.allow_all_formats.get():
            return None

        allowed = []
        if self.allow_jpg.get():
            allowed += ["jpg", "jpeg"]
        if self.allow_png.get():
            allowed.append("png")
        if self.allow_gif.get():
            allowed.append("gif")

        if not allowed:
            return None

        return [fmt.lower() for fmt in allowed]

    def update_resolution_fields(self):
        # MINIMUM
        if self.no_min_resolution.get():
            self.min_width_entry.config(state="disabled")
            self.min_height_entry.config(state="disabled")
        else:
            self.min_width_entry.config(state="normal")
            self.min_height_entry.config(state="normal")

        # MAXIMUM
        if self.no_max_resolution.get():
            self.max_width_entry.config(state="disabled")
            self.max_height_entry.config(state="disabled")
        else:
            self.max_width_entry.config(state="normal")
            self.max_height_entry.config(state="normal")

    def update_resize_fields(self):
        if self.resize_enabled.get():
            self.resize_radio_resize.config(state="normal")
            self.resize_radio_crop.config(state="normal")
            self.width_entry.config(state="normal")
            self.height_entry.config(state="normal")
        else:
            self.resize_radio_resize.config(state="disabled")
            self.resize_radio_crop.config(state="disabled")
            self.width_entry.config(state="disabled")
            self.height_entry.config(state="disabled")

    def get_resolution_filter(self):
        """Zwraca słownik z filtrami rozdzielczości lub None."""
        result = {}

        # MIN
        if not self.no_min_resolution.get():
            try:
                result["min_w"] = int(self.min_width_var.get()) if self.min_width_var.get() else None
                result["min_h"] = int(self.min_height_var.get()) if self.min_height_var.get() else None
            except ValueError:
                return None

        # MAX
        if not self.no_max_resolution.get():
            try:
                result["max_w"] = int(self.max_width_var.get()) if self.max_width_var.get() else None
                result["max_h"] = int(self.max_height_var.get()) if self.max_height_var.get() else None
            except ValueError:
                return None

        if not any(result.values()):
            return None

        return result

    def get_filesize_filter(self):
        result = {}

        # MIN
        if not self.no_min_filesize.get():
            try:
                result["min_mb"] = float(self.min_filesize_var.get()) if self.min_filesize_var.get() else None
            except ValueError:
                return None

        # MAX
        if not self.no_max_filesize.get():
            try:
                result["max_mb"] = float(self.max_filesize_var.get()) if self.max_filesize_var.get() else None
            except ValueError:
                return None

        if not any(result.values()):
            return None

        return result

    def infer_target_output_format(self):

        allowed = self.get_allowed_input_formats()
        if allowed:
            first = allowed[0].lower()
            if first == "jpeg":
                first = "jpg"
            return first
        return "jpg"

    # =========================
    #   INNE
    # =========================

    def on_close(self):
        if self.download_in_progress:
            if self.gui_alive:
                resp = messagebox.askyesno(
                "Zamykanie aplikacji",
                "Trwa pobieranie.\n\n"
                "Czy chcesz przerwać pobieranie i zamknąć aplikację?"
                )
            else:
                resp = None
            if not resp:
                return

            self.stop_download = True
            self.gui_alive = False

        self.master.destroy()

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Wybierz folder docelowy")
        self.folder_path.set(folder)

    def update_filesize_fields(self):
        if self.no_min_filesize.get():
            self.min_filesize_entry.config(state="disabled")
        else:
            self.min_filesize_entry.config(state="normal")

        if self.no_max_filesize.get():
            self.max_filesize_entry.config(state="disabled")
        else:
            self.max_filesize_entry.config(state="normal")

    def update_progress(self, current, total):
        if not self.gui_alive:
            return

        percent = int((current / total) * 100) if total > 0 else 0

        self.master.after(
            0,
            lambda: self.progress_bar.config(value=percent)
        )

    def get_target_size_if_crop(self):
        if self.method_var.get() != "crop":
            return None

        try:
            w = int(self.width_entry.get())
            h = int(self.height_entry.get())
            return (w, h)
        except:
            return None

    def request_stop_download(self):
        if self.gui_alive:
            resp = messagebox.askyesno(
            "Przerwanie pobierania",
            "Czy na pewno chcesz przerwać pobieranie?\n"
            "Częściowo pobrane pliki zostana usunięte."
            )
        else:
            resp = None
        if resp:
            self.stop_download = True
            if self.gui_alive:
                self.master.after(0, lambda: self.progress_bar.config(value=0))
                self.download_button.config(state="normal")
                self.back_button.config(state="normal")
                self.download_in_progress = False

            print("[STOP] Użytkownik zażądał przerwania pobierania.")

    # =========================
    #   START DOWNLOAD
    # =========================
    def start_download(self):
        if self.gui_alive:
            self.master.after(0, lambda: self.progress_bar.config(value=0))
            self.back_button.config(state="disabled")
        self.stop_download = False
        self.download_in_progress = True


        # ======================================================
        # INTERNET CHECK W WĄTKU (JEDYNA ZMIANA)
        # ======================================================
        def internet_check_worker():
            latency, quality = measure_connection_quality()

            def continue_in_ui():
                # --- SPRAWDZENIE INTERNETU + JAKOŚCI ---
                if quality == "no_internet":
                    if self.gui_alive:
                        messagebox.showerror(
                            "Brak internetu",
                            "Nie wykryto połączenia z internetem.\n"
                            "Sprawdź połączenie i spróbuj ponownie."
                        )
                    self.download_in_progress = False
                    return

                if quality == "bad":
                    if self.gui_alive:
                        resp = messagebox.askyesno(
                            "Słabe połączenie",
                            f"Wykryto słabe połączenie。\n"
                            f"Ping: {latency:.1f} ms.\n"
                            "Przy takim łączu pobieranie może być wolne lub niestabilne.\n\n"
                            "Czy chcesz kontynuować?"
                        )
                    else:
                        resp = None
                    if not resp:
                        self.download_in_progress = False
                        return

                elif quality == "medium":
                    if self.gui_alive:
                        resp = messagebox.askyesno(
                            "Średnia jakość połączenia",
                            f"Ping: {latency:.1f} ms.\n"
                            "Pobieranie może chwilami zwalniać.\n"
                            "Kontynuować?"
                        )
                    else:
                        resp = None
                    if not resp:
                        self.download_in_progress = False
                        return

                # ======================================================
                # OD TEGO MOMENTU KOD JEST IDENTYCZNY JAK U CIEBIE
                # ======================================================

                query = self.query_entry.get().strip()
                class_name = self.class_entry.get().strip()
                folder = self.folder_path.get().strip()
                count = self.count_entry.get().strip()

                # walidacja filtrów rozdzielczości
                res_filter = self.get_resolution_filter_val()
                if res_filter == "error":
                    self.download_in_progress = False
                    return

                # walidacja filtru wagi
                filesize_filter = self.get_filesize_filter_val()
                if filesize_filter == "error":
                    self.download_in_progress = False
                    return

                # walidacja resize/crop
                resize_size = self.get_target_resize_size_val()
                if resize_size == "error":
                    self.download_in_progress = False
                    return

                train_ratio = self.train_scale.get()
                valid_ratio = self.valid_scale.get()
                test_ratio = self.test_scale.get()

                total = train_ratio + valid_ratio + test_ratio
                if total != 100:
                    if self.gui_alive:
                        messagebox.showerror(
                            "Błąd podziału",
                            f"Suma udziałów musi wynosić 100%, a wynosi {total}%."
                        )
                    self.download_in_progress = False
                    return

                subsets = []
                if self.use_train.get():
                    subsets.append("train")
                if self.use_valid.get():
                    subsets.append("valid")
                if self.use_test.get():
                    subsets.append("test")

                if not subsets:
                    if self.gui_alive:
                        messagebox.showerror("Błąd", "Wybierz co najmniej jeden podzbiór.")
                    self.download_button.config(state="normal")
                    self.back_button.config(state="normal")
                    self.download_in_progress = False
                    return

                class_dir = os.path.join(folder, class_name)
                if os.path.exists(class_dir):
                    resp = messagebox.askyesnocancel(
                        "Folder już istnieje",
                        f"Folder zbioru:\n\n{class_dir}\n\njuż istnieje.\n"
                        "TAK = usuń i nadpisz cały zbiór.\n"
                        "NIE = anuluj proces pobierania.\n"
                        "ANULUJ = wróć."
                    )

                    if resp is True:
                        try:
                            import shutil
                            shutil.rmtree(class_dir)
                        except Exception as e:
                            if self.gui_alive:
                                messagebox.showerror(
                                    "Błąd",
                                    f"Nie można usunąć folderu:\n{e}"
                                )
                            self.download_button.config(state="normal")
                            self.back_button.config(state="normal")
                            self.download_in_progress = False
                            return
                    else:
                        self.download_button.config(state="normal")
                        self.back_button.config(state="normal")
                        self.download_in_progress = False
                        return

                if not all([query, count, class_name, folder]):
                    if self.gui_alive:
                        messagebox.showerror("Błąd", "Uzupełnij wszystkie pola.")
                    self.download_in_progress = False
                    return

                try:
                    count = int(count)
                except ValueError:
                    if self.gui_alive:
                        messagebox.showerror(
                            "Błąd",
                            "Liczba obrazów musi być liczbą całkowitą."
                        )
                    self.download_in_progress = False
                    return

                self.query = query
                self.class_name = class_name
                self.folder = folder
                self.count = count

                self.force_output_format = None
                self.download_button.config(state="disabled")
                self.back_button.config(state="disabled")

                self.available_sources = [
                    "google", "pexels", "pixabay", "unsplash", "openverse"
                ]

                def on_source(selected_source):
                    self.source_selector_window = None
                    threading.Thread(
                        target=self.run_download,
                        args=(selected_source,),
                        daemon=True
                    ).start()

                def on_cancel_source():
                    self.source_selector_window = None
                    self.download_button.config(state="normal")
                    self.back_button.config(state="normal")
                    self.download_in_progress = False

                if self.source_selector_window is not None and self.source_selector_window.winfo_exists():
                    self.source_selector_window.lift()
                    self.source_selector_window.focus_force()
                    return

                if self.gui_alive:
                    SourceSelector(
                        self.master,
                        self.available_sources,
                        on_select=on_source,
                        on_cancel=on_cancel_source,
                        confirm_on_close = False
                    )

            if self.gui_alive:
                self.master.after(0, continue_in_ui)

        threading.Thread(
            target=internet_check_worker,
            daemon=True
        ).start()

    # =========================
    #   WŁAŚCIWE POBIERANIE
    # =========================
    def run_download(self, source):
        threading.Thread(target=self._download_thread, args=(source,)).start()

    def _download_thread(self, source):
        query = self.query
        class_name = self.class_name
        folder = self.folder
        expected_count = self.count


        tmp_dir = os.path.join(folder, f"_tmp_{class_name}")
        os.makedirs(tmp_dir, exist_ok=True)
        self.tmp_dir = tmp_dir

        try:
            current_files = [
                f for f in os.listdir(tmp_dir)
                if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
            ]
            current_count = len(current_files)
            missing = expected_count - current_count
            print(f"[{source}] Pobieram brakujące {missing} z {expected_count} obrazów (już jest {current_count})")

            if missing <= 0:
                if self.gui_alive:
                    self.master.after(0, lambda: self.prompt_next_action(tmp_dir, query, expected_count, source))
                return

            downloaded = self.download_from_source(source, query, missing, tmp_dir)
            print(f"[{source.upper()}] ZAKOŃCZONO – pobrano: {downloaded}, oczekiwane: {missing}")

            # po udanym pobieraniu sprawdzamy, czy mamy komplet
            if self.gui_alive:
                self.master.after(0, lambda: self.after_download_phase(source, tmp_dir, query, expected_count))

        except RateLimitException:
            print(f"[{source}] Przekroczony limit lub błąd — pytam o nowe źródło")
            if self.gui_alive:
                self.master.after(0, lambda: self.handle_rate_limit(source))

        except TooManyFormatFilteredException as e:
            print(f"[{source}] FORMAT FILTER: {e}")
            if self.gui_alive:
                self.master.after(0, lambda: self.handle_format_filtered(source, str(e)))

        except TooManyResolutionFilteredException as e:
            print(f"[{source}] RESOLUTION FILTER: {e}")
            if self.gui_alive:
                self.master.after(0, lambda: self.handle_resolution_filtered(source, str(e)))

        except TooManyFilesizeFilteredException as e:
            print(f"[{source}] FILESIZE FILTER: {e}")
            if self.gui_alive:
                self.master.after(0, lambda: self.handle_filesize_filtered(source, str(e)))

        except SourceExhaustedException as e:
            print(f"[{source}] EXHAUSTED: {e}")
            if self.gui_alive:
                self.master.after(0, lambda exc=e: self.handle_source_exhausted(source, str(exc)))

        except DownloadCancelledException:
            print("[STOP] Pobieranie przerwane przez użytkownika.")
            self.cleanup_tmp_dir()
            if self.gui_alive:
                self.master.after(0, lambda: messagebox.showinfo(
                "Pobieranie przerwane",
                "Pobieranie zostało przerwane przez użytkownika."
                ))
            if self.gui_alive:
                self.master.after(0, lambda: self.download_button.config(state="normal"))
                self.master.after(0, lambda: self.back_button.config(state="normal"))
                self.master.after(0, lambda: self.progress_bar.config(value=0))
            return


    def after_download_phase(self, source, tmp_dir, query, expected_count):
        current_files = [
            f for f in os.listdir(tmp_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
        ]
        current_count = len(current_files)

        if current_count < expected_count and self.available_sources:
            # jeszcze brakuje, ale nie było wyjątku – na wszelki wypadek
            self.available_sources = [s for s in self.available_sources if s != source]
            if not self.available_sources:
                if self.gui_alive:
                    self.master.after(0, lambda: messagebox.showwarning(
                    "Brak źródeł",
                    "Wszystkie źródła zostały wykorzystane."
                    ))
                self.prompt_next_action(tmp_dir, query, expected_count, source)
                return
            if self.gui_alive:
                self.master.after(0, lambda:SourceSelector(
                    self.master,
                    self.available_sources,
                    lambda new_src: self.run_download_with_resume(
                        new_src, tmp_dir, query, expected_count, current_count
                    ),
                    on_cancel=self.request_stop_download,
                    confirm_on_close=True
                ))
        else:
            # mamy komplet albo nie ma innych źródeł
            self.prompt_next_action(tmp_dir, query, expected_count, source)

    # =========================
    #   HANDLERY BŁĘDÓW
    # =========================
    def handle_rate_limit(self, source):
        if self.gui_alive:
            self.master.after(0, lambda: messagebox.showwarning(
            "Limit zapytań",
            f"Źródło {source.capitalize()} przekroczyło limit zapytań. Wybierz kolejne źródło."
            ))
        self.available_sources = [s for s in self.available_sources if s != source]

        if not self.available_sources:
            if self.gui_alive:
                self.master.after(0, lambda: messagebox.showwarning("Brak źródeł", "Wszystkie źródła zostały wykorzystane."))
            self.download_button.config(state="normal")
            self.back_button.config(state="normal")
            return

        tmp_dir = self.tmp_dir
        current_files = [
            f for f in os.listdir(tmp_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
        ]
        current_count = len(current_files)
        if self.gui_alive:
            self.master.after(0, lambda:SourceSelector(
                self.master,
                self.available_sources,
                lambda new_source: self.run_download_with_resume(
                    new_source,
                    tmp_dir,
                    self.query,
                    self.count,
                    current_count,
                ),
                on_cancel=self.request_stop_download,
                confirm_on_close=True
            ))

    def handle_source_exhausted(self, source, reason):
        tmp_dir = self.tmp_dir
        current_files = [
            f for f in os.listdir(tmp_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
        ]
        current_count = len(current_files)
        missing = self.count - current_count
        if self.gui_alive:
            self.master.after(0, lambda: messagebox.showinfo(
            "Źródło wyczerpane",
            f"{reason}\n\nPobrano {current_count} z {self.count} obrazów."
            ))

        if missing <= 0:
            self.prompt_next_action(tmp_dir, self.query, self.count, source)
            return

        # usuwamy wyczerpane źródło
        self.available_sources = [s for s in self.available_sources if s != source]

        if not self.available_sources:
            if self.gui_alive:
                self.master.after(0, lambda: messagebox.showwarning(
                "Brak źródeł",
                "Wszystkie źródła zostały wykorzystane. Przechodzę do etapu czyszczenia/resize/split."
                ))
            self.prompt_next_action(tmp_dir, self.query, self.count, source)
            return
        if self.gui_alive:
            self.master.after(0, lambda:SourceSelector(
                self.master,
                self.available_sources,
                lambda new_src: self.run_download_with_resume(
                    new_src, tmp_dir, self.query, self.count, current_count
                ),
                on_cancel=self.request_stop_download,
                confirm_on_close=True
            ))

    def handle_format_filtered(self, source, reason):
        msg = (
            f"{reason}\n\n"
            "Wybrane filtry formatu prawdopodobnie są zbyt restrykcyjne dla tego źródła.\n\n"
            "TAK = akceptuj inne formaty i KONWERTUJ na docelowy format.\n"
            "NIE = wybierz inne źródło.\n"
            "ANULUJ = przerwij pobieranie."
        )
        if self.gui_alive:
            resp = messagebox.askyesnocancel("Brak zgodnych formatów", msg)
        else:
            resp = None
        if resp is True:
            # TAK → włączamy konwersję i wyłączamy filtr formatu
            self.force_output_format = self.infer_target_output_format()
            print("[FORMAT] Włączono konwersję do:", self.force_output_format)
            self.allow_all_formats.set(True)
            self.update_format_checkboxes()

            tmp_dir = self.tmp_dir
            current_files = [
                f for f in os.listdir(tmp_dir)
                if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
            ]
            current_count = len(current_files)
            self.run_download_with_resume(source, tmp_dir, self.query, self.count, current_count)

        elif resp is False:
            # NIE → wybieramy inne źródło (obecne usuwamy z listy)
            self.available_sources = [s for s in self.available_sources if s != source]
            if not self.available_sources:
                if self.gui_alive:
                    self.master.after(0, lambda: messagebox.showwarning("Brak źródeł", "Wszystkie źródła zostały wykorzystane."))
                self.download_button.config(state="normal")
                self.back_button.config(state="normal")
                return

            tmp_dir = self.tmp_dir
            current_files = [
                f for f in os.listdir(tmp_dir)
                if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
            ]
            current_count = len(current_files)
            if self.gui_alive:
                self.master.after(0, lambda:SourceSelector(
                    self.master,
                    self.available_sources,
                    lambda new_src: self.run_download_with_resume(
                        new_src, tmp_dir, self.query, self.count, current_count
                    ),
                    on_cancel=self.request_stop_download,
                    confirm_on_close=True
                ))
        else:
            # ANULUJ
            self.download_button.config(state="normal")
            self.back_button.config(state="normal")

    def handle_resolution_filtered(self, source, reason):
        msg = (
            f"{reason}\n\n"
            "Wybrane filtry rozdzielczości są prawdopodobnie zbyt restrykcyjne dla tego źródła.\n\n"
            "TAK = wyłącz filtry rozdzielczości i spróbuj ponownie.\n"
            "NIE = wybierz inne źródło.\n"
            "ANULUJ = przerwij pobieranie."
        )
        if self.gui_alive:
            resp = messagebox.askyesnocancel("Brak zgodnej rozdzielczości", msg)
        else:
            resp = None
        if resp is True:
            # TAK → wyłączamy filtry rozdzielczości
            self.no_min_resolution.set(True)
            self.no_max_resolution.set(True)
            self.update_resolution_fields()

            tmp_dir = self.tmp_dir
            current_files = [
                f for f in os.listdir(tmp_dir)
                if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
            ]
            current_count = len(current_files)
            self.run_download_with_resume(source, tmp_dir, self.query, self.count, current_count)

        elif resp is False:
            # NIE → wybieramy inne źródło
            self.available_sources = [s for s in self.available_sources if s != source]
            if not self.available_sources:
                if self.gui_alive:
                    self.master.after(0, lambda: messagebox.showwarning("Brak źródeł", "Wszystkie źródła zostały wykorzystane."))
                self.download_button.config(state="normal")
                self.back_button.config(state="normal")
                return

            tmp_dir = self.tmp_dir
            current_files = [
                f for f in os.listdir(tmp_dir)
                if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
            ]
            current_count = len(current_files)
            if self.gui_alive:
                self.master.after(0, lambda:SourceSelector(
                    self.master,
                    self.available_sources,
                    lambda new_src: self.run_download_with_resume(
                        new_src, tmp_dir, self.query, self.count, current_count
                    ),
                    on_cancel=self.request_stop_download,
                    confirm_on_close=True
                ))
        else:
            # ANULUJ
            self.download_button.config(state="normal")
            self.back_button.config(state="normal")

    def handle_filesize_filtered(self, source, reason):
        msg = (
            f"{reason}\n\n"
            "Wybrane filtry rozmiaru pliku są prawdopodobnie zbyt restrykcyjne.\n\n"
            "TAK = wyłącz filtr wagi i spróbuj ponownie.\n"
            "NIE = wybierz inne źródło.\n"
            "ANULUJ = przerwij pobieranie."
        )
        if self.gui_alive:
            resp = messagebox.askyesnocancel("Brak zgodnego rozmiaru pliku", msg)
        else:
            resp = None

        if resp is True:
            # wyłączenie filtra
            self.no_min_filesize.set(True)
            self.no_max_filesize.set(True)
            self.update_filesize_fields()

            tmp_dir = self.tmp_dir
            current_files = [
                f for f in os.listdir(tmp_dir)
                if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
            ]
            current_count = len(current_files)
            self.run_download_with_resume(source, tmp_dir, self.query, self.count, current_count)

        elif resp is False:
            # wybór nowego źródła
            self.available_sources = [s for s in self.available_sources if s != source]

            if not self.available_sources:
                if self.gui_alive:
                    self.master.after(0, lambda: messagebox.showwarning("Brak źródeł", "Wszystkie źródła zostały wykorzystane."))
                self.download_button.config(state="normal")
                self.back_button.config(state="normal")
                return

            tmp_dir = self.tmp_dir
            current_files = [
                f for f in os.listdir(tmp_dir)
                if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
            ]
            current_count = len(current_files)
            if self.gui_alive:
                self.master.after(0, lambda:SourceSelector(
                    self.master,
                    self.available_sources,
                    lambda new_src: self.run_download_with_resume(
                        new_src, tmp_dir, self.query, self.count, current_count
                    ),
                    on_cancel=self.request_stop_download,
                    confirm_on_close=True
                ))
        else:
            self.download_button.config(state="normal")
            self.back_button.config(state="normal")

    # =========================
    #   WYBÓR ŹRÓDŁA I RESUME
    # =========================
    def download_from_source(self, source, query, missing, save_dir):
        allowed_formats = self.get_allowed_input_formats()
        resolution_filter = self.get_resolution_filter()

        common_kwargs = dict(
            progress_callback=self.update_progress,
            start_index=utils.get_next_image_index(save_dir),
            method=self.method_var.get(),
            min_size=self.get_target_size_if_crop(),
            allowed_formats=allowed_formats,
            resolution_filter=resolution_filter,
            force_output_format=self.force_output_format,
            filesize_filter=self.get_filesize_filter(),
            should_stop=lambda: self.stop_download,
        )

        if source == "google":
            return download_images_google(query, missing, save_dir, **common_kwargs)
        elif source == "pexels":
            return download_images_pexels(query, missing, save_dir, **common_kwargs)
        elif source == "pixabay":
            return download_images_pixabay(query, missing, save_dir, **common_kwargs)
        elif source == "unsplash":
            return download_images_unsplash(query, missing, save_dir, **common_kwargs)
        elif source == "openverse":
            return download_images_openverse(query, missing, save_dir, **common_kwargs)

        print(f"Nieznane źródło: {source}")
        return 0

    def dispatch_download(self, source, query, missing, tmp_dir, progress_callback=None, start_index=0):
        func = {
            "google": download_images_google,
            "pexels": download_images_pexels,
            "pixabay": download_images_pixabay,
            "unsplash": download_images_unsplash,
            "openverse": download_images_openverse,
        }.get(source)

        if not func:
            print(f"Nieznane źródło: {source}")
            return 0

        allowed_formats = self.get_allowed_input_formats()
        resolution_filter = self.get_resolution_filter()
        start_index = utils.get_next_image_index(tmp_dir)

        return func(
            query,
            missing,
            tmp_dir,
            progress_callback=progress_callback,
            start_index=start_index,
            method=self.method_var.get(),
            min_size=self.get_target_size_if_crop(),
            allowed_formats=allowed_formats,
            resolution_filter=resolution_filter,
            force_output_format=self.force_output_format,
            filesize_filter=self.get_filesize_filter(),
            should_stop=lambda: self.stop_download,
        )

    def run_download_with_resume(self, source, tmp_dir, query, expected_count, current_count):
        threading.Thread(
            target=self._resume_download_thread,
            args=(source, tmp_dir, query, expected_count, current_count)
        ).start()

    def _resume_download_thread(self, source, tmp_dir, query, expected_count, _current_count_ignored):
        print(f"Kontynuuję pobieranie z nowego źródła: {source}")

        current_files = [
            f for f in os.listdir(tmp_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
        ]
        current_count = len(current_files)
        missing = expected_count - current_count

        print(f"[{source}] RESUME: expected={expected_count}, current={current_count}, missing={missing}")

        if missing <= 0:
            print(f"[{source}] RESUME: nic nie brakuje, pomijam dodatkowe pobieranie.")
            if self.gui_alive:
                self.master.after(0, lambda: self.prompt_next_action(tmp_dir, query, expected_count, source))
            return

        try:
            downloaded = self.dispatch_download(
                source,
                query,
                missing,
                tmp_dir,
                progress_callback=self.update_progress,
                start_index=utils.get_next_image_index(tmp_dir),
            )
            print(f"[{source.upper()} - RESUME] ZAKOŃCZONO – pobrano: {downloaded}, brakowało: {missing}")

        except RateLimitException:
            print(f"[{source}] Przekroczony limit lub błąd — pytam o nowe źródło")
            if self.gui_alive:
                self.master.after(0, lambda: self.handle_rate_limit(source))
            return

        except TooManyFormatFilteredException as e:
            print(f"[{source}] FORMAT FILTER (RESUME): {e}")
            if self.gui_alive:
                self.master.after(0, lambda: self.handle_format_filtered(source, str(e)))
            return

        except TooManyResolutionFilteredException as e:
            print(f"[{source}] RESOLUTION FILTER (RESUME): {e}")
            if self.gui_alive:
                self.master.after(0, lambda: self.handle_resolution_filtered(source, str(e)))
            return

        except TooManyFilesizeFilteredException as e:
            print(f"[{source}] FILESIZE FILTER: {e}")
            if self.gui_alive:
                self.master.after(0, lambda: self.handle_filesize_filtered(source, str(e)))
            return

        except SourceExhaustedException as e:
            print(f"[{source}] EXHAUSTED (RESUME): {e}")
            if self.gui_alive:
                self.master.after(0, lambda exc=e: self.handle_source_exhausted(source, str(exc)))
            return

        except DownloadCancelledException:
            print("[STOP] Pobieranie przerwane przez użytkownika.")
            self.cleanup_tmp_dir()
            if self.gui_alive:
                self.master.after(0, lambda: messagebox.showinfo(
                "Pobieranie przerwane",
                "Pobieranie zostało przerwane przez użytkownika."
                ))
                self.master.after(0, lambda: self.download_button.config(state="normal"))
                self.master.after(0, lambda: self.back_button.config(state="normal"))
                self.master.after(0, lambda: self.progress_bar.config(value=0))
                self.download_in_progress = False
                self.stop_download = False
            return


        new_count = len([
            f for f in os.listdir(tmp_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
        ])
        print(f"[{source}] RESUME: po pobraniu w folderze jest {new_count}/{expected_count}")

        if new_count < expected_count:
            self.available_sources = [s for s in self.available_sources if s != source]

            if not self.available_sources:
                if self.gui_alive:
                    self.master.after(0, lambda: messagebox.showwarning(
                    "Brak źródeł",
                    "Wszystkie źródła zostały wykorzystane."
                    ))
                    self.master.after(0, lambda: self.download_button.config(state="normal"))
                    self.master.after(0, lambda: self.back_button.config(state="normal"))
                return
            if self.gui_alive:
                self.master.after(0, lambda: SourceSelector(
                    self.master,
                    self.available_sources,
                    lambda new_src: self.run_download_with_resume(
                    new_src, tmp_dir, query, expected_count, new_count
                    ),
                    on_cancel=self.request_stop_download,
                    confirm_on_close=True
            ))
        else:
            if self.gui_alive:
                self.master.after(0, lambda: self.prompt_next_action(tmp_dir, query, expected_count, source))

    # =========================
    #   CLEAN / RESIZE / SPLIT
    # =========================

    def bind_mousewheel(self):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def prompt_next_action(self, tmp_dir, query, expected_count, source):
        def ask():
            if self.gui_alive:
                resp = messagebox.askquestion("Co dalej?", "Tak = ręczne czyszczenie, Nie = resize/crop")
            else:
                resp = None
            if resp == "yes":
                CleanerWindow(tmp_dir, lambda _: self.check_and_continue(tmp_dir, query, expected_count, source))
            else:
                self.process_resize_and_split(tmp_dir)
        if self.gui_alive:
            self.master.after(0, ask)

    def check_and_continue(self, tmp_dir, query, expected_count, source):
        utils.renumber_images(tmp_dir)
        self.bind_mousewheel()
        current_files = [
            f for f in os.listdir(tmp_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
        ]
        current_count = len(current_files)

        if current_count < expected_count:
            missing = expected_count - current_count
            print(f"Brakuje {missing} obrazów.")

            def continue_with_new_source(new_source):
                self.run_download_with_resume(new_source, tmp_dir, query, expected_count, current_count)

            if not self.available_sources:
                if self.gui_alive:
                    self.master.after(0, lambda: messagebox.showwarning("Brak źródeł", "Wszystkie źródła zostały wykorzystane."))
                self.prompt_next_action(tmp_dir, query, expected_count, source)
                return
            if self.gui_alive:
                self.master.after(0, lambda:SourceSelector(self.master, self.available_sources, continue_with_new_source, on_cancel=self.request_stop_download, confirm_on_close=True))
        else:
            self.prompt_next_action(tmp_dir, query, expected_count, source)

    def process_resize_and_split(self, tmp_dir):
        self.download_in_progress = False
        self.stop_download = False
        if self.resize_enabled.get():
            try:
                width = int(self.width_entry.get())
                height = int(self.height_entry.get())
                apply_resize_to_folder(tmp_dir, (width, height), self.method_var.get())
            except Exception as e:
                if self.gui_alive:
                    self.master.after(0, lambda: messagebox.showerror("Błąd", f"Nie udało się przeskalować: {e}"))
                self.download_button.config(state="normal")
                self.back_button.config(state="normal")
                return

        folder = self.folder_path.get()
        class_name = self.class_entry.get()
        save_dir = os.path.join(folder, class_name)

        train_ratio = self.train_scale.get()
        valid_ratio = self.valid_scale.get()
        test_ratio = self.test_scale.get()




        subsets = []
        if self.use_train.get():
            subsets.append("train")
        if self.use_valid.get():
            subsets.append("valid")
        if self.use_test.get():
            subsets.append("test")


        split_images(
            tmp_dir,
            save_dir,
            (train_ratio, valid_ratio, test_ratio),
            subsets,
            mode=self.split_mode.get()
        )
        shutil.rmtree(tmp_dir)
        if self.gui_alive:
            self.master.after(0, lambda: messagebox.showinfo("Zakończono", f"Dane zapisano w: {save_dir}"))
        self.download_button.config(state="normal")
        self.back_button.config(state="normal")
