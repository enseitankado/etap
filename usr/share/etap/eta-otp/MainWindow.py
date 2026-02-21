#!/usr/bin/env python3
import gi
import sys
import os
import threading
import subprocess
import random
import base64
import pyotp
import pickle
import qrcode
from io import BytesIO

import locale
from locale import gettext as _

# Translation Constants:
APPNAME = "eta-otp-lock"
TRANSLATIONS_PATH = "/usr/share/locale"

# Translation functions:
locale.bindtextdomain(APPNAME, TRANSLATIONS_PATH)
locale.textdomain(APPNAME)


import gui
gui._ = _

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gio, GdkPixbuf

action_file = os.path.dirname(os.path.abspath(__file__))+"/actions.py"
class MainWindow:
    def __init__(self, application):
        self.secret = self.generate_secret()

        gui.create_gui(self)
        self.application = application
        self.ui_window_main.set_application(application)

        self.ui_button_newotp.connect("clicked", self.on_newotp_event)
        self.ui_button_show.connect("clicked", self.on_show_event)
        self.ui_button_import.connect("clicked", self.on_import_event)
        self.ui_button_export.connect("clicked", self.on_export_event)
        self.ui_button_delete.connect("clicked", self.on_delete_event)
        self.ui_button_fromkey.connect("clicked", self.on_fromkey_event)
        self.ui_button_qr_back.connect("clicked", self.on_qr_back_event)

        self.ui_window_main.show_all()
        self.ui_button_qr_back.hide()

        self.ui_stack_main.set_visible_child_name("main")
        sp = subprocess.run(["pkexec", action_file, "status"])
        if sp.returncode == 1:
            pass
        elif sp.returncode == 0:
            sp = subprocess.run(["pkexec", action_file, "load"], capture_output=True)
            self.secret = sp.stdout.decode("utf-8").strip()
            self.ui_stack_main.set_visible_child_name("settings")
        else:
            self.application.quit()

########### button event functions ###########

    def on_qr_back_event(self, widget):
        self.ui_button_qr_back.hide()
        self.ui_stack_main.set_visible_child_name("settings")

    def on_newotp_event(self, widget):
        self.secret = self.generate_secret()
        self.ui_stack_main.set_visible_child_name("settings")
        subprocess.run(["pkexec", action_file, "save", self.secret])

    def on_show_event(self, widget):
        self.update_qr()
        self.ui_stack_main.set_visible_child_name("qr")
        self.ui_button_qr_back.show()

    def on_delete_event(self, widget):
        self.ui_stack_main.set_visible_child_name("main")
        subprocess.run(["pkexec", action_file, "remove"])

    def on_fromkey_event(self, widget):
        secret = self.input_secret()
        if secret:
            if self.is_base32(secret):
                self.secret = secret
            else:
                self.secret = self.generate_secret(secret.encode("utf-8"))
            self.ui_stack_main.set_visible_child_name("settings")
            subprocess.run(["pkexec", action_file, "save", self.secret])

    def on_import_event(self, widget):
        filename = self.open_file()
        if filename:
            try:
                with open(filename, "rb") as f:
                    data = pickle.load(f)
                    if data["user"] != os.environ["USER"]:
                        self.info_dialog(_("Invalid Pin"), _("Pin user is not you"))
                    self.secret = base64.b32encode(data["secret"]).decode("utf-8")
                self.ui_stack_main.set_visible_child_name("settings")
                subprocess.run(["pkexec", action_file, "save", self.secret])
            except:
                self.info_dialog("ERROR", _("Failed to read Pin file"))

    def on_export_event(self, widget):
        filename = self.save_file()
        if filename:
            try:
                with open(filename, "wb") as f:
                    data = {}
                    data["secret"] = base64.b32decode(self.secret.encode("utf-8"))
                    data["user"] = os.environ["USER"]
                    pickle.dump(data, file=f)
            except:
                self.info_dialog(_("Error"), _("Failed to export Pin key file"))



########### helper functions ###########

    def update_qr(self):
        self.ui_label_secret.set_text(self.secret)
        self.ui_image_qr.set_from_pixbuf(self.get_qr_code(self.secret))

    def generate_secret(self, random_bytes = None):
        if random_bytes is None:
            random_bytes = os.urandom(10)
        return base64.b32encode(random_bytes).decode("utf-8")

    def is_base32(self, data):
        if len(data) % 4 > 0:
            return False
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567="
        for c in data:
            if not c in alphabet:
                return False
        return True

    def get_qr_code(self, secret):
        # Generate the QR code
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(os.environ["USER"]+"@etap", issuer_name="pardus-etap")
        qr = qrcode.make(uri+"&algorithm=SHA1&digits=6&period=30", box_size=5)

        # Convert QR code to a format that GTK can use
        with BytesIO() as output:
            qr.save(output, format="PNG")
            output.seek(0)
            # Create a Gio.MemoryInputStream from the BytesIO object
            memory_stream = Gio.MemoryInputStream.new_from_data(output.getvalue(), None)
            return GdkPixbuf.Pixbuf.new_from_stream(memory_stream, None)
        return None

########### file pick / save functions ###########

    def open_file(self):
        dialog = Gtk.FileChooserDialog(
            title=_("Select a File"),
            parent=self.ui_window_main,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dialog.add_button(Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        filter = Gtk.FileFilter()
        filter.set_name(_("Pin keys"))
        filter.add_pattern("*.totp")
        dialog.add_filter(filter)

        response = dialog.run()
        filename = None
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
        dialog.destroy()
        return filename

    def save_file(self):
        dialog = Gtk.FileChooserDialog(
            title=_("Save a File"),
            parent=self.ui_window_main,
            action=Gtk.FileChooserAction.SAVE
        )
        dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dialog.add_button(Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        filter = Gtk.FileFilter()
        filter.set_name(_("Pin keys"))
        filter.add_pattern("*.totp")
        dialog.add_filter(filter)

        response = dialog.run()
        filename = None
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            if not filename.endswith(".totp"):
                filename += ".totp"
        dialog.destroy()
        return filename

    def input_secret(self):
        dialog = Gtk.Dialog(
            title=_("Enter a Secret"),
            parent=self.ui_window_main
        )
        dialog.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)


        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        dialog.get_content_area().add(box)

        entry = Gtk.Entry()
        entry.set_max_length(16)
        entry.set_placeholder_text(_("Enter your key here"))
        box.pack_start(entry, True, True, 0)

        dialog.show_all()
        response = dialog.run()

        # Check the response
        user_input = None
        if response == Gtk.ResponseType.OK:
            user_input = entry.get_text()
        dialog.destroy()
        return user_input

    def info_dialog(self, msg, desc):
        dialog = Gtk.MessageDialog(
            parent=self.ui_window_main,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=msg,
        )
        dialog.format_secondary_text(desc)
        dialog.run()
        dialog.destroy()
