import sys 
import json 
import io 
import struct
import socket
import threading
import logging
from abc import ABC, abstractmethod




class ServerSocketHandler:
    def __init__(self, sock, addr):
        self.sock = sock 
        self.addr = addr
        self._buffer = b""
        self._mHTTPheaders_len = None 
        self.mHTTPheader = None 
        self.json = None 

        self._send_buffer = b""
        self.response_flag = False 
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
        assert lines[0].startswith('GET') or lines[0].startswith(' GET')
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
        #print(self._buffer[:headerlen])
        if len(self._buffer) >= headerlen:
            header = self._buffer[:headerlen].decode("utf-8")
            self._buffer = self._buffer[headerlen:]
            self.mHTTPheader = self._extract_mHTTP_header(header)
            for header in headers:
                if header not in self.mHTTPheader.keys():
                    raise ValueError(f"Missing required header {header}.")

    def _process_socket_data(self):
        content_len = int(self.mHTTPheader['content-length'])
        if not len(self._buffer) >= content_len:
            return 
        data = self._buffer[:content_len] # Actual json content
        self._buffer = self._buffer[content_len:]
        if self.mHTTPheader['content-type'] == "text/json":
            encoding = self.mHTTPheader['content-encoding']
            decoded = data.decode(encoding)
            print(decoded)
            self.json = json.loads(decoded)
            print("Recived request", repr(self.json), "from", self.addr)
        else:
            self.json = data 
            content_type = self.mHTTPheader["content-type"]
            print(f"Recieved {content_type} request from {self.addr}.")
                
    def read(self):
        self._read()
        if not self._mHTTPheaders_len:
            self._process_proto_header()
        
        if not self.mHTTPheader:
            self._process_mHTTP_headers()
        
        self._process_socket_data()
        self.callback_response()
    
    def query_database(self):
        action = self.json['action']
        if self.json['action'] == 'read':
            assert self.json['data'] == None 
            response = self.json 
            response['data'] = DB[response['index']]
            self.response_created = True
            self.json_response += raw_json_encode(response)
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
        headers = ['GET 127.0.0.1 HTTP/1.1',
                  'bytorder: big-endian',
                  'content-type: text/json',
                  f'content-length: {len(self.response)}',
                  'content-encoding: utf-8']
        self.response_mHTTPheader = bytes('\n'.join(headers),encoding='utf-8')

    def _create_proto_header_response(self):
        # Write length of mHTTP header in a big-endian format with 2 bytes.
        self.response_protoheader = struct.pack(">H", len(self.response_mHTTPheader))

    def send_response(self):
        if self._send_buffer:
            print(f"Sending response to {self.addr}")
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
        
        if not self.response_protoheader and self.response_httpheader != None:
            self._create_proto_header_response()
        # Accumulate whole headers together to be sent in right order in the buffer.
        self._send_buffer += self.response_protoheader
        self._send_buffer += self.response_mHTTPheader
        self._send_buffer += self.response_json
        self.send_response()
    
    def close(self):
        try:
            self.sock.close()
        except OSError as e:
            print(f"Error: can't close socket {self.addr} connect propery       Exception: {repr(e)}.")
        finally:
            self.sock = None


