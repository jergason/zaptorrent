import socket
import threading
import sys
from zap_protocol import ZapTorrentProtocolParser, ZapTorrentProtocolResponse
from zap_config import ZapConfig, zap_debug_print
import random

class ZapBroadcast(threading.Thread):
    def __init__(self, broadcast_port, local_files, remote_files, ip, ignore_port):
        threading.Thread.__init__(self)
        threading.Thread.daemon = True
        self.port = broadcast_port
        self.host = ''
        self.local_files = local_files
        self.remote_files = remote_files
        self.ip = ip
        self.ignore_port = ignore_port
        self.open_socket()

    def open_socket(self):
        self.sock = None
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sys.platform == 'darwin':
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.bind(('', self.port))
        except socket.error, (code, message):
            print("could not open socket", message)
            sys.exit(1)

    def run(self):
        SIZE = 65000
        while True:
            #TODO: what if not all the data comes at once?
            data, address = self.sock.recvfrom(SIZE)
            if address[0] == self.ip and address[1] == self.ignore_port:
                continue
            query = ZapTorrentProtocolParser(data)
            zap_debug_print("in zap_broadcast and got some data! ", data)
            zap_debug_print("address is", address)
            zap_debug_print("my ignoring stuff is", self.ip, self.ignore_port)
            query.parse()
            if query.message_type == 'error':
                self.sock.sendto(query.response, address)
            elif query.message_type == 'files?':
                zap_debug_print("got a files? message")
                #BUILD LIST OF FILES AND SEND BACK
                response = ZapTorrentProtocolResponse(response_type='files', name='hurp',
                                                      ip=socket.gethostbyname(socket.gethostname()),
                                                      port=ZapConfig.tcp_port)
                for filename in self.local_files.get_files():
                    f = self.local_files.get_files()[filename]
                    zap_debug_print("Adding a local file, and it is", f)
                    response.add(f)
                zap_debug_print("response is ", response.as_response())
                self.sock.sendto(response.as_response(), address)
