import socket
import json
import struct
import math
import time

# --- Server Settings ---
SERVER_IP = "0.0.0.0"
SERVER_PORT = 5683
PAYLOAD_MARKER = 0xFF

# --- Fragmentation Constants ---
MAX_SIZE_PACHET = 14000
HEADER_SIZE = 4
FRAGMENT_OVERHEAD = 500  # Safe space reserved for JSON metadata (path, index, keys)
MAX_PAYLOAD_SIZE = MAX_SIZE_PACHET - HEADER_SIZE - 1 - FRAGMENT_OVERHEAD


def parse_coap_header(data):
    """Parses the first 4 bytes of the CoAP header"""
    if len(data) < 4:
        raise ValueError("Packet too short for CoAP header")

    first_byte, code, msg_id = struct.unpack("!BBH", data[:4])

    version = (first_byte >> 6) & 0x03
    msg_type = (first_byte >> 4) & 0x03
    tkl = first_byte & 0x0F

    return {
        "version": version,
        "type": msg_type,
        "tkl": tkl,
        "code": code,
        "message_id": msg_id
    }


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
            print("[!] JSON Parse Error")

    return header, payload


# --- 1. Fragmentation Logic ---
def split_payload(content, path):
    """Splits content into a list of JSON payloads"""
    total_len = len(content)
    # Calculate how many fragments are needed
    if total_len <= MAX_PAYLOAD_SIZE:
        total_fragments = 1
    else:
        total_fragments = math.ceil(total_len / MAX_PAYLOAD_SIZE)

    fragments = []

    for i in range(total_fragments):
        start = i * MAX_PAYLOAD_SIZE
        end = min(start + MAX_PAYLOAD_SIZE, total_len)
        chunk = content[start:end]

        # Structure expected by the Client Assembler
        fragment_payload = {
            "path": path,
            "content": chunk,
            "fragment": {
                "index": i,
                "total": total_fragments,
                "size": len(chunk)
            }
        }
        fragments.append(fragment_payload)

    return fragments


def send_fragmented_response(sock, client_addr, start_msg_id, path, content):
    """Orchestrates sending all fragments"""
    fragments = split_payload(content, path)
    print(f"[FRAGMENT] Splitting '{path}' ({len(content)} bytes) into {len(fragments)} fragments.")

    for i, frag_payload in enumerate(fragments):
        # Construct Header
        # We use Code 69 (2.05 Content) for the response
        version = 1
        msg_type = 0  # CON (Confirmable) - we want the client to process it
        tkl = 0
        code = 69

        # Increment Message ID for each packet so they are distinct
        current_msg_id = (start_msg_id + i + 1) % 0xFFFF

        first_byte = (version << 6) | (msg_type << 4) | tkl
        header = struct.pack("!BBH", first_byte, code, current_msg_id)

        # Construct Payload
        payload_bytes = json.dumps(frag_payload).encode("utf-8")

        # Combine
        packet = header + bytes([PAYLOAD_MARKER]) + payload_bytes

        # Send
        sock.sendto(packet, client_addr)
        print(f"[->] Sent Fragment {i + 1}/{len(fragments)} (Size: {len(packet)} bytes)")

        # Small sleep to prevent overflowing the UDP buffer if running locally
        time.sleep(0.05)

    # --- Existing ACK Logic ---


def build_and_send_acknowledgement(sock, client_addr, msg_id, info="OK"):
    version = 1
    msg_type = 2  # ACK
    tkl = 0
    code = 69  # 2.05 Content
    first_byte = (version << 6) | (msg_type << 4) | tkl

    header = struct.pack("!BBH", first_byte, code, msg_id)
    payload = json.dumps({"response": info}).encode("utf-8")
    packet = header + bytes([PAYLOAD_MARKER]) + payload

    sock.sendto(packet, client_addr)
    print(f"[<] Sent ACK to {client_addr} (msg_id={msg_id})")


def handle_request(header, payload, client_addr, sock):
    code = header.get("code")
    msg_type = header.get("type")
    msg_id = header.get("message_id")

    # 1. Always ACK the received Confirmable (CON) message first
    if msg_type == 0:
        build_and_send_acknowledgement(sock, client_addr, msg_id, "Request Received")

    # 2. Handle Logic
    if code == 1:  # GET Request (Download)
        path = payload.get("path", "unknown_file.txt")
        print(f"[OP] Client requested download: {path}")

        # --- SIMULATE LARGE FILE ---
        # Generate a dummy large text (e.g., ~50KB)
        large_content = f"Start of {path}\n" + ("ABC 123 " * 8000) + "\nEnd of File."

        # Send fragments
        send_fragmented_response(sock, client_addr, msg_id, path, large_content)

    elif code == 2:  # POST Request (Upload)
        print("[OP] Handling Upload...")
        # (Upload logic would go here)

    elif code == 4:  # DELETE Request
        print(f"[OP] Deleting {payload.get('path')}")

    else:
        print("[!] Unknown Code")


if __name__ == "__main__":
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SERVER_IP, SERVER_PORT))
    print(f"[+] Server listening on {SERVER_IP}:{SERVER_PORT}")

    while True:
        try:
            data, client_addr = sock.recvfrom(20000)
            print(f"\n[>] Packet received from {client_addr}")

            header, payload = parse_packet(data)
            if header:
                handle_request(header, payload, client_addr, sock)
        except KeyboardInterrupt:
            print("\nShutting down server.")
            break
        except Exception as e:
            print(f"Error: {e}")