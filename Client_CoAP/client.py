import socket
import json
import struct
import threading
import queue
import time
#encoding
import base64
import ast

from message_parse import Message
from fragmentAsembler import FragmentAssembler
from Asembler import Asembler

PAYLOAD_MARKER = 0xFF

class ClientCoap:
    def __init__(self,server_ip = '127.0.0.1',server_port = 5683,client_port = 5003):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_port = client_port
        self.sock = None

        self.confirmable = Message.CON
        self.response_queue = queue.Queue()
        self.response_thread = None
        self.gui_callback = None  #callback pentru primire raspunsuri

    def set_confirmable(self):
        self.confirmable = Message.CON

    def set_unconfirmable(self):
        self.confirmable = Message.NON

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', self.client_port))
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.settimeout(0.5)

        self.response_thread = threading.Thread(target=self.response ,daemon=True)
        self.response_thread.start()

        self.sock.settimeout(5.0)
        print(f"[CLIENT] sock conectat si asculta pe portul {self.client_port}")

    def disconnect(self):
        self.sock.close()

    def send_ack(self, msg_id, server_addr, code=0):

        version = 1
        msg_type = Message.ACK  # ACK type = 2
        tkl = 0
        first_byte = (version << 6) | (msg_type << 4) | tkl
        
        header = struct.pack("!BBH", first_byte, code, msg_id)
        packet = header
        
        try:
            self.sock.sendto(packet, server_addr)
            print(f"[CLIENT] ACK trimis pentru fragment (Msg ID: {msg_id})")
        except Exception as e:
            print(f"[CLIENT X] Eroare trimitere ACK: {e}")

    def send_request(self,code,msg_type = Message.CON,payload = None):
        m = Message(code, msg_type, payload)
        packet, msg_id = m.parse_packet()

        print(f"[CLIENT] trimte cererea: (Code: {code}),Msg ID: {msg_id}) catre {self.server_ip}")
        try:
            self.sock.sendto(packet, (self.server_ip,self.server_port))

        except socket.timeout:
            print(f"[CLIENT X] Timeout: Serverul nu a răspuns în 5 secunde.")
            return {"status": "error", "message": "Timeout"}

        except Exception as e:
            print(f"[CLIENT X] Eroare de comunicare: {e}")
            return {"status": "error", "message": str(e)}

    def response(self):
        assembler = FragmentAssembler()
        while True:
            try:
                response_data, server_addr = self.sock.recvfrom(14000)
                print("Teo")
                if len(response_data) < 4:
                    raise ValueError("Response data is too short")

                first_byte, code,msg_id = struct.unpack("!BBH",response_data[:4])
                version = (first_byte >> 6) & 0x03
                msg_type = (first_byte >> 4) & 0x03
                tkl = first_byte & 0x0F

                payload_dict = None
                if 0xFF in response_data:
                    try:
                        _, payload_part = response_data.split(bytes([0xFF]), 1)
                        if payload_part:
                            payload_dict = json.loads(payload_part.decode('utf-8'))
                    except json.JSONDecodeError:
                        print("[CLIENT] Eroare decodare JSON payload")
                    except Exception as e:
                        print(f"[CLIENT] Eroare parsare payload: {e}")

                if msg_type == Message.ACK:
                    log_msg = f"ACK primit (Msg ID: {msg_id}, Code: {code})"
                    self.response_queue.put({"status": "ack", "message": log_msg})

                    # Daca e un ACK gol (Code 0), nu mai avem ce procesa
                if code == 0 and payload_dict is None:
                    continue
                current_msg = Message(code, msg_type, payload_dict, msg_id=msg_id)

                is_fragment = (msg_type == Message.CON and 
                              payload_dict and 
                              isinstance(payload_dict, dict) and 
                              "fragment" in payload_dict and
                              isinstance(payload_dict.get("fragment"), dict) and
                              "index" in payload_dict.get("fragment", {}))
                
                if is_fragment:
                    # Send ACK for the fragment
                    self.send_ack(msg_id, server_addr, code=0)
                    frag_info = payload_dict.get("fragment", {})
                    frag_index = frag_info.get("index", "?")
                    frag_total = frag_info.get("total", "?")

                    frag_msg = f"Fragment {frag_index+1}/{frag_total} receptionat, ACK trimis"
                    print(f"[CLIENT] {frag_msg} (Msg ID: {msg_id})")
                    # Also notify GUI about fragment reception
                    if self.gui_callback:
                        try:
                            self.gui_callback({"status": "fragment", "message": frag_msg, "index": frag_index, "total": frag_total})
                        except Exception as e:
                            print(f"[CLIENT X] Error updating GUI for fragment: {e}")

                processed_msg = assembler.handle_if_fragment(current_msg)
                final_payload = processed_msg.get_payload()


                if final_payload:
                    is_simple_ack = (msg_type == Message.ACK and code == 0)

                    if not is_simple_ack:
                        self.response_queue.put(final_payload)

            except socket.timeout:
                continue
            except OSError as e:
                if 'closed' in str(e):
                    print("[CLIENT X] Response thread detected socket closed.")
                    break
                else:
                    print(f"[CLIENT X] OSError in response thread: {e}")
                    break
            except Exception as e:
                print(f"[CLIENT X] Unexpected error in response thread: {e}")
                break
    def set_gui_callback(self, callback):
        self.gui_callback = callback

    def response_handler(self):
        while True:
            response = self.response_queue.get()
            print(f"[SERVER] {response}")

            if self.gui_callback:
                try:
                    self.gui_callback(response)
                except Exception as e:
                    print(f"[CLIENT X] Error updating GUI: {e}")

    def send_get(self,path):
        path = {"path":path}
        self.send_request(Message.GET, self.confirmable,path)

    def send_post(self,path,payload):

        path = f"storage/{path}"# pentru incarcare unui fisier avem nevoie de "storage/"

        if isinstance(payload, str):
            payload_bytes = payload.encode('utf-8')
        else:
            payload_bytes = payload

        content_b64 = base64.b64encode(payload_bytes).decode("utf-8")
        
        asm = Asembler()
        nr_fragments = asm.fragmente_necesare(content_b64)
        
        if nr_fragments == 1:
            #no fragmentation neded
            path_dict = {"path": path, "content": content_b64}
            self.send_request(Message.POST, self.confirmable, path_dict)
        else:
            fragments = asm.split_in_fragments(content_b64, path)
            print(f"[CLIENT] Fragmenting payload into {nr_fragments} fragments for path: {path}")
            
            for fragment in fragments:
                self.send_request(Message.POST, self.confirmable, fragment)
                time.sleep(0.01)

    def send_delete(self,path):
        path = {"path":path}
        self.send_request(Message.DELETE,self.confirmable,path)

    def send_move(self,path,new_path):
        path = {"source":path}
        if new_path:
            path["destination"] = new_path
        print(path)
        self.send_request(Message.MOVE,self.confirmable,path)

    def start_threading(self):
        handle_thread = threading.Thread(target=self.response_handler, args=(), daemon=True)
        handle_thread.start()

    def send_get_thread(self,path):
        send_get_thread = threading.Thread(target=self.send_get, args=(path,), daemon=True)
        send_get_thread.start()

    def send_post_thread(self,path,payload):
        send_thread = threading.Thread(target=self.send_post, args=(path,payload), daemon=True)
        send_thread.start()

    def send_delete_thread(self,path):
        send_delete_thread = threading.Thread(target=self.send_delete, args=(path,), daemon=True)
        send_delete_thread.start()

    def send_move_thread(self, path, new_path):
        send_move_thread = threading.Thread(target=self.send_move, args=(path,new_path), daemon=True)
        send_move_thread.start()
'''
if __name__ == '__main__':

    c1 = ClientCoap()
    c1.connect()

    c1.start_threading()
    c1.send_post_thread("storage/teo.txt",payload="teo"*100000)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[MAIN] Oprire client.")
        c1.disconnect()
'''








