import gi
import re

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # noqa


def info(msg, msg_type=Gtk.MessageType.INFO):
    dialog = Gtk.MessageDialog(
        text=msg,
        message_type=msg_type,
        buttons=Gtk.ButtonsType.OK,
        window_position=Gtk.WindowPosition.CENTER_ON_PARENT,
    )

    dialog.run()
    dialog.destroy()


def ok_cancel(msg, secondary_text="Emin misiniz?"):
    dialog = Gtk.MessageDialog(
        text=msg,
        secondary_text=secondary_text,
        message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.OK_CANCEL,
        window_position=Gtk.WindowPosition.CENTER_ON_PARENT,
    )

    result = dialog.run()
    dialog.destroy()

    return result


def with_custom_buttons(msg, secondary_text, buttons):
    dialog = Gtk.MessageDialog(
        text=msg,
        secondary_text=secondary_text,
        message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.NONE,
        window_position=Gtk.WindowPosition.CENTER_ON_PARENT,
    )

    for btn, response in buttons:
        dialog.add_button(btn, response)

    result = dialog.run()
    dialog.destroy()

    return result


class InputDialog(Gtk.Window):
    def __init__(
        self,
        parent_window,
        title,
        subtitle,
        entry_callback,
        regex=None,
        window_title=None,
    ):
        super().__init__(
            transient_for=parent_window,
            modal=True,
            window_position=Gtk.WindowPosition.CENTER_ON_PARENT,
        )

        self.setup_window()
        if window_title is not None:
            self.set_title(window_title)

        self.setup_ui(title, subtitle)

        self.entry_callback = entry_callback
        self.regex = regex

    # UI
    def setup_window(self):
        self.set_default_size(300, 100)
        self.set_title("Sınırlı Erişim")

    def setup_ui(self, title, subtitle):
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=7,
            margin_top=11,
            margin_bottom=11,
            margin_start=11,
            margin_end=11,
        )

        if title:
            lbl_title = Gtk.Label(label=title)
            box.add(lbl_title)

        if subtitle:
            lbl_subtitle = Gtk.Label(label=subtitle)
            box.add(lbl_subtitle)

        entry_input = Gtk.Entry(placeholder_text="...", activates_default=True)
        entry_input.connect("activate", self.on_entry_input_activated)
        entry_input.connect("key-release-event", self.on_entry_key_released)

        box.add(entry_input)

        box_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        btn_cancel = Gtk.Button(label="İptal Et")
        btn_ok = Gtk.Button(label="Tamam", hexpand=True, halign="end")
        btn_ok.get_style_context().add_class("suggested-action")

        btn_cancel.connect("clicked", lambda btn: self.close())
        btn_ok.connect(
            "clicked", lambda btn: self.on_entry_input_activated(entry_input)
        )

        box_buttons.add(btn_cancel)
        box_buttons.add(btn_ok)
        box.add(box_buttons)

        self.add(box)

        entry_input.grab_focus_without_selecting()

    def is_regex_valid(self, text):
        if self.regex is not None:
            return re.search(self.regex, text) is not None
        else:
            return True

    # == CALLBACKS ==
    def on_entry_input_activated(self, entry):
        if entry.get_text() != "":
            if self.is_regex_valid(entry.get_text()):
                entry.set_name("")
                self.entry_callback(entry.get_text())
                self.close()

            else:
                entry.set_name("entry_not_valid")

    def on_entry_key_released(self, entry, event_key):
        if event_key.keyval == Gdk.KEY_Escape:
            self.close()

        return False  # not prevent event to propagate
