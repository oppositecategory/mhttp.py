import sys 
import json 
import io 
import struct
import socket
import threading

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

class SocketHandler:
    """ Implements message protocol for webserever.

        The protocol imititates HTTP protocol but a more simiplified version named mHTTP for minimal HTTP.
        # TODO: 
            - Add HTTP verbs.
            - Transfer arbitrary binary data over the network. As of now only handles JSON.
    """
    def __init__(self, sock:socket.socket, addr:tuple):
        self.sock = sock 
        self.addr = adddr
        # Notes buffers are a bytes type.
        self._recv_buffer = b"" 
        self._sent_buffer = b"" # Buffer for holding the response.
        self._httpheaders_len = None
        self.httpheader = None
        self.request = None

        self.response = b""
        self.response_created = False
        self.response_protoheader = None
        self.response_httpheader = None

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
    
    def _extract_HTTP_header(self, header):
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
            header, value = line.strip(':')
            header = header.strip()
            value = value.strip()
            headers[header] = value 
        return headers
            
    def _process_HTTP_headers(self):
        headers = {}
        headerlen = self._httpheaders_len
        if len(self._recv_buffer) >= headerlen:
            header = self._recv_buffer[:headerlen].decode("utf-8")
            self._recv_buffer = self._recv_buffer[headerlen:]
            self.httpheader = self._extract_HTTP_header(header)
            for header in headers:
                if header not in self.httpheader.keys():
                    raise ValueError(f"Missing required header {header}.")
    
    def process_request(self):
        content_len = self.httpheader['content-length']
        if not len(self._recv_buffer) >= content_len:
            return 
        data = self._recv_buffer[:content_len] # Actual json content
        self._recv_buffer = self._recv_buffer[content_len:]
        if self.httpheader['content-type'] == "text/json":
            encoding = self.httpheader['content-encoding']
            self.request = json_decode(data, encoding)
            print("Recived request", repr(self.request), "from", self.addr)
            self.write() # Callback function to answer request
        else:
            self.request = data 
            print(f"Recieved {self.httpheader["content-type"]} request from {self.addr}.")
            self.write() # Callback

    def read(self):
        self._read()
        if not self._httpheaders_len:
            self._process_proto_header()
        
        if not self.httpheader:
            self._process_HTTP_headers()
        
        self.process_request()

    def _handle_database_queries(self):
        """ Handles database queries and create a echo message to client with requested data.
        """
        action = self.request['action']
        if action == 'read':
            assert self.request['data'] == None 
            response = self.request 
            response['data'] = DB[response['query']]
            self.response_created = True
            self.response += raw_json_encode(response)
        elif action == 'write':
            # To prevent race conditions a simple mutex lock is acquired.
            # NOTE: No computation is actually done here but as a good 
            # practice we add mutex lock whenever we deal with data shared between threads.
            self.filesystem_lock.acquire()
            response = self.request 
            response['action'] = 'read' # Protocol assumes read action when sending data over network.
            DB[self.request['query']] = self.request['data']
            self.response_created = True 
            self.response += raw_json_encode(response)
            self.filesystem_lock.release()

    def _create_respone_binary(self):
        # TODO: Handling binary data sent over the network.
        raise NotImplementedError()()
    
    def _create_response_HTTPheader(self):
        headers = ['GET 127.0.0.1 HTTP/1.1',
                  'bytorder: big-endian',
                  'content-type: text/json',
                  f'content-length: {len(self.response)}',
                  'content-encoding: utf-8']
        self.response_httpheader = bytes('\n'.join(headers),encoding='utf-8')

    def _create_response_proto_header(self):
        # Write length of mHTTP header in a big-endian format with 2 bytes.
        self.response_protoheader = struct.pack(">H", len(self.response_httpheader))
    
    def _write(self):
        try:
            resp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            resp_sock.connect(self.addr)
            resp_sock.setblocking(False)

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

    def write(self):
        if not self.response_created:
            self._create_response()
        
        if not self.response_protoheader and self.response_created:
            self._create_response_HTTPheader()
        
        if not self.response_protoheader and self.response_httpheader != None:
            self._create_response_proto_header()
        
        # Accumulate whole headers together to be sent in right order in the buffer.
        self._sent_buffer += self.response_protoheader
        self._sent_buffer += self.httpheader
        self._sent_buffer += self.response

        self._write()
        
        
        
        




        