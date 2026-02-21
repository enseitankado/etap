#!/usr/bin/python3

import os
import sys
import gi

os.environ["GDK_CORE_DEVICE_EVENTS"] = "1"

gi.require_version("Gtk", "3.0")
from gi.repository import Gio, Gtk


from MainWindow import MainWindow


class Application(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            application_id="tr.org.eta.usb-register",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
            **kwargs,
        )
        self.window = None

    def do_activate(self):
        self.window = MainWindow(self)


app = Application()
app.run(sys.argv)
