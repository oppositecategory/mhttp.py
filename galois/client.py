import socket 
import threading 
from queue import Queue


HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 65432  # The port used by the server


def start_connections(host, port, num_conns):
    addr = (host, port)
    for i in range(num_conns):
        connid = i+1 
        print(f"Starting connection {connid} to {addr}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        set.blocking(False)
        sock.connect_ex(addr)
        #pool.put(sock)
        


if len(sys.argv) != 4:
    print("usage:", sys.argv[0], "<host> <port> <num_connections>")
    sys.exit(1)

host, port, num_conns = sys.argv[1:4]
start_connections(host, int(port), int(num_conns))
pool = Queue()