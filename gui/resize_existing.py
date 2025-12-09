import tkinter as tk
from tkinter import filedialog, messagebox
import os
from resizer.image_resizer import apply_resize_to_folder2
from gui.mode_selector import ModeSelectorWindow


class ResizeExistingWindow:

    def __init__(self, master):
        self.master = master


        frame = tk.Frame(master, padx=20, pady=20)
        frame.pack(fill="both", expand=True)
        tk.Button(frame, text="⬅ Powrót", command=self.return_to_mode_selector).pack(pady=10)

        tk.Label(frame, text="Wybierz folder istniejącego zbioru:").pack()

        tk.Button(
            frame, text="Wybierz folder", command=self.select_folder
        ).pack(pady=5)

        self.folder_var = tk.StringVar(value="")
        tk.Label(frame, textvariable=self.folder_var, fg="gray").pack()

        tk.Label(frame, text="Docelowa szerokość:").pack(pady=(10, 0))
        self.w_entry = tk.Entry(frame, width=10)
        self.w_entry.insert(0, "224")
        self.w_entry.pack()

        tk.Label(frame, text="Docelowa wysokość:").pack()
        self.h_entry = tk.Entry(frame, width=10)
        self.h_entry.insert(0, "224")
        self.h_entry.pack()

        tk.Button(
            frame, text="Rozpocznij skalowanie", command=self.start_resize
        ).pack(pady=20)

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

        apply_resize_to_folder2(folder, (w, h), method="resize")

        messagebox.showinfo("Sukces", "Skalowanie zakończone.")
