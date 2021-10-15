import threading 
import socket
import logging

import protocol


class WebServer:
    def __init__(self, host:str, port:int, max_conn:int):
        self.server_host = host
        self.server_port = port
        self.max_conn = max_conn
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lsock.bind((self.server_host, self.server_port))
        self.storage = []

    def _handle_request(self, s, sock_addr):
        handler = protocol.NonBlockingSocketHandler(s, sock_addr)
        handler.read()
            
    def run(self):
        lsock.listen(self.max_conn)
        lsock.setblocking(False)
        log.info(f"Listening on: {self.addr} and port: {self.port}")
        try:
            while True:
                s, sock_addr = self.lsock.accept()
                conn.setblocking(False)
                logging.info(f"Connection request made from {sock_addr}.")
                threading.Thread(target=self.accept_request, args=(s, sock_addr)).start()
        except KeyboardInerrupt:
            logging.info(f"Keybaord inetrrupt, exiting.")





