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

class ZapFile:
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
        elif attribute == "number_of_blocks":
            return len(self.blocks)
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
                self.blocks.append(ZapFileBlock(self.path, block_id,
                    block_size, status="present"))
            # return True
        else:
            return False


    #TODO: grant thread-safe access to blocks
    def get_block(self, block_id):
        return self.blocks[block_id]



class ZapFiles:
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
        return self.files

    def clear(self):
        self.sem.acquire()
        self.files = []
        self.sem.release()

    def count(self):
        return len(self.files)
