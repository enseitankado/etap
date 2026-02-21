import gi, time, os

gi.require_version("Gtk","3.0")
from gi.repository import Gtk, GLib

import audio

from util import *

try:
    import locale
    from locale import gettext as _

    # Translation Constants:
    APPNAME = "eta-count"
    TRANSLATIONS_PATH = "/usr/share/locale"
    locale.bindtextdomain(APPNAME, TRANSLATIONS_PATH)
    locale.textdomain(APPNAME)
except:
    # locale load issue fix
    def _(msg):
        return msg


status = "PAUSE"
alarm = False
alarm_path = ""


class counter(Gtk.Box):
    def __init__(self, main):
        super().__init__()
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.main = main

        self.increase = Gtk.Button(label="+")
        self.decrease = Gtk.Button(label="-")
        self.label = Gtk.Label(label="0")
        self.__cur = 0
        self.set(0)

        def inc_fn(widget=None):
            if self.get() < 9:
                self.set(self.get()+1)
            else:
                self.set(0)

        def dec_fn(widget=None):
            if self.get() > 0:
                self.set(self.get()-1)
            else:
              self.set(9)

        self.increase.connect("clicked", inc_fn)
        self.decrease.connect("clicked", dec_fn)
        self.pack_start(self.increase, True, True, 5)
        self.pack_start(self.label, True, True, 5)
        self.pack_start(self.decrease, True, True, 5)

    def hide_but(self):
        self.increase.hide()
        self.decrease.hide()

    def show_but(self):
        self.increase.show()
        self.decrease.show()

    def set(self, cur):
        self.__cur = int(cur)
        self.label.set_markup("<span font='128'>{}</span>".format(self.__cur))
        self.main.update_ui()

    def get(self):
        return self.__cur

