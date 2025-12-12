import tkinter as tk
from tkinter import messagebox


class SourceSelector(tk.Toplevel):
    def __init__(self, master, sources, on_select, on_cancel=None, confirm_on_close = False):
        super().__init__(master)
        self.title("Wybierz źródło pobierania")
        self.on_select = on_select
        self.on_cancel = on_cancel
        self.var = tk.StringVar(value=sources[0])
        self.confirm_on_close = confirm_on_close

        tk.Label(self, text="Wybierz źródło:").pack(pady=5)
        for src in sources:
            tk.Radiobutton(self, text=src.capitalize(), variable=self.var, value=src).pack(anchor="w")
        tk.Button(self, text="OK", command=self.confirm).pack(pady=10)

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
