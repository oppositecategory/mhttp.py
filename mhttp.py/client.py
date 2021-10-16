import sys 
import json 
import io 
import struct
import socket
import threading
import logging
from abc import ABC, abstractmethod

import protocol

#sel = selectors.DefaultSelector()
messages = [b"Message 1 from client.", b"Message 2 from client."]

def json_decode(raw_bytes, encoding):
    # Decode raw data sent over a socket into json using the encoding the client used.
    decoded = io.TextIOWrapper(
        io.BytesIO(raw_bytes, encoding=encoding,newline="")
    )
    obj = json.load(decoded)
    decoded.closer()
    return obj

class ClientmHTTPSocket(socket.socket):
    """ Implements mHTTP client-side."""
    def __init__(self, mode, index=None, data=None):
        super().__init__(socket.AF_INET, socket.SOCK_STREAM)
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
            data = super().recv(4096)
        except BlockingIOError:
            pass 
        else:
            if data:
                self._buffer += data
            else:
                raise RuntimeError("Connection closed.")

    def _process_proto_header(self):
        # Message Protocol assumes the first 2 bytes are reserved for the
        # variable-length of the HTTP header.
        headerlen = 2
        if len(self._buffer) >= headerlen:
            # Using format ">H" where ">" stands for big-endian format and 
            # "H" stands for unsigned char i.e 2-byte length data.
            self._mHTTPheaders_len = struct.unpack(
                ">H", self._buffer[:headerlen]
            )[0]
            # Points "point" to start of the HTTP header.
            self._buffer = self._buffer[headerlen:]

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
        print(lines[0])
        #assert lines[0].startswith('HTTP') or lines[0].startswith(' HTTP')
        lines = lines[1:] # First line is a HTTP GET.
        for line in lines:
            assert len(line.split(':')) == 2
            header, value = line.split(':')
            header = header.strip()
            value = value.strip()
            headers[header] = value 
        return headers
    
    def _process_mHTTP_headers(self):
        headers = {}
        headerlen = self._mHTTPheaders_len
        if len(self._buffer) >= headerlen:
            header = self._buffer[:headerlen].decode("utf-8")
            self._buffer = self._buffer[headerlen:]
            self.mHTTPheader = self._extract_mHTTP_header(header)
            for header in headers:
                if header not in self.mHTTPheader.keys():
                    raise ValueError(f"Missing required header {header}.")
    
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
        self.response_protoheader = struct.pack(">H", len(self.response_mHTTPheader)+1)

    def send(self):
        if not self.json:
            self._create_json_body()
        
        self._create_mHTTPheader_request()
        self._create_proto_header_response()
        self._buffer += self.response_protoheader
        self._buffer += b" "
        self._buffer += self.response_mHTTPheader
        self._buffer += b" "
        self._buffer += bytes(self.json,'utf-8')
        self._send_request()
    
    def _send_request(self):
        if self._buffer:
            print(f"Sending request to server.")
            try:
                total_sent = 0
                while total_sent < len(self._buffer):
                    sent = super().send(self._buffer[total_sent:])
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
                print("Buffer state after sending data:", self._buffer)
        else:
            self._buffer = self._buffer[total_sent:]
            # Close when buffer is drained and response has been sent.
            if sent and not self._buffer:
                super().close()

    def _process_socket_data(self):
        content_len = int(self.mHTTPheader['content-length'])
        if not len(self._buffer) >= content_len:
            return 
        data = self._buffer[:content_len] # Actual json content
        self._buffer = self._buffer[content_len:]
        if self.mHTTPheader['content-type'] == "text/json":
            encoding = self.mHTTPheader['content-encoding']
            decoded = data.decode(encoding)
            self.json = json.loads(decoded)
            print("Recived answer:", self.json['data'], "from server.")
        else:
            self.json = data 
            content_type = self.mHTTPheader["content-type"]
            #print(f"Recieved {content_type} data from server..")
    
    def recv(self):
        self._read()
        print(repr(self._buffer))
        if not self._mHTTPheaders_len:
            self._process_proto_header()
        
        if not self.mHTTPheader:
            self._process_mHTTP_headers()
        
        self._process_socket_data()
    
    def close(self):
        try:
            super().close()
        except OSError as e:
            print(f"Error: can't close socket. Exception: {repr(e)}.")

HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 65432  # The port used by the server

with ClientmHTTPSocket('r',1) as s:
    s.connect((HOST, PORT))
    s.send()
    data = s.recv()
