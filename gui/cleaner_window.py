import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os
from functools import partial

class CleanerWindow:

    def _on_mousewheel(self, event):
        # Windows / macOS
        if event.delta:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        # Linux
        elif event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")


    def __init__(self, folder_path, on_close=None):
        self.folder_path = folder_path
        self.on_close = on_close
        self.selected_files = set()

        self.window = tk.Toplevel()
        self.window.title("INŻYNIERKA – ręczne czyszczenie obrazów")
        self.window.geometry("700x600")
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self._on_window_close)

        BG = "#f5f5f5"
        CARD = "#ffffff"

        # ===== ROOT =====
        root_frame = tk.Frame(self.window, bg=BG)
        root_frame.pack(fill="both", expand=True)

        # ===== HEADER =====
        header = tk.Frame(root_frame, bg=BG, padx=20, pady=15)
        header.pack(fill="x")

        tk.Label(
            header,
            text="Ręczne czyszczenie obrazów",
            font=("Segoe UI", 14, "bold"),
            bg=BG
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Zaznacz obrazy do usunięcia i zatwierdź na dole",
            font=("Segoe UI", 10),
            fg="#555",
            bg=BG
        ).pack(anchor="w", pady=(4, 0))

        ttk.Separator(root_frame).pack(fill="x", padx=20, pady=(0, 10))

        # ===== CONTENT (SCROLL) =====
        content_frame = tk.Frame(root_frame, bg=BG)
        content_frame.pack(fill="both", expand=True, padx=20)

        self.canvas = tk.Canvas(content_frame, bg=BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=self.canvas.yview)

        self.scroll_frame = tk.Frame(self.canvas, bg=CARD, padx=15, pady=15)

        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # ===== BOTTOM BAR =====
        bottom = tk.Frame(root_frame, bg=BG, padx=20, pady=15)
        bottom.pack(fill="x")

        ttk.Separator(bottom).pack(fill="x", pady=(0, 12))

        self.delete_button = ttk.Button(
            bottom,
            text="🗑️ Usuń zaznaczone obrazy",
            command=self.delete_selected
        )
        self.delete_button.pack(anchor="e")

        # ===== LOAD =====
        self.load_images()

    def load_images(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        files = sorted([f for f in os.listdir(self.folder_path) if f.lower().endswith((".jpg", ".png", ".jpeg", ".gif"))])
        for idx, fname in enumerate(files):
            path = os.path.join(self.folder_path, fname)
            try:
                img = Image.open(path)
                img.thumbnail((100, 100))
                tk_img = ImageTk.PhotoImage(img)
                label = tk.Label(self.scroll_frame, image=tk_img, bd=2, relief="solid", highlightthickness=0)
                label.image = tk_img
                label.grid(row=idx // 5, column=idx % 5, padx=5, pady=5)
                label.bind("<Button-1>", partial(self.toggle_select, path, label))
            except Exception as e:
                print(f"Nie można załadować {fname}: {e}")

    def toggle_select(self, path, label, event=None):
        if path in self.selected_files:
            self.selected_files.remove(path)
            label.config(highlightbackground="white", highlightthickness=0)
        else:
            self.selected_files.add(path)
            label.config(highlightbackground="red", highlightthickness=2)

    def delete_selected(self):
        deleted = 0
        for f in list(self.selected_files):
            try:
                os.remove(f)
                deleted += 1
            except Exception as e:
                print(f"Błąd usuwania {f}: {e}")

        self.selected_files.clear()
        self.load_images()

        tk.messagebox.showinfo("Czyszczenie zakończone", f"Usunięto {deleted} plików.")

        if self.on_close:
            self.on_close(self.folder_path)

        self.window.destroy()

    def _on_window_close(self):
        """
        Zamknięcie cleanera krzyżykiem:
        zachowuje się TAK SAMO jak zakończenie ręcznego czyszczenia
        """
        if self.on_close:
            self.on_close(None)
        self.window.destroy()

