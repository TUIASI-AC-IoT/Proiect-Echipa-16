from enum import Enum
import json



class T(Enum):
    Confirmable = 0
    NonConfirmable = 1
    Acknowledgement = 2
    Reset = 3
#tipuri de cereri
class Code(Enum):
    GET = b'00000001'
    POST = b'00000010'
    PUT = b'00000011'
    DELETE = b'00000100'
    MOVE = b'00000101'
#options
class Option(Enum):
    FILE = "file"
    DIR = "dir"

class Message:
    __version = 0b01
    #versiune implicita
    def __init__(self ,token = None,option: Option = None, payload: dict = None):
        self.msg_type = T.Confirmable

        #viitor JSON
        self.payload = payload
        self.option = option
        self.code = b'00000000'
        self.token = token
        self.tokenLength = 0

    def pack(self) :
        msg = bytearray()

        if self.token is not None and self.token > 0:
            self.tokenLength = (self.token.bit_length() + 7) //8
        else:
            self.tokenLength = 0

        if self.tokenLength > 8:
            self.tokenLength = 8

        msg.append(((self.__version << 6) + (self.msg_type.value << 4) + self.tokenLength))

        # Ultimul pas: to_bytes() foloseste self.tokenLength calculat
        msg.extend(self.token.to_bytes(self.tokenLength))

        #option file/dir
        json_option = json.dumps(self.option.value)
        msg.extend(json_option.encode('utf-8'))

        #Marcator de payload
        msg.append(0xFF)
        json_payload = json.dumps(self.payload)
        msg.extend(json_payload.encode('utf-8'))

        return msg
    def addPayload(self, payload):
        self.payload = payload

    def addOption(self, option):
        self.option = option



json_msg = {
    "path": "/directory/file.txt",
    "content": "Data"
}
msg = Message(token = 3,option = Option.DIR,payload = json_msg)
print(msg.pack())
msg.addOption(Option.FILE)
print(msg.pack())

