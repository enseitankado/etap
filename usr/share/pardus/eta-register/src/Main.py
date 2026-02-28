#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
# HACK: Ensure localhost requests are not proxied by default by libsoup.
# This should be set before any network-related gi imports.
no_proxy = os.environ.get("no_proxy", "")
if "localhost" not in no_proxy:
    os.environ["no_proxy"] = f"{no_proxy},localhost,127.0.0.1".strip(',')

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib
import sys
import locale
import gettext
import pwd
from config import APPNAME_CODE, TRANSLATIONS_PATH, REQUIRED_USER
from MainWindow import MainWindow
from logger import logger
from checks import is_vm, is_correct_user

try:
    locale.bindtextdomain(APPNAME_CODE, TRANSLATIONS_PATH)
    gettext.bindtextdomain(APPNAME_CODE, TRANSLATIONS_PATH)
    gettext.textdomain(APPNAME_CODE)
    _ = gettext.gettext
except Exception as e:
    print(f"Error setting up translation: {e}")
    _ = str


def show_preflight_error_and_quit(title, message):
    """
    Displays a simple GTK error dialog for checks that fail before the
    main application loop starts, then exits.
    """
    dialog = Gtk.MessageDialog(
        transient_for=None,
        modal=True,
        destroy_with_parent=True,
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.OK,
        text=title,
    )
    dialog.format_secondary_text(message)
    dialog.run()
    dialog.destroy()
    sys.exit(1)


class Application(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            application_id="tr.org.pardus.eta-register",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
            **kwargs,
        )
        self.window = None
        self.status = None

        self.add_main_option(
            "status",
            0, # no short name
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING,
            _("Set the initial status from the dispatcher."),
            None,
        )

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        status_variant = options.lookup_value("status", None)
        
        if status_variant:
            self.status = status_variant.get_string()
        else:
            # If no status is provided, it means the app was likely started directly.
            # We'll handle this inside MainWindow.
            self.status = "unknown"

        self.activate()
        return 0

    def do_activate(self):
        if not self.window:
            self.window = MainWindow(self, status=self.status)
        self.window.present()


if __name__ == "__main__":
    logger.info("--- Application Starting ---")

    # --- Pre-flight Checks ---
    # These checks run before any part of the main application window is created.

    # 1. Virtual Machine Check
    if is_vm():
        show_preflight_error_and_quit(
            _("Virtual Machine Detected"),
            _("This application cannot be run inside a virtual machine.")
        )

    # 2. User Check
    correct_user, current_user = is_correct_user()
    if not correct_user:
        error_msg = _("This application must be run by the '{required}' user, but it is run by '{current}'.").format(
            required=REQUIRED_USER,
            current=current_user
        )
        show_preflight_error_and_quit(
            _("Invalid User"),
            error_msg
        )

    app = Application()
    exit_status = app.run(sys.argv)
    logger.info("--- Application Exited with status: {exit_status} ---".format(exit_status=exit_status))
    sys.exit(exit_status)
