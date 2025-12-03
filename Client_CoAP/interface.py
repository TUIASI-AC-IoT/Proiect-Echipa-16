from tkinter import *
from tkinter import ttk
import tkinter as tk


if __name__ == '__main__':
    root = Tk()
    root.title("Client CoAP")
    root.geometry("600x500")

    frm = ttk.Frame(root)
    frm.pack(fill = tk.X, padx = 6, pady = 6)

    btn_get = tk.Button(frm, text = "Get File",)
    btn_get.pack(side = tk.LEFT, padx = 4)

    btn_upload = tk.Button(frm, text = "Upload File(POST)",)
    btn_upload.pack(side = tk.LEFT, padx = 4)

    btn_delete = tk.Button(frm, text="DELETE", )
    btn_delete.pack(side=tk.LEFT, padx=4)

    btn_move = tk.Button(frm, text="MOVE", )
    btn_move.pack(side=tk.LEFT, padx=4)

    var_con = tk.BooleanVar(value = True)
    chk = tk.Checkbutton(frm, text="Confirmable Mesages", variable = var_con)
    chk.pack(side = tk.TOP, padx = 4)



    root.mainloop()

