import tkinter as tk

class SourceSelector(tk.Toplevel):
    def __init__(self, master, sources, on_select, on_cancel=None):
        super().__init__(master)
        self.title("Wybierz źródło pobierania")
        self.on_select = on_select
        self.on_cancel = on_cancel
        self.var = tk.StringVar(value=sources[0])

        tk.Label(self, text="Wybierz źródło:").pack(pady=5)
        for src in sources:
            tk.Radiobutton(self, text=src.capitalize(), variable=self.var, value=src).pack(anchor="w")
        tk.Button(self, text="OK", command=self.confirm).pack(pady=10)

        # Obsługa zamknięcia okna krzyżykiem
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        if self.on_cancel:
            self.on_cancel()
        self.destroy()

    def confirm(self):
        self.on_select(self.var.get())
        self.destroy()
