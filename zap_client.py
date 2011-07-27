import sys
import re
import optparse
import socket
from zap_file import ZapFile, ZapFiles
from zap_protocol import ZapTorrentProtocolParser, ZapTorrentProtocolResponse
from zap_broadcast import ZapBroadcast

class ZapClient:
    def __init__(self, port, verbose):
        self.prompt = "[Zap Torrent]"
        self.port = port
        self.verbose = verbose
        self.local_files = ZapFiles()
        self.remote_files = ZapFiles()

    def quit(self):
        print("Thanks for using Zap Torrent!")
        sys.exit(0)

    def print_usage(self):
        print("""usage:
quit #quits the program
name [name] #sets the name of the peer
list #lists all files available to download from other peers
load [file] #makes a fie availible to peers for download
get [file] #downloads file""")

    def print_welcome(self):
        print("""Welcome to ZapTorrent. Type `usage` for instructions.""")

    def run(self):
        self.print_welcome()

        b = ZapBroadcast(self.port, self.local_files, self.remote_files)
        b.start()

        while True:
            line = raw_input(self.prompt + " ")
            if re.match('^quit$', line):
                self.quit()
            elif re.match('^name (\w+)$', line):
                "name"
                #TODO: set name of this host. Has to be somewhere shared I guess.
            elif re.match('^list$', line):
                # We only broadcast now, i guess, and store the results in ZapFiles?
                # make a new broadcast socket and send out a files? message. Results will come to the b thread
                # TODO: Should i clear out the files each time?
                self.remote_files.clear()
                query = ZapTorrentProtocolResponse("files?").as_response()
                #TODO: clean this up
                #TODO: WHAT PORT DO I BIND TO TO BROADCAST? DOES IT MATTER?
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                if sys.platform == 'darwin':
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                # s.bind(("192.168.0.112", 3001))
                length = 0
                while length < len(query):
                    sent_length = s.sendto(query, ("192.168.0.112", self.port))
                    length += sent_length
            elif re.match('^load ([\w\._\-/]+)$', line):
                #TODO: handle if they give an incorrect path
                path = re.match('^load ([\w\._\-/]+)$', line).groups(1)[0]
                f = ZapFile()
                f.set_path(path)
                self.local_files.add(f)
                print("File at %s loaded for sharing." % path)
            elif re.match('^get (\w+)$', line):
                "get"
            else:
                self.print_usage()
                continue

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
