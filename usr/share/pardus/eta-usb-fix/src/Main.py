#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Sep 27 16:13:59 2025

@author: fatih
"""
import sys

import gi

from MainWindow import MainWindow

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib


class Application(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="tr.org.pardus.eta-usb-fix",
                         flags=Gio.ApplicationFlags.NON_UNIQUE, **kwargs)
        GLib.set_prgname("tr.org.pardus.eta-usb-fix")
        self.window = None

    def do_activate(self):
        self.window = MainWindow(self)


app = Application()
app.run(sys.argv)
