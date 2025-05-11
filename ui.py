import tkinter as tk
from tkinter.constants import *

tk_scrn = tk.Tk()
frame = tk.Frame(tk_scrn, relief=RIDGE, borderwidth=2)
frame.pack(fill=BOTH,expand=1)
label = tk.Label(frame, text="Hello, World")
label.pack(fill=X, expand=1, side=TOP)
button = tk.Button(frame,text="Exit",command=tk_scrn.destroy)
button.pack(side=BOTTOM)
tk_scrn.mainloop()