import json 
import struct
import socket
from abc import ABC, abstractmethod

def raw_json_encode(resp):
    dump = json.dumps(resp)
    raw_bytes = bytes(dump, 'utf-8')
    return raw_bytes

class mHTTPProtocol(ABC):
    def __init__(self):
        self._buffer = b""
        self._mHTTPheaders_len = None 
        self.mHTTPheader = None 
        self.json = None 
    
    @abstractmethod
    def _extract_mHTTP_header(self, head):
        pass

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
    
    def _process_mHTTP_headers(self):
        headers = {}
        headerlen = self._mHTTPheaders_len
        print(self._buffer[:headerlen])
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
            self.json = json.loads(decoded)
        else:
            self.json = data 
            content_type = self.mHTTPheader["content-type"]




