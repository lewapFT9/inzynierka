import tkinter as tk

class SourceSelector(tk.Toplevel):
    def __init__(self, master, sources, on_select):
        super().__init__(master)
        self.title("Wybierz źródło pobierania")
        self.on_select = on_select
        self.var = tk.StringVar(value=sources[0])

        tk.Label(self, text="Wybierz źródło:").pack(pady=5)
        for src in sources:
            tk.Radiobutton(self, text=src.capitalize(), variable=self.var, value=src).pack(anchor="w")
        tk.Button(self, text="OK", command=self.confirm).pack(pady=10)

    def confirm(self):
        self.on_select(self.var.get())
        self.destroy()
