import hashlib
import threading
import os
import sys
from collections import namedtuple

BLOCK_SIZE_IN_BYTES = 262144 #1024 bytes in a kilobyte times 256K sized-blocks
class ZapFileBlock:
    #Assume it points to a valid file
    file_flags = os.O_RDONLY
    if sys.platform == "win32":
        file_flags = file_flags | os.O_BINARY
    def __init__(self, path, id, size, **kwargs):
        for k in kwargs:
            self.k = kwargs[k]
        # Status can either be present, downloading or missing
        if "status" not in kwargs:
            self.status = "present"
        self.path = path
        self.id = id
        self.size = size

    def get_bytes(self):
        fd = os.open(self.path, ZapFileBlock.file_flags)
        os.lseek(fd, self.id * BLOCK_SIZE_IN_BYTES, 0)
        block_bytes = os.read(fd, self.size)
        return block_bytes

class ZapBetterFile:
    def __init__(self, **kwargs):
        self.properties = {}
        self.blocks = []
        for k in kwargs:
            if k == 'path':
                self.set_path(kwargs[k])
            else:
                self.properties[k] = kwargs[k]

    def __getattr__(self, attribute):
        if self.properties.has_key(attribute):
            return self.properties[attribute]
        else:
            raise AttributeError, name

    def __setattr__(self, name, value):
        self.properties[name] = value

    def set_path(self, path):
        if os.path.exists(path):
            self.properties['path'] = path
            (p, self.properties['filename']) = os.path.split(self.path)
            self.calculate_digest_and_create_blocks()
            return True
        else:
            return False

    def calculate_digest_and_create_blocks(self):
        if self.path is not None:
            f = open(self.path, "rb")
            f_str = f.read()
            f.close()
            self.properties['digest'] = hashlib.sha224(f_str).hexdigest()
            self.blocks = []
            size = os.path.getsize(self.path)
            num_blocks = size / BLOCK_SIZE_IN_BYTES
            if (size  % BLOCK_SIZE_IN_BYTES) != 0:
                num_blocks += 1
            last_block_size = size - ((num_blocks - 1) * BLOCK_SIZE_IN_BYTES)
            for block_id in range(num_blocks):
                if block_id == (num_blocks - 1):
                    block_size = last_block_size
                else:
                    block_size = BLOCK_SIZE_IN_BYTES
                self.blocks.append(ZapFileBlock(self.path, block_id,block_size))
            # return True
        else:
            return False

    #TODO: grant thread-safe access to blocks
    def get_block(self, block_id):
        return self.blocks[block_id]



class ZapLocalFiles:
    def __init__(self):
        self.files = {}
        self.sem = threading.Semaphore()
        # self.lock = threading.Lock()

    def add(self, f):
        """Add a file to the files we are sharing."""
        self.sem.acquire()
        self.files[f.filename] = f
        self.sem.release()

    def get(self, filename):
        """Check for filename in files. If in it, return the file. Else return None"""
        return self.files.get(filename)

    def get_files(self):
        #TODO: see how to make an immutable copy and return it so we
        # don't need to worry about anyone changing them.
        return self.files

    def clear(self):
        self.sem.acquire()
        self.files = []
        self.sem.release()

    def count(self):
        return len(self.files)

class ZapRemoteFiles:
    def __init__(self):
        self.files = {}
        self.sem = threading.Semaphore()

    def add(self, f):
        self.sem.acquire()
        if f.filename in self.files:
            self.files[f.filename].append(f)
        else:
            self.files[f.filename] = [f]
        self.sem.release()

    def get_by_filename(self, filename):
        self.sem.acquire()
        if filename in self.files:
            return self.files[filename]
        else:
            return None
        self.sem.release()

    def clear(self):
        self.sem.acquire()
        self.files = {}
        self.sem.release()

    def get_all_files(self):
        #TODO: what if there are multiple copies of the file
        # across the network?
        print("someone called get_all_files!")
        return self.files


namedtuple("ZapBlock", "id bytes")
class ZapFile:
    """Represents the attributes of a local file."""
    def __init__(self):
        self.path = None
        self.filename = None
        self.digest = None
        self.blocks = None
        self.size = None
        self.last_block_size = None

    def create_digest(self):
        if self.path != None:
            # Hash file at path
            f = open(self.path, "rb")
            #TODO: look at this for larger files
            f_str = f.read()
            f.close()
            self.digest = hashlib.sha224(f_str).hexdigest()
            return True
        else:
            return False

    def calculate_blocks(self):
        if self.path != None:
            size = 0
            try:
                size = os.path.getsize(self.path)
            except os.error, (code, message):
                print("Error: path is set but file does not exist.")
                return
            # If the size is not a multiple of block_size_in_bytes, then
            # the number of blocks was rounded down by integer division, so
            # we add 1 to get the correct number of blocks.
            self.blocks = size /  BLOCK_SIZE_IN_BYTES
            if size % BLOCK_SIZE_IN_BYTES != 0:
                self.blocks += 1
            self.last_block_size = size - ((self.blocks - 1) * BLOCK_SIZE_IN_BYTES)

    def get_blocks_description(self):
        blocks = []
        for block_id in range(self.blocks):
            if block_id == self.blocks - 1:
                blocks.append(ZapBlock(block_id, self.last_block_size))
            else:
                blocks.append(ZapBlock(block_id, BLOCK_SIZE_IN_BYTES))
        return blocks


    def set_path(self, path):
        if not os.path.exists(path):
            return False
        else:
            self.path = path
            (fp, self.filename) = os.path.split(path)
            self.create_digest()
            self.calculate_blocks()
            return True

class ZapRemoteFile:
    def __init__(self):
        # Should the file know its ip address and port? Yes, because that makes is its location!
        self.ip = None
        self.port = None
        self.hostname = None
        self.blocks = None
        self.last_block_size = None
        self.digest = None
        self.filename = None

