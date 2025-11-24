import random
import socket
import json
import struct
<<<<<<< HEAD
import threading
import queue
=======
>>>>>>> 1a0431c924717be64328acf5c6daf2d3527431e5

SERVER_IP = '127.0.0.1'
SERVER_PORT = 5683
CLIENT_PORT = 5003
PAYLOAD_MARKER = 0xFF

def parse_coap_header( code :int,payload:dict = None,msg_type: int = 0 ):

    msg_id = random.randint(0, 0xFFFF)
    version = 1
    tkl = 0 # Nu folosim token

    first_byte = (version << 6) | (msg_type << 4) | tkl

    # Pachetul binar: (Byte 1, Byte Code, Message ID)
    header = struct.pack("!BBH", first_byte, code, msg_id)

    #Punem payload in Json
    packet = header
    if payload:
        json_bytes = json.dumps(payload).encode('utf-8')
        packet += bytes([PAYLOAD_MARKER])
        packet += json_bytes

    return packet, msg_id

def send_request(sock,code:int, payload:dict = None, msg_type: int = 0):
    packet, msg_id = parse_coap_header(code,payload,msg_type)

    print(f"[CLIENT] trimte cererea: (Code: {code}),Msg ID: {msg_id}) catre {SERVER_IP}")
    try:
        sock.sendto(packet, (SERVER_IP, SERVER_PORT))

    except socket.timeout:
        print(f"[CLIENT X] Timeout: Serverul nu a răspuns în 5 secunde.")
        return {"status": "error", "message": "Timeout"}
    except Exception as e:
        print(f"[CLIENT X] Eroare de comunicare: {e}")
        return {"status": "error", "message": str(e)}

def response(sock,response_queue):
    # Raspunsul de la server
    response_data, server_addr = sock.recvfrom(4096)

    if (len(response_data) < 4):
        raise ValueError("Response data is too short")

    response_first_byte, response_code, response_msg_id = struct.unpack("!BBH", response_data[:4])
    response_type = (response_first_byte >> 4) & 0x03
    print(f"[CLIENT] primeste raspunsul : (Code:{response_code},Type:{response_type},Msg ID:{response_msg_id})")
    # In cazul in care avem payload
    if PAYLOAD_MARKER in response_data:
        response_payload = response_data.split(b'\xff')[1]
        try:
            response_queue.put(json.loads(response_payload.decode('utf-8')))
        except json.JSONDecodeError:
            response_queue.put({"status": "error", "message": "Json Invalid"})
    response_queue.put({"status": "corect", "message": "ACK primit fara payload"})

def response_handler(response_queue):
    response = response_queue.get()
    print(f"[SERVER] {response}")

if __name__ == '__main__':
    # socket initialization
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #sock.bind((SERVER_IP, CLIENT_PORT))
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    response_queue = queue.Queue()

    sock.settimeout(5.0)
    print("[SERVER] bind success")

    download = {"path":"/home/text.txt"}
    send_thread = threading.Thread(target=send_request, args=(sock,1,download,0))
    resp_thread = threading.Thread(target=response, args=(sock,response_queue))
    handle_thread = threading.Thread(target=response_handler, args=(response_queue,))

    send_thread.start()
    resp_thread.start()
    handle_thread.start()
    #response = send_request(sock, 1, payload=download, msg_type=0)

    send_thread.join()
    resp_thread.join()
    handle_thread.join()

    #response = response_queue.get()
    #print(f"[SERVER] {response}")
    sock.close()



