import socket
import json
import struct


# Setări server
SERVER_IP = "0.0.0.0"
SERVER_PORT = 5683
PAYLOAD_MARKER = 0xFF



def parse_coap_header(data):
    """Parsează primii 4 bytes ai headerului CoAP"""
    if len(data) < 4:
        raise ValueError("Pachet prea scurt pentru header CoAP")

    # Despachetăm primii 4 bytes: (Version/Type/TKL, Code, Message ID)
    first_byte, code, msg_id = struct.unpack("!BBH", data[:4])

    version = (first_byte >> 6) & 0x03
    msg_type = (first_byte >> 4) & 0x03
    tkl = first_byte & 0x0F

    header = {
        "version": version,
        "type": msg_type,
        "tkl": tkl,
        "code": code,
        "message_id": msg_id
    }

    return header


def parse_packet(data):
    if PAYLOAD_MARKER in data:
        header_part, payload_part = data.split(bytes([PAYLOAD_MARKER]), 1)
    else:
        header_part, payload_part = data, b""

    header = parse_coap_header(header_part)

    payload = {}
    if payload_part:
        try:
            payload = json.loads(payload_part.decode('utf-8'))
        except json.JSONDecodeError:
            print("[!] Eroare parsare JSON payload")

    return header, payload


def build_and_send_acknowledgement(sock, client_addr, msg_id, info="OK"):
    """
    Trimite un mesaj CoAP de tip ACK (type = 2) către clientul care a trimis un CON.

    sock        -> socket-ul UDP deja deschis
    client_addr -> (ip, port) al clientului
    msg_id      -> Message ID al cererii originale (trebuie să fie același!)
    info        -> mesaj text/JSON trimis în payload (opțional)
    """

    # --- Header CoAP ---
    version = 1
    msg_type = 2  # ACK
    tkl = 0
    code = 69  # 2.05 Content (răspuns OK)
    first_byte = (version << 6) | (msg_type << 4) | tkl

    header = struct.pack("!BBH", first_byte, code, msg_id)

    # --- Payload JSON ---
    payload = json.dumps({"response": info}).encode("utf-8")

    # --- Pachet final ---
    packet = header + bytes([PAYLOAD_MARKER]) + payload

    # --- Trimitem pachetul ---
    sock.sendto(packet, client_addr)
    print(f"[<] Trimis ACK către {client_addr} (msg_id={msg_id}, code={code})")


def handle_request(header, payload, client_addr, sock):
    """Procesează cererea primită în funcție de codul CoAP"""
    code = header.get("code")
    msg_type = header.get("type")
    msg_id = header.get("message_id")
    if msg_type == 0:
        build_and_send_acknowledgement(sock, client_addr, msg_id)
    if code == 1:
        print("download fisier")
    elif code == 2:
        print("upload fisier")
    elif code == 4:
        print("delete fisier")
    else:
        print("cod necunoscut!")


if __name__ == "__main__":
    nr_cereri = 0
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SERVER_IP, SERVER_PORT))
    print(f"[+] Server ascultă pe {SERVER_IP}:{SERVER_PORT}")

    while nr_cereri < 4:
        data, client_addr = sock.recvfrom(4096)
        print(f"[>] Pachet primit de la {client_addr}")
        nr_cereri += 1
        header, payload = parse_packet(data)
        if header:
            handle_request(header, payload, client_addr, sock)