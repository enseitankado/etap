#!/usr/bin/env python3
import sys
sys.path.insert(0, "/usr/share/eta/eta-qr-login")

from qrwidget import QrWidget

qr_page_status = False

qr = QrWidget()
button = Gtk.Button()
but_image = Gtk.Image()


def _set_qr_button_image(name):
    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
        filename=appdir+"/data/"+name+".svg",
        width=36*scale,
        height=36*scale,
        preserve_aspect_ratio=True)
    but_image.set_from_pixbuf(pixbuf)

def _qr_event(widget):
    global qr_page_status
    qr_page_status = not qr_page_status
    loginwindow.ignore_password_cache = True
    if qr_page_status:
        page = "page_qr"
        _set_qr_button_image("qr-login-key")
        qr.refresh(widget)
    else:
        page = "page_main"
        _set_qr_button_image("qr-login-qr")
    loginwindow.o("ui_stack_main").set_visible_child_name(page)

def _timeout_event():
    global qr_page_status
    qr_page_status = True
    _qr_event(None)

def _fail_event():
    qr.time_expire = 0
    qr.time_begin = 0

qr.timeout_handler = _timeout_event
qr.fail_handler = _fail_event

def module_init():
    # Qr button
    button.get_style_context().add_class("icon")
    button.add(but_image)
    button.show_all()
    button.connect("clicked", _qr_event)
    _set_qr_button_image("qr-login-qr")

    # Qr Widget
    qr.img.get_style_context().add_class("icon")

    qr.label.get_style_context().add_class("text")
    qr.label_msg.get_style_context().add_class("text")
    print(qr, file=sys.stderr)

    # Add qr button
    loginwindow.o("ui_box_bottom_left").pack_start(button,False, False, 0)
    loginwindow.o("ui_box_bottom_left").reorder_child(button, -1)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box.pack_start(qr.img, True, True, 5)
    box.pack_start(qr.progressbar, False, True, 8)
    box.pack_start(qr.label, False, False, 5)
    box.pack_start(qr.label_msg, False, False, 5)
    box.set_valign(Gtk.Align.CENTER)
    box.set_halign(Gtk.Align.CENTER)
    loginwindow.o("ui_stack_main").add_named(box, "page_qr")
    loginwindow.o("ui_stack_main").set_visible_child_name("page_qr")
    box.show_all()

