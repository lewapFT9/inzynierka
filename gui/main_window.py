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


class ImageDownloaderGUI:

    def __init__(self, master):
        self.master = master
        master.title("INŻYNIERKA")
        self.build_ui()

    def build_ui(self):
        tk.Label(self.master, text="Hasło do wyszukiwania (query):").pack()
        self.query_entry = tk.Entry(self.master, width=40)
        self.query_entry.pack()

        tk.Label(self.master, text="Liczba obrazów:").pack()
        self.count_entry = tk.Entry(self.master, width=10)
        self.count_entry.pack()

        tk.Label(self.master, text="Nazwa klasy (folder):").pack()
        self.class_entry = tk.Entry(self.master, width=20)
        self.class_entry.pack()

        self.select_button = tk.Button(self.master, text="Wybierz folder docelowy", command=self.choose_folder)
        self.select_button.pack(pady=5)

        self.folder_path = tk.StringVar()
        tk.Label(self.master, textvariable=self.folder_path, fg="gray").pack()

        tk.Label(self.master, text="Wybierz podzbiory:").pack()
        self.use_train = tk.BooleanVar(value=True)
        self.use_valid = tk.BooleanVar(value=True)
        self.use_test = tk.BooleanVar(value=True)
        tk.Checkbutton(self.master, text="train", variable=self.use_train).pack()
        tk.Checkbutton(self.master, text="valid", variable=self.use_valid).pack()
        tk.Checkbutton(self.master, text="test", variable=self.use_test).pack()

        tk.Label(self.master, text="Podział zbioru (train / valid / test)").pack()
        self.train_scale = tk.Scale(self.master, from_=10, to=90, orient=tk.HORIZONTAL, label="Train (%)")
        self.valid_scale = tk.Scale(self.master, from_=0, to=90, orient=tk.HORIZONTAL, label="Valid (%)")
        self.train_scale.set(70)
        self.valid_scale.set(20)
        self.train_scale.pack()
        self.valid_scale.pack()

        tk.Label(self.master, text="Zmiana rozdzielczości obrazów:").pack(pady=(10, 0))
        self.resize_enabled = tk.BooleanVar(value=True)
        tk.Checkbutton(self.master, text="Włącz skalowanie", variable=self.resize_enabled).pack()
        self.method_var = tk.StringVar(value="resize")
        tk.Radiobutton(self.master, text="Zmień rozmiar", variable=self.method_var, value="resize").pack()
        tk.Radiobutton(self.master, text="Wytnij środek", variable=self.method_var, value="crop").pack()
        tk.Label(self.master, text="Szerokość x Wysokość (np. 224x224):").pack()
        self.resolution_entry = tk.Entry(self.master)
        self.resolution_entry.insert(0, "224x224")
        self.resolution_entry.pack()

        self.progress = tk.IntVar()
        self.progress_bar = ttk.Progressbar(self.master, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.pack(pady=10)
        self.download_button = ttk.Button(self.master, text="Pobierz obrazy", command=self.start_download)
        self.download_button.pack(pady=10)


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

        self.available_sources = ["google", "pexels", "pixabay", "unsplash", "openverse", "wikimedia"]

        def on_source(selected_source):
            threading.Thread(target=self.run_download, args=(selected_source,)).start()

        # pokaż okno wyboru źródła
        SourceSelector(self.master, self.available_sources, on_source)

    def run_download(self, source):
        query = self.query
        class_name = self.class_name
        folder = self.folder
        count = self.count

        tmp_dir = os.path.join(folder, f"_tmp_{class_name}")
        os.makedirs(tmp_dir, exist_ok=True)
        self.tmp_dir = tmp_dir

        # tutaj pobieranie z wybranego źródła
        downloaded = self.download_from_source(source, query, int(count), tmp_dir)

        self.prompt_next_action(tmp_dir, query, int(count), source)

    def download_from_source(self, source, query, count, save_dir):
        if source == "google":
            from downloader.google_downloader import download_images_google
            return download_images_google(query, count, save_dir, self.update_progress)
        elif source == "openverse":
            from downloader.openverse_downloader import download_images_openverse
            return download_images_openverse(query, count, save_dir, self.update_progress)
        elif source == "pexels":
            from downloader.pexels_downloader import download_images_pexels
            return download_images_pexels(query, count, save_dir, self.update_progress)
        elif source == "pixabay":
            from downloader.pixabay_downloader import download_images_pixabay
            return download_images_pixabay(query, count, save_dir, self.update_progress)
        elif source == "unsplash":
            from downloader.unsplash_downloader import download_images_unsplash
            return download_images_unsplash(query, count, save_dir, self.update_progress)
        elif source == "wikimedia":
            from downloader.wikimedia_downloader import download_images_wikimedia
            return download_images_wikimedia(query, count, save_dir, self.update_progress)
        else:
            print(f"Nieznane źródło: {source}")
            return 0


    def dispatch_download(self, source, query, count, tmp_dir, progress_callback=None, start_index=0):
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
        start_index = utils.get_next_image_index(tmp_dir)
        return func(query, count, tmp_dir, progress_callback, start_index)


    def prompt_next_action(self, tmp_dir, query, expected_count, source):
        def ask():
            resp = messagebox.askquestion("Co dalej?", "Tak = ręczne czyszczenie, Nie = resize/crop")
            if resp=="yes":
                CleanerWindow(tmp_dir, lambda _: self.check_and_continue(tmp_dir, query, expected_count, source))
            else:
                self.process_resize_and_split(tmp_dir)
        self.master.after(0,ask)

    def check_and_continue(self, tmp_dir, query, expected_count, source):
        current_files = [f for f in os.listdir(tmp_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        current_count = len(current_files)

        if current_count < expected_count:
            missing = expected_count - current_count
            print(f"Brakuje {missing} obrazów.")

            def continue_with_new_source(new_source):
                self.run_download_with_resume(new_source, tmp_dir, query, expected_count, current_count)

            # Usuń obecne źródło z listy
            self.available_sources = [s for s in self.available_sources if s != source]

            if not self.available_sources:
                messagebox.showwarning("Brak źródeł", "Wszystkie źródła zostały wykorzystane.")
                self.prompt_next_action(tmp_dir, query, expected_count, source)
                return

            # Pytamy użytkownika o kolejne źródło
            SourceSelector(self.master, self.available_sources, continue_with_new_source)

        else:
            self.prompt_next_action(tmp_dir, query, expected_count, source)

    def run_download_with_resume(self, source, tmp_dir, query, expected_count, current_count):
        print(f"Kontynuuję pobieranie z nowego źródła: {source}")
        missing = expected_count - current_count

        downloaded = self.dispatch_download(source, query, missing, tmp_dir, self.update_progress,
                                            start_index=current_count)

        if current_count + downloaded < expected_count:
            # Znów brakuje — ponownie pokaż wybór źródła
            self.available_sources = [s for s in self.available_sources if s != source]

            if not self.available_sources:
                messagebox.showwarning("Brak źródeł", "Wszystkie źródła zostały wykorzystane.")
                self.prompt_next_action(tmp_dir, query, expected_count, source)
                return

            SourceSelector(self.master, self.available_sources, lambda new_src:
            self.run_download_with_resume(new_src, tmp_dir, query, expected_count, current_count + downloaded)
                           )
        else:
            self.prompt_next_action(tmp_dir, query, expected_count, source)

    def process_resize_and_split(self, tmp_dir):
        if self.resize_enabled.get():
            try:
                width, height = map(int, self.resolution_entry.get().lower().strip().split("x"))
                apply_resize_to_folder(tmp_dir, (width, height), self.method_var.get())
                print(f" Przeskalowano do {width}x{height}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie udało się przeskalować: {e}")
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
            return

        split_images(tmp_dir, save_dir, (train_ratio, valid_ratio, test_ratio), subsets)
        shutil.rmtree(tmp_dir)
        messagebox.showinfo("Zakończono", f"Dane zapisano w: {save_dir}")
