import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
import os
from resizer.image_resizer import apply_resize_to_folder2
from gui.mode_selector import ModeSelectorWindow


class ResizeExistingWindow:

    def __init__(self, master):
        self.master = master
        self.master.title("PRACA INŻYNIERSKA – zmiana rozdzielczości")
        self.master.geometry("420x360")
        self.master.resizable(False, False)
        self.master.configure(bg="#f4f6fb")

        root = tk.Frame(master, bg="#f4f6fb")
        root.pack(fill="both", expand=True)

        card = tk.Frame(root, bg="#ffffff", padx=20, pady=20)
        card.place(relx=0.5, rely=0.5, anchor="center")

        self.back_button = ttk.Button(card, text="Powrót", command=self.return_to_mode_selector)
        self.back_button.pack(fill="x", pady=(0, 10))

        tk.Label(
            card,
            text="Zmiana rozdzielczości istniejącego zbioru",
            font=("Segoe UI", 12, "bold"),
            fg="#1976d2",
            bg="#ffffff"
        ).pack(pady=(0, 15))

        tk.Label(card, text="Folder zbioru:", bg="#ffffff").pack(anchor="w")
        ttk.Button(card, text="Wybierz folder", command=self.select_folder).pack(fill="x", pady=5)

        self.folder_var = tk.StringVar(value="")
        tk.Label(card, textvariable=self.folder_var, fg="#6b7280", bg="#ffffff").pack(anchor="w", pady=(0, 10))

        size = tk.Frame(card, bg="#ffffff")
        size.pack(pady=10)

        tk.Label(size, text="Szerokość:", bg="#ffffff").grid(row=0, column=0, sticky="e", padx=5)
        self.w_entry = tk.Entry(size, width=8)
        self.w_entry.insert(0, "224")
        self.w_entry.grid(row=0, column=1)

        tk.Label(size, text="Wysokość:", bg="#ffffff").grid(row=1, column=0, sticky="e", padx=5)
        self.h_entry = tk.Entry(size, width=8)
        self.h_entry.insert(0, "224")
        self.h_entry.grid(row=1, column=1)

        ttk.Separator(card).pack(fill="x", pady=15)

        ttk.Button(
            card,
            text="Rozpocznij skalowanie",
            command=self.start_resize
        ).pack(fill="x")

    def return_to_mode_selector(self):
        self.master.destroy()

        new_root = tk.Tk()
        ModeSelectorWindow(new_root)
        new_root.mainloop()


    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_var.set(folder)

    def start_resize(self):
        folder = self.folder_var.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Błąd", "Wybierz poprawny folder.")
            return

        try:
            w = int(self.w_entry.get())
            h = int(self.h_entry.get())
        except ValueError:
            messagebox.showerror("Błąd", "Wymiary muszą być liczbami.")
            return
        self.back_button.config(state="disabled")
        apply_resize_to_folder2(folder, (w, h), method="resize")

        messagebox.showinfo("Sukces", "Skalowanie zakończone.")
        self.back_button.config(state="normal")
