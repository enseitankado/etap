from ui_gtk3 import PActionRow
from managers import ApplicationManager
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, GLib  # noqa


class ApplicationChooserWindow(Gtk.Window):
    def __init__(self, parent_window):
        super().__init__(
            transient_for=parent_window,
            modal=True,
            window_position=Gtk.WindowPosition.CENTER_ON_PARENT,
        )

        self.setup_window()

        self.setup_ui()

    # == SETUP ==
    def setup_window(self):
        self.set_default_size(450, 600)
        self.set_title("Uygulama Seçiniz...")
        self.connect("delete-event", self.on_window_delete)

    def setup_ui(self):
        box = Gtk.Box()
        box.add(Gtk.Label(label="Uygulamalar Getiriliyor..."))

        self.add(box)

        GLib.timeout_add(10, self.add_all_applications_to_group, box)

    # == FUNCTIONS ==
    def show_ui(self, application_selected_callback=None):
        if application_selected_callback is not None:
            self.on_application_selected_callback = application_selected_callback

        self.show_all()

    def add_all_applications_to_group(self, box):
        self.remove(box)
        box = Gtk.Box(orientation="vertical")
        box.add(
            Gtk.Label(
                label="<b>Önemli:</b>\nDışarıdan yüklenen uygulamalar (örn: Snap, AppImage) düzgün çalışmayabilir.\n\nPardus Yazılım Merkezi, .deb ve Flatpak uygulamaları desteklenmektedir.",
                halign="start",
                margin_top=11,
                margin_start=9,
                margin_end=9,
                use_markup=True,
            )
        )

        listbox = Gtk.ListBox()
        scrolledwindow = Gtk.ScrolledWindow(
            max_content_width=400, min_content_height=580
        )
        frame = Gtk.Frame(margin=7)
        frame.add(scrolledwindow)
        scrolledwindow.add(listbox)

        for app in ApplicationManager.get_all_applications():
            app_id = app.get_id()

            sensitive = True
            if app_id in ApplicationManager.ALWAYS_ALLOWED_APPLICATIONS:
                app_id = "Her zaman izinli"  # subtitle
                sensitive = False

            action_row = PActionRow.new(
                title=app.get_name(),
                subtitle=app_id,
                gicon=app.get_icon(),
                user_data=app,
                is_activatable=True,
            )
            action_row.set_sensitive(sensitive)

            listbox.add(action_row)

        listbox.connect("row-activated", self.on_action_application_selected)

        box.add(frame)
        self.add(box)

    # == CALLBACKS ==
    def on_window_delete(self, win, event):
        # Don't delete window on close, just hide.
        self.hide()
        return True

    def on_action_application_selected(self, listbox, row):
        gdesktop_app_info = row.user_data

        if self.on_application_selected_callback is not None:
            self.on_application_selected_callback(gdesktop_app_info)

        self.close()
