#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul 25 14:53:13 2024

@author: fatihaltun
"""

import os
import signal
import base64
import distro
import webbrowser
import re
import gi
from PIL import Image

gi.require_version("GdkPixbuf", "2.0")
gi.require_version("GLib", "2.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject, GdkPixbuf, Gdk, Pango, GLib

try:
    gi.require_version('AppIndicator3', '0.1')
    from gi.repository import AppIndicator3 as appindicator
except:
    # fall back to Ayatana
    gi.require_version('AyatanaAppIndicator3', '0.1')
    from gi.repository import AyatanaAppIndicator3 as appindicator

from UserSettings import UserSettings
from Server import Server
import utils

import locale
from locale import gettext as _

locale.bindtextdomain('eta-help', '/usr/share/locale')
locale.textdomain('eta-help')


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
        self.main_window.set_application(application)

        # self.user_settings()
        # self.set_autostart()
        # self.init_indicator()
        self.init_ui()

        self.about_dialog.set_program_name(_("ETA Help"))
        if self.about_dialog.get_titlebar() is None:
            about_headerbar = Gtk.HeaderBar.new()
            about_headerbar.set_show_close_button(True)
            about_headerbar.set_title(_("About ETA Help"))
            about_headerbar.pack_start(Gtk.Image.new_from_icon_name("eta-help", Gtk.IconSize.LARGE_TOOLBAR))
            about_headerbar.show_all()
            self.about_dialog.set_titlebar(about_headerbar)

        # Set version
        # If not getted from __version__ file then accept version in MainWindow.glade file
        try:
            version = open(os.path.dirname(os.path.abspath(__file__)) + "/__version__").readline()
            self.about_dialog.set_version(version)
        except:
            pass

        cssProvider = Gtk.CssProvider()
        cssProvider.load_from_path(os.path.dirname(os.path.abspath(__file__)) + "/../data/style.css")
        screen = Gdk.Screen.get_default()
        styleContext = Gtk.StyleContext()
        styleContext.add_provider_for_screen(screen, cssProvider,
                                             Gtk.STYLE_PROVIDER_PRIORITY_USER)

        def sighandler(signum, frame):
            if self.about_dialog.is_visible():
                self.about_dialog.hide()
            self.main_window.get_application().quit()

        signal.signal(signal.SIGINT, sighandler)
        signal.signal(signal.SIGTERM, sighandler)

        if "tray" in self.Application.args.keys():
            self.main_window.set_visible(False)
        else:
            self.main_window.set_visible(True)
            self.main_window.show_all()

        # self.set_indicator()

        self.last_init_ui()

        self.Server = Server()
        self.Server.on_server_response = self.on_server_response

    def define_components(self):
        self.main_window = self.GtkBuilder.get_object("ui_main_window")
        self.about_dialog = self.GtkBuilder.get_object("ui_about_dialog")

        self.ui_menuback_button = self.GtkBuilder.get_object("ui_menuback_button")

        self.ui_banner_image = self.GtkBuilder.get_object("ui_banner_image")
        self.ui_faq_image = self.GtkBuilder.get_object("ui_faq_image")
        self.ui_docs_image = self.GtkBuilder.get_object("ui_docs_image")
        self.ui_learn_image = self.GtkBuilder.get_object("ui_learn_image")

        self.ui_main_stack = self.GtkBuilder.get_object("ui_main_stack")

        self.ui_report_content_scrolledwindow = self.GtkBuilder.get_object("ui_report_content_scrolledwindow")

        self.ui_pictures_box = self.GtkBuilder.get_object("ui_pictures_box")
        self.ui_selectpicture_button = self.GtkBuilder.get_object("ui_selectpicture_button")
        self.ui_addpicinfo_label = self.GtkBuilder.get_object("ui_addpicinfo_label")

        self.ui_report_email_entry = self.GtkBuilder.get_object("ui_report_email_entry")
        self.ui_distro_entry = self.GtkBuilder.get_object("ui_distro_entry")
        self.ui_suggestion_radiobutton = self.GtkBuilder.get_object("ui_suggestion_radiobutton")
        self.ui_bugreport_radiobutton = self.GtkBuilder.get_object("ui_bugreport_radiobutton")
        self.ui_report_title_entry = self.GtkBuilder.get_object("ui_report_title_entry")
        self.ui_report_content_textview = self.GtkBuilder.get_object("ui_report_content_textview")
        self.ui_report_content_textbuffer = self.GtkBuilder.get_object("ui_report_content_textbuffer")
        self.ui_sendreportinfo_label = self.GtkBuilder.get_object("ui_sendreportinfo_label")
        self.ui_sendreport_button = self.GtkBuilder.get_object("ui_sendreport_button")

        self.ui_reportsplash_box = self.GtkBuilder.get_object("ui_reportsplash_box")
        self.ui_reportdone_box = self.GtkBuilder.get_object("ui_reportdone_box")
        self.ui_reportdone_button = self.GtkBuilder.get_object("ui_reportdone_button")
        self.ui_reportdone_label = self.GtkBuilder.get_object("ui_reportdone_label")

    def define_variables(self):
        self.server = "http://etahelp.etap.org.tr/etahelp23.php"
        self.pictures = []

        self.current_desktop = self.get_current_desktop()

        self.user_distro = ", ".join(filter(bool, (distro.name(), distro.version(), distro.codename())))
        desktop_env = utils.get_desktop_env()
        desktop_env_vers = utils.get_desktop_env_version(desktop_env)
        session = utils.get_session_type()
        self.user_desktop_env = "{} {}, {}".format(desktop_env, desktop_env_vers, session)
        self.user_distro_full = "{}, ({})".format(self.user_distro, self.user_desktop_env)

    def init_ui(self):
        self.ui_banner_image.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
            os.path.dirname(os.path.abspath(__file__)) + "/../data/etap-banner.png", 750, 100, False))
        self.ui_faq_image.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
            os.path.dirname(os.path.abspath(__file__)) + "/../data/faq.png", 233, 213, False))
        self.ui_docs_image.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
            os.path.dirname(os.path.abspath(__file__)) + "/../data/docs.png", 233, 213, False))
        self.ui_learn_image.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
            os.path.dirname(os.path.abspath(__file__)) + "/../data/learn.png", 233, 213, False))

        self.ui_menuback_button.set_sensitive(False)

        if "cinnamon" in self.current_desktop:
            self.ui_report_content_scrolledwindow.set_min_content_width(483)

    def last_init_ui(self):
        self.ui_sendreportinfo_label.set_visible(False)

    def get_current_desktop(self):
        if "XDG_CURRENT_DESKTOP" in os.environ:
            return os.environ["XDG_CURRENT_DESKTOP"].lower()
        elif "DESKTOP_SESSION" in os.environ:
            return os.environ["DESKTOP_SESSION"].lower()
        elif "SESSION" in os.environ:
            return os.environ["SESSION"].lower()
        else:
            return ""

    def user_settings(self):
        self.UserSettings = UserSettings()
        self.UserSettings.createDefaultConfig()
        self.UserSettings.readConfig()

    def init_indicator(self):
        self.indicator = appindicator.Indicator.new(
            "eta-help", "eta-help-status", appindicator.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
        self.indicator.set_title(_("ETA Help"))
        self.menu = Gtk.Menu()
        self.item_sh_app = Gtk.MenuItem()
        self.item_sh_app.connect("activate", self.on_menu_show_app)
        self.item_separator = Gtk.SeparatorMenuItem()
        self.item_quit = Gtk.MenuItem()
        self.item_quit.set_label(_("Quit"))
        self.item_quit.connect('activate', self.on_menu_quit_app)
        self.menu.append(self.item_sh_app)
        self.menu.append(self.item_separator)
        self.menu.append(self.item_quit)
        self.menu.show_all()
        self.indicator.set_menu(self.menu)

    def set_indicator(self):

        if self.main_window.is_visible():
            self.item_sh_app.set_label(_("Hide App"))
        else:
            self.item_sh_app.set_label(_("Show App"))

    def set_autostart(self):
        self.UserSettings.set_autostart(self.UserSettings.config_autostart)

    def get_mac(self):
        if_path = "/sys/class/net"
        mac_address = ""
        try:
            for root, dirs, files in os.walk(if_path):
                for interface in dirs:
                    mac_dir = os.path.join(root, interface, "address")
                    mac_dir_exist = os.path.exists(mac_dir)
                    wireless_dir = not os.path.exists(os.path.join(root, interface, "wireless"))
                    if mac_dir_exist and interface != "lo" and wireless_dir:
                        with open(mac_dir, "r") as f:
                            mac = f.readline().strip().upper()
                            if mac and len(mac) > 0:
                                mac_address = mac
        except Exception as e:
            print("Exception on get_mac: {}".format(e))
        return mac_address

    def add_pictures_to_ui(self, pictures):

        for picture in pictures:

            if len(self.pictures) >= 3:
                break
            try:
                img = Image.open(picture)
            except IsADirectoryError:
                print("{} is a directory, so skipping for now.".format(picture))
                utils.ErrorDialog(_("Error"), "{} is a directory, so skipping for now.".format(picture))
                continue
            except Exception as e:
                print("{}".format(e))
                utils.ErrorDialog(_("Error"), "{}".format(e))
                continue

            if (img.format == "JPEG" or img.format == "PNG") and picture not in self.pictures:

                size = os.path.getsize(picture)
                if size > 10000000:
                    print("{} size is {} ({})".format(picture, GLib.format_size(size), size))
                    utils.ErrorDialog(_("Error"), "{}".format(
                        "{} size is {} ({})".format(picture, GLib.format_size(size), size)))
                    continue

                vert_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 5)
                picture_image = Gtk.Image.new_from_pixbuf(
                    GdkPixbuf.Pixbuf.new_from_file_at_scale(picture, 144, 89, False))

                picture_delete_button = Gtk.Button.new_from_icon_name("edit-delete-symbolic", Gtk.IconSize.BUTTON)
                picture_delete_button.name = picture
                picture_delete_button.connect('clicked', self.on_picture_delete_button_clicked)
                picture_delete_button.set_relief(Gtk.ReliefStyle.NONE)
                picture_delete_button.props.valign = Gtk.Align.CENTER
                picture_delete_button.props.halign = Gtk.Align.CENTER

                button_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 3)
                button_box.props.valign = Gtk.Align.CENTER
                button_box.props.halign = Gtk.Align.CENTER
                button_box.pack_start(picture_delete_button, False, True, 0)

                label = Gtk.Label.new()
                label.set_markup("<small>{}</small>".format(GLib.markup_escape_text(os.path.basename(picture), -1)))
                label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
                label.set_max_width_chars(17)

                vert_box.pack_start(label, False, True, 0)
                vert_box.pack_start(picture_image, False, True, 0)
                vert_box.pack_start(button_box, False, False, 0)
                vert_box.name = picture

                self.ui_pictures_box.add(vert_box)
                self.pictures.append(picture)

        self.ui_pictures_box.show_all()

        self.ui_selectpicture_button.set_visible(not len(self.pictures) == 3)
        self.ui_addpicinfo_label.set_visible(len(self.pictures) == 0)

    def on_picture_delete_button_clicked(self, button):
        for row in self.ui_pictures_box:
            if row.name == button.name:
                self.ui_pictures_box.remove(row)
                # removing from pictures list too
                index = next((index for (index, picture) in enumerate(self.pictures) if picture == button.name), None)
                self.pictures.pop(index)

        self.ui_selectpicture_button.set_visible(not len(self.pictures) == 3)
        self.ui_addpicinfo_label.set_visible(len(self.pictures) == 0)

    def on_ui_bugreport_button_clicked(self, button):
        if button.get_name() == "bug":
            self.ui_main_stack.set_visible_child_name("report")
            self.ui_bugreport_radiobutton.set_active(True)

        elif button.get_name() == "suggest":
            self.ui_main_stack.set_visible_child_name("report")
            self.ui_suggestion_radiobutton.set_active(True)

        self.ui_menuback_button.set_sensitive(True)
        self.ui_distro_entry.set_text("{}".format(self.user_distro_full))

    def on_ui_selectpicture_button_clicked(self, button):
        file_chooser = Gtk.FileChooserDialog(title=_("Select Image(s)"), parent=self.main_window,
                                             action=Gtk.FileChooserAction.OPEN)
        file_chooser.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        file_chooser.add_button(_("Open"), Gtk.ResponseType.ACCEPT).get_style_context().add_class("suggested-action")
        file_chooser.set_select_multiple(True)

        filter_all = Gtk.FileFilter()
        filter_all.set_name(_("All supported files"))
        filter_all.add_mime_type("image/png")
        filter_all.add_mime_type("image/jpg")
        filter_all.add_mime_type("image/jpeg")

        filter_png = Gtk.FileFilter()
        filter_png.set_name(_("PNG files"))
        filter_png.add_mime_type("image/png")

        filter_jpg = Gtk.FileFilter()
        filter_jpg.set_name(_("JPG/JPEG files"))
        filter_jpg.add_mime_type("image/jpg")
        filter_jpg.add_mime_type("image/jpeg")

        file_chooser.add_filter(filter_all)
        file_chooser.add_filter(filter_png)
        file_chooser.add_filter(filter_jpg)
        file_chooser.set_filter(filter_all)

        response = file_chooser.run()
        if response == Gtk.ResponseType.ACCEPT:
            self.add_pictures_to_ui(file_chooser.get_filenames())
        file_chooser.destroy()

    def on_ui_sendreport_button_clicked(self, button):
        def get_base64(file_abspath):
            img_string = ""
            try:
                with open(file_abspath, "rb") as img_file:
                    img_bytes = base64.b64encode(img_file.read())
                    img_string = img_bytes.decode("utf-8")
            except Exception as e:
                print("Exception on get_base64: {}".format(e))
            return img_string

        def control_text(text):
            if text.strip() == "":
                self.ui_sendreportinfo_label.set_visible(True)
                return False
            self.ui_sendreportinfo_label.set_visible(False)
            return True

        def is_valid_email(email):
            email_regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
            if re.match(email_regex, email) is None:
                self.ui_sendreportinfo_label.set_visible(True)
                return False
            self.ui_sendreportinfo_label.set_visible(False)
            return True


        report_type = ""
        if self.ui_bugreport_radiobutton.get_active():
            report_type = _("ETAP Bug Report")
        elif self.ui_suggestion_radiobutton.get_active():
            report_type = _("ETAP Suggestion")

        report_email = self.ui_report_email_entry.get_text()
        report_title = self.ui_report_title_entry.get_text()
        report_content = self.ui_report_content_textbuffer.get_text(self.ui_report_content_textbuffer.get_start_iter(),
                                                                    self.ui_report_content_textbuffer.get_end_iter(),
                                                                    True)

        if not control_text(report_title):
            self.ui_sendreportinfo_label.set_markup("<span color='red'>{}</span>".format(_("Title is empty")))
            return

        if not control_text(report_content):
            self.ui_sendreportinfo_label.set_markup("<span color='red'>{}</span>".format(_("Content is empty")))
            return

        if not control_text(report_email):
            self.ui_sendreportinfo_label.set_markup("<span color='red'>{}</span>".format(_("E-Mail is empty")))
            return

        if not is_valid_email(report_email):
            self.ui_sendreportinfo_label.set_markup("<span color='red'>{}</span>".format(_("Invalid E-Mail")))
            return

        if len(report_content) > 5000:
            report_content = report_content[:5000]

        json_data = {"mac": self.get_mac(), "subject": report_type, "title": report_title, "details": report_content,
                     "from": report_email, "distro": self.user_distro_full,
                     "image1": "", "image2": "", "image3": ""}

        i = 1
        for picture in self.pictures:
            if os.path.isfile(picture):
                json_data["image{}".format(i)] = get_base64(picture)
                json_data["image{}_name".format(i)] = os.path.basename(picture)
            i += 1

        GLib.idle_add(self.ui_menuback_button.set_sensitive, False)
        GLib.idle_add(self.ui_sendreport_button.set_sensitive, False)
        GLib.idle_add(self.ui_reportsplash_box.set_visible, True)
        GLib.idle_add(self.ui_reportdone_box.set_visible, False)
        GLib.idle_add(self.ui_main_stack.set_visible_child_name, "splash")

        self.Server.post(self.server, json_data)

    def on_server_response(self, status, response, error_message=""):
        print("on_server_response")
        print(status)
        print(response)
        print(error_message)

        GLib.idle_add(self.ui_sendreport_button.set_sensitive, True)
        GLib.idle_add(self.ui_reportsplash_box.set_visible, False)
        GLib.idle_add(self.ui_reportdone_box.set_visible, True)
        if status and response and response["status"]:
            self.ui_reportdone_label.set_text(_("Your request has been forwarded to the relevant unit. "
                                                "You can follow the result of your request via e-mail."))
            self.ui_reportdone_button.set_label(_("Home Page"))
            self.ui_reportdone_button.get_style_context().add_class("suggested-action")
            self.ui_reportdone_button.name = "success"
        else:
            self.ui_reportdone_label.set_text("{}\n\n{}".format(_("Your request could not be sent."), error_message))
            self.ui_reportdone_button.set_label(_("Try Again"))
            if self.ui_reportdone_button.get_style_context().has_class("suggested-action"):
                self.ui_reportdone_button.get_style_context().remove_class("suggested-action")
            self.ui_reportdone_button.name = "error"

    def on_ui_reportdone_button_clicked(self, button):
        if button.name == "success":
            self.ui_main_stack.set_visible_child_name("home")
            self.clear_report_data()
        elif button.name == "error":
            self.ui_main_stack.set_visible_child_name("report")

    def clear_report_data(self):
        self.ui_report_title_entry.set_text("")
        self.ui_report_email_entry.set_text("")
        start, end = self.ui_report_content_textbuffer.get_bounds()
        self.ui_report_content_textbuffer.delete(start, end)
        for row in self.ui_pictures_box:
            self.ui_pictures_box.remove(row)
        self.pictures.clear()

    def on_ui_report_email_entry_icon_press(self, entry, icon_pos, event):
        entry.set_text("")

    def on_ui_menuback_button_clicked(self, button):
        self.ui_main_stack.set_visible_child_name("home")
        self.ui_menuback_button.set_sensitive(False)
        self.ui_sendreportinfo_label.set_visible(False)

    def on_ui_reportcancel_button_clicked(self, button):
        self.ui_main_stack.set_visible_child_name("home")
        self.ui_menuback_button.set_sensitive(False)
        self.ui_sendreportinfo_label.set_visible(False)

    def on_ui_forum_button_clicked(self, button):
        webbrowser.open("https://forum.pardus.org.tr")

    def on_ui_community_button_clicked(self, button):
        webbrowser.open("https://gonullu.pardus.org.tr")

    def on_ui_contribute_button_clicked(self, button):
        webbrowser.open("https://gonullu.pardus.org.tr/katki-sagla")

    def on_ui_faq_button_clicked(self, button):
        webbrowser.open("https://rehber.etap.org.tr")

    def on_ui_docs_button_clicked(self, button):
        webbrowser.open("https://belge.pardus.org.tr")

    def on_ui_learn_button_clicked(self, button):
        webbrowser.open("https://uzem.pardus.org.tr")

    def on_menu_show_app(self, *args):
        window_state = self.main_window.is_visible()
        if window_state:
            self.main_window.set_visible(False)
            self.item_sh_app.set_label(_("Show App"))
        else:
            self.main_window.set_visible(True)
            self.item_sh_app.set_label(_("Hide App"))
            self.main_window.present()

    def on_menu_quit_app(self, *args):
        if self.about_dialog.is_visible():
            self.about_dialog.hide()
        self.main_window.get_application().quit()

    def on_ui_about_button_clicked(self, button):
        self.about_dialog.run()
        self.about_dialog.hide()

    # def on_ui_main_window_delete_event(self, widget, event):
    #     self.main_window.hide()
    #     self.item_sh_app.set_label(_("Show App"))
    #     return True
    #
    # def on_ui_main_window_destroy(self, widget, event):
    #     if self.about_dialog.is_visible():
    #         self.about_dialog.hide()
    #     self.main_window.get_application().quit()
