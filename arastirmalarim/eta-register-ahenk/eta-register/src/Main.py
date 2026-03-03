#!/usr/bin/env python3
import gi
import sys
import locale
from datetime import datetime
from MainWindow import MainWindow
from utils import check_args
from logger import logger

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, GLib

# Translation setup
import gettext

APPNAME_CODE = "eta-register"
TRANSLATIONS_PATH = "/usr/share/locale/"
locale.bindtextdomain(APPNAME_CODE, TRANSLATIONS_PATH)
locale.textdomain(APPNAME_CODE)
gettext.bindtextdomain(APPNAME_CODE, TRANSLATIONS_PATH)
gettext.textdomain(APPNAME_CODE)

# Attempt to set locale for sorting (collation)
try:
    # Use '' to respect user's environment settings for locale
    # Forcing 'tr_TR.UTF-8' might be an option if '' doesn't work and Turkish is always desired
    locale.setlocale(locale.LC_COLLATE, '')
    logger.info(f"Successfully set LC_COLLATE to: {locale.getlocale(locale.LC_COLLATE)}")
except locale.Error as e:
    logger.warning(f"Could not set locale for sorting (LC_COLLATE): {e}. Using default system sorting.")

# Shortcut for translations
_ = gettext.gettext


class Application(Gtk.Application):
    def __init__(self, *args, **kwargs):
        logger.info(_("Initializing ETA Register Application"))
        super().__init__(
            *args,
            application_id="tr.org.pardus.eta-register",
            flags=Gio.ApplicationFlags(8),
            **kwargs,
        )
        self.window = None

        self.add_main_option(
            "control",
            ord("c"),
            GLib.OptionFlags(0),
            GLib.OptionArg(0),
            _("Control of application"),
            None,
        )

    def do_activate(self):
        logger.info(_("Activating application"))
        if not self.window:
            logger.info(_("Creating new MainWindow"))
            self.window = MainWindow(self)
        else:
            logger.info(_("Calling controlArgs for existing window"))
            self.window.controlArgs()

    def do_command_line(self, command_line):
        logger.info(_("Processing command line arguments"))
        options = command_line.get_options_dict()
        options = options.end().unpack()
        self.args = options
        try:
            check_args(self)
        except Exception as e:
            logger.error(_("Error processing arguments: {}").format(e))
            return 1
        return 0


# Log application startup
logger.info(_("ETA Register Application starting"))
app = Application()
app.run(sys.argv)
