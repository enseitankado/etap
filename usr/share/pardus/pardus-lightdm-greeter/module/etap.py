def _screen_keyboard_event(widget):
    os.system(get("screen-keyboard", "onboard", "keyboard")+"&")

def _login_ogrenci(widget):
    lightdm.greeter.authenticate("ogrenci")
    lightdm.set("ogrenci", "ogrenci")
    lightdm.login()

def module_init():
    button = Gtk.Button()
    button.get_style_context().add_class("icon")

    image = Gtk.Image()
    image.set_pixel_size(32*scale)
    image.set_from_icon_name("input-keyboard-symbolic", 0)
    button.add(image)
    button.show_all()

    button.connect("clicked", _screen_keyboard_event)
    loginwindow.o("ui_box_bottom_right").pack_start(button,False, False, 0)
    loginwindow.o("ui_box_bottom_right").reorder_child(button, 0)

    if lightdm.is_valid_user("ogrenci"):

        button2 = Gtk.Button()
        button2.get_style_context().add_class("icon")

        image2 = Gtk.Image()
        image2.set_pixel_size(32*scale)
        image2.set_from_icon_name("preferences-system-parental-controls-symbolic", 0)
        button2.add(image2)
        button2.show_all()

        button2.connect("clicked", _login_ogrenci)


        loginwindow.o("ui_box_bottom_right").pack_start(button2,False, False, 0)
        loginwindow.o("ui_box_bottom_right").reorder_child(button2, 0)

    loginwindow.o("ui_button_virtual_keyboard").hide()
    loginwindow.o("ui_box_keyboard_menu").hide()
    # force enable wifi
    os.system("nmcli radio wifi on")
