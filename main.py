import tkinter as tk
from gui.mode_selector import ModeSelectorWindow

if __name__ == "__main__":
    root = tk.Tk()
    ModeSelectorWindow(root)
    root.geometry("350x350")
    root.mainloop()
