import sys
import re
import optparse
import socket
import random
import threading
import time
from zap_file import ZapFile, ZapFiles
from zap_protocol import ZapTorrentProtocolParser, ZapTorrentProtocolResponse
from zap_broadcast import ZapBroadcast
from zap_config import ZapConfig

class ZapClient:
    def __init__(self, port, verbose):
        self.prompt = "[Zap Torrent]"
        self.port = port
        self.local_files = ZapFiles()
        self.remote_files = ZapFiles()
        ZapConfig.debug = verbose
        self.ip = self.get_ip()
        self.broadcast_port = port
        ZapConfig.ip = self.get_ip()
        self.discoverer = FilesLister(port=self.broadcast_port, remote_files=self.remote_files)
        ZapConfig.tcp_port = random.randint(1300, 40000)

    def get_ip(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("google.com", 80))
        ip = sock.getsockname()[0]
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
        print("own address for my comms port is", own_address)
        ignore_port = own_address[1]
        b = ZapBroadcast(self.broadcast_port, self.local_files,
                self.remote_files, self.ip, ignore_port)
        b.start()

        while True:
            line = raw_input(self.prompt + " ")
            if re.match('^quit$', line):
                self.quit()
            elif re.match('^name (\w+)$', line):
                "name"
                #TODO: set name of this host. Has to be somewhere shared I guess.
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
                for k in self.remote_files.get_all_files():
                    print("File: %s" % k)
            elif re.match('^load ([\w\._\-/]+)$', line):
                path = re.match('^load ([\w\._\-/]+)$', line).group(1)
                f = ZapFile()
                if f.set_path(path):
                    self.local_files.add(f)
                    print("File at %s loaded for sharing." % path)
                else:
                    print("File at %s doesn't exist. Try a different path." % path)
            elif re.match('^get (\w+)$', line):
                filename =  re.match('^get (\w+)$', line).group(1)
                remote_files = self.remote_files.get(filename)

            else:
                self.print_usage()
                continue

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
            print("Got some data! ", data)
            print("my address is", (ZapConfig.ip, self.port))
            print("other address is", address)
            print("about to parse the query in FilesLister")
            query.parse()
            if query.message_type == "files":
                # Parse the files out of the query, and store them in the remote files
                print("got a files reponse: ", data)
                ip = query.get_field('ip')
                port = query.get_field('port')
                name = query.get_field('name')
                for f in query.get_files():
                    #just make them use remote files?
                    zf = ZapFile(status="not-present")
                    zf.ip = ip
                    zf.port = port
                    zf.hostname = name
                    zf.number_of_blocks = f['blocks']
                    zf.digest = f['digest']
                    zf.filename = f['filename']
                    self.remote_files.add(zf)

if __name__ == "__main__":
    parser = optparse.OptionParser(usage = "%prog [options]",
                                   version = "%prog 1.0")
    parser.add_option("-p", "--port", type="int", dest="port",
                      metavar="PORT", default=3000,
                      help="port number that the peer will broadcast on")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      help="Display debugging output")
    parser.set_defaults(verbose=True)
    options, args = parser.parse_args()
    z = ZapClient(options.port, options.verbose)
    z.run()
