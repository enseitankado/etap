#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gi

gi.require_version("GLib", "2.0")
gi.require_version("Gtk", "3.0")
gi.require_version("Notify", "0.7")
from gi.repository import Gtk, GObject, GLib, Notify


class Notification(GObject.GObject):
    __gsignals__ = {
        'notify-action': (GObject.SIGNAL_RUN_FIRST, None,
                          (str,))
    }

    def __init__(self, summary="", body="", icon="eta-usb-fix", appid="tr.org.pardus.eta-usb-fix"):
        GObject.GObject.__init__(self)
        self.appid = appid
        if Notify.is_initted():
            Notify.uninit()
        Notify.init(appid)
        self.notification = Notify.Notification.new(summary, body, icon)
        self.notification.connect('closed', self.on_closed)

    def show(self):
        self.notification.show()

    def close_callback(self, widget, action):
        self.emit('notify-action', 'closed')

    def on_closed(self, widget):
        self.emit('notify-action', 'closed')
