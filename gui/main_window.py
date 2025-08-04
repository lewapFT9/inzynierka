import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
import shutil

from downloader.google_downloader import download_images_google
from gui.cleaner_window import CleanerWindow
from splitter.splitter import split_images
from resizer.image_resizer import apply_resize_to_folder

class ImageDownloaderGUI:
    def __init__(self, master):
        self.master = master
        master.title("INŻYNIERKA")

        tk.Label(master, text="Hasło do wyszukiwania (query):").pack()
        self.query_entry = tk.Entry(master, width=40)
        self.query_entry.pack()

        tk.Label(master, text="Liczba obrazów:").pack()
        self.count_entry = tk.Entry(master, width=10)
        self.count_entry.pack()

        tk.Label(master, text="Nazwa klasy (folder):").pack()
        self.class_entry = tk.Entry(master, width=20)
        self.class_entry.pack()

        self.select_button = tk.Button(master, text="Wybierz folder docelowy", command=self.choose_folder)
        self.select_button.pack(pady=5)

        self.folder_path = tk.StringVar()
        tk.Label(master, textvariable=self.folder_path, fg="gray").pack()

        tk.Label(master, text="Wybierz podzbiory:").pack()
        self.use_train = tk.BooleanVar(value=True)
        self.use_valid = tk.BooleanVar(value=True)
        self.use_test = tk.BooleanVar(value=True)
        tk.Checkbutton(master, text="train", variable=self.use_train).pack()
        tk.Checkbutton(master, text="valid", variable=self.use_valid).pack()
        tk.Checkbutton(master, text="test", variable=self.use_test).pack()

        tk.Label(master, text="Podział zbioru (train / valid / test)").pack()
        self.train_scale = tk.Scale(master, from_=10, to=90, orient=tk.HORIZONTAL, label="Train (%)")
        self.valid_scale = tk.Scale(master, from_=0, to=90, orient=tk.HORIZONTAL, label="Valid (%)")
        self.train_scale.set(70)
        self.valid_scale.set(20)
        self.train_scale.pack()
        self.valid_scale.pack()

        tk.Label(master, text="Zmiana rozdzielczości obrazów:").pack(pady=(10, 0))
        self.resize_enabled = tk.BooleanVar(value=True)
        tk.Checkbutton(master, text="Włącz skalowanie", variable=self.resize_enabled).pack()
        self.method_var = tk.StringVar(value="resize")
        tk.Radiobutton(master, text="Zmień rozmiar", variable=self.method_var, value="resize").pack()
        tk.Radiobutton(master, text="Wytnij środek", variable=self.method_var, value="crop").pack()
        tk.Label(master, text="Szerokość x Wysokość (np. 224x224):").pack()
        self.resolution_entry = tk.Entry(master)
        self.resolution_entry.insert(0, "224x224")
        self.resolution_entry.pack()

        self.progress = tk.IntVar()
        self.progress_bar = tk.Scale(master, from_=0, to=100, orient=tk.HORIZONTAL, variable=self.progress, length=300)
        self.progress_bar.pack(pady=10)

        self.download_button = tk.Button(master, text="Pobierz obrazy", command=self.start_download)
        self.download_button.pack(pady=10)

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Wybierz folder docelowy")
        self.folder_path.set(folder)

    def update_progress(self, current, total):
        percent = int((current / total) * 100)
        self.progress.set(percent)

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

        save_dir = os.path.join(folder, class_name)
        tmp_dir = os.path.join(folder, f"_tmp_{class_name}")
        os.makedirs(tmp_dir, exist_ok=True)

        def task():
            downloaded = download_images_google(query, count, tmp_dir, self.update_progress)
            self.prompt_next_action(tmp_dir, query, count)

        threading.Thread(target=task).start()

    def prompt_next_action(self, tmp_dir, query, expected_count):
        def ask():
            response = messagebox.askquestion("Co dalej?", "Wybierz kolejne działanie:\nTak = ręczne czyszczenie\nNie = zmiana rozmiaru/wycięcie")
            if response == "yes":
                CleanerWindow(tmp_dir, lambda _: self.check_and_continue(tmp_dir, query, expected_count))
            else:
                self.process_resize_and_split(tmp_dir)

        self.master.after(0, ask)

    def check_and_continue(self, tmp_dir, query, expected_count):
        current_files = [f for f in os.listdir(tmp_dir) if f.lower().endswith((".jpg", ".png", ".jpeg"))]
        current_count = len(current_files)

        if current_count < expected_count:
            missing = expected_count - current_count
            print(f"Uzupełniam {missing} brakujących obrazów...")
            start_index = current_count
            downloaded = download_images_google(query, missing, tmp_dir, self.update_progress, start_index)
            print(f" Uzupełniono o {downloaded} obrazów.")
            self.prompt_next_action(tmp_dir, query, expected_count)
        else:
            self.prompt_next_action(tmp_dir, query, expected_count)

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
