import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gi
from gi.repository import GLib

from service import service

sec = 60

def main():
    service()
    GLib.timeout_add(1000*sec, main)


GLib.idle_add(main)
GLib.MainLoop().run()
