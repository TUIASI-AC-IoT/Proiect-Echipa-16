from tkinter import *
from tkinter import ttk
from tkinter import filedialog
import tkinter as tk
from client import ClientCoap

# Global variables for GUI elements and client
T = None
root = None
client = None

def update_gui_with_response(response):
    if T and root:
        # construim raspunsul de afisat pe textbox
        if isinstance(response, dict):
            if "status" in response:
                if response["status"] == "ack":
                    message = f"[ACK] {response.get('message', '')}\n"
                elif response["status"] == "fragment":
                    frag_index = response.get("index", "?")
                    frag_total = response.get("total", "?")
                    message = f"[<-] {response.get('message', '')} ({frag_index+1}/{frag_total})\n"
                else:
                    message = f"[{response.get('status', 'UNKNOWN')}] {response.get('message', '')}\n"
            elif "path" in response:

                path = response.get("path", "unknown")
                content = response.get("content", "")
                
                # pentru fragmente
                fragment_info = response.get("fragment", {})
                if fragment_info:
                    frag_index = fragment_info.get("index", "?")
                    frag_total = fragment_info.get("total", "?")
                    frag_size = fragment_info.get("size", "?")
                    message = f"[<-] Received file (Fragment {frag_index+1}/{frag_total}, {frag_size} bytes):\n  Path: {path}\n"
                else:
                    #s-au strimis toate pachetele
                    content_preview = content[:200] + "..." if len(content) > 200 else content
                    message = f"[<-] Received complete file from server:\n  Path: {path}\n  Size: {len(content)} bytes\n preview: {content_preview}\n"
            else:
                message = f"[<-] Response: {response}\n"
        else:
            message = f"[<-] Response: {response}\n"
        
        # Use root.after() for thread-safe GUI update
        root.after(0, lambda msg=message: T.insert("1.0", msg))

def get_file_payload(filepath):
    with open(filepath, "r") as f:
        payload = f.read()
    return payload

def on_send_get():
    path = entry.get()
    T.insert("1.0",f"[->] Sending File from server: {path}\n")
    client.send_get_thread(path)

def on_send_upload():
    filepath = filedialog.askopenfilename(title= "Select a file",filetypes= [("All Files","*.*")])
    print(filepath)
    payload = get_file_payload(filepath)
    T.insert("1.0",f"[->] Uploading File on server: {filepath}\n")
    client.send_post_thread(filepath,payload)

def on_send_delete():
    filepath = entry.get()
    T.insert("1.0",f"[->] Deleting File: {filepath}\n")
    client.send_delete_thread(filepath)

def on_send_move():
    text = entry.get()
    txt = text.split(' to ')
    T.insert("1.0", f"[->] Moving File {txt[0]} to {txt[1]}\n")
    client.send_move_thread(txt[0],txt[1])


if __name__ == '__main__':
    root = Tk()
    root.title("Client CoAP")
    root.geometry("600x500")

    frm = ttk.Frame(root)
    frm.pack(fill = tk.X, padx = 6, pady = 6)

    entry = tk.Entry(root)
    entry.pack(padx=10, pady=10)

    #Text console with scrollbar
    text = ttk.Frame(root)
    text.pack(fill = tk.X, padx = 6, pady = 6)

    S = tk.Scrollbar(text)
    T = Text(text,height = 10,width = 50)
    S.config(command = T.yview)
    S.pack(side = tk.RIGHT,fill = tk.Y)
    T.pack(side = tk.LEFT,fill = tk.BOTH,expand = True)
    T.config(yscrollcommand = S.set)

    client = ClientCoap()
    client.connect()
    client.set_gui_callback(update_gui_with_response)
    client.start_threading()


    btn_get = tk.Button(frm, text = "Get File",command= on_send_get)
    btn_get.pack(side = tk.LEFT, padx = 4)

    btn_upload = tk.Button(frm, text = "Upload File(POST)",command= on_send_upload)
    btn_upload.pack(side = tk.LEFT, padx = 4)

    btn_delete = tk.Button(frm, text="DELETE",command= on_send_delete )
    btn_delete.pack(side=tk.LEFT, padx=4)

    btn_move = tk.Button(frm, text="MOVE",command = on_send_move )
    btn_move.pack(side=tk.LEFT, padx=4)

    var_con = tk.BooleanVar(value = True)
    chk = tk.Checkbutton(frm, text="Confirmable Mesages", variable = var_con)
    chk.pack(side = tk.TOP, padx = 4)

    root.mainloop()
    client.disconnect()

