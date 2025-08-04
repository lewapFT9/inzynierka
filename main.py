import tkinter as tk
from gui.main_window import ImageDownloaderGUI

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageDownloaderGUI(root)
    root.mainloop()