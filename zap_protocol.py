import re

class ZapTorrentProtocolParser:
    """Parse the ZapTorrent protocol and return relevent information."""
    def __init__(self, data, **kwargs):
        self.message_type = ""
        self.protocol_matchers = {
            'files?': re.compile(r"^ZT 1\.0 files\?\n$"),
            'files': re.compile(r"^ZT 1\.0 files (?P<name>\w+) (?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) (?P<port>\d+) (?P<num_files>\d+)\n(?P<rest>.*)$",
                re.DOTALL),
            'inventory?': re.compile(r"^ZT 1\.0 inventory? (?P<filename>\w+)\n$"),
            #TODO: match the correct number of fields after the first line
            'inventory': re.compile(r"^ZT 1\.0 inventory (?P<filename>\w+) (?P<blocks>\d+)\n(.*)$"),
        }
        self.data = data
        self.fields = {}
        for k in kwargs:
            self.fields[k] = kwargs[k]

    def parse(self):
        if self.protocol_matchers['files?'].match(self.data):
            self.message_type = "files?"
        elif self.protocol_matchers['files'].match(self.data):
            print("found something that matches files")
            match = self.protocol_matchers['files'].match(self.data)
            self.message_type = 'files'
            self.fields['ip'] = match.group('ip')
            self.fields['name'] = match.group('name')
            self.fields['port'] = match.group('port')
            self.files_list = []
            num_files = match.group('num_files')
            file_list = match.group('rest')
            filename_re = re.compile(r"^(?P<filename>[\w\.\-_]+) (?P<digest>[\w\d]+) (?P<blocks>\d+)$")
            for line_number, line in enumerate(file_list.split("\n")):
                # parse the file fields
                file_line_match = filename_re.match(line)
                if file_line_match is None or line_number + 1 > num_files:
                    print("error in parsing files query:", self.data)
                    self.message_type = 'error'
                    self.response = "ZT 1.0 error File lines not correctly formatted.\n"


                    #TODO: what to do if the later lines don't match?
        else:
            self.message_type = "error"
            self.response = "ZT 1.0 error Could not recognize protocol.\n"

class ZapTorrentProtocolResponse:
    def __init__(self, **kwargs):
        self.fields = {}
        self.response_type = None
        for k in kwargs:
            if k == "response_type":
                self.response_type = kwargs[k]
            else:
                self.fields[k] = kwargs[k]
        self.string = "ZT 1.0 " + self.response_type
        self.stuff_to_add = []


    def add(self, stuff):
        self.stuff_to_add.append(stuff)

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
            for f in self.stuff_to_add:
                self.string += "%s %s %d\n" % (f.filename, f.digest, f.blocks)
            print("in as_response, and constructed following response: %s" % self.string)
        elif self.response_type == "files?":
            self.string += "\n"
        return self.string

