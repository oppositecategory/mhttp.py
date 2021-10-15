import threading 
import socket
import logging
from abc import ABC, abstractmethod

import protocol


class WebServer(ABC):
    """ Implement WebServer interface.
    """
    def __init__(self, host:tuple, max_conn:int):
        self.addr = addr
        self.max_conn = max_conn
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lsock.bind((self.server_host, self.server_port))
    
    @abstractmethod
    def _handler_request(self, s, _addr):
        pass 

    def run(self):
        pass


class MultiThreadedWebServer(WebServer):
    """ Implementes a multithreaded webserver. 
        The server opens a non-blocking socket for connection and for each socket
        reaching the server we open a thread to handle communication with the socket.

        NOTE: Multithreaded server designed this way isn't optimal and suffers mainly from threads
              scaling with the number of requests. Numeroues threads can consume computation power plus
              handling threads requires us to add mutex locks when needed to avoid race conditions. 
              Such locks force us to wait on I/O operations.
        """
    def __init__(self, adrr:tuple, max_conn:int):
        super(addr, max_conn).__init__()
        
    def run(self):
        lsock.listen(self.max_conn)
        lsock.setblocking(False)
        log.info(f"Listening on: {self.addr} and port: {self.port}")
        try:
            while True:
                s, sock_addr = self.lsock.accept()
                handler = protocol.ThreadedSocketProtocol(s, sock_addr)
                conn.setblocking(False)
                logging.info(f"Connection request made from {sock_addr}.")
                threading.Thread(target=handler.read(), args=(s, sock_addr)).start()
        except KeyboardInerrupt:
            logging.info(f"Keybaord inetrrupt, exiting.")





