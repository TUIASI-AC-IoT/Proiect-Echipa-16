import json
import random
import struct


class Message:
    CON = 0 #Confirmable
    NON = 1 #Non confirmable
    ACK = 2 #Aacknowledgement

    GET = 1
    POST = 2
    DELETE = 3
    MOVE = 4

    PAYLOAD_MARKER = 0xFF

    def __init__(self,code:int,msg_type = CON,payload = None, msg_id = None):
        self.version = 1
        self.msg_type = msg_type
        self.tkl = 0
        self.code = code
        if msg_id is not None:
            self.msg_id = msg_id
        else:
            self.msg_id = random.randint(0, 0xFFFF)

        self.payload = payload

    def parse_packet(self):

        first_byte = (self.version << 6) | (self.msg_type << 4) | self.tkl

        # Pachetul binar: (Byte 1, Byte Code, Message ID)
        header = struct.pack("!BBH", first_byte, self.code, self.msg_id)

        # Punem payload in Json
        packet = header
        if self.payload:
            json_bytes = json.dumps(self.payload).encode('utf-8')
            packet += bytes([self.PAYLOAD_MARKER])
            packet += json_bytes

        return packet, self.msg_id

    def parse_coap_header(response_data):
        response_first_byte, response_code, response_msg_id = struct.unpack("!BBH", response_data[:4])
        response_type = (response_first_byte >> 4) & 0x03
        print(f"[CLIENT] primeste raspunsul : (Code:{response_code},Type:{response_type},Msg ID:{response_msg_id})")
        # In cazul in care avem payload
        if 0xFF in response_data:
            response_payload = response_data.split(b'\xff')[1]
        return response_payload

    def get_payload(self):
        return self.payload


download = {"path":"/home/text.txt"}
msg = Message(1,0,download)
pack,m = msg.parse_packet()
print(pack)
print (msg.get_payload())