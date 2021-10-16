import sys 
import json 
import io 
import struct
import threading
import logging
from abc import ABC, abstractmethod
from socket import *
import selectors

from protocol import mHTTPProtocol

sel = selectors.DefaultSelector()

class ClientmHTTPSocket(socket, mHTTPProtocol):
    """ Implements mHTTP client-side."""
    def __init__(self, mode, index=None, data=None):
        socket.__init__(self,AF_INET, SOCK_STREAM)
        mHTTPProtocol.__init__(self)
        # Request attributes
        self._buffer = b""
        self._mHTTPheaders_len = None
        self.mHTTPheader = None 
        self.json = None

        assert mode in ['w','r']
        self.mode = mode 
        self.index = index 
        self.data = data

    def _read(self):
        try:
            data = super(socket,self).recv(4096)
        except BlockingIOError:
            pass 
        else:
            if data:
                self._buffer += data
            else:
                raise RuntimeError("Connection closed.")

    def _extract_mHTTP_header(self, header):
        """
        Example mHTTP header:
        GET 127.0.0.1 HTTP/1.1
        byteorder: big-endian
        content-type: text/json
        content-length: 2
        content-encoding: utf-8
        """
        headers = {}
        lines = header.split('\n')
        assert lines[0].startswith('HTTP') or lines[0].startswith(' HTTP')
        lines = lines[1:] # First line is a HTTP GET.
        for line in lines:
            assert len(line.split(':')) == 2
            header, value = line.split(':')
            header = header.strip()
            value = value.strip()
            headers[header] = value 
        return headers
        
    def process_server_answer(self):
        self._read()
        if not self._mHTTPheaders_len:
            self._process_proto_header()
        
        if not self.httpheader:
            self._process_mHTTP_headers()
        
        self.process_request()
    
    def _create_json_body(self):
        query = {}
        query['action'] = 'read' if self.mode == 'r' else 'write'
        query['index'] = self.index 
        query['data'] = self.data 
        self.json = json.dumps(query)

    def _create_mHTTPheader_request(self):
        content_len = len(bytes(self.json,'utf8'))+1
        headers = ['GET 127.0.0.1 HTTP/1.1',
                  'bytorder: big-endian',
                  'content-type: text/json',
                  f'content-length: {content_len}',
                  'content-encoding: utf-8']
        self.response_mHTTPheader = bytes('\n'.join(headers),encoding='utf-8')

    def _create_proto_header_response(self):
        # Write length of mHTTP header in a big-endian format with 2 bytes.
        # NOTE: We add one for the number of bytes to account
        #       for the whitespace added for extracting.
        self._mHTTPheaders_len = struct.pack(">H", len(self.response_mHTTPheader)+1)

    def send(self):
        if not self.json:
            self._create_json_body()
        
        self._create_mHTTPheader_request()
        self._create_proto_header_response()
        self._buffer += self._mHTTPheaders_len
        self._buffer += b" "
        self._buffer += self.response_mHTTPheader
        self._buffer += b" "
        self._buffer += bytes(self.json,'utf-8')
        self._send_request()
    
    def _send_request(self):
        if self._buffer:
            try:
                total_sent = 0
                while total_sent < len(self._buffer):
                    sent = super(socket,self).send(self._buffer[total_sent:])
                    if sent == 0:
                        raise RuntimeError(f"Lost connectiong to server.")
                    total_sent += sent
            except BlockingIOError:
                pass
            finally:
                # If data sent properly empty the buffer and header attributes 
                # for later usage of reading response.
                self._buffer = b"" 
                self._mHTTPheaders_len = None
                self.mHTTPheader = None 
                self.json = None
        else:
            self._buffer = self._buffer[total_sent:]
            # Close when buffer is drained and response has been sent.
            if sent and not self._buffer:
                super(socket,self).close()

    def _server_socket_process_wrapper(self):
        self._process_socket_data()
        if self.mHTTPheader['content-type'] == 'text/json':
            print("Recived answer:", self.json['data'], "from server.")
        else:
            print(f"Recieved {content_type} data from server.")
    
    def recv(self):
        self._read()
        #print(repr(self._buffer))
        if not self._mHTTPheaders_len:
            self._process_proto_header()
        
        if not self.mHTTPheader:
            self._process_mHTTP_headers()
        
        self._server_socket_process_wrapper()
    
    def close(self):
        try:
            super(socket,self).close()
        except OSError as e:
            print(f"Error: can't close socket. Exception: {repr(e)}.")

HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 65432  # The port used by the server
num_conns = 5 

def start_connections(host, port, num_conns):
    server_addr = (host, port)
    for i in range(0, num_conns):
        connid = i + 1
        print("starting connection", connid, "to", server_addr)
        sock = ClientmHTTPSocket('r',i)
        sock.setblocking(False)
        sock.connect_ex(server_addr)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        sel.register(sock, events)


def handle_connection(key, mask):
    sock = key.fileobj
    if mask & selectors.EVENT_READ:
        sock.recv()
    if mask & selectors.EVENT_WRITE:
        sock.send()


"""
start_connections(HOST, PORT, num_conns)
try:
    while True:
        events = sel.select(timeout=1)
        if events:
            for key, mask in events:
                handle_connection(key, mask)    
        # Check for a socket being monitored to continue.
        if not sel.get_map():
            break
except KeyboardInterrupt:
    print("caught keyboard interrupt, exiting")
finally:
    sel.close()

"""
with ClientmHTTPSocket('r',5) as s:
    s.connect((HOST, PORT))
    s.send()
    data = s.recv()
