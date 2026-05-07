import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk


class HardwareGridCell(Gtk.Box):
    def __init__(self, icon_name, title, value, can_hide=False, value_loading=False):
        super().__init__()

        self.get_style_context().add_class("card")
        self.get_style_context().add_class("p-7")
        self.get_style_context().add_class("p-15-lr")

        # Icon
        main_box = Gtk.Box(spacing=7, halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
        icon_img = Gtk.Image(icon_name=icon_name, pixel_size=42)

        # Title
        box = Gtk.Box(
            orientation="vertical",
            spacing=3,
            valign=Gtk.Align.CENTER,
            halign=Gtk.Align.START,
        )
        title_lbl = Gtk.Label(label=f"{title}", halign=Gtk.Align.START)
        box.add(title_lbl)

        # Name + (Optional Hide Button)
        self.value = value  # store value
        value_box = Gtk.Box(spacing=7)
        self.value_lbl = Gtk.Label(
            label=f"<b>{value}</b>",
            halign=Gtk.Align.START,
            use_markup=True,
            ellipsize="end",
            selectable=True,
        )
        value_box.add(self.value_lbl)

        self.spinner = None

        if value_loading:
            self.spinner = Gtk.Spinner(active=True)
            value_box.add(self.spinner)

        if can_hide:
            self.hide_btn = Gtk.Button.new_from_icon_name(
                "view-reveal-symbolic", Gtk.IconSize.BUTTON
            )
            self.hide_btn.set_valign(Gtk.Align.START)
            self.hide_btn.revealed = True
            # self.hide_btn.get_style_context().add_class("flat")

            # Hide button if loading
            if value_loading:
                self.hide_btn.set_visible(False)
                self.hide_btn.set_no_show_all(True)

            self.hide_btn.connect("clicked", self.on_hide_btn_clicked)

            value_box.add(self.hide_btn)

        box.add(value_box)

        main_box.add(icon_img)
        main_box.add(box)

        self.add(main_box)

    def on_hide_btn_clicked(self, btn):
        if btn.revealed:
            btn.set_image(Gtk.Image(icon_name="view-conceal-symbolic"))
            self.value_lbl.set_label("{}".format(len(self.value) * "*"))
        else:
            btn.set_image(Gtk.Image(icon_name="view-reveal-symbolic"))
            self.value_lbl.set_label(f"<b>{self.value}</b>")

        btn.revealed = not btn.revealed

    def set_value(self, value):
        self.value = value
        self.value_lbl.set_label(f"<b>{self.value}</b>")

        if self.spinner:
            self.spinner.destroy()
            self.hide_btn.set_visible(True)
