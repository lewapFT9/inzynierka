import tkinter as tk
from tkinter import ttk



class ModeSelectorWindow:
    """
    Ekran startowy aplikacji:
    1. Pobieranie nowego zbioru
    2. Zmiana rozdzielczości istniejącego zbioru
    """

    def __init__(self, master: tk.Tk):
        self.master = master
        self.master.title("INŻYNIERKA – wybór trybu")

        W, H = 420, 320
        self.master.geometry(f"{W}x{H}")
        self.master.resizable(False, False)
        self.master.configure(bg="#f4f6fb")

        root = tk.Frame(master, bg="#f4f6fb")
        root.pack(fill="both", expand=True)

        card = tk.Frame(root, bg="#ffffff", padx=24, pady=24)
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            card,
            text="Wybierz tryb pracy",
            font=("Segoe UI", 14, "bold"),
            fg="#1976d2",
            bg="#ffffff"
        ).pack(pady=(0, 20))

        def btn(text, cmd):
            return ttk.Button(
                card,
                text=text,
                command=cmd
            )

        btn("📥 Pobierz nowy zbiór", self.open_downloader).pack(fill="x", pady=6)
        btn("🖼️ Zmień rozdzielczość istniejącego zbioru", self.open_resize_existing).pack(fill="x", pady=6)

        ttk.Separator(card).pack(fill="x", pady=16)

        btn("ℹ️ Jak korzystać z aplikacji", self.open_about).pack(fill="x")

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

    def open_about(self):
        """Okno z instrukcją korzystania z aplikacji."""
        about = tk.Toplevel(self.master)
        about.title("O aplikacji")
        about.geometry("420x450")
        about.resizable(False, False)

        frame = tk.Frame(about, padx=20, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text="Jak korzystać z aplikacji",
            font=("Arial", 12, "bold")
        ).pack(pady=(0, 10))

        info_text = (
            "1. Wybierz tryb pracy na ekranie startowym.\n\n"
            "📥 Pobierz nowy zbiór:\n"
            "– wpisz hasło wyszukiwania\n"
            "– wybierz folder docelowy\n"
            "– ustaw filtry i podział zbioru\n"
            "– rozpocznij pobieranie\n\n"
            "🖼️ Zmień rozdzielczość istniejącego zbioru:\n"
            "– wybierz folder ze zdjęciami\n"
            "– ustaw rozmiar docelowy\n"
            "W każdej chwili możesz przerwać pobieranie.\n"
            "Aplikacja sprawdza połączenie z internetem\n"
            "i zabezpiecza dane przed nadpisaniem."
        )

        text = tk.Label(
            frame,
            text=info_text,
            justify="left",
            anchor="w",
            wraplength=380
        )
        text.pack(fill="x", pady=10)

        tk.Label(
            frame,
            text="Autor: Paweł Łopocki\nPraca inżynierska – Informatyka",
            font=("Arial", 9),
            fg="gray"
        ).pack(pady=(20, 0))

        tk.Button(
            frame,
            text="Zamknij",
            command=about.destroy
        ).pack(pady=10)
