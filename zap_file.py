import hashlib
import threading
import os
import sys
from zap_config import zap_debug_print

BLOCK_SIZE_IN_BYTES = 262144 #1024 bytes in a kilobyte times 256K sized-blocks
class ZapFileBlock:
    # Assume it points to a valid file
    file_flags = os.O_RDONLY
    if sys.platform == 'win32':
        file_flags = file_flags | os.O_BINARY

    def __init__(self, path, id, size, **kwargs):
        for k in kwargs:
            self.__dict__[k] = kwargs[k]
        # Status can either be present, downloading or not-present
        if 'status' not in kwargs:
            self.status = 'present'
        self.path = path
        self.id = id
        self.size = size

    def get_bytes(self):
        fd = os.open(self.path, ZapFileBlock.file_flags)
        os.lseek(fd, self.id * BLOCK_SIZE_IN_BYTES, 0)
        block_bytes = os.read(fd, self.size)
        os.close(fd)
        return block_bytes

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

class ZapFile:
    def __init__(self, **kwargs):
        self.blocks = []
        for k in kwargs:
            if k == 'path':
                self.set_path(kwargs[k])
            else:
                self.__dict__[k] = kwargs[k]
        self.sem = threading.Semaphore()

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def set_path(self, path):
        if os.path.isfile(path):
            self.path = path
            (p, self.filename) = os.path.split(self.path)
            self.calculate_digest_and_create_blocks()
            return True
        else:
            return False

    def calculate_digest_and_create_blocks(self):
        if self.path is not None:
            self.calculate_digest()
            f = open(self.path, "rb")
            f_str = f.read()
            f.close()
            self.blocks = []
            size = os.path.getsize(self.path)
            num_blocks = size / BLOCK_SIZE_IN_BYTES
            if (size  % BLOCK_SIZE_IN_BYTES) != 0:
                num_blocks += 1
            self.last_block_size = size - ((num_blocks - 1) * BLOCK_SIZE_IN_BYTES)
            for block_id in range(num_blocks):
                if block_id == (num_blocks - 1):
                    block_size = self.last_block_size
                else:
                    block_size = BLOCK_SIZE_IN_BYTES
                self.blocks.append(ZapFileBlock(self.path, block_id,
                    block_size, status="present"))
            self.number_of_blocks = len(self.blocks)
            return True
        else:
            return False

    def calculate_digest(self):
        if self.path is not None:
            f = open(self.path, "rb")
            f_str = f.read()
            f.close()
            self.digest = hashlib.sha224(f_str).hexdigest()

    def get_block(self, block_id):
        return self.blocks[block_id]

    def get_blocks(self, **kwargs):
        if 'status' in kwargs:
            for block in self.blocks:
                zap_debug_print(dir(block))

            return filter(lambda x: x.status == kwargs['status'], self.blocks)
        else:
            return self.blocks

    def mark_as_remote(self):
        # each block stores its bytes in internal storage?
        self.path = os.path.join(os.path.abspath(sys.path[0]), 'downloads', self.filename)
        for i in range(int(self.number_of_blocks)):
            self.blocks.append(ZapFileBlock(self.path, i, BLOCK_SIZE_IN_BYTES, status='not-present'))


    def does_block_needs_downloading(self, block_id):
        return self.blocks[block_id].status == 'not-present'

    def mark_block_as(self, status, block_id):
        self.blocks[block_id].status = status

    def set_block_data(self, block_id, data):
        self.blocks[block_id].data = data

    def block_is_present(self, block_id):
        # zap_debug_print("Calling block_is_present, and len(self.blocks) = ", len(self.blocks),
        #     "block_id is ", block_id, "status is ", self.blocks[block_id].status)
        return len(self.blocks) > block_id and block_id >= 0 and self.blocks[block_id].status == 'present'

    def is_downloaded(self):
        """If any blocks are not downloaded, then the whole
        file is not downloaded."""
        for block in self.blocks:
            if block.status != 'present':
                return False
        return True

    def save_to_disk(self):
        fp = open(self.path, "w")
        for block in self.blocks:
            fp.write(block.data)
        fp.close()
        self.calculate_digest()


class ZapFiles:
    def __init__(self):
        self.files = {}
        self.sem = threading.Semaphore()

    def add(self, f):
        """Add a file to the files we are sharing."""
        self.sem.acquire()
        if f.filename not in self.files:
            self.files[f.filename] = [f]
        else:
            self.files[f.filename].append(f)
        self.sem.release()

    def get(self, filename):
        """Check for filename in files. If in it, return the file. Else return None"""
        return self.files.get(filename)

    def get_files(self):
        return self.files

    def clear(self):
        self.sem.acquire()
        self.files = {}
        self.sem.release()

    def remove(self, f):
        if f.filename not in self.files:
            return None
        else:
            if f in self.files[f.filename]:
                self.files[f.filename].remove(f)
                return True
            else:
                return False



    def count(self):
        return len(self.files)
