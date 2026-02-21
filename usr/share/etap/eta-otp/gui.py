import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf, Gio

import qrcode
from io import BytesIO


def create_gui(self):
########## Main widgets ##########
        self.ui_window_main = Gtk.Window()

        headerbar = Gtk.HeaderBar()
        self.ui_window_main.set_titlebar(headerbar)
        headerbar.set_show_close_button(True)
        headerbar.set_title(_("Pin Login Settings"))

        self.ui_stack_main = Gtk.Stack()

        box1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        box1.pack_start(Gtk.Label(), True, True, 0)
        box1.pack_start(box2, True, True, 0)
        box1.pack_start(Gtk.Label(), True, True, 0)

        box2.pack_start(Gtk.Label(), True, True, 0)
        box2.pack_start(self.ui_stack_main, True, True, 0)
        box2.pack_start(Gtk.Label(), True, True, 0)

        self.ui_window_main.add(box1)
        self.ui_window_main.set_resizable(False)
        self.ui_window_main.set_size_request(400,400)

########## Otp create page ##########

        self.ui_box_main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.ui_box_main.set_spacing(8)
        self.ui_stack_main.add_named(self.ui_box_main, "main")

        self.ui_box_main.pack_start(Gtk.Label(label=_("Pin is not available.")), False, False, 0)

        self.ui_button_newotp = Gtk.Button(label=_("Generate a new Pin"))
        self.ui_box_main.pack_start(self.ui_button_newotp, False, False, 0)

        self.ui_button_import = Gtk.Button(label=_("Import Pin from File"))
        self.ui_box_main.pack_start(self.ui_button_import, False, False, 0)


        self.ui_button_fromkey = Gtk.Button(label=_("Generate Pin from key"))
        self.ui_box_main.pack_start(self.ui_button_fromkey, False, False, 0)

########## Otp settings page ##########

        self.ui_box_settings = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.ui_box_settings.set_spacing(8)
        self.ui_stack_main.add_named(self.ui_box_settings, "settings")

        self.ui_box_settings.pack_start(Gtk.Label(label=_("Pin available.")), False, False, 0)

        self.ui_button_show = Gtk.Button(label=_("Show Pin QR/Key"))
        self.ui_box_settings.pack_start(self.ui_button_show, False, False, 0)

        self.ui_button_export = Gtk.Button(label=_("Export Pin to file"))
        self.ui_box_settings.pack_start(self.ui_button_export, False, False, 0)

        self.ui_button_delete = Gtk.Button(label=_("Remove Pin"))
        self.ui_box_settings.pack_start(self.ui_button_delete, False, False, 0)

########## QR / Key page ##########

        self.ui_box_qr = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.ui_box_qr.set_spacing(8)
        self.ui_stack_main.add_named(self.ui_box_qr, "qr")

        self.ui_image_qr = Gtk.Image()
        self.ui_image_qr.set_pixel_size(256)
        self.ui_image_qr.set_from_icon_name("image-missing", 0)
        self.ui_box_qr.pack_start(self.ui_image_qr, True, True, 0)

        self.ui_label_secret = Gtk.Label(label="JBSWY3DPEHPK3PXP")
        self.ui_box_qr.pack_start(self.ui_label_secret, False, False, 0)

########## Headerbar ##########

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.ui_button_qr_back = Gtk.Button(label=_("Back"))
        self.ui_button_help = Gtk.Button(label=_("Help"))
        button_box.pack_start(self.ui_button_help, False, False, 3)
        button_box.pack_start(self.ui_button_qr_back, False, False, 3)
        headerbar.pack_start(button_box)

        popover = Gtk.Popover()
        popover.set_relative_to(self.ui_button_help)
        def help_clicked(widget):
           popover.popup()
        self.ui_button_help.connect("clicked", help_clicked)
        help_img = Gtk.Image()
        popover.add(help_img)
        help_img.show()
        qr = qrcode.make("https://rehber.etap.org.tr/dokumanlar/pin-giris", box_size=5)

        # Convert QR code to a format that GTK can use
        with BytesIO() as output:
            qr.save(output, format="PNG")
            output.seek(0)
            # Create a Gio.MemoryInputStream from the BytesIO object
            memory_stream = Gio.MemoryInputStream.new_from_data(output.getvalue(), None)
            help_img.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_stream(memory_stream, None))

