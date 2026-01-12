import json
import struct
import math
from message_parse import *

#Fragmentare pachete pentru upload
class Asembler:
    MAX_SIZE_PACHET = 14000
    HEADER_SIZE = 4
    PAYLOAD_MARKER_SIZE = 1
    FRAGMENT_OVERHEAD = 200  # spatiu pentru metadata JSON

    MAX_PAYLOAD_SIZE = MAX_SIZE_PACHET - HEADER_SIZE - PAYLOAD_MARKER_SIZE - FRAGMENT_OVERHEAD
    PAYLOAD_MARKER = 0xFF
    def __init__(self):

        pass

    def fragmente_necesare(self,payload):
        size = len(payload)
        if size > self.MAX_PAYLOAD_SIZE:
            return math.ceil(size / self.MAX_PAYLOAD_SIZE)
        else:
            return 1

    def split_in_fragments(self,payload,path):
        nr_of_fragments = self.fragmente_necesare(payload)
        if nr_of_fragments ==1:
            return [{
                "path": path,
                "content": payload,
            }]
        fragments = []
        for i in range(nr_of_fragments):
            start = i*self.MAX_PAYLOAD_SIZE
            end = min((i + 1) * self.MAX_PAYLOAD_SIZE, len(payload))
            chunk = payload[start:end]

            fragment_payload = {
                "path": path,
                "content": chunk,
                "fragment": {
                    "index": i,
                    "total": nr_of_fragments,
                    "size": len(chunk),
                }
            }
            fragments.append(fragment_payload)
        return fragments

    def build_fragment_pachet(self,code, fragment_payload, msg_id, msg_type=0):
        version = 1
        tkl = 0

        first_byte = (version << 6) | (msg_type << 4) | tkl
        header = struct.pack("!BBH", first_byte, code, msg_id)

        payload = json.dumps(fragment_payload).encode("utf-8")
        packet = header + bytes([self.PAYLOAD_MARKER]) + payload

        return packet
    def build_fragments(self,path,code, payload, msg_id, msg_type=0):

        fragments = self.split_in_fragments(payload,path)
        packets = []
        for fragment in fragments:
            packet = self.build_fragment_pachet(code, fragment, msg_id, msg_type)
            packets.append(packet)
            print(packet)
        return packets

#asm = Asembler()
#asm.build_fragments("download/teo",1,"teo"*100000,1)

