import socket
import json
import struct
import os
import math
import time

"""
Server CoAP complet, folosit pentru testarea tuturor funcțiilor clientului:
 - GET    (download fișier, cu fragmentare dacă e mare)
 - POST   (upload fișier, cu re-asamblare dacă vine fragmentat)
 - DELETE (ștergere fișier)
 - MOVE   (mutare / redenumire fișier)

Clientul folosește același port (5683) și aceleași formate de payload
ca în Asembler.py și FragmentAssembler.py.
"""

# Setări server
SERVER_IP = "0.0.0.0"
SERVER_PORT = 5683
PAYLOAD_MARKER = 0xFF

# Fragmentare – aliniat la Asembler.py
MAX_SIZE_PACHET = 14000
HEADER_SIZE = 4
PAYLOAD_MARKER_SIZE = 1
FRAGMENT_OVERHEAD = 200  # spațiu pentru metadata JSON
MAX_PAYLOAD_SIZE = MAX_SIZE_PACHET - HEADER_SIZE - PAYLOAD_MARKER_SIZE - FRAGMENT_OVERHEAD


# -------- Utilitare CoAP --------

def parse_coap_header(data: bytes) -> dict:
    """Parsează primii 4 bytes ai headerului CoAP."""
    if len(data) < 4:
        raise ValueError("Pachet prea scurt pentru header CoAP")

    first_byte, code, msg_id = struct.unpack("!BBH", data[:4])

    version = (first_byte >> 6) & 0x03
    msg_type = (first_byte >> 4) & 0x03
    tkl = first_byte & 0x0F

    return {
        "version": version,
        "type": msg_type,
        "tkl": tkl,
        "code": code,
        "message_id": msg_id,
    }


def parse_packet(data: bytes):
    """Împarte pachetul în header (CoAP) și payload JSON."""
    if PAYLOAD_MARKER in data:
        header_part, payload_part = data.split(bytes([PAYLOAD_MARKER]), 1)
    else:
        header_part, payload_part = data, b""

    header = parse_coap_header(header_part)

    payload = {}
    if payload_part:
        try:
            payload = json.loads(payload_part.decode("utf-8"))
        except json.JSONDecodeError:
            print("[SERVER] Eroare parsare JSON payload")

    return header, payload


def build_and_send_acknowledgement(sock, client_addr, msg_id, info="OK"):
    """
    Trimite un mesaj CoAP de tip ACK (type = 2) către clientul care a trimis un CON.
    """
    version = 1
    msg_type = 2  # ACK
    tkl = 0
    code = 69  # 2.05 Content
    first_byte = (version << 6) | (msg_type << 4) | tkl

    header = struct.pack("!BBH", first_byte, code, msg_id)
    payload = json.dumps({"response": info}).encode("utf-8")
    packet = header + bytes([PAYLOAD_MARKER]) + payload

    sock.sendto(packet, client_addr)
    print(f"[ACK] Trimis ACK către {client_addr} (msg_id={msg_id}, code={code})")


# -------- Fragmentare RĂSPUNS (GET) --------

def split_payload(content: str, path: str):
    """Împarte conținutul în fragmente JSON (structură compatibilă cu FragmentAssembler)."""
    total_len = len(content)
    if total_len <= MAX_PAYLOAD_SIZE:
        total_fragments = 1
    else:
        total_fragments = math.ceil(total_len / MAX_PAYLOAD_SIZE)

    fragments = []
    for i in range(total_fragments):
        start = i * MAX_PAYLOAD_SIZE
        end = min(start + MAX_PAYLOAD_SIZE, total_len)
        chunk = content[start:end]

        fragment_payload = {
            "path": path,
            "content": chunk,
            "fragment": {
                "index": i,
                "total": total_fragments,
                "size": len(chunk),
            },
        }
        fragments.append(fragment_payload)

    return fragments


def send_fragmented_response(sock, client_addr, start_msg_id, path, content: str):
    """
    Trimite un răspuns (de ex. la GET) fragmentat în mai multe pachete CON,
    cu același format ca în server2.py / Asembler.py.
    """
    fragments = split_payload(content, path)
    print(
        f"[FRAGMENT] Splitting '{path}' ({len(content)} bytes) into {len(fragments)} fragments."
    )

    for i, frag_payload in enumerate(fragments):
        version = 1
        msg_type = 0  # CON
        tkl = 0
        code = 69  # 2.05 Content

        current_msg_id = (start_msg_id + i + 1) % 0xFFFF
        first_byte = (version << 6) | (msg_type << 4) | tkl
        header = struct.pack("!BBH", first_byte, code, current_msg_id)

        payload_bytes = json.dumps(frag_payload).encode("utf-8")
        packet = header + bytes([PAYLOAD_MARKER]) + payload_bytes

        sock.sendto(packet, client_addr)
        print(
            f"[->] Sent Fragment {i + 1}/{len(fragments)} "
            f"(Msg ID: {current_msg_id}, Size: {len(packet)} bytes)"
        )

        time.sleep(0.02)


# -------- Re-asamblare FRAGMENTE UPLOAD (POST) --------

class UploadFragmentAssembler:
    """Re-asamblează fragmentele de upload (POST) și scrie fișierul pe disc."""

    def __init__(self):
        self.fragments = {}  # path -> { index: content_str }
        self.expected_total = {}  # path -> total_fragments

    def add_fragment(self, path: str, index: int, total: int, content: str):
        if path not in self.fragments:
            self.fragments[path] = {}
            self.expected_total[path] = total

        self.fragments[path][index] = content

        if len(self.fragments[path]) == total:
            # Avem toate fragmentele, le asamblăm în ordine
            assembled = []
            for i in range(total):
                if i not in self.fragments[path]:
                    return False, None
                assembled.append(self.fragments[path][i])

            assembled_content = "".join(assembled)
            del self.fragments[path]
            del self.expected_total[path]
            return True, assembled_content

        return False, None


