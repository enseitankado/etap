import os
import gi
import threading
import subprocess

import locale
from locale import gettext as _

# Translation Constants:
APPNAME = "eta-shutdown"
TRANSLATIONS_PATH = "/usr/share/locale"

# Translation functions:
locale.bindtextdomain(APPNAME, TRANSLATIONS_PATH)
locale.textdomain(APPNAME)


gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, GLib

ACTION=os.path.dirname(os.path.abspath(__file__))+"/actions.py"

class ShutdownMenu:
    def __init__(self, application):
        window = Gtk.Window()
        window.set_application(application)
        window.connect("destroy", Gtk.main_quit)
        window.set_skip_taskbar_hint(True)
        window.set_position(Gtk.WindowPosition.CENTER)
        window.set_title(_("ETA Shutdown"))

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_spacing(18)
        box.pack_start(self.create_button("eta-shutdown-poweroff", _("Power Off"),
            ["dbus-send", "--system", "--print-reply",
             "--dest=org.freedesktop.login1", "/org/freedesktop/login1",
             "org.freedesktop.login1.Manager.PowerOff", "boolean:true"
            ]), True, True, 0)
        box.pack_start(self.create_button("eta-shutdown-reboot", _("Restart"), ["pkexec", ACTION, "reboot"]), True, True, 0)
        box.pack_start(self.create_button("eta-shutdown-force-poweroff", _("Force Power Off"), ["pkexec", ACTION, "poweroff"]), True, True, 0)
        box.pack_start(self.create_button("eta-shutdown-logout", _("Log Out"), ["pkill","-KILL", "-u", os.environ["USER"]]), True, True, 0)

        window.add(box)
        window.set_resizable(False)
        window.set_keep_above(True)
        window.show_all()

    def create_button(self, icon, name, command):
        def event(winget):
            subprocess.run(command)
        button = Gtk.Button()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        image = Gtk.Image()
        image.set_from_icon_name(icon, 0)
        image.set_pixel_size(150)
        box.add(image)
        label=Gtk.Label()
        label.set_markup("<span font=\"16\">"+name+"</span>")
        box.add(label)
        button.add(box)
        button.connect("clicked", event)
        button.set_relief(Gtk.ReliefStyle.NONE)
        return button



class Application(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="tr.org.etap.poweroff",
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS, **kwargs)
        self.window = None

    def do_activate(self):
        if not self.window:
            self.window = ShutdownMenu(self)


def run():
    app = Application()
    app.run()


if __name__ == "__main__":
    run()
