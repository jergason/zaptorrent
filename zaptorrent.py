import sys
import os
import re
import optparse
import socket
import random
import threading
import time
import copy
from zap_file import ZapFile, ZapFiles
from zap_protocol import ZapTorrentProtocolParser, ZapTorrentProtocolResponse
from zap_broadcast import ZapBroadcast
from zap_config import ZapConfig, zap_debug_print, zap_log
from zap_tcp_server import ZapTCPServer

class ZapClient:
    def __init__(self, port, verbose):
        self.prompt = "[Zap Torrent]"
        self.port = port
        self.local_files = ZapFiles()
        self.remote_files = ZapFiles()
        ZapConfig.verbose = verbose
        self.ip = self.get_ip()
        zap_debug_print("my ip is %s, port is %d" % (self.ip, self.port))
        self.broadcast_port = port
        ZapConfig.ip = self.get_ip()
        self.discoverer = FilesLister(port=self.broadcast_port, remote_files=self.remote_files)
        ZapConfig.tcp_port = random.randint(1300, 40000)
        self.tcp_port = ZapConfig.tcp_port

    def get_ip(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ip = ""
        try:
            sock.connect(("google.com", 80))
            ip = sock.getsockname()[0]
        except socket.gaierror:
            # if there is no connection to the internet, try getting it by just
            # broadcasting
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.sendto("HURP DURP", ("<broadcast>", self.port))
                zap_debug_print("self.port is %d" % self.port)
                ip = sock.getsockname()[0]
            except socket.error:
                print >> sys.stderr, ("Sorry, but I can't connect to the network for some reason.")
                print >> sys.stderr, ("Check your network connection and try running ZapTorrent again.")
                sys.exit(2)
        return ip

    def quit(self):
        print("Thanks for using Zap Torrent!")
        sys.exit(0)

    def print_usage(self):
        print("""usage:
quit        #quits the program
name [name] #sets the name of the peer
list        #lists all files available to download from other peers
load [file] #makes a fie availible to peers for download
get [file]  #downloads file""")

    def print_welcome(self):
        print("Welcome to ZapTorrent. Type `usage` for instructions.")

    def run(self):
        self.print_welcome()

        self.discoverer.start()
        #Send something to the discover sock so we can bind it to a port
        self.discoverer.sock.sendto("HURP DURP", ("<broadcast>", self.broadcast_port))
        own_address = self.discoverer.sock.getsockname()
        zap_debug_print("my udp discovery port is", own_address[1])
        ignore_port = own_address[1]
        b = ZapBroadcast(self.broadcast_port, self.local_files,
                self.remote_files, self.ip, ignore_port)
        b.start()

        tcp_server = ZapTCPServer(port=self.tcp_port, host=self.ip, local_files=self.local_files)
        tcp_server.start()

        while True:
            line = raw_input(self.prompt + " ")
            if re.match('^quit$', line):
                self.quit()
            elif re.match('^name (\w+)$', line):
                ZapConfig.name = re.match(r"^name (\w+)$", line).group(1)
                print("Name is now %s" % ZapConfig.name)
            elif re.match('^list$', line):
                self.remote_files.clear()
                query = ZapTorrentProtocolResponse(response_type="files?").as_response()
                s = self.discoverer.sock
                length = 0
                while length < len(query):
                    sent_length = s.sendto(query, ("<broadcast>", self.broadcast_port))
                    length += sent_length
                #now wait for the filesLister to get more info
                print("Waiting for response from peers. . .")
                time.sleep(3)
                for k in self.remote_files.get_files():
                    print("File: %s" % k)
            elif re.match('^load ([\w\._\-/]+)$', line):
                path = re.match('^load ([\w\._\-/]+)$', line).group(1)
                f = ZapFile()
                if f.set_path(path):
                    zap_debug_print("Loaded a local file and it is ", f)
                    self.local_files.add(f)
                    print("File at %s loaded for sharing." % path)
                else:
                    print("File at %s doesn't exist, or it is a directory. Try a different path." % path)
            elif re.match('^get ([\w\.\-]+)$', line):
                filename =  re.match('^get ([\w\.\-]+)$', line).group(1)
                remote_files = self.remote_files.get(filename)
                if remote_files is not None:
                    downloader = ZapDownloader(remote_files, self.local_files)
                    downloader.start()
                    print("Starting to download %s." % filename)
                else:
                    print("No files by that name. Sorry. Try 'list' to update your list of files.")

            else:
                self.print_usage()
                continue


class ZapDownloader(threading.Thread):
    def __init__(self, remote_files, local_files):
        threading.Thread.__init__(self)
        threading.Thread.daemon = True
        self.remote_files = remote_files
        self.local_files = local_files

    def remote_file_downloader(self, remote_file, file_attributes):
        return ZapTCPDownloadThread(remote_file, file_attributes)

    def run(self):
        """Spawn off threads to download each block. When all
        threads return, check if the file is completely
        downloaded. If so, determine its digest and make
        sure it matches, and save it to disk."""
        start_time = time.time()
        file_info = self.remote_files[0]
        remote_file = ZapFile()
        remote_file.filename = file_info.filename
        remote_file.number_of_blocks = file_info.number_of_blocks
        remote_file.mark_as_remote()
        self.local_files.add(remote_file)
        child_threads = []

        for f in self.remote_files:
            remote_location = {}
            remote_location['ip'] = f.ip
            remote_location['port'] = f.port
            remote_location['name'] = f.name
            child_thread = self.remote_file_downloader(remote_file, f)
            child_thread.start()
            child_threads.append(child_thread)

        # How do we wait for them to finish?
        # TODO: what if I can't download the whole file?
        while not remote_file.is_downloaded():
            time.sleep(4)

        # Now all child threads are gone, I hope.
        remote_file.save_to_disk()
        zap_debug_print("remote file digest is ", remote_file.digest, "file_info.digest is ", file_info.digest)
        if remote_file.digest != file_info.digest:
            # Our file does not match. Quit this thread and return an error
            zap_debug_print("Digest does not match! I should delete downloaded file!")
            self.local_files.remove(remote_file)
            os.remove(remote_file.path)
            return False
        else:
            stop_time = time.time()
            log_string = "file %s %s %s" % (remote_file.filename, os.path.getsize(remote_file.path),
                    stop_time - start_time)
            zap_log(log_string)
            print("Finished downloading %s. Find it at %s." % (remote_file.filename, remote_file.path))
            return True

class ZapTCPDownloadThread(threading.Thread):
    def __init__(self, remote_file, peer_info):
        threading.Thread.__init__(self)
        threading.Thread.daemon = True
        self.remote_file = remote_file
        self.peer_info = peer_info

    def run(self):
        # In a loop - aquire the lock
        # Check if the peer info has any stuff that I don't have
        # If so, mark it as downloading and release the lock
        # download it
        # Aquire the lock again
        # Mark the downloaded block as present
        # Release the lock
        while True:
            # We get the blocks each time in case the peer
            # has since received new blocks
            blocks_available = self.get_available_blocks(self.peer_info.ip,
                    self.peer_info.port, self.peer_info.filename)
            zap_debug_print("Blocks available are ", blocks_available)
            self.remote_file.sem.acquire()
            block_to_download = None
            for block_id in blocks_available:
                if self.remote_file.does_block_needs_downloading(int(block_id)):
                    block_to_download = int(block_id)
                    self.remote_file.mark_block_as('downloading', int(block_to_download))
                    break
            self.remote_file.sem.release()
            if block_to_download is None:
                zap_debug_print("No more blocks to download from" +
                        " this peer: ", self.peer_info)
                break
            data = self.download_block(self.peer_info.filename,
                    block_to_download, self.peer_info.ip,
                    self.peer_info.port)
            zap_debug_print("received %s back from the download query" % data)
            if data is not None:
                self.remote_file.set_block_data(block_to_download, data)
                self.remote_file.mark_block_as('present', block_to_download)
                log_string = "download %s %s %s %s %s %s" % (self.peer_info.filename,
                        self.peer_info.name, self.peer_info.ip, self.peer_info.port,
                        block_to_download, len(data))
                zap_log(log_string)
            else:
                # Mark the block to be downloaded again.
                print(("error downloading block %s from" % block_to_download), self.peer_info)
                self.remote_file.mark_block_as('not-present', int(block_to_download))

    def get_available_blocks(self, ip, port, filename):
        """Return a list of blocks that the peer at
        ip, port has for the given filename."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        query = ZapTorrentProtocolResponse(response_type='inventory?',
                filename=filename)
        msg = query.as_response()
        sock.connect((ip, int(port)))
        self.send_to_socket(sock, msg)
        results = sock.recv(54000)
        if len(results) == 0:
            raise RuntimeError("socket closed remotely")
        parser = ZapTorrentProtocolParser(results)
        parser.parse()
        sock.close()
        return [block['id'] for block in parser.get_blocks()]


    def download_block(self, filename, id, ip, port):
        query = ZapTorrentProtocolResponse(response_type='download?',
            filename=filename, id=id, name=ZapConfig.name,
            ip=ZapConfig.ip, port=ZapConfig.tcp_port)
        msg = query.as_response()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, int(port)))
        self.send_to_socket(sock, msg)
        resp = sock.recv(54000)
        zap_debug_print("download_blocks got %s back" % resp)
        #TODO: what if we don't receive the
        # entire first chunk, or we get an error?
        if len(resp) == 0:
            raise RuntimeError("socket closed remotely!")
        parser = ZapTorrentProtocolParser(resp)
        parser.parse()
        if parser.message_type == 'download':
            #make sure we have the whole block
            while len(parser.fields['data']) < int(parser.fields['bytes']):
                parser.fields['data'] += sock.recv(54000)
            sock.close()
            return parser.fields['data']
        else:
            zap_debug_print("Error downloading a block: got ", resp)
            sock.close()
            return None


    def send_to_socket(self, sock, msg):
        message_length = len(msg)
        sent_length = 0
        while sent_length < message_length:
            #TODO: check if it is zero
            length = sock.send(msg[sent_length:])
            if length == 0:
                raise RuntimeError("socket closed remotely")
            sent_length += length
        return sent_length





class FilesLister(threading.Thread):
    """This thread shares a socket, and will wait for responses listing files."""
    def __init__(self, **kwargs):
        threading.Thread.__init__(self)
        threading.Thread.daemon = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.port = kwargs['port']
        self.remote_files = kwargs['remote_files']
        self.sock.sendto("HURP DURP", ("<broadcast>", self.port))
        own_address = self.sock.getsockname()
        self.ignore_port = own_address[1]
        #get the ignore port

    def run(self):
        size = 55000
        while True:
            data, address = self.sock.recvfrom(size)
            #ignore stuff sent from our own socket
            if address[0] == ZapConfig.ip and address[1] == self.ignore_port:
                continue
            query = ZapTorrentProtocolParser(data)
            zap_debug_print("Got some data! ", data)
            zap_debug_print("my address is", (ZapConfig.ip, self.port))
            zap_debug_print("other address is", address)
            zap_debug_print("about to parse the query in FilesLister")
            query.parse()
            if query.message_type == "files":
                # Parse the files out of the query, and store them in the remote files
                zap_debug_print("got a files reponse: ", data)
                ip = query.get_field('ip')
                port = query.get_field('port')
                name = query.get_field('name')
                for f in query.get_files():
                    zf = ZapFile(status="not-present")
                    zf.ip = ip
                    zf.port = port
                    zf.name = name
                    zf.number_of_blocks = f['blocks']
                    zf.digest = f['digest']
                    zf.filename = f['filename']
                    zap_debug_print("Someone told me about a file named", zf.filename)
                    self.remote_files.add(zf)

if __name__ == "__main__":
    parser = optparse.OptionParser(usage = "%prog [options]",
                                   version = "%prog 1.0")
    parser.add_option("-p", "--port", type="int", dest="port",
                      metavar="PORT", default=3000,
                      help="port number that the peer will broadcast on")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      help="Display debugging output")
    parser.set_defaults(verbose=False)
    options, args = parser.parse_args()
    z = ZapClient(options.port, options.verbose)
    z.run()
