#!/usr/bin/env python3

import sys
import gi

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, Gio, GLib

from MainWindow import MainWindow

if __name__ == "__main__":
    window = MainWindow()
    Gtk.main()
