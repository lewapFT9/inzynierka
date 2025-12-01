import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import utils.utils as utils
import threading
import os
import shutil
import re
from downloader.google_downloader import download_images_google
from downloader.pexels_downloader import download_images_pexels
from downloader.pixabay_downloader import download_images_pixabay
from downloader.unsplash_downloader import download_images_unsplash
from downloader.openverse_downloader import download_images_openverse
from downloader.wikimedia_downloader import download_images_wikimedia
from gui.cleaner_window import CleanerWindow
from splitter.splitter import split_images
from resizer.image_resizer import apply_resize_to_folder
from gui.source_selector import SourceSelector
from exceptions.exceptions import RateLimitException



class ImageDownloaderGUI:

    def __init__(self, master):
        self.master = master
        master.title("INŻYNIERKA")
        self.source_selector_window = None  # <--- DODANE

        # --- SCROLLABLE MAIN FRAME ---
        self.canvas = tk.Canvas(master)
        self.scrollbar = tk.Scrollbar(master, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.build_ui()

    def build_ui(self):
        f = self.scrollable_frame  # skrót do scrollowanego kontenera

        tk.Label(f, text="Hasło do wyszukiwania (query):").pack()
        self.query_entry = tk.Entry(f, width=40)
        self.query_entry.pack()

        tk.Label(f, text="Liczba obrazów:").pack()
        self.count_entry = tk.Entry(f, width=10)
        self.count_entry.pack()

        tk.Label(f, text="Nazwa klasy (folder):").pack()
        self.class_entry = tk.Entry(f, width=20)
        self.class_entry.pack()

        self.select_button = tk.Button(f, text="Wybierz folder docelowy", command=self.choose_folder)
        self.select_button.pack(pady=5)

        self.folder_path = tk.StringVar()
        tk.Label(f, textvariable=self.folder_path, fg="gray").pack()

        tk.Label(f, text="Wybierz podzbiory:").pack()
        self.use_train = tk.BooleanVar(value=True)
        self.use_valid = tk.BooleanVar(value=True)
        self.use_test = tk.BooleanVar(value=True)
        tk.Checkbutton(f, text="train", variable=self.use_train).pack()
        tk.Checkbutton(f, text="valid", variable=self.use_valid).pack()
        tk.Checkbutton(f, text="test", variable=self.use_test).pack()

        tk.Label(f, text="Podział zbioru (train / valid / test)").pack()
        self.train_scale = tk.Scale(f, from_=10, to=90, orient=tk.HORIZONTAL, label="Train (%)")
        self.valid_scale = tk.Scale(f, from_=0, to=90, orient=tk.HORIZONTAL, label="Valid (%)")
        self.train_scale.set(70)
        self.valid_scale.set(20)
        self.train_scale.pack()
        self.valid_scale.pack()

        # ----------------------------
        # FILTR ROZDZIELCZOŚCI WEJŚCIOWEJ
        # ----------------------------
        tk.Label(f, text="Filtr rozdzielczości obrazów (WEJŚCIOWYCH):").pack(pady=(10, 0))

        # --- MINIMUM ---
        min_frame = tk.Frame(f)
        min_frame.pack()

        self.min_width_var = tk.StringVar(value="")
        self.min_height_var = tk.StringVar(value="")
        self.no_min_resolution = tk.BooleanVar(value=True)

        tk.Checkbutton(
            min_frame, text="Brak minimalnej", variable=self.no_min_resolution,
            command=self.update_resolution_fields
        ).grid(row=0, column=0, sticky="w")

        tk.Label(min_frame, text="Min szerokość:").grid(row=1, column=0, sticky="e")

        self.min_width_entry = tk.Entry(min_frame, textvariable=self.min_width_var, width=8)
        self.min_width_entry.grid(row=1, column=1)

        tk.Label(min_frame, text="Min wysokość:").grid(row=2, column=0, sticky="e")

        self.min_height_entry = tk.Entry(min_frame, textvariable=self.min_height_var, width=8)
        self.min_height_entry.grid(row=2, column=1)

        # --- MAKSIMUM ---
        max_frame = tk.Frame(f)
        max_frame.pack(pady=(5, 0))

        self.max_width_var = tk.StringVar(value="")
        self.max_height_var = tk.StringVar(value="")
        self.no_max_resolution = tk.BooleanVar(value=True)

        tk.Checkbutton(
            max_frame, text="Brak maksymalnej", variable=self.no_max_resolution,
            command=self.update_resolution_fields
        ).grid(row=0, column=0, sticky="w")

        tk.Label(max_frame, text="Max szerokość:").grid(row=1, column=0, sticky="e")

        self.max_width_entry = tk.Entry(max_frame, textvariable=self.max_width_var, width=8)
        self.max_width_entry.grid(row=1, column=1)

        tk.Label(max_frame, text="Max wysokość:").grid(row=2, column=0, sticky="e")

        self.max_height_entry = tk.Entry(max_frame, textvariable=self.max_height_var, width=8)
        self.max_height_entry.grid(row=2, column=1)

        # ustawienie stanu pól (disable/enable)
        self.update_resolution_fields()

        # ----------------------------
        # SCALING / CROP
        # ----------------------------
        tk.Label(f, text="Zmiana rozdzielczości obrazów:").pack(pady=(10, 0))
        self.resize_enabled = tk.BooleanVar(value=True)
        tk.Checkbutton(f, text="Włącz skalowanie", variable=self.resize_enabled).pack()

        self.method_var = tk.StringVar(value="resize")
        tk.Radiobutton(f, text="Zmień rozmiar", variable=self.method_var, value="resize").pack()
        tk.Radiobutton(f, text="Wytnij środek", variable=self.method_var, value="crop").pack()

        tk.Label(f, text="Szerokość x Wysokość (np. 224x224):").pack()
        self.resolution_entry = tk.Entry(f)
        self.resolution_entry.insert(0, "224x224")
        self.resolution_entry.pack()

        # ----------------------------
        # FORMATY WEJŚCIOWE
        # ----------------------------
        tk.Label(f, text="Dozwolone formaty wejściowe:").pack(pady=(10, 0))

        self.allow_all_formats = tk.BooleanVar(value=True)
        self.allow_jpg = tk.BooleanVar(value=True)
        self.allow_png = tk.BooleanVar(value=True)
        self.allow_gif = tk.BooleanVar(value=True)

        self.jpg_cb = tk.Checkbutton(f, text="JPG / JPEG", variable=self.allow_jpg,
                                     command=self.update_format_checkboxes)
        self.jpg_cb.pack(anchor="w")

        self.png_cb = tk.Checkbutton(f, text="PNG", variable=self.allow_png,
                                     command=self.update_format_checkboxes)
        self.png_cb.pack(anchor="w")

        self.gif_cb = tk.Checkbutton(f, text="GIF", variable=self.allow_gif,
                                     command=self.update_format_checkboxes)
        self.gif_cb.pack(anchor="w")

        self.all_cb = tk.Checkbutton(f, text="Wszystkie formaty dozwolone",
                                     variable=self.allow_all_formats,
                                     command=self.update_format_checkboxes)
        self.all_cb.pack(anchor="w")

        self.update_format_checkboxes()

        # ----------------------------
        # PRZYCISK POBIERANIA
        # ----------------------------
        self.progress = tk.IntVar()
        self.progress_bar = ttk.Progressbar(f, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.pack(pady=10)

        self.download_button = ttk.Button(f, text="Pobierz obrazy", command=self.start_download)
        self.download_button.pack(pady=10)

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

        # jeśli nic nie zaznaczono → traktujemy jako brak filtra
        if not allowed:
            return None

        return allowed

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

    def get_resolution_filter(self):
        """Zwraca słownik z filtrami rozdzielczości lub None."""
        result = {}

        # MIN
        if not self.no_min_resolution.get():
            try:
                result["min_w"] = int(self.min_width_var.get()) if self.min_width_var.get() else None
                result["min_h"] = int(self.min_height_var.get()) if self.min_height_var.get() else None
            except ValueError:
                return None  # lub podnieś wyjątek później

        # MAX
        if not self.no_max_resolution.get():
            try:
                result["max_w"] = int(self.max_width_var.get()) if self.max_width_var.get() else None
                result["max_h"] = int(self.max_height_var.get()) if self.max_height_var.get() else None
            except ValueError:
                return None

        return result


    def choose_folder(self):
        folder = filedialog.askdirectory(title="Wybierz folder docelowy")
        self.folder_path.set(folder)

    def update_progress(self, current, total):
        percent = int((current / total) * 100)
        self.progress_bar['value'] = percent


    def start_download(self):
        query = self.query_entry.get().strip()
        class_name = self.class_entry.get().strip()
        folder = self.folder_path.get().strip()
        count = self.count_entry.get().strip()

        if not all([query, count, class_name, folder]):
            messagebox.showerror("Błąd", "Uzupełnij wszystkie pola.")
            return

        try:
            count = int(count)
        except ValueError:
            messagebox.showerror("Błąd", "Liczba obrazów musi być liczbą całkowitą.")
            return

        self.query = query
        self.class_name = class_name
        self.folder = folder
        self.count = count

        self.download_button.config(state="disabled")

        self.available_sources = ["google", "pexels", "pixabay", "unsplash", "openverse", "wikimedia"]

        def on_source(selected_source):
            # po wybraniu źródła zapominamy o oknie i startujemy pobieranie
            self.source_selector_window = None
            threading.Thread(target=self.run_download, args=(selected_source,)).start()

        def on_cancel_source():
            # użytkownik zamknął okno wyboru – odblokowujemy przycisk
            self.source_selector_window = None
            self.download_button.config(state="normal")

            # jeśli okno już istnieje – tylko je wyciągamy na wierzch

        if self.source_selector_window is not None and self.source_selector_window.winfo_exists():
            self.source_selector_window.lift()
            self.source_selector_window.focus_force()
            return

            # tworzymy nowe okno wyboru i zapamiętujemy referencję
        self.source_selector_window = SourceSelector(
            self.master,
            self.available_sources,
            on_select=on_source,
            on_cancel=on_cancel_source
        )

    from exceptions.exceptions import RateLimitException

    def run_download(self, source):
        threading.Thread(target=self._download_thread, args=(source,)).start()

    def _download_thread(self, source):
        query = self.query
        class_name = self.class_name
        folder = self.folder
        count = self.count

        tmp_dir = os.path.join(folder, f"_tmp_{class_name}")
        os.makedirs(tmp_dir, exist_ok=True)
        self.tmp_dir = tmp_dir

        try:
            current_files = [f for f in os.listdir(tmp_dir) if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))]
            current_count = len(current_files)
            missing = int(count) - current_count
            print(f"[{source}] Pobieram brakujące {missing} z {count} obrazów (już jest {current_count})")

            downloaded = self.download_from_source(source, query, missing, tmp_dir)
            print(f"[{source.upper()}] ZAKOŃCZONO – pobrano: {downloaded}, oczekiwane: {missing}")

            self.master.after(0, lambda: self.prompt_next_action(tmp_dir, query, int(count), source))

        except RateLimitException:
            print(f"[{source}] Przekroczony limit lub błąd — pytam o nowe źródło")

            self.master.after(0, lambda: messagebox.showwarning(
                "Limit zapytań",
                f"Źródło {source.capitalize()} przekroczyło limit zapytań. Wybierz kolejne źródło."
            ))
            self.available_sources = [s for s in self.available_sources if s != source]

            if not self.available_sources:
                self.master.after(0, lambda: (
                    messagebox.showwarning("Brak źródeł", "Wszystkie źródła zostały wykorzystane."),
                    self.download_button.config(state="normal")  # <-- TU
                ))
                return

            self.master.after(0, lambda: SourceSelector(
                self.master,
                self.available_sources,
                lambda new_source: self.run_download_with_resume(new_source, tmp_dir, query, int(count), current_count)
            ))

    def get_target_size_if_crop(self):
        if self.method_var.get() == "crop":
            try:
                w, h = map(int, self.resolution_entry.get().lower().strip().split("x"))
                return (w, h)
            except:
                return None
        return None

    def download_from_source(self, source, query, missing, save_dir):
        allowed_formats = self.get_allowed_input_formats()
        resolution_filter = self.get_resolution_filter()

        if source == "google":
            from downloader.google_downloader import download_images_google
            return download_images_google(
                query, missing, save_dir, self.update_progress,
                min_size=self.get_target_size_if_crop(),
                method=self.method_var.get(),
                allowed_formats=allowed_formats,
                resolution_filter=resolution_filter
            )

        elif source == "openverse":
            from downloader.openverse_downloader import download_images_openverse
            return download_images_openverse(
                query, missing, save_dir, self.update_progress,
                min_size=self.get_target_size_if_crop(),
                method=self.method_var.get(),
                allowed_formats=allowed_formats,
                resolution_filter=resolution_filter
            )


        elif source == "pexels":
            from downloader.pexels_downloader import download_images_pexels
            return download_images_pexels(
                query,
                missing,
                save_dir,
                self.update_progress,
                utils.get_next_image_index(save_dir),  # start_index
                self.method_var.get(),  # method
                self.get_target_size_if_crop(),  # min_size
                allowed_formats,  # allowed_formats
                resolution_filter  # resolution_filter
            )

        elif source == "pixabay":
            from downloader.pixabay_downloader import download_images_pixabay
            return download_images_pixabay(
                query, missing, save_dir, self.update_progress,
                min_size=self.get_target_size_if_crop(),
                method=self.method_var.get(),
                allowed_formats=allowed_formats,
                resolution_filter=resolution_filter
            )

        elif source == "unsplash":
            from downloader.unsplash_downloader import download_images_unsplash
            return download_images_unsplash(
                query, missing, save_dir, self.update_progress,
                min_size=self.get_target_size_if_crop(),
                method=self.method_var.get(),
                allowed_formats=allowed_formats,
                resolution_filter=resolution_filter
            )

        elif source == "wikimedia":
            from downloader.wikimedia_downloader import download_images_wikimedia
            return download_images_wikimedia(
                query, missing, save_dir, self.update_progress
            )

        print(f"Nieznane źródło: {source}")
        return 0

    def dispatch_download(self, source, query, missing, tmp_dir, progress_callback=None, start_index=0):
        func = {
            "google": download_images_google,
            "pexels": download_images_pexels,
            "pixabay": download_images_pixabay,
            "unsplash": download_images_unsplash,
            "openverse": download_images_openverse,
            "wikimedia": download_images_wikimedia
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
            progress_callback,
            start_index,
            self.method_var.get(),
            self.get_target_size_if_crop(),
            allowed_formats,
            resolution_filter
        )

    def prompt_next_action(self, tmp_dir, query, expected_count, source):
        def ask():
            resp = messagebox.askquestion("Co dalej?", "Tak = ręczne czyszczenie, Nie = resize/crop")
            if resp=="yes":
                CleanerWindow(tmp_dir, lambda _: self.check_and_continue(tmp_dir, query, expected_count, source))
            else:
                self.process_resize_and_split(tmp_dir)
        self.master.after(0,ask)

    def check_and_continue(self, tmp_dir, query, expected_count, source):
        current_files = [f for f in os.listdir(tmp_dir) if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))]
        current_count = len(current_files)

        if current_count < expected_count:
            missing = expected_count - current_count
            print(f"Brakuje {missing} obrazów.")

            def continue_with_new_source(new_source):
                self.run_download_with_resume(new_source, tmp_dir, query, expected_count, current_count)

            # Usuń obecne źródło z listy
            #self.available_sources = [s for s in self.available_sources if s != source]

            if not self.available_sources:
                messagebox.showwarning("Brak źródeł", "Wszystkie źródła zostały wykorzystane.")
                self.prompt_next_action(tmp_dir, query, expected_count, source)
                return

            # Pytamy użytkownika o kolejne źródło
            SourceSelector(self.master, self.available_sources, continue_with_new_source)

        else:
            self.prompt_next_action(tmp_dir, query, expected_count, source)

    def run_download_with_resume(self, source, tmp_dir, query, expected_count, current_count):
        threading.Thread(target=self._resume_download_thread,
                         args=(source, tmp_dir, query, expected_count, current_count)).start()

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
            self.master.after(0, lambda: self.prompt_next_action(tmp_dir, query, expected_count, source))
            return

        try:
            downloaded = self.dispatch_download(
                source,
                query,
                missing,
                tmp_dir,
                self.update_progress,
                start_index=utils.get_next_image_index(tmp_dir),
            )
            print(f"[{source.upper()} - RESUME] ZAKOŃCZONO – pobrano: {downloaded}, brakowało: {missing}")
        except RateLimitException:
            print(f"[{source}] Przekroczony limit lub błąd — pytam o nowe źródło")

            self.master.after(0, lambda: messagebox.showwarning(
                "Limit zapytań",
                f"Źródło {source.capitalize()} przekroczyło limit zapytań. Wybierz kolejne źródło."
            ))
            self.available_sources = [s for s in self.available_sources if s != source]

            if not self.available_sources:
                self.master.after(0, lambda: (
                    messagebox.showwarning("Brak źródeł", "Wszystkie źródła zostały wykorzystane."),
                    self.download_button.config(state="normal")
                ))
                return

            self.master.after(0, lambda: SourceSelector(
                self.master,
                self.available_sources,
                lambda new_src: self.run_download_with_resume(
                    new_src, tmp_dir, query, expected_count, current_count
                )
            ))
            return

        new_count = len([
            f for f in os.listdir(tmp_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".gif"))
        ])
        print(f"[{source}] RESUME: po pobraniu w folderze jest {new_count}/{expected_count}")

        if new_count < expected_count:
            self.available_sources = [s for s in self.available_sources if s != source]

            if not self.available_sources:
                self.master.after(0, lambda: messagebox.showwarning(
                    "Brak źródeł",
                    "Wszystkie źródła zostały wykorzystane."
                ))
                return

            self.master.after(0, lambda: SourceSelector(
                self.master,
                self.available_sources,
                lambda new_src: self.run_download_with_resume(
                    new_src, tmp_dir, query, expected_count, new_count
                )
            ))
        else:
            self.master.after(0, lambda: self.prompt_next_action(tmp_dir, query, expected_count, source))

    def process_resize_and_split(self, tmp_dir):
        if self.resize_enabled.get():
            try:
                width, height = map(int, self.resolution_entry.get().lower().strip().split("x"))
                apply_resize_to_folder(tmp_dir, (width, height), self.method_var.get())
                print(f" Przeskalowano do {width}x{height}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie udało się przeskalować: {e}")
                self.download_button.config(state="normal")

                return

        folder = self.folder_path.get()
        class_name = self.class_entry.get()
        save_dir = os.path.join(folder, class_name)

        train_ratio = self.train_scale.get()
        valid_ratio = self.valid_scale.get()
        test_ratio = 100 - train_ratio - valid_ratio

        subsets = []
        if self.use_train.get(): subsets.append("train")
        if self.use_valid.get(): subsets.append("valid")
        if self.use_test.get(): subsets.append("test")

        if not subsets:
            messagebox.showerror("Błąd", "Wybierz co najmniej jeden podzbiór.")
            self.download_button.config(state="normal")
            return

        split_images(tmp_dir, save_dir, (train_ratio, valid_ratio, test_ratio), subsets)
        shutil.rmtree(tmp_dir)
        messagebox.showinfo("Zakończono", f"Dane zapisano w: {save_dir}")
        self.download_button.config(state="normal")

