"""Entry point — run with: python main.py"""

import sys
import os

# Ensure the package directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from gui import KaraokeApp


def main() -> None:
    root = tk.Tk()
    root.title("Karaoke Generator — by Frank")
    root.geometry("760x600")
    root.minsize(640, 500)
    root.resizable(True, True)
    app = KaraokeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
