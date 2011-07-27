import re

class ZapTorrentProtocolParser:
    """Parse the ZapTorrent protocol and return relevent information."""
    def __init__(self, data):
        self.message_type = ""
        self.protocol_matchers = {
            #TODO: make these match newlines
            #TODO: match multiple fields
            'files?': re.compile(r"^ZT 1\.0 files\?\n$"),
            'files': re.compile(r"^ZT 1\.0 files (?P<name>\w+) (?<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) (?P<port>\d+) (?P<num_files>\d+)\n(?P<rest>.*)$"),
            'inventory?': re.compile(r"^ZT 1\.0 inventory? (?P<filename>\w+)\n$"),
            #match the correct number of fields after the first line
            'inventory': re.compile(r"^ZT 1\.0 inventory (?P<filename>\w+) (?P<blocks>\d+)\n(.*)$"),
        }
        self.data = data

    def parse(self):
        if not self.protocol_re.match(self.data):
            self.message_type = "error"
            self.response = "ZT 1.0 error Could not recognize protocol.\n"
        elif self.protocol_matchers['files?'].match(self.data):
            match = self.protocol_matchers['files?'].match(self.data)
            self.message_type = "files?"
        elif self.protocol_matchers['files'].match(self.data):
            match = self.protocol_matcher['files'].match(self.data)
            self.message_type = 'files'

class ZapTorrentProtocolResponse:
    def __init__(self, response_type):
        self.response_type = response_type
        self.string = "ZT 1.0 " + self.response_type
        self.fields = {}
        self.stuff_to_add = []


    def add(self, stuff):
        stuff_to_add.append(stuff)

    def as_response(self):
        """Format the response as a ZapTorrent protocol response and
        return it as a string."""
        # <b>Response</b>
        # ZT 1.0 files [name] [IP] [port] [number]\n
        # [filename] [digest] [blocks]\n
        # [filename] [digest] [blocks]\n
        # ...
        if self.response_type == "files":
            # add the four fields
            self.string += " %s %s %d %d\n" % (self.fields['name'],
                    self.fields['ip'], self.fields['port'], len(self.stuff_to_add))
            for f in stuff_to_add:
                self.string += "%s %s %d\n" % (f.filename, f.digest, f.blocks)
        elif self.response_type == "files?":
            self.string += "\n"
        return self.string

