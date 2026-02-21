#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import locale
import os
from locale import gettext as _

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gio, Gdk, Gtk  # noqa

APPNAME = "eta-screen-cover"
TRANSLATIONS_PATH = "/usr/share/locale"

locale.bindtextdomain(APPNAME, TRANSLATIONS_PATH)
locale.textdomain(APPNAME)

CWD = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "{}/../data".format(CWD)


class MainWindow:
    def __init__(self, application):
        self.setup_window(application)

        self.setup_css()

        self.setup_ui()

    def setup_window(self, application):
        self.window = Gtk.ApplicationWindow.new(application)
        self.window.set_default_size(400, 400)
        self.window.set_resizable(True)
        self.window.set_keep_above(True)

        self.headerbar = Gtk.HeaderBar(
            custom_title=Gtk.Label(label=_("Eta Screen Cover"))
        )
        self.window.set_titlebar(self.headerbar)
        self.window.get_style_context().add_class("dark-background")

    def setup_ui(self):
        grid = Gtk.Grid(
            orientation="vertical",
            halign="start",
            valign="end",
            vexpand=False,
            hexpand=False,
            margin=11,
            row_spacing=11,
            column_spacing=11,
        )

        btn_close = Gtk.Button()
        btn_img_close = Gtk.Image.new_from_icon_name(
            "window-close-symbolic", Gtk.IconSize.LARGE_TOOLBAR
        )
        btn_close.add(btn_img_close)
        btn_close.get_style_context().add_class("destructive-action")
        btn_close.connect("clicked", self.btn_close_clicked)

        # Change Position Buttons
        btn_snap_left = Gtk.Button()
        btn_snap_left.add(
            Gtk.Image.new_from_icon_name(
                "go-first-symbolic", Gtk.IconSize.LARGE_TOOLBAR
            )
        )
        btn_snap_left.connect("clicked", self.btn_snap_clicked, "left")

        btn_snap_right = Gtk.Button()
        btn_snap_right.add(
            Gtk.Image.new_from_icon_name("go-last-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        )
        btn_snap_right.connect("clicked", self.btn_snap_clicked, "right")

        btn_snap_up = Gtk.Button()
        btn_snap_up.add(
            Gtk.Image.new_from_icon_name("go-top-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        )
        btn_snap_up.connect("clicked", self.btn_snap_clicked, "up")

        btn_snap_down = Gtk.Button()
        btn_snap_down.add(
            Gtk.Image.new_from_icon_name(
                "go-bottom-symbolic", Gtk.IconSize.LARGE_TOOLBAR
            )
        )
        btn_snap_down.connect("clicked", self.btn_snap_clicked, "down")

        # Full Screen Button
        btn_maximize = Gtk.Button()
        btn_maximize.add(
            Gtk.Image.new_from_icon_name(
                "view-fullscreen-symbolic", Gtk.IconSize.LARGE_TOOLBAR
            )
        )
        btn_maximize.connect("clicked", self.btn_maximize_clicked)

        # Dark Light Theme selector
        btn_dark_light_change = Gtk.Button()
        btn_dark_light_change.add(
            Gtk.Image.new_from_icon_name(
                "night-light-symbolic", Gtk.IconSize.LARGE_TOOLBAR
            )
        )
        btn_dark_light_change.connect("clicked", self.btn_dark_light_change_clicked)

        # 4x4 Grid
        # _       _ UP _
        # _    LEFT MAXIMIZE RIGHT
        # _     _ DOWN _
        # CLOSE _ _ LIGHTS ON/OFF
        grid.attach(btn_snap_left, 1, 1, 1, 1)
        grid.attach(btn_snap_right, 3, 1, 1, 1)
        grid.attach(btn_snap_up, 2, 0, 1, 1)
        grid.attach(btn_snap_down, 2, 2, 1, 1)

        grid.attach(btn_maximize, 2, 1, 1, 1)

        grid.attach(btn_close, 0, 3, 1, 1)
        grid.attach(btn_dark_light_change, 3, 3, 1, 1)

        self.window.add(grid)

    def setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path("{}/style.css".format(DATA_DIR))

        style = self.window.get_style_context()
        style.add_provider_for_screen(
            Gdk.Screen.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

        self.settings = Gtk.Settings.get_default()
        self.settings.set_property("gtk-application-prefer-dark-theme", True)

    def show_ui(self):
        self.window.show_all()

        self.calculate_maximized_geometry()

    # FUNCTIONS
    def calculate_maximized_geometry(self):
        screen = Gdk.Screen.get_default()
        monitor = screen.get_primary_monitor()
        geometry = screen.get_monitor_workarea(monitor)

        self.maximized_geometry = geometry

    # CALLBACKS
    def btn_close_clicked(self, btn):
        self.window.get_application().quit()

    def btn_snap_clicked(self, btn, direction):
        if self.window.is_maximized():
            self.window.unmaximize()

        geometry = self.maximized_geometry

        # Window Decoration Borders margin
        desktop_environment = os.environ.get("DESKTOP_SESSION")
        if desktop_environment == "gnome":
            margin = 0
        else:
            margin = 30

        self.window.resize(300, 300)

        def move_window(w, geometry):
            new_pos = (0, 0)

            if direction == "up":
                new_pos = (geometry.x, geometry.y)
            elif direction == "down":
                new_pos = (geometry.x, geometry.y + geometry.height / 2)
            elif direction == "left":
                new_pos = (geometry.x, geometry.y)
            elif direction == "right":
                new_pos = (geometry.x + geometry.width / 2, geometry.y)

            new_pos = (new_pos[0] + margin, new_pos[1] + margin)

            w.move(new_pos[0], new_pos[1])

        def resize_window(w, geometry):
            new_size = (0, 0)

            if direction == "up":
                new_size = (geometry.width, geometry.height / 2)
            elif direction == "down":
                new_size = (geometry.width, geometry.height / 2)
            elif direction == "left":
                new_size = (geometry.width / 2, geometry.height)
            elif direction == "right":
                new_size = (geometry.width / 2, geometry.height)

            new_size = (new_size[0] - margin, new_size[1] - margin)

            w.resize(new_size[0], new_size[1])

        GLib.timeout_add(40, move_window, self.window, geometry)
        GLib.timeout_add(80, resize_window, self.window, geometry)

    def btn_maximize_clicked(self, btn):
        if self.window.is_maximized():
            self.window.unmaximize()
            self.window.resize(400, 400)
        else:
            self.window.maximize()

    def btn_dark_light_change_clicked(self, btn):
        style = self.window.get_style_context()

        if style.has_class("dark-background"):
            style.remove_class("dark-background")
            style.add_class("white-background")
        else:
            style.add_class("dark-background")
            style.remove_class("white-background")
