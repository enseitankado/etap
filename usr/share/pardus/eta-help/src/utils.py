#!/usr/bin/env python3

import os
import subprocess

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class Dialog(Gtk.MessageDialog):
    def __init__(self, style, buttons, title, text, text2=None, parent=None):
        Gtk.MessageDialog.__init__(self, parent, 0, style, buttons)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_title(title)
        self.set_markup(text)

    def show(self):
        try:
            response = self.run()
        finally:
            self.destroy()


def ErrorDialog(*args):
    dialog = Dialog(Gtk.MessageType.ERROR, Gtk.ButtonsType.NONE, *args)
    dialog.add_button("OK", Gtk.ResponseType.OK)
    return dialog.show()


def get_desktop_env():
    current_desktop = "{}".format(os.environ.get('XDG_CURRENT_DESKTOP'))
    return current_desktop


def get_desktop_env_version(desktop):
    de_version_command = {"xfce": ["xfce4-session", "--version"],
                          "gnome": ["gnome-shell", "--version"],
                          "cinnamon": ["cinnamon", "--version"],
                          "mate": ["mate-about", "--version"],
                          "kde": ["plasmashell", "--version"],
                          "lxqt": ["lxqt-about", "--version"],
                          "budgie": ["budgie-desktop", "--version"]}
    version = ""
    desktop = "{}".format(desktop.lower())
    try:
        if "xfce" in desktop:
            output = (subprocess.run(de_version_command["xfce"], shell=False, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)).stdout.decode().strip()
            for line in output.split("\n"):
                if line.startswith("xfce4-session "):
                    version = line.split(" ")[-1].strip("()")
                    break

        elif "gnome" in desktop:
            output = (subprocess.run(de_version_command["gnome"], shell=False, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)).stdout.decode().strip()
            for line in output.split("\n"):
                if "GNOME Shell" in line:
                    version = line.split(" ")[-1]

        elif "cinnamon" in desktop:
            output = (subprocess.run(de_version_command["cinnamon"], shell=False, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)).stdout.decode().strip()
            version = output.split(" ")[-1]

        elif "mate" in desktop:
            output = (subprocess.run(de_version_command["mate"], shell=False, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)).stdout.decode().strip()
            version = output.split(" ")[-1]

        elif "kde" in desktop:
            output = (subprocess.run(de_version_command["kde"], shell=False, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)).stdout.decode().strip()
            version = output.split(" ")[-1]

        elif "lxqt" in desktop:
            output = (subprocess.run(de_version_command["lxqt"], shell=False, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)).stdout.decode().strip()
            for line in output:
                if "liblxqt" in line:
                    version = line.split()[1].strip()

        elif "budgie" in desktop:
            output = (subprocess.run(de_version_command["budgie"], shell=False, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)).stdout.decode().strip()
            version = output.split("\n")[0].strip().split(" ")[-1]
    except Exception as e:
        print("{}".format(e))

    return version


def get_session_type():
    session = "{}".format(os.environ.get('XDG_SESSION_TYPE')).capitalize()
    return session
