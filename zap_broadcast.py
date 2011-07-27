import socket
import threading
import sys
from zap_protocol import ZapTorrentProtocolParser, ZapTorrentProtocolResponse
import random

class ZapBroadcast(threading.Thread):
    def __init__(self, broadcast_port, local_files, remote_files):
        threading.Thread.__init__(self)
        self.port = broadcast_port
        self.host = ''
        self.local_files = local_files
        self.remote_files = remote_files
        self.open_socket()

    def open_socket(self):
        self.sock = None
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sys.platform == 'darwin':
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.bind((self.host, self.port))
        except socket.error, (code, message):
            print("could not open socket", message)
            sys.exit(1)

    def run(self):
        SIZE = 65000
        while True:
            #TODO: what if not all the data comes at once?
            data, address = self.sock.recvfrom(SIZE)
            query = ZapTorrentProtocolParser(data)
            query.parse()
            if query.message_type == 'error':
                self.sock.sendto(query.response, address)
            elif query.message_type == 'files?':
                """BUILD LIST OF FILES AND SEND BACK"""
                response = ZapTorrentProtocolResponse(type='files?')
                for file in files.get_files():
                    response.add(file)
                self.sock.sendto(response.as_response(), address)
            elif query.message_type == "file":
                # Parse the files out of the query, and store them in the remote files
                ip = query.get_field('ip')
                port = query.get_field('port')
                name = query.get_field('name')
                for f in query.get_files():
                    #just make them use remote files?
                    zf = ZapRemoteFile()
                    zf.ip = ip
                    zf.port = port
                    zf.hostname = name
                    zf.blocks = f['blocks']
                    zf.digest = f['digest']
                    zf.filename = f['filename']
                    self.remote_files.add(zf)
