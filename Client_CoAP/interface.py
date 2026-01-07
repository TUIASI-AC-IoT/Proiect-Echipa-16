from tkinter import *
from tkinter import ttk
from tkinter import filedialog
import tkinter as tk
from client import ClientCoap

# Global variables for GUI elements and client
T = None
root = None
client = None

import base64
import ast #for single quotes ' ' instead of json " "


def update_gui_with_response(response):
    if T and root:
        # If the response is a string representation of a dict, convert it
        if isinstance(response, str) and response.startswith("{"):
            try:
                response = ast.literal_eval(response)
            except Exception as e:
                print(f"Error parsing response string: {e}")

        if isinstance(response, dict):
            if "status" in response:
                if response["status"] == "ack":
                    message = f"[ACK] {response.get('message', '')}\n"
                elif response["status"] == "fragment":
                    frag_index = response.get("index", "?")
                    frag_total = response.get("total", "?")
                    message = f"[<-] {response.get('message', '')} ({frag_index + 1}/{frag_total})\n"
                else:
                    message = f"[{response.get('status', 'UNKNOWN')}] {response.get('message', '')}\n"

            elif "path" in response or "name" in response:
                # Support both 'path' or 'name' as per your first message
                path = response.get("path") or response.get("name", "unknown")
                raw_content = response.get("content", "")

                # decoding
                try:
                    # Decode Base64 to bytes, then to a UTF-8 string
                    decoded_bytes = base64.b64decode(raw_content)
                    content = decoded_bytes.decode('utf-8', errors='replace')
                except Exception as e:
                    print(f"Decoding error: {e}")
                    content = raw_content  #revert the changes

                fragment_info = response.get("fragment", {})
                if fragment_info:
                    frag_index = fragment_info.get("index", "?")
                    frag_total = fragment_info.get("total", "?")
                    frag_size = fragment_info.get("size", "?")
                    message = f"[<-] Received file (Fragment {frag_index + 1}/{frag_total}, {frag_size} bytes):\n  Path: {path}\n Content: {content}\n"
                else:
                    content_preview = content[:200] + "..." if len(content) > 200 else content
                    message = f"[<-] Received complete file from server:\n  Path: {path}\n  Size: {len(content)} bytes\n preview: {content_preview}\n"
            else:
                message = f"[<-] Response: {response}\n"
        else:
            message = f"[<-] Response: {response}\n"

        root.after(0, lambda msg=message: T.insert("1.0", msg))

def on_button_toggle():
    if var_con.get() == True:
        client.set_confirmable()
        print("Confirmable Mesages")
    else:
        client.set_unconfirmable()
        print("Unconfirmable Mesages")

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

    #CheckButton vor Con and Non-Con mesages
    var_con = tk.BooleanVar(value = True)
    chk = tk.Checkbutton(frm, text="Confirmable Mesages", variable = var_con,onvalue= True, offvalue = False, command= on_button_toggle)

    chk.pack(side = tk.TOP, padx = 4)

    root.mainloop()
    client.disconnect()

