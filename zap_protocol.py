import re

class ZapTorrentProtocolParser:
    """Parse the ZapTorrent protocol and return relevent information."""
    def __init__(self, data, **kwargs):
        self.message_type = ""
        self.protocol_matchers = {
            'files?': re.compile(r"^ZT 1\.0 files\?\n$"),
            'files': re.compile(r"^ZT 1\.0 files (?P<name>\w+) (?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) (?P<port>\d+) (?P<num_files>\d+)\n(?P<rest>.*)\n$",
                re.DOTALL),
            'inventory?': re.compile(r"^ZT 1\.0 inventory\? (?P<filename>[\w\.\-_]+)\n$"),
            'inventory': re.compile(r"^ZT 1\.0 inventory (?P<filename>[\w\.\-_]+) (?P<blocks>\d+)\n(?P<rest>.*)\n$", re.DOTALL),
            'download?': re.compile(r"^ZT 1\.0 download\? (?P<filename>[\w\.\-_]+) (?P<id>\d+) (?P<name>[\w]+) (?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})" +
                r" (?P<port>\d+)\n$"),
            'download': re.compile(r"^ZT 1\.0 download (?P<filename>[\w\.\-_]+) (?P<id>\d+) (?P<bytes>.*)$\n", re.DOTALL),
        }
        self.data = data
        self.fields = {}
        for k in kwargs:
            self.fields[k] = kwargs[k]

    def get_field(self, field_name):
        return self.fields.get(field_name)

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
            # splitting on new lines when the string ends with a newline results in
            # an empty string. Check for empty string when looking.
            for line_number, line in enumerate(file_list.split("\n")):
                # parse the file fields
                file_line_match = filename_re.match(line)
                if file_line_match is None or line_number + 1 > num_files:
                    if line == "":
                        continue
                    else:
                        self.message_type = 'error'
                        self.response = "ZT 1.0 error File lines not correctly formatted.\n"
                self.files_list.append({ 'filename': file_line_match.group('filename'),
                    'digest': file_line_match.group('digest'), 'blocks': file_line_match.group('blocks')})
        elif self.protocol_matchers['inventory?'].match(self.data):
            match = self.protocol_matchers['inventory?'].match(self.data)
            self.message_type = 'inventory?'
            self.fields['filename'] = match.group('filename')
        elif self.protocol_matchers['inventory'].match(self.data):
            match =  self.protocol_matchers['inventory'].match(self.data)
            self.message_type = 'inventory'
            self.fields['filename'] = match.group('filename')
            self.fields['blocks'] = match.group('blocks')
            block_list = match.group('rest')
            block_line_re = re.compile(r"^$")
            for line_number, line in enumerate(block_list.split('\n')):
                block_line_match = block_line_re.match(line)
                if block_line_match is None or line_number + 1 > self.fields['blocks']:
                    ""
            ""
        elif self.protocol_matchers['download?'].match(self.data):
            ""
        elif self.protocol_matchers['download'].match(self.data):
            ""
        else:
            self.message_type = "error"
            self.response = "ZT 1.0 error Could not recognize protocol.\n"

    def get_files(self):
        return self.files_list

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
        response_string = self.string
        if self.response_type == "files":
            # add the four fields
            response_string += " %s %s %d %d\n" % (self.fields['name'],
                    self.fields['ip'], self.fields['port'], len(self.stuff_to_add))
            print("in as_response before for loop, and constructed following response: %s" % response_string)
            for f in self.stuff_to_add:
                response_string += "%s %s %d\n" % (f.filename, f.digest, f.blocks)
            print("in as_response, and constructed following response: %s" % response_string)
        elif self.response_type == "files?":
            response_string += "\n"
        # <b>Message</b>
        # ZT 1.0 inventory? [filename]\n

        # <b>Response</b>
        # ZT 1.0 inventory [filename] [blocks]\n
        # [id] [bytes]\n
        # [id] [bytes]\n
        # ...
        elif self.response_type == 'inventory?':
            response_string += " %s\n" % self.fields['filename']
        elif self.response_type == 'inventory':
            response_string += " %s %d\n" % (self.fields['filename'], self.fields['blocks'])
            for f in self.stuff_to_add:
                response_string += "%d %d\n" % (f.id, f.bytes)
        # <b>Message</b>
        # ZT 1.0 download? [filename] [id] [name] [IP] [port]\n

        # <b>Response</b>
        # ZT 1.0 download [filename] [id] [bytes]\n
        # ...
        elif self.response_type == 'download?':
            response_string += " %s %d %s %s %d\n" % (self.fields['filename'],
                    self.fields['id'], self.fields['name'], self.fields['ip'],
                    self.fields['port'])
        elif self.response_type == 'download':
            response_string += " %s %d %d\n" % (self.fields['filename'], self.fields['id'],
                    len(self.fields['bytes']))
            response_string += self.fields['bytes']
        return response_string

