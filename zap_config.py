# Class that just holds config variables shared across the program.
# Yup, it is dirty.

class ZapConfig:
    verbose = False
    ip = None
    tcp_port = None
    name = "BEANS"

def zap_debug_print(*args):
    if ZapConfig.verbose:
        print(args)
