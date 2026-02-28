#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 23 23:47:01 2024

@author: fatih
"""
import sys

import gi

from MainWindow import MainWindow

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib


class Application(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="tr.org.pardus.eta-resolution",
                         flags=Gio.ApplicationFlags(8), **kwargs)
        self.window = None

        self.add_main_option(
            "set",
            ord("s"),
            GLib.OptionFlags(0),
            GLib.OptionArg(1),
            "Set the new resolution",
            None,
        )

        self.add_main_option(
            "nogui",
            ord("n"),
            GLib.OptionFlags(0),
            GLib.OptionArg(0),
            "Set the new resolution but not show gui.",
            None,
        )

        self.add_main_option(
            "autostart-mode",
            ord("a"),
            GLib.OptionFlags(0),
            GLib.OptionArg(0),
            "Autostart mode with sleep",
            None,
        )

    def do_activate(self):
        # We only allow a single window and raise any existing ones
        if not self.window:
            self.window = MainWindow(self)
            Gtk.main()
        else:
            self.window.control_args()

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        options = options.end().unpack()
        self.args = options
        self.activate()
        return 0

app = Application()
app.run(sys.argv)
