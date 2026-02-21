import threading
import gi
from gi.repository import Gio

def asynchronous(func):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread
    return wrapper

gsettings = Gio.Settings.new("tr.org.pardus.eta.count")

def gsettings_get(variable):
    return gsettings.get_string(variable)

def gsettings_set(variable, value):
    gsettings.set_string(variable,value)
    gsettings.sync()
