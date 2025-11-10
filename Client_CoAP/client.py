import socket
import threading

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5001

#socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(5.0)
