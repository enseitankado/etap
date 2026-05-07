#!/usr/bin/python3

import sys
import gi
import os

is_expired = os.path.isfile("/var/lib/eta/expire-uid/{}".format(os.getuid()))
if ("--test" not in sys.argv and "-t" not in sys.argv) and not is_expired:
    sys.exit(0)

gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gio, Gtk

from MainWindow import MainWindow

class Application(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="tr.org.eta.password-changer",
                         flags=Gio.ApplicationFlags.FLAGS_NONE, **kwargs
        )
        self.window = None
        GLib.set_prgname("tr.org.eta.password-changer")

        self.add_main_option(
            "test",
            ord("t"),
            GLib.OptionFlags(0),
            GLib.OptionArg(0),
            "Force start",
            None,
        )


    def do_activate(self):
        if not self.window:
            self.window = MainWindow(self)
        else:
            self.window.present()


app = Application()
app.run(sys.argv)
