import hashlib
import threading
import os

class ZapLocalFiles:
    def __init__(self):
        self.files = []
        self.sem = threading.Semaphore()
        # self.lock = threading.Lock()

    def add(self, f):
        """Add a file to the files we are sharing."""
        self.sem.acquire()
        self.files.append(f)
        self.sem.release()

    def get(self, filename):
        """Check for filename in files. If in it, return the file. Else return None"""
        self.sem.acquire()
        self.sem.release()

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
        print("someone called get_all_files!")
        return self.files


BLOCK_SIZE_IN_BYTES = 262144 #1024 bytes in a kilobyte times 256K sized-blocks
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
            self.last_block = size - ((self.blocks - 1) * BLOCK_SIZE_IN_BYTES)

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

