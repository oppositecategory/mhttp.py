import json 
import struct
import socket
import threading
import logging
from abc import ABC, abstractmethod

import protocol 

# Global variables 
DB = [f'Bob number {i}' for i in range(10)]

def raw_json_encode(resp):
    dump = json.dumps(resp)
    raw_bytes = bytes(dump, 'utf-8')
    return raw_bytes

class ServerSocketHandler(protocol.mHTTPProtocol):
    def __init__(self, sock, addr):
        super().__init__()
        self.sock = sock 
        self.addr = addr
        

        self._send_buffer = b""
        self.response_flag = False 
        self.response_mHTTPheader = None
        self.response_protoheader = None 
        self.response_json = b""
        self.write_lock = threading.Lock()

    def _read(self):
        try:
            data = self.sock.recv(4096)
        except BlockingIOError:
            pass 
        else:
            if data:
                self._buffer += data
            else:
                print('Connection with  {} closed.'.format(self.addr))
                self.sock.close()
                #raise RuntimeError("Connection closed.")
    
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
        assert lines[0].startswith('GET') or lines[0].startswith(' GET')
        lines = lines[1:] # First line is a HTTP GET.
        for line in lines:
            assert len(line.split(':')) == 2
            header, value = line.split(':')
            header = header.strip()
            value = value.strip()
            headers[header] = value 
        return headers
    
    def _server_socket_process_wrapper(self):
        self._process_socket_data()
        if self.mHTTPheader['content-type'] == 'text/json':
            print("Recived request", repr(self.json), "from", self.addr)
        else:
            print(f"Recieved {content_type} request from {self.addr}.")
                
    def read(self):
        self._read()
        print(self._buffer)
        if not self._mHTTPheaders_len:
            self._process_proto_header()
        
        if not self.mHTTPheader:
            self._process_mHTTP_headers()
        
        self._server_socket_process_wrapper()
        self.callback_response()
    
    def query_database(self):
        action = self.json['action']
        if self.json['action'] == 'read':
            assert self.json['data'] == None 
            response = self.json 
            response['data'] = DB[response['index']]
            self.response_created = True
            self.response_json += raw_json_encode(response)
        else:
            # NOTE: No computation is actually done here but as a good 
            # practice we add mutex lock whenever we deal with data shared between threads.
            self.filesystem_lock.acquire()
            response = self.json 
            response['action'] = 'read' # Protocol assumes read action when sending data over network.
            DB[self.json['index']] = self.json['data']
            self.response_created = True 
            self.json_response += raw_json_encode(response)
            self.filesystem_lock.release()
        
    def _create_mHTTPheader_response(self):
        headers = ['HTTP/1.1 200 OK',
                  'bytorder: big-endian',
                  'content-type: text/json',
                  f'content-length: {len(self.response_json)+1}',
                  'content-encoding: utf-8']
        self.response_mHTTPheader = bytes('\n'.join(headers),encoding='utf-8')

    def _create_proto_header_response(self):
        # Write length of mHTTP header in a big-endian format with 2 bytes.
        self.response_protoheader = struct.pack(">H", len(self.response_mHTTPheader)+1)

    def send_response(self):
        if self._send_buffer:
            print(f"Sending response to {self.addr}")
            print("Response:", repr(self._send_buffer))
            try:
                total_sent = 0
                while total_sent < len(self._send_buffer):
                    sent = self.sock.send(self._send_buffer[total_sent:])
                    if sent == 0:
                        raise RuntimeError(f"Lost connectiong to {self.addr}")
                    total_sent += sent 
            except BlockingIOError:
                pass 
        else:
            self._send_buffer = self._send_buffer[sent:]
            # Close when buffer is drained and response has been sent.
            if sent and not self._send_buffer:
                self.close()

    def callback_response(self):
        if not self.response_flag:
            self.query_database()
        
        if not self.response_protoheader and self.response_created:
            self._create_mHTTPheader_response()
        
        if not self.response_protoheader and self.response_mHTTPheader != None:
            self._create_proto_header_response()
        # Accumulate whole headers together to be sent in right order in the buffer.
        self._send_buffer += self.response_protoheader
        self._send_buffer += b" "
        self._send_buffer += self.response_mHTTPheader
        self._send_buffer += b" "
        self._send_buffer += self.response_json
        self.send_response()
    
    def close(self):
        try:
            self.sock.close()
        except OSError as e:
            print(f"Error: can't close socket {self.addr} connect propery       Exception: {repr(e)}.")
        finally:
            self.sock = None

class WebServer:
    def __init__(self, addr, max_conn):
        self.addr = addr
        self.max_conn = max_conn
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lsock.bind(self.addr)
        
    def run(self):
        self.lsock.listen()
        print(f"Listening on: {self.addr}")
        #self.lsock.setblocking(False)
        try:
            while True:
                s, sock_addr = self.lsock.accept()
                s.setblocking(False)
                handler = ServerSocketHandler(s, sock_addr)
                logging.info(f"Connection request made from {sock_addr}.")
                threading.Thread(target=handler.read(), args=(s, sock_addr)).start()
        except KeyboardInterrupt:
            logging.info(f"Keybaord inetrrupt, exiting.")

class AsyncWebServer:
    def __init__(self, addr, max_conn):
        self.addr = addr 
        self.max_conn = max_conn 
        self.lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lsock.bind(addr)
    
    async def run(self):
        self.lsock.listen(10)
        self.lsock.setblocking(False)

        loop = asyncio.get_event_loop()

        requests = []
        while True:
            client, addr = await loop.sock_accept(self.lsock)
            handler = ServerSocketHandler(client, addr)
            requests.append(handler.read())
        asyncio.gather(*requests)


HOST = '127.0.0.1'
PORT = 65432
addr = (HOST,PORT)


server = WebServer(addr, 5)
server.run()
