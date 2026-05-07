#!/usr/bin/env python3

import gi
import os
import subprocess

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

try:
    import locale
    from locale import gettext as _

    # Translation Constants:
    APPNAME = "eta-password-changer"
    TRANSLATIONS_PATH = "/usr/share/locale"
    locale.bindtextdomain(APPNAME, TRANSLATIONS_PATH)
    locale.textdomain(APPNAME)
except:
    # locale load fallback
    def _(msg):
        return msg

ACTIONS = os.path.dirname(os.path.abspath(__file__)) + "/Actions.py"

class MainWindow:
    def __init__(self, application):
        self.builder = Gtk.Builder()

        # Import UI file:
        glade_file = (
            os.path.dirname(os.path.abspath(__file__)) + "/ui/MainWindow.ui"
        )

        self.builder.add_from_file(glade_file)

        self.ui_window_main.set_application(application)
        self.application = application

        self.connect_signals()

        # show main window
        self.ui_window_main.show()
        self.check_match(None)

    def __getattr__(self, name):
        # return object if exists
        if self.builder.get_object(name):
            return self.builder.get_object(name)


    def connect_signals(self):
        self.ui_button_cancel.connect("clicked", lambda x: self.application.quit())
        self.ui_button_change.connect("clicked", self.change_password)
        self.ui_password_1.connect("changed", self.check_match)
        self.ui_password_2.connect("changed", self.check_match)

        self.ui_password_1.connect("icon-press", self.on_icon_pressed)
        self.ui_password_1.connect("icon-release", self.on_icon_released)
        self.ui_password_2.connect("icon-press", self.on_icon_pressed)
        self.ui_password_2.connect("icon-release", self.on_icon_released)


    def on_icon_pressed(self, entry, icon_pos, event):
        entry.set_visibility(True)
        entry.set_icon_from_icon_name(icon_pos, "view-conceal-symbolic")

    def on_icon_released(self, entry, icon_pos, event):
        entry.set_visibility(False)
        entry.set_icon_from_icon_name(icon_pos, "view-reveal-symbolic")

    def check_match(self, widget):
        pass1 = self.ui_password_1.get_text()
        pass2 = self.ui_password_2.get_text()
        match = (pass1 == pass2 and len(pass1) > 0)
        self.ui_button_change.set_sensitive(match)
        if len(pass1) == 0:
            self.ui_label_status.set_text("")
        elif match:
            self.ui_label_status.set_text("")
        else:
            self.ui_label_status.set_text(_("Passwords do not match."))

    def change_password(self, widget):
        sp = subprocess.run(["pkexec", ACTIONS, self.ui_password_1.get_text()], capture_output=True)
        if sp.returncode == 0:
            self.application.quit()
