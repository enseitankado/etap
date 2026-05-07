import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class HardwareDetailRow(Gtk.Box):
    def __init__(self, icon_name, title, headers, table):
        super().__init__(orientation="vertical")

        self.get_style_context().add_class("card")
        self.get_style_context().add_class("p-7")

        # Clickable
        eventbox = Gtk.EventBox()
        eventbox.connect("button-press-event", self.on_expand_clicked)

        # Header
        header_box = Gtk.Box(spacing=11, margin_top=3, margin_bottom=3)

        icon_img = Gtk.Image(icon_name=icon_name, margin_start=7, pixel_size=24)
        title_lbl = Gtk.Label(
            label=f"<b>{title}</b>", halign="start", hexpand=True, use_markup=True
        )
        revealer_img = Gtk.Image(icon_name="go-down-symbolic", margin_end=7)

        header_box.add(icon_img)
        header_box.add(title_lbl)
        header_box.add(revealer_img)
        eventbox.add(header_box)

        # Body
        revealer_box = Gtk.Box(orientation="vertical", margin_top=7)
        revealer_box.add(Gtk.Separator())
        revealer_box.add(TableContent(headers, table))
        self.revealer = Gtk.Revealer(child=revealer_box)

        self.add(eventbox)
        self.add(self.revealer)

    def on_expand_clicked(self, w, d):
        is_revealed = self.revealer.get_reveal_child()
        self.revealer.set_reveal_child(not is_revealed)


class TableContent(Gtk.Box):
    def __init__(self, headers, table):
        super().__init__()

        self.get_style_context().add_class("p-7")

        # Example Usage
        example_headers = ["Vendor", "Model", "Family"]
        example_table = [
            ["XYZ Notebook", "Model 1.1", "XYZ"],
        ]

        # Fill
        for i in range(len(headers)):
            # Header
            col_box = Gtk.Box(
                orientation="vertical",
                hexpand=True,
                halign="start",
                spacing=7,
            )
            col_box.add(
                Gtk.Label(label=f"<b>{headers[i]}</b>", use_markup=True, halign="start")
            )

            # Data Column
            for row in table:
                col_box.add(Gtk.Label(label=row[i], halign="start"))

            self.add(col_box)
