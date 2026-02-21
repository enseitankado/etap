import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gio, Gtk

import configparser
import subprocess


import locale
from locale import gettext as _

# Translation Constants:
APPNAME = "eta-shutdown"
TRANSLATIONS_PATH = "/usr/share/locale"

# Translation functions:
locale.bindtextdomain(APPNAME, TRANSLATIONS_PATH)
locale.textdomain(APPNAME)

CONFIG_FILE = "/etc/pardus/eta-shutdown.conf"

class MainWindow:
    def __init__(self, application):
        # Gtk Builder
        self.builder = Gtk.Builder()

        # Translate things on glade:
        self.builder.set_translation_domain(APPNAME)

        # Import UI file:
        self.builder.add_from_file(os.path.dirname(os.path.abspath(__file__)) + "/../ui/MainWindow.glade")
        self.builder.connect_signals(self)

        # Window
        self.window = self.builder.get_object("ui_main_window")
        self.window.set_application(application)

        # Set application:
        self.application = application

        # Global Definings
        self.define_components()
        self.define_variables()

        # Show Screen:
        self.window.show_all()

    def define_components(self):
        def UI(str):
            return self.builder.get_object(str)
        
        # switches
        self.ui_auto_shutdown_switch = UI("ui_auto_shutdown_switch")
        self.ui_timed_switch = UI("ui_timed_switch")

        # radio buttons
        self.ui_timed_suspend_rbutton = UI("ui_timed_suspend_rbutton")
        self.ui_timed_shutdown_rbutton = UI("ui_timed_shutdown_rbutton")
        
        # time boxes
        self.ui_countdown_mode_box = UI("ui_countdown_mode_box")
        self.ui_shutdown_mode_box = UI("ui_shutdown_mode_box")
        self.ui_auto_shutdown_time_box = UI("ui_auto_shutdown_time_box")
        self.ui_timed_time_box = UI("ui_timed_shutdown_time_box")
        self.ui_auto_shutdown_hour_box = UI("ui_auto_shutdown_hour_box")
        self.ui_auto_shutdown_minute_box = UI("ui_auto_shutdown_minute_box")
        self.ui_timed_hour_box = UI("ui_timed_hour_box")
        self.ui_timed_minute_box = UI("ui_timed_minute_box")

        # plus/minues buttons
        self.ui_auto_shutdown_hour_plus_button = UI("ui_auto_shutdown_hour_plus_button")
        self.ui_auto_shutdown_hour_minus_button = UI("ui_auto_shutdown_hour_minus_button")
        self.ui_auto_shutdown_minute_plus_button = UI("ui_auto_shutdown_minute_plus_button")
        self.ui_auto_shutdown_minute_minus_button = UI("ui_auto_shutdown_minute_minus_button")
        self.ui_timed_hour_plus_button = UI("ui_timed_hour_plus_button")
        self.ui_timed_hour_minus_button = UI("ui_timed_hour_minus_button")
        self.ui_timed_minute_plus_button = UI("ui_timed_minute_plus_button")
        self.ui_timed_minute_minus_button = UI("ui_timed_minute_minus_button")

        # labels
        self.ui_auto_shutdown_hour_label = UI("ui_auto_shutdown_hour_label")
        self.ui_auto_shutdown_minute_label = UI("ui_auto_shutdown_minute_label")
        self.ui_timed_hour_label = UI("ui_timed_hour_label")
        self.ui_timed_minute_label = UI("ui_timed_minute_label")
        self.ui_status_label = UI("ui_status_label")
        self.ui_warning_label = UI("ui_warning_label")

        # buttons
        self.ui_save_button = UI("ui_save_button")

    def define_variables(self):
        # plus/minues buttons
        self.ui_auto_shutdown_hour_plus_button.connect("clicked", lambda w: self.on_ui_increase_hour_button(self.ui_auto_shutdown_hour_label))
        self.ui_auto_shutdown_hour_minus_button.connect("clicked", lambda w: self.on_ui_decrease_hour_button(self.ui_auto_shutdown_hour_label))
        self.ui_auto_shutdown_minute_plus_button.connect("clicked", lambda w: self.on_ui_increase_minute_button(self.ui_auto_shutdown_minute_label))
        self.ui_auto_shutdown_minute_minus_button.connect("clicked", lambda w: self.on_ui_decrease_minute_button(self.ui_auto_shutdown_minute_label))
        self.ui_timed_hour_plus_button.connect("clicked", lambda w: self.on_ui_increase_hour_button(self.ui_timed_hour_label))
        self.ui_timed_hour_minus_button.connect("clicked", lambda w: self.on_ui_decrease_hour_button(self.ui_timed_hour_label))
        self.ui_timed_minute_plus_button.connect("clicked", lambda w: self.on_ui_increase_minute_button(self.ui_timed_minute_label, True))
        self.ui_timed_minute_minus_button.connect("clicked", lambda w: self.on_ui_decrease_minute_button(self.ui_timed_minute_label, True))

        self.ui_warning_label.set_text("")

        # text
        self.warning_message = _("This mode may not work on some boards.")
        self.auto_mode_message = _("Auto shutdown mode active")
        self.timed_suspend_mode_message = _("Timed suspend mode active")
        self.timed_shutdown_mode_message = _("Timed shutdown mode active")
        self.no_setting_message = _("No settings")

        self.on_ui_show_warning_message()
        self.on_ui_show_settings()

    def on_ui_increase_hour_button(self, label):
        hour = label.get_text()
        hour = int(hour)
        hour = (hour + 1) % 24
        label.set_text(str(hour).zfill(2))

    def on_ui_decrease_hour_button(self, label):
        hour = label.get_text()
        hour = int(hour)
        hour = (hour - 1) % 24
        label.set_text(str(hour).zfill(2))

    def on_ui_increase_minute_button(self, label, limit=False):
        minute = label.get_text()
        minute = int(minute)
        minute = (minute + 1) % 60
        if limit and minute < 5:
            minute = 5
        label.set_text(str(minute).zfill(2))

    def on_ui_decrease_minute_button(self, label, limit=False):
        minute = label.get_text()
        minute = int(minute)
        minute = (minute - 1) % 60
        if limit and minute < 5:
            minute = 59
        label.set_text(str(minute).zfill(2))

    def on_ui_save_button_clicked(self, button):
        #self.ui_status_label.set_text("Hello Pardus!")
        self.on_ui_set_status()
        self.save_eta_shutdown_config()

    def on_ui_auto_shutdown_switch_toggled(self, switch, _):
        is_active = switch.get_active()
        self.ui_auto_shutdown_hour_plus_button.set_sensitive(is_active)
        self.ui_auto_shutdown_hour_minus_button.set_sensitive(is_active)
        self.ui_auto_shutdown_minute_plus_button.set_sensitive(is_active)
        self.ui_auto_shutdown_minute_minus_button.set_sensitive(is_active)

    def on_ui_timed_switch_toggled(self, switch, _):
        is_active = switch.get_active()
        self.ui_timed_hour_plus_button.set_sensitive(is_active)
        self.ui_timed_hour_minus_button.set_sensitive(is_active)
        self.ui_timed_minute_plus_button.set_sensitive(is_active)
        self.ui_timed_minute_minus_button.set_sensitive(is_active)
        self.ui_timed_suspend_rbutton.set_sensitive(is_active)
        self.ui_timed_shutdown_rbutton.set_sensitive(is_active)
        if self.ui_timed_switch.get_active() and self.ui_timed_suspend_rbutton.get_active():
            self.ui_warning_label.set_text(self.warning_message)
        else:
            self.ui_warning_label.set_text("")

    def on_ui_show_warning_message(self):
        if self.ui_timed_switch.get_active():
            if self.ui_timed_suspend_rbutton.get_active():
                self.ui_warning_label.set_text(self.warning_message)
            else:
                self.ui_warning_label.set_text("")
        self.ui_warning_label.set_text("")

    def on_ui_set_status(self):
        if self.ui_auto_shutdown_switch.get_active():
            self.ui_status_label.set_text(self.auto_mode_message)
        elif self.ui_timed_switch.get_active():
            if self.ui_timed_suspend_rbutton.get_active():
                self.ui_status_label.set_text(self.timed_suspend_mode_message)
                self.ui_warning_label.set_text(self.warning_message)
            else:
                self.ui_status_label.set_text(self.timed_shutdown_mode_message)
                self.ui_warning_label.set_text("")
        else:
            self.ui_status_label.set_text(self.no_setting_message)

    def load_or_create_eta_shutdown_config(self):
        config = configparser.ConfigParser()

        if not os.path.exists(CONFIG_FILE):
            config["AUTO_SHUTDOWN"] = {
                "enabled": "False",
                "hour": "0",
                "minute": "0"
            }

            config["TIMED_MODE"] = {
                "mode": "False",
                "hour": "0",
                "minute": "0"
            }

            with open(CONFIG_FILE, "w") as file:
                config.write(file)

        config.read(CONFIG_FILE)
        return config

    def save_eta_shutdown_config(self):
        config = configparser.ConfigParser()

        config["AUTO_SHUTDOWN"] = {
            "enabled": str(self.ui_auto_shutdown_switch.get_active()),
            "hour": str(self.ui_auto_shutdown_hour_label.get_text()),
            "minute": str(self.ui_auto_shutdown_minute_label.get_text())
        }

        config["TIMED_MODE"] = {
            "mode": "none",
            "hour": str(self.ui_timed_hour_label.get_text()),
            "minute": str(self.ui_timed_minute_label.get_text())
        }
        if self.ui_timed_switch.get_active():
            if self.ui_timed_shutdown_rbutton.get_active():
                config["TIMED_MODE"]["mode"] = "shutdown"
            elif self.ui_timed_suspend_rbutton.get_active():
                config["TIMED_MODE"]["mode"] = "suspend"

        with open(CONFIG_FILE, "w") as file:
            config.write(file)

        subprocess.run(["systemctl", "restart", "eta-shutdown"])

    def on_ui_show_settings(self):
        config = self.load_or_create_eta_shutdown_config()

        self.ui_auto_shutdown_switch.set_active(config.getboolean("AUTO_SHUTDOWN", "enabled"))
        self.ui_auto_shutdown_hour_label.set_text(config.get("AUTO_SHUTDOWN", "hour").zfill(2))
        self.ui_auto_shutdown_minute_label.set_text(config.get("AUTO_SHUTDOWN", "minute").zfill(2))

        suspend_radio_button = (config.get("TIMED_MODE", "mode") == "suspend")
        self.ui_timed_suspend_rbutton.set_active(suspend_radio_button)

        self.ui_timed_shutdown_rbutton.set_active(not suspend_radio_button)
        self.ui_timed_hour_label.set_text(config.get("TIMED_MODE", "hour").zfill(2))
        self.ui_timed_minute_label.set_text(config.get("TIMED_MODE", "minute").zfill(2))

        timed_enabled = (config.get("TIMED_MODE", "mode") != "none")
        if timed_enabled:
            self.ui_timed_switch.set_active(True)

        if config.getboolean("AUTO_SHUTDOWN", "enabled"):
            self.ui_status_label.set_text(self.auto_mode_message)
        elif not timed_enabled:
            self.ui_status_label.set_text(self.no_setting_message)
        elif not suspend_radio_button:
            self.ui_status_label.set_text(self.timed_shutdown_mode_message)
        else:
            self.ui_status_label.set_text(self.timed_suspend_mode_message)

        self.ui_shutdown_mode_box.set_sensitive(config.getboolean("AUTO_SHUTDOWN", "enabled"))
        self.ui_countdown_mode_box.set_sensitive(timed_enabled)


    def on_radio_button_toggled(self, button):
        if button.get_active():
            self.ui_warning_label.set_text(self.warning_message)
        else:
            self.ui_warning_label.set_text("")

    def on_ui_auto_shutdown_switch_state_set(self, switch, state):
        self.ui_shutdown_mode_box.set_sensitive(state)

    def on_ui_timed_switch_state_set(self, switch, state):
        self.ui_countdown_mode_box.set_sensitive(state)