class MainWindow(Gtk.Window):

    def __init__(self):
        global status
        global alarm_path
        super().__init__()
        self.settings = Gtk.Settings.get_default()
        self.init = False
        self.set_icon_name("eta-count")
        self.set_title(_("Eta Count"))

        self.start_time = int(time.time())
        self.labels = [Gtk.Label(), Gtk.Label()]
        self.start = Gtk.Button(label=_("Start"))
        self.stop = Gtk.Button(label=_("Reset"))


        self.dark_theme = True
        self.settings.set_property("gtk-application-prefer-dark-theme", True)

        self.labels[0].set_markup("<span font='64'>:</span>")
        self.labels[1].set_markup("<span font='64'>:</span>")

        # main skack
        stack = Gtk.Stack()
        stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        # main box
        main_widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_top = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        main_widget.pack_start(main_top, True, True, 0)
        main_widget.pack_start(main_bottom, False, False, 0)
        main_widget.set_margin_start(13)
        main_widget.set_margin_end(13)
        main_widget.set_margin_top(13)
        main_widget.set_margin_bottom(13)
        main_top.set_center_widget(stack)
        stack.add_named(main, "main")
        self.add(main_widget)


        # time remaining label
        self.titles = [Gtk.Label(), Gtk.Label()]
        main.pack_start(self.titles[0], False, True, 13)
        main.pack_start(self.titles[1], False, True, 13)

        # counters
        self.cnt = []
        eta = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        eta.pack_start(Gtk.Label(), True, True, 0)
        for i in range(0,6):
            self.cnt.append(counter(self))
            eta.pack_start(self.cnt[i], False, False, 5)
            if i in [1, 3]:
                eta.pack_start(self.labels[int((i-1)/2)], False, False, 12)

        eta.pack_start(Gtk.Label(), True, True, 0)
        main.pack_start(eta, False, False, 0)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        button_box.set_homogeneous(True)
        button_box.set_size_request(600, -1)
        main_bottom.pack_start(button_box, False, False, 0)
        main_bottom.pack_start(Gtk.Label(), True, True, 0)


        # settings page
        settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        settings_widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        settings_widget.pack_start(Gtk.Label(), True, True, 0)
        settings_widget.pack_start(settings_box, False, False, 0)
        settings_widget.pack_start(Gtk.Label(), True, True, 0)
        settings_box.set_size_request(600, -1)
        stack.add_named(settings_widget, "settings")

        # start button
        def start_fn(widget=None):
            global status
            global alarm
            alarm = False
            self.start_time = int(time.time())
            self.timeout = self.get()
            status = "START"
            self.start.hide()
            pause.show()
            GLib.idle_add(self.loop)
            for i in range(0,6):
                self.cnt[i].hide_but()
        self.start.connect("clicked", start_fn)
        button_box.pack_start(self.start, True, True, 13)

        self.start.set_sensitive(False)
        self.stop.set_sensitive(False)

        # pause button (without reset)
        pause = Gtk.Button(label=_("Pause"))
        def pause_fn(widget=None):
            global status
            global alarm
            alarm = False
            status="STOP"
            self.start.show()
            pause.hide()
            for i in range(0,6):
                self.cnt[i].show_but()
        pause.connect("clicked", pause_fn)
        button_box.pack_start(pause, True, True, 13)

        # stop button (with reset)
        def stop_fn(widget=None):
            pause_fn()
            self.set(0)

        self.stop.connect("clicked", stop_fn)
        button_box.pack_start(self.stop, True, True, 13)

        # minimize button
        exit = Gtk.Button(label=_("Minimize"))
        exit.connect("clicked", (lambda widget: self.iconify()))
        main_bottom.pack_start(exit, False, False, 13)

        # exit button
        exit = Gtk.Button(label=_("Exit"))
        exit.connect("clicked", Gtk.main_quit)
        main_bottom.pack_start(exit, False, False, 13)


        # theme button
        theme = Gtk.Button(label=_("Light Theme"))
        def theme_fn(widget=None):
            self.dark_theme = not self.dark_theme
            self.settings.set_property("gtk-application-prefer-dark-theme", self.dark_theme)
            if self.dark_theme:
                theme.set_label(_("Light Theme"))
            else:
                theme.set_label(_("Dark Theme"))
        theme.connect("clicked", theme_fn)
        settings_box.pack_start(theme, False, False, 13)

        # settings button
        settings_button = Gtk.Button(label=_("Settings"))
        def settings_fn(widget=None):
            if stack.get_visible_child_name() == "main":
                settings_button.set_label(_("Main Page"))
                stack.set_visible_child_name("settings")
            else:
                settings_button.set_label(_("Settings"))
                stack.set_visible_child_name("main")

        settings_button.connect("clicked", settings_fn)
        button_box.pack_start(settings_button, True, True, 13)

        # Title0 entry
        title0_entry = Gtk.Entry()
        title0_entry.set_text(gsettings_get("title0"))
        def title0_event(widget=None):
            gsettings_set("title0", title0_entry.get_text())
            if title0_entry.get_text() == "":
                self.titles[0].hide()
            else:
                self.titles[0].show()
                self.titles[0].set_markup("<span font='31'>{}</span>".format(title0_entry.get_text()))
        title0_entry.connect("changed", title0_event)
        settings_box.pack_start(Gtk.Label(label=_("First Title")), False, False, 13)
        settings_box.pack_start(title0_entry, False, False, 0)
        title0_event()

        # Title0 entry
        title1_entry = Gtk.Entry()
        title1_entry.set_text(gsettings_get("title1"))
        def title1_event(widget=None):
            gsettings_set("title1", title1_entry.get_text())
            if title0_entry.get_text() == "":
                self.titles[1].hide()
            else:
                self.titles[1].show()
                self.titles[1].set_markup("<span font='21'>{}</span>".format(title1_entry.get_text()))
        title1_entry.connect("changed", title1_event)
        settings_box.pack_start(Gtk.Label(label=_("Second Title")), False, False, 13)
        settings_box.pack_start(title1_entry, False, False, 0)
        title1_event()

        # Alarm file selection
        settings_box.pack_start(Gtk.Label(label=_("Alarm")), False, False, 13)
        alarm_path = gsettings_get("alarm")
        if alarm_path == "":
            alarm_path = os.path.dirname(__file__)+"/alarm.ogg"
        alarm_button = Gtk.Button(label=alarm_path)
        def select_alarm(widget=None):
            global alarm_path
            dialog = Gtk.FileChooserDialog(_("Please choose an alarm file"), self,
                Gtk.FileChooserAction.OPEN,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                 Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
            filter_audio = Gtk.FileFilter()
            filter_audio.set_name('Audio')
            filter_audio.add_mime_type('audio/*')
            dialog.add_filter(filter_audio)
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                gsettings_set("alarm", dialog.get_filename())
                alarm_path = dialog.get_filename()
                alarm_button.set_label(dialog.get_filename())
            dialog.destroy()
        alarm_button.connect("clicked", select_alarm)
        settings_box.pack_start(alarm_button, False, False, 0)


        self.show_all()
        self.fullscreen()
        stop_fn()
        self.init = True


    @asynchronous
    def alarm_fn(self):
        print(alarm_path)
        while status == "STOP" and alarm:
            audio.play(alarm_path)

    def loop(self):
        global status
        global alarm
        print(self.get())
        if status == "STOP":
            return
        else:
            cur = int(self.start_time + self.timeout - time.time())
            if cur <= 0:
                status = "STOP"
                alarm = True
                self.alarm_fn()
                self.set(0)
                return
            self.set(cur)

        GLib.timeout_add(100,self.loop)

    def get(self):
        ret = 0
        ret += self.cnt[5].get()
        ret += self.cnt[4].get()*10
        ret += self.cnt[3].get()*60
        ret += self.cnt[2].get()*600
        ret += self.cnt[1].get()*3600
        ret += self.cnt[0].get()*36000
        return ret

    def set(self, cur):
        h = int(cur / 3600)
        self.cnt[0].set(h / 10)
        self.cnt[1].set(h % 10)
        m = int((cur % 3600) / 60)
        self.cnt[2].set(m / 10)
        self.cnt[3].set(m % 10)
        s = int(cur - h*3600 - m*60)
        self.cnt[4].set(s / 10)
        self.cnt[5].set(s % 10)


    def update_ui(self):
        if self.init:
            self.start.set_sensitive(self.get() > 0)
            self.stop.set_sensitive(self.get() > 0)
