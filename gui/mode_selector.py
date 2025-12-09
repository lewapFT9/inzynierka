import tkinter as tk



class ModeSelectorWindow:
    """
    Ekran startowy aplikacji:
    1. Pobieranie nowego zbioru
    2. Zmiana rozdzielczości istniejącego zbioru
    """

    def __init__(self, master: tk.Tk):
        self.master = master
        self.master.title("INŻYNIERKA – wybór trybu")

        frame = tk.Frame(master, padx=20, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text="Wybierz tryb pracy:",
            font=("Arial", 12, "bold")
        ).pack(pady=(0, 10))

        tk.Button(
            frame,
            text="📥 Pobierz nowy zbiór",
            height=2,
            command=self.open_downloader
        ).pack(fill="x", pady=5)

        tk.Button(
            frame,
            text="🖼️ Zmień rozdzielczość istniejącego zbioru",
            height=2,
            command=self.open_resize_existing
        ).pack(fill="x", pady=5)

    def reopen(self):
        """Ponownie pokazuje okno wyboru trybu."""
        self.master.deiconify()

    def _clear_root(self):
        """Czyści okno przed załadowaniem nowego modułu."""
        for w in self.master.winfo_children():
            w.destroy()

    def open_downloader(self):
        """Uruchamia GUI pobierania danych."""
        from gui.main_window import ImageDownloaderGUI

        self._clear_root()
        self.master.title("INŻYNIERKA – pobieranie zbioru")
        self.master.geometry("350x800")
        ImageDownloaderGUI(self.master)

    def open_resize_existing(self):
        from gui.resize_existing import ResizeExistingWindow
        """Uruchamia GUI zmiany rozdzielczości istniejącego zbioru."""
        self._clear_root()
        self.master.title("INŻYNIERKA – zmiana rozdzielczości")
        ResizeExistingWindow(self.master)
