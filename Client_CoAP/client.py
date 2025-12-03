import socket
import json
import threading
import queue
from message_parse import Message

PAYLOAD_MARKER = 0xFF

class ClientCoap:
    def __init__(self,server_ip = '127.0.0.1',server_port = 5683,client_port = 5003):
        self.server_ip = server_ip
        self.server_port = server_port
        self.client_port = client_port
        self.sock = None

        self.response_queue = queue.Queue()
        self.response_thread = None

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
        while True:
            try:
                response_data, server_addr = self.sock.recvfrom(4096)
                if len(response_data) < 4:
                    raise ValueError("Response data is too short")

                response_payload = Message.parse_coap_header(response_data)
                try:
                    self.response_queue.put(json.loads(response_payload.decode('utf-8')))
                except json.JSONDecodeError:
                    self.response_queue.put({"status": "error", "message": "Json Invalid"})
                self.response_queue.put({"status": "corect", "message": "ACK primit fara payload"})
            except socket.timeout:
                continue  # Timeout occurred, keep listening
            except OSError as e:
                # Catches socket closing error
                if 'closed' in str(e):
                    print("[CLIENT X] Response thread detected socket closed.")
                    break
                else:
                    print(f"[CLIENT X] OSError in response thread: {e}")
                    break
            except Exception as e:
                print(f"[CLIENT X] Unexpected error in response thread: {e}")
                break
    def response_handler(self):
        while True:
            response = self.response_queue.get()
            print(f"[SERVER] {response}")



if __name__ == '__main__':

    c1 = ClientCoap()
    c1.connect()
    download = {"path":"/home/text.txt"}
    send_thread = threading.Thread(target=c1.send_request, args=(1,0,download))
    handle_thread = threading.Thread(target=c1.response_handler, args=(),daemon=True)

    send_thread.start()
    handle_thread.start()

    send_thread.join()







