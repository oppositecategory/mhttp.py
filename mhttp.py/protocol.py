import sys 
import json 
import io 
import struct
import socket
import threading
from abc import ABC, abstractmethod

# ---GLOBAL VARIABLES---
headers = ("byteorder",
            "content-length",
            "content-type",
            "content-encoding",
          )
DB = [f'Message {i}' for i in range(10)] 
# ---GLOBAL VARIABLES---

def json_decode(raw_bytes, encoding):
    # Decode raw data sent over a socket into json using the encoding the client used.
    decoded = io.TextIOWrapper(
        io.BytesIO(raw_bytes, encoding=encoding,newline="")
    )
    obj = json.load(decoded)
    decoded.closer()
    return obj

def raw_json_encode(resp):
    json = json.dumps(resp)
    raw_bytes = bytes(json, 'utf-8')
    return raw_bytes


class SocketProtocol(ABC):
    """ Virtual class implementing the mHTTP (minimal HTTP) protocol. 
        The class encapsulates the protocol-handling code to distinguish it from the I/O code 
        so one can extend it later on according to his will to use AsyncIO/threading/select and etc. 

        # TODO: 
            - Add HTTP verbs.
            - Transfer arbitrary binary data over the network. As of now only handles JSON.
    """
    def __init__(self, sock: socket.socket, addr: tuple):
        self.sock = sock 
        self.addr = addr 
        # NOTE: Buffers are bytes type and not str.
        self._recv_buffer = b""
        self._sent_buffer = b""
        self._mHTTPheaders_len = None 
        self.mHTTPheader = None 
        self.json_request = None 

        self.json_response = b""
        self.response_created = False
        self.response_protoheader = None
        self.response_mHTTPheader = None

    @abstractmethod
    def _read(self):
        pass

    def _process_proto_header(self):
        # Message Protocol assumes the first 2 bytes are reserved for the
        # variable-length of the HTTP header.
        headerlen = 2
        if len(self._recv_buffer) >= headerlen:
            # Using format ">H" where ">" stands for big-endian format and 
            # "H" stands for unsigned char i.e 2-byte length data.
            self._httpheader_len = struct.unpack(
                ">H", self._recv_buffer[:headerlen]
            )[0]
            # Points "point" to start of the HTTP header.
            self._recv_buffer = self._recv_buffer[headerlen:]

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
        assert lines[0].startswith('GET')
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
        if len(self._recv_buffer) >= headerlen:
            header = self._recv_buffer[:headerlen].decode("utf-8")
            self._recv_buffer = self._recv_buffer[headerlen:]
            self.mHTTPheader = self._extract_mHTTP_header(header)
            for header in headers:
                if header not in self.mHTTPheader.keys():
                    raise ValueError(f"Missing required header {header}.")
    
    @abstractmethod
    def process_request(self):
        pass
    
    @abstractmethod
    def read(self):
        pass

    @abstractmethod
    def _write_to_filesystem(self, data):
        pass

    def _read_from_filesystem(self):
        action = self.json_request['action']
        assert self.json_request['data'] == None 
        response = self.json_request 
        response['data'] = DB[response['query']]
        self.response_created = True
        self.json_response += raw_json_encode(response)

    @abstractmethod
    def _write_to_filesystem(self):
        """ Unlike reading from the filesystem, writing to it can result in race condition hence we leave it 
            as abstact class to be implemented by the extending class.
        """
        pass

    @abstractmethod
    def query_database(self):
        """ Handles database queries and echoes a message to client with requested data.
        """
        pass
    
    def _create_mHTTPheader(self):
        headers = ['GET 127.0.0.1 HTTP/1.1',
                  'bytorder: big-endian',
                  'content-type: text/json',
                  f'content-length: {len(self.response)}',
                  'content-encoding: utf-8']
        self.response_mHTTPheader = bytes('\n'.join(headers),encoding='utf-8')

    def _create_proto_header(self):
        # Write length of mHTTP header in a big-endian format with 2 bytes.
        self.response_protoheader = struct.pack(">H", len(self.response_httpheader))
    
    @abstractmethod
    def _write(self):
        pass
        
    def create_response(self):
        if not self.response_created:
            self._query_database()()
        
        if not self.response_protoheader and self.response_created:
            self._create_HTTPheader()
        
        if not self.response_protoheader and self.response_httpheader != None:
            self._create_proto_header()
        
        # Accumulate whole headers together to be sent in right order in the buffer.
        self._sent_buffer += self.response_protoheader
        self._sent_buffer += self.httpheader
        self._sent_buffer += self.response

    @abstractmethod 
    class write(self):
        pass


class ThreadedSocketProtocol(SocketProtocol):
    """ Implementing the protocol for multi-threaded server.
        NOTE: ThreadedSocketHandler uses mutex lock for writing to filesystem.
    """
    def __init__(self):
        super(sock, addr).__init__()
        self.filesystem_lock = threading.Lock()
    
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
    
    def process_request(self):
        content_len = self.mHTTPheader['content-length']
        if not len(self._recv_buffer) >= content_len:
            return 
        data = self._recv_buffer[:content_len] # Actual json content
        self._recv_buffer = self._recv_buffer[content_len:]
        if self.mHTTPheader['content-type'] == "text/json":
            encoding = self.mHTTPheader['content-encoding']
            self.json_request = json_decode(data, encoding)
            print("Recived request", repr(self.request), "from", self.addr)
        else:
            self.json_request = data 
            print(f"Recieved {self.mHTTPheader["content-type"]} request from {self.addr}.")
                
    def read(self):
        self._read()
        if not self._mHTTPheaders_len:
            self._process_proto_header()
        
        if not self.httpheader:
            self._process_mHTTP_headers()
        
        self.process_request()
        self.callback_response() # Callback function to return a mHTTP response for request.
    
    def _write_to_filesystem(self):
        # NOTE: No computation is actually done here but as a good 
        # practice we add mutex lock whenever we deal with data shared between threads.
        self.filesystem_lock.acquire()
        response = self.json_request 
        response['action'] = 'read' # Protocol assumes read action when sending data over network.
        DB[self.json_request['query']] = self.json_request['data']
        self.response_created = True 
        self.query += raw_json_encode(response)
        self.filesystem_lock.release()
    
    def query_database(self):
        if self.json_request['action'] == 'read':
            self._read_from_filesystem()
        else:
            self._write_to_filesystem(self.json_request['query'])

    def _create_mHTTP_response(self):
        try:
            resp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            resp_sock.connect(self.addr)
            resp_sock.setblocking(False)

            # Simple mechanism to ensure all data is sent.
            toal_sent = 0 
            while bytes_sent < len(self._sent_buffer):
                sent = resp_sock.send(self._sent_buffer[bytes_sent:])
                if sent == 0:
                    raise RuntimeError(f"Lost connection to {self.addr}.")
                total_sent += sent 
        except BlockingIOError:
            pass
        else:
            raise RuntimeError(f"Lost connection to {self.addr}.")
    
    def callback_response(self):
        # Wrapper to break the functionality of creating a full response and writing back to function
        # so we can embed the create_response() functionality in the virtual class.
        if not addr: # Socket holds data to be sent back
            self.create_response()
            self._create_mHTTP_response()
        
        

        
        
        
        




        