import sys 
import json 
import io 
import struct
import socket

# GLOBAL VARIABLE
headers = ("byteorder",
            "content-length",
            "content-type",
            "content-encoding",
          )

class SocketHandler:
    """ Implements message protocol for webserever.

        The protocol imititates HTTP protocol but a more simiplified version which includes 
        only necessary headers stated in global headers variable and requests recived from
        the server assumed to be only GET; hence no verbs option.
    """
    def __init__(self, sock:socket.socket, addr:int):
        self.sock = sock 
        self.addr = adddr
        self._recv_buffer = b"" # Bytes type not str
        self._httpheaders_len = None
        self.httpheader = None

    def _read(self):
        try:
            data = self.sock.recv(4096)
        except BlockingIOError:
            pass 
        else:
            if data:
                self._recv_buffer += data
            else:
                raise RuntimeError("Connection closed.")
    
    def _process_proto_header(self):
        # Message Protocol assumes the first 2 bytes are reserved for the
        # variable-length of the JSON header.
        headerlen = 2
        if len(self._recv_buffer) >= headerlen:
            # Using format ">H" where ">" stands for big-endian format and 
            # "H" stands for unsigned char i.e 2-byte length data.
            self._jsonheader_len = struct.unpack(
                ">H", self._recv_buffer[:headerlen]
            )[0]
            # Points "point" to start of the JSON header.
            self._recv_buffer = self._recv_buffer[headerlen:] 
    
    def _extract_http_header(self, header):
        headers = {}
        lines = header.split('\n')
        assert lines[0].startswith('GET')
        lines = lines[1:] # First line is a HTTP GET.
        for line in lines:
            assert len(line.split(':')) == 2
            header, value = line.strip(':')
            headers[header] = value 
        return headers
            

    def _process_http_headers(self):
        headers = {}
        headerlen = self._httpheaders_len
        if len(self._recv_buffer) >= headerlen:
            header = self._recv_buffer[:headerlen].decode("utf-8")
            self._recv_buffer = self._recv_buffer[headerlen:]
            self.httpheader = self._extract_http_header(header)
            for header in headers:
                if header not in self.httpheader:
                    raise ValueError(f"Missing required header {header}.")
    
    def process_request(self):

                
                

    def read(self):
        self._read()
        
        if not self._httpheaders_len:
            self._process_proto_header()


        