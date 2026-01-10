import json
from message_parse import *

class FragmentAssembler:
    MAX_SIZE_PACHET = 14000
    HEADER_SIZE = 4
    PAYLOAD_MARKER_SIZE = 1
    FRAGMENT_OVERHEAD = 200  # spatiu pentru metadata JSON

    MAX_PAYLOAD_SIZE = MAX_SIZE_PACHET - HEADER_SIZE - PAYLOAD_MARKER_SIZE - FRAGMENT_OVERHEAD

    PAYLOAD_MARKER = 0xFF
    def __init__(self):
        self.fragments = {}
        self.expected_total = {}

    def if_fragment(self,msg: Message):
        #return 1 if has fragments and 0 if not
        if "fragment" in msg.get_payload() :
            return 1
        return 0

    def handle_if_fragment(self,msg: Message):
        if self.if_fragment(msg):
            return msg

        path = msg.get_payload().get("path")
        index,total,size = self.get_fragment_info(msg)
        content = msg.get_payload().get("content")
        if path is None or index is None or total is None:
            return msg
        complete,assembled_content = self.add_fragment(path,index,total,content)
        if not complete:
            print(f"[CLIENT] Fragment {index}din {total} receptionat pt path:{path}")

        assembled_payload = {
            "path":path,
            "content":assembled_content.decode('UTF-8'),
            "fragment":{
                "index":index,
                "total":total,
                "size":size
            }
        }
        return Message(code = msg.code,
                       msg_type= msg.msg_type,
                       payload = assembled_payload,
                       msg_id= msg.msg_id)


    def get_fragment_info(self,msg: Message):
        frag = msg.get_payload().get("fragment",{})
        index = frag.get("index")
        total = frag.get("total")
        size = frag.get("size")
        return index,total,sizegit

    def add_fragment(self,path,index,total,content):
        if path not in self.fragments:
            self.fragments[path] = {}
            self.expected_total[path] = total
        self.fragments[path][index] = content

        if len(self.fragments[path]) == total:
            assembled =[]
            for i in range (total):
                if i not in self.fragments[path]:
                    return False, None
                assembled.append(self.fragments[path][i])
            assembled_content ="".join(assembled)
            del self.fragments[path]
            del self.expected_total[path]
            return True, assembled_content
        return False,None















