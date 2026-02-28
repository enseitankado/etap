import pickle
import json
import binascii
import sys
import traceback

def read(ctx):
    if ctx == None:
        return None
    try:
        print("########")
        print("Cretential Reading")
        loaded = pickle.loads(ctx)
        loaded = binascii.unhexlify(loaded)
        loaded = json.loads(loaded.decode("utf-8"))
        print("########")
        print("Cretential data", loaded)
    except Exception:
        print(traceback.format_exc())
        return None
    return loaded