upload_assembler = UploadFragmentAssembler()


def ensure_parent_dir(path: str):
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


# -------- Handlere pentru coduri CoAP --------

def handle_get(header, payload, client_addr, sock):
    msg_id = header.get("message_id")
    path = payload.get("path")

    if not path:
        print("[OP][GET] Lipsă 'path' în payload")
        return

    print(f"[OP][GET] Client requested download: {path}")

    try:
        with open(path, "r") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"[OP][GET] Fișierul nu există: {path}")
        # Trimitem un singur răspuns cu eroare (NON-CON pentru simplitate)
        version = 1
        msg_type = 1  # NON
        tkl = 0
        code = 132  # 4.04 Not Found (8*16 + 4)
        first_byte = (version << 6) | (msg_type << 4) | tkl
        header_bytes = struct.pack("!BBH", first_byte, code, msg_id)
        payload_bytes = json.dumps(
            {"error": "File not found", "path": path}
        ).encode("utf-8")
        packet = header_bytes + bytes([PAYLOAD_MARKER]) + payload_bytes
        sock.sendto(packet, client_addr)
        return
    except Exception as e:
        print(f"[OP][GET] Eroare la citirea fișierului: {e}")
        return

    # Trimitem conținutul fragmentat (chiar și dacă e un singur fragment)
    send_fragmented_response(sock, client_addr, msg_id, path, content)


def handle_post(header, payload, client_addr, sock):
    code = header.get("code")
    msg_id = header.get("message_id")

    path = payload.get("path")
    content = payload.get("content", "")
    frag = payload.get("fragment")

    if not path:
        print("[OP][POST] Lipsă 'path' în payload")
        return

    # Daca nu avem fragment, e un upload mic -> scriem direct
    if not frag:
        print(f"[OP][POST] Upload mic primit pentru {path} (len={len(content)})")
        try:
            ensure_parent_dir(path)
            with open(path, "w") as f:
                f.write(content)
            print(f"[OP][POST] Fișier salvat: {path}")
        except Exception as e:
            print(f"[OP][POST] Eroare salvare fișier: {e}")
        return

    # Avem fragment
    index = frag.get("index")
    total = frag.get("total")
    size = frag.get("size")

    print(
        f"[FRAGMENT-POST] Fragment {index + 1}/{total} pentru upload {path} "
        f"(declared size={size}, real={len(content)})"
    )

    complete, assembled_content = upload_assembler.add_fragment(
        path, index, total, content
    )

    if complete:
        print(
            f"[FRAGMENT-POST] Toate fragmentele ({total}) au fost primite pentru {path}. "
            f"Scriem fișierul pe disc..."
        )
        try:
            ensure_parent_dir(path)
            with open(path, "w") as f:
                f.write(assembled_content)
            print(f"[OP][POST] Fișier upload complet: {path}")
        except Exception as e:
            print(f"[OP][POST] Eroare salvare fișier (asamblat): {e}")


def handle_delete(header, payload, client_addr, sock):
    path = payload.get("path")
    if not path:
        print("[OP][DELETE] Lipsă 'path' în payload")
        return

    print(f"[OP][DELETE] Solicitare ștergere: {path}")
    try:
        os.remove(path)
        print(f"[OP][DELETE] Fișier șters: {path}")
    except FileNotFoundError:
        print(f"[OP][DELETE] Fișier inexistent: {path}")
    except Exception as e:
        print(f"[OP][DELETE] Eroare ștergere: {e}")


def handle_move(header, payload, client_addr, sock):
    old_path = payload.get("path")
    new_path = payload.get("content")  # în client, new_path este trimis în 'content'

    if not old_path or not new_path:
        print("[OP][MOVE] Lipsă 'path' sau 'content' (new_path) în payload")
        return

    print(f"[OP][MOVE] Mutare {old_path} -> {new_path}")
    try:
        ensure_parent_dir(new_path)
        os.rename(old_path, new_path)
        print(f"[OP][MOVE] Fișier mutat cu succes")
    except FileNotFoundError:
        print(f"[OP][MOVE] Fișier sursă inexistent: {old_path}")
    except Exception as e:
        print(f"[OP][MOVE] Eroare mutare: {e}")


def handle_request(header, payload, client_addr, sock):
    """Procesează cererea primită în funcție de codul CoAP."""
    code = header.get("code")
    msg_type = header.get("type")
    msg_id = header.get("message_id")

    # 1. Trimitem ACK pentru mesajele CON (type = 0)
    if msg_type == 0:
        build_and_send_acknowledgement(sock, client_addr, msg_id, "Request Received")

    # 2. Tratamente în funcție de cod
    if code == 1:  # GET
        handle_get(header, payload, client_addr, sock)
    elif code == 2:  # POST (upload)
        handle_post(header, payload, client_addr, sock)
    elif code == 4:  # DELETE
        handle_delete(header, payload, client_addr, sock)
    elif code == 5:  # MOVE
        handle_move(header, payload, client_addr, sock)
    else:
        print(f"[OP] Cod necunoscut: {code}")


if __name__ == "__main__":
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SERVER_IP, SERVER_PORT))
    print(f"[+] Server ascultă pe {SERVER_IP}:{SERVER_PORT}")

    while True:
        try:
            data, client_addr = sock.recvfrom(20000)
            print(f"\n[>] Pachet primit de la {client_addr}")

        header, payload = parse_packet(data)
        if header:
            handle_request(header, payload, client_addr, sock)
        except KeyboardInterrupt:
            print("\n[SERVER] Oprire server.")
            break
        except Exception as e:
            print(f"[SERVER] Eroare: {e}")
