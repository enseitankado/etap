#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Sep 27 16:13:59 2025

@author: fatih
"""
import json
import locale
import os

import gi

from Notification import Notification
from USBDeviceManager import USBDeviceManager

gi.require_version("GLib", "2.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject, GLib, Pango

from locale import gettext as _

locale.bindtextdomain('eta-usb-fix', '/usr/share/locale')
locale.textdomain('eta-usb-fix')


class MainWindow(object):
    def __init__(self, application):
        self.Application = application

        self.main_window_ui_filename = os.path.dirname(os.path.abspath(__file__)) + "/../ui/MainWindow.glade"
        try:
            self.GtkBuilder = Gtk.Builder.new_from_file(self.main_window_ui_filename)
            self.GtkBuilder.connect_signals(self)
        except GObject.GError:
            print("Error reading GUI file: " + self.main_window_ui_filename)
            raise

        self.define_components()
        self.define_variables()

        self.ui_main_window.set_application(application)

        # Set version
        # If not getted from __version__ file then accept version in MainWindow.glade file
        try:
            version = open(os.path.dirname(os.path.abspath(__file__)) + "/__version__").readline()
            self.ui_about_dialog.set_version(version)
        except:
            pass

        self.ui_about_dialog.set_program_name(_("ETA USB Fix"))

        # Get inserted USB devices
        self.usbDevice = []
        self.usbManager = USBDeviceManager()
        self.usbManager.setUSBRefreshSignal(self.list_usb_devices)
        self.list_usb_devices()

        self.ui_main_window.show_all()

    def define_components(self):
        self.ui_main_window = self.GtkBuilder.get_object("ui_main_window")
        self.ui_about_dialog = self.GtkBuilder.get_object("ui_about_dialog")
        self.ui_usbdevices_combobox = self.GtkBuilder.get_object("ui_usbdevices_combobox")
        self.ui_usbdevices_liststore = self.GtkBuilder.get_object("ui_usbdevices_liststore")
        self.ui_fix_button = self.GtkBuilder.get_object("ui_fix_button")

        # make combobox text bold
        renderer = Gtk.CellRendererText()
        renderer.set_property("weight", Pango.Weight.BOLD)
        self.ui_usbdevices_combobox.pack_start(renderer, True)
        self.ui_usbdevices_combobox.add_attribute(renderer, "text", 1)

    def define_variables(self):
        self.unknown_fs = False

    def list_usb_devices(self):
        self.ui_usbdevices_liststore.clear()
        device_list = self.usbManager.getUSBDevices()
        self.ui_fix_button.set_sensitive(device_list)
        for device in device_list:
            self.ui_usbdevices_liststore.append(device)
            self.ui_usbdevices_combobox.set_active_id(device[0])

    def on_ui_fix_button_clicked(self, button):
        self.ui_fix_button.set_sensitive(False)
        active_tree_iter = self.ui_usbdevices_combobox.get_active_iter()
        if active_tree_iter:
            model = self.ui_usbdevices_combobox.get_model()
            device_info = model[active_tree_iter][:2]

            device_parts = self.usbManager.get_partitions_with_fstype(device_info[0])

            print(f"Active device: {device_info} {device_parts}")

            if device_parts:

                device_parts_json = json.dumps(device_parts)

                command = ["/usr/bin/pkexec", os.path.dirname(os.path.abspath(__file__)) + "/USBFix.py",
                           device_info[0], device_parts_json]

                self.pid = self.action_process(command)

            else:
                print(f"No partitions found for {device_info}")

    def on_ui_about_button_clicked(self, button):
        self.ui_about_dialog.run()
        self.ui_about_dialog.hide()

    def action_process(self, params):
        pid, stdin, stdout, stderr = GLib.spawn_async(params, flags=GLib.SpawnFlags.DO_NOT_REAP_CHILD,
                                                      standard_output=True, standard_error=True)
        GLib.io_add_watch(GLib.IOChannel(stdout), GLib.IO_IN | GLib.IO_HUP, self.on_action_process_stdout)
        GLib.io_add_watch(GLib.IOChannel(stderr), GLib.IO_IN | GLib.IO_HUP, self.on_action_process_stderr)
        GLib.child_watch_add(GLib.PRIORITY_DEFAULT, pid, self.on_action_process_exit)

        return pid

    def on_action_process_stdout(self, source, condition):
        if condition == GLib.IO_HUP:
            return False

        line = source.readline()
        print(line)

        return True

    def on_action_process_stderr(self, source, condition):
        if condition == GLib.IO_HUP:
            return False

        line = source.readline()
        print(line)

        if "eta-usb-fix" in line and "404" in line:
            Notification(summary=_("ETA USB Fix"), body=f"{line}").show()
            self.unknown_fs = True
        return True

    def on_action_process_exit(self, pid, status):
        print(f"{pid} exit code:{status}")
        self.ui_fix_button.set_sensitive(True)
        if status == 0 and not self.unknown_fs:
            Notification(summary=_("ETA USB Fix"), body=_("Operation completed successfully")).show()
        elif status == 32256:  # operation cancelled | Request dismissed
            pass
        else:
            if status != 0:
                Notification(summary=_("ETA USB Fix"), body=_("Error! exit-code: {code}").format(code=status)).show()
            self.unknown_fs = False
