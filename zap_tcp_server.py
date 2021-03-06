import threading
import socket
from zap_protocol import ZapTorrentProtocolParser, ZapTorrentProtocolResponse
from zap_config import zap_debug_print, zap_log, ZapConfig


class ZapTCPServer(threading.Thread):
    """TCP server that listens on a given port for incomping connections and spawns different threads to
    answer them."""
    def __init__(self, **kwargs):
        threading.Thread.__init__(self)
        threading.Thread.daemon = True

        self.local_files = kwargs.get("local_files")
        self.port = kwargs.get("port")
        self.host = kwargs.get("host")
        self.sock = self.setup_socket(5)


    def setup_socket(self, listen):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((self.host, self.port))
        sock.listen(listen)
        return sock

    def run(self):
        # wait for connections
        while True:
            (client_socket, address) = self.sock.accept()
            ct = self.socket_thread(client_socket)
            ct.start()

    def socket_thread(self, sock):
        """Make a new thread to handle an incoming TCP connection."""
        return ZapTCPResponseThread(sock, self.local_files)

class ZapTCPResponseThread(threading.Thread):
    def __init__(self, sock, local_files):
        threading.Thread.__init__(self)
        threading.Thread.daemon = True
        self.sock = sock
        self.local_files = local_files

    def run(self):
        #TODO: what if we don't receive it all at once?
        msg = self.sock.recv(54000)
        zap_debug_print("Got a message on the ZAPTCPResponseThread and it is", msg)
        response = ""
        query = ZapTorrentProtocolParser(msg)
        query.parse()
        if query.message_type == 'error':
            response = query.response
        elif query.message_type == 'inventory?':
            #Look for the file in local_files
            f = self.local_files.get(query.fields['filename'])
            if f is None:
                response = "ZT 1.0 error No file named %s" % query.fields['filename']
            else:
                f = f[0]
                r = ZapTorrentProtocolResponse(response_type="inventory", filename=f.filename, blocks=f.number_of_blocks)
                r.stuff_to_add = f.get_blocks(status='present')
                zap_debug_print("got back some blocks and they looks like this:", r.stuff_to_add)
                response = r.as_response()
        elif query.message_type == 'download?':
            #make sure we have the file
            f = self.local_files.get(query.fields['filename'])
            if f is None:
                response = "ZT 1.0 error No file named %s" % query.fields['filename']
            else:
                f = f[0]
                if f.block_is_present(int(query.fields['id'])):
                    r = ZapTorrentProtocolResponse(response_type="download", filename=f.filename, id=query.fields['id'],
                            bytes=f.get_block(int(query.fields['id'])).get_bytes())
                    response = r.as_response()
                    log_string = "upload %s %s %s %s %s %s" % (f.filename, ZapConfig.name,
                            query.fields['ip'], query.fields['port'], query.fields['id'],
                            len(f.get_block(int(query.fields['id'])).get_bytes()))
                    zap_log(log_string)
                else:
                    response = "ZT 1.0 error No block for %s at %s\n" % (f.filename, query.fields['id'])

        else:
            response = "ZT 1.0 error unknown TCP query type.\n"
        sent_length = 0
        zap_debug_print("sending %s as response" % response)
        while sent_length < len(response):
            message_remaining = response[sent_length:]
            length = self.sock.send(message_remaining)
            sent_length += length
        #TODO: do I close it on my end?
        self.sock.close()

