import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter.messagebox import CANCEL


class SourceSelector(tk.Toplevel):
    def __init__(self, master, sources, on_select, on_cancel=None, confirm_on_close=False):
        super().__init__(master)
        self.title("Wybierz źródło")
        self.on_select = on_select
        self.on_cancel = on_cancel
        self.confirm_on_close = confirm_on_close
        self.var = tk.StringVar(value=sources[0])

        self.geometry("320x350")
        self.resizable(False, False)
        self.configure(bg="#f4f6fb")

        if confirm_on_close:
            self.protocol("WM_DELETE_WINDOW", self._on_close)
        else:
            self.protocol("WM_DELETE_WINDOW", self.destroy)

        card = tk.Frame(self, bg="#ffffff", padx=20, pady=20)
        card.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Label(
            card,
            text="Wybierz źródło pobierania",
            font=("Segoe UI", 12, "bold"),
            fg="#1976d2",
            bg="#ffffff"
        ).pack(anchor="w", pady=(0, 10))

        for src in sources:
            tk.Radiobutton(
                card,
                text=src.capitalize(),
                variable=self.var,
                value=src,
                bg="#ffffff"
            ).pack(anchor="w")

        ttk.Separator(card).pack(fill="x", pady=12)

        ttk.Button(card, text="OK", command=self.confirm).pack(fill="x")

        if self.on_cancel:
            ttk.Button(card, text="Anuluj", command=self._on_close).pack(fill="x", pady=(6, 0))

        # Obsługa zamknięcia okna krzyżykiem
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        # TRYB 1 – bez pytania (pierwszy wybór)
        if not self.confirm_on_close:
            if self.on_cancel:
                self.on_cancel()
            self.destroy()
            return

        # TRYB 2 – z pytaniem
        if messagebox.askyesno(
                "Przerwać pobieranie?",
                "Trwa proces pobierania.\n\n"
                "Czy na pewno chcesz przerwać pobieranie?"
        ):
            if self.on_cancel:
                self.on_cancel()
            self.destroy()

    def confirm(self):
        self.on_select(self.var.get())
        self.destroy()
