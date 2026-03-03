import asyncio
durum=0
icon=None
def _k_button_event(widget=None, event=None):
     os.system("setxkbmap tr")
     os.system("onboard --theme=/usr/share/onboard/themes/Nightshade.theme --layout=/usr/share/onboard/layouts/'Full Keyboard.onboard'&")
     #os.system("pkill e-keyboard;/usr/bin/e-keyboard show&")
     
     #os.system(get("screen-keyboard", "onboard", "keyboard")+"&")     
     #icon.set_from_file("/usr/share/icons/hicolor/scalable/status/keyboardoff.svg")
     loginwindow.o("ui_entry_password").grab_focus()
         
def _klv_button_event(widget=None):
     global durum
     if durum==0:
         durum=1
         os.system(get("screen-keyboard", "sh -c 'pkill e-keyboard;/usr/bin/e-keyboard login;'", "keyboard")+"&")
         icon.set_from_file("/usr/share/icons/hicolor/scalable/status/keyboardoff.svg")
         loginwindow.o("ui_entry_password").grab_focus()
     elif durum==1:
         durum=0
         os.system(get("screen-keyboard", "sh -c 'pkill e-keyboard;'", "keyboard")+"&")
         icon.set_from_file("/usr/share/icons/hicolor/scalable/status/keyboardon.svg")
         loginwindow.o("ui_entry_password").grab_focus()

def module_init():
    global durum
    global icon
    icon = Gtk.Image()
    icon.set_from_file("/usr/share/icons/hicolor/scalable/status/keyboardon.svg")
    #button = Gtk.Button(image=icon)
    button = Gtk.Button()
    button.add(icon)
    button.get_style_context().add_class("icon")
    button.connect("clicked", _k_button_event)
    #button.connect("clicked", _klv_button_event)
    loginwindow.o("ui_box_bottom_right").pack_start(button, False, True, 10)
    button.show_all()
    #loginwindow.o("ui_entry_password").connect("focus-in-event",_k_button_event)

