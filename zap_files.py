import threading

print("IMPORTING ZAP_FILES")
class ZapFiles:
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

    def get_all_files(self):
        #TODO: see how to make an immutable copy and return it so we
        # don't need to worry about anyone changing them.
        return self.files

    def clear(self):
        self.sem.acquire()
        self.files = []
        self.sem.release()

    def count(self):
        return len(self.files)
