from tkinter import *
from tkinter import ttk
from tkinter import filedialog
import tkinter as tk
from client import ClientCoap

client = ClientCoap()
client.connect()
client.start_threading()

def get_file_payload(filepath):
    with open(filepath, "r") as f:
        payload = f.read()
    return payload

def on_send_get():
    path = entry.get()
    print(f"[->] Sending File: {path}")
    client.send_get(path)

def on_upload_get():
    print(f"[->] Uploading File")
    filepath = filedialog.askopenfilename(title= "Select a file",filetypes= [("All Files","*.*")])
    print(filepath)
    payload = get_file_payload(filepath)
    client.send_post_thread(filepath,payload)

if __name__ == '__main__':
    root = Tk()
    root.title("Client CoAP")
    root.geometry("600x500")

    frm = ttk.Frame(root)
    frm.pack(fill = tk.X, padx = 6, pady = 6)

    entry = tk.Entry(root)
    entry.pack(padx=10, pady=10)

    btn_get = tk.Button(frm, text = "Get File",command= on_send_get)
    btn_get.pack(side = tk.LEFT, padx = 4)

    btn_upload = tk.Button(frm, text = "Upload File(POST)",command= on_upload_get)
    btn_upload.pack(side = tk.LEFT, padx = 4)

    btn_delete = tk.Button(frm, text="DELETE", )
    btn_delete.pack(side=tk.LEFT, padx=4)

    btn_move = tk.Button(frm, text="MOVE", )
    btn_move.pack(side=tk.LEFT, padx=4)

    var_con = tk.BooleanVar(value = True)
    chk = tk.Checkbutton(frm, text="Confirmable Mesages", variable = var_con)
    chk.pack(side = tk.TOP, padx = 4)






    root.mainloop()
    client.disconnect()

