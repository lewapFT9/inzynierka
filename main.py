import ctypes
import tkinter as tk
import os
import sys
from gui.mode_selector import ModeSelectorWindow

# =========================
# APP USER MODEL ID (WINDOWS TASKBAR)
# =========================
APP_ID = "pawel.inzynierka.imagedownloader"
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)


def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


if __name__ == "__main__":
    root = tk.Tk()

    # IKONA OKNA
    try:
        root.iconbitmap(resource_path("assets/logo.ico"))
    except Exception:
        pass

    # fallback (Linux / macOS)
    try:
        root.iconphoto(
            True,
            tk.PhotoImage(file=resource_path("assets/logo_256x256.png"))
        )
    except Exception:
        pass

    root.title("INŻYNIERKA")
    root.geometry("350x350")

    ModeSelectorWindow(root)
    root.mainloop()
