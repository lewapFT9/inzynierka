import tkinter as tk
from PIL import Image, ImageTk
import os
from functools import partial

class CleanerWindow:
    def __init__(self, folder_path, on_close=None):
        self.folder_path = folder_path
        self.on_close = on_close
        self.selected_files = set()

        self.window = tk.Toplevel()
        self.window.title(" Ręczne czyszczenie obrazów")
        self.window.geometry("600x600")

        self.canvas = tk.Canvas(self.window)
        self.scrollbar = tk.Scrollbar(self.window, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas)

        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.bottom_frame = tk.Frame(self.window)
        self.bottom_frame.pack(fill="x", pady=10)

        self.delete_button = tk.Button(self.bottom_frame, text="🗑️ Usuń zaznaczone", command=self.delete_selected)
        self.delete_button.pack()

        self.load_images()

    def load_images(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        files = sorted([f for f in os.listdir(self.folder_path) if f.lower().endswith((".jpg", ".png", ".jpeg"))])
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
