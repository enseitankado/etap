import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.0')
from gi.repository import Gtk
from gi.repository import WebKit2
from gi.repository import Soup
import json
from logla import logla
import os
import subprocess

userid_cacheonline = ""
ebaonlinepopover = None
q1 = None

class EbaonlineWidget(Gtk.Box):

    def __init__(self):
        super().__init__()
        self.__webonline=WebKit2.WebView()
        self.__webonline.set_size_request(400,500)

        self.__webonline2=WebKit2.WebView()
        self.__webonline.load_uri("https://giris.eba.gov.tr/EBA_GIRIS/studentQrcode.jsp")
        self.__webonline.connect("load-changed",self.__load_eventonline)
        self.__webonline.set_zoom_level(self.__webonline.get_zoom_level() - 0.6)

        self.__webonline2.connect("load-changed",self.__load_eventonline2)
        self.__webonline.set_sensitive(False)
        self.data_actiononline = None
        self.loginType="ebaqronline"
        
        self.hbox = Gtk.HBox(spacing=6)
 
        self.button1 = Gtk.RadioButton.new_with_label_from_widget(None, "Kişiye Özel Giriş")
        self.button1.connect("toggled", self.on_selectedonline, "1")
        self.hbox.pack_start(self.button1, False, False, 0)

        #self.button2 = Gtk.RadioButton.new_from_widget(self.button1)
        #self.button2.set_label("Kişiye Özel Giriş")
        #self.button2.connect("toggled", self.on_selectedonline, "2")
        #self.hbox.pack_start(self.button2, False, False, 0)
        
        self.vbox = Gtk.VBox(spacing=6)
        self.vbox.pack_start(self.hbox, False, False, 0)
        self.vbox.pack_start(self.__webonline, False, False, 0)
        #self.add(self.__webonline)
        self.add(self.vbox)
	
    def on_selectedonline(self, widget, data=None):
        self.loginType="ebaqronline"
        logla('debug', 'loginType=ebaqronline ayarlandi.')
        
    def on_selectedebaqr(self, widget, data=None):
        self.loginType="ebaqrebaqr"
        logla('debug', 'loginType=ebaqrebaqr ayarlandi.')
      
    def refresh(self,widget=None):
        self.__webonline.get_website_data_manager().clear(WebKit2.WebsiteDataTypes.ALL,0,None,None,None)
        self.show_all()
        self.__webonline.load_uri("https://giris.eba.gov.tr/EBA_GIRIS/studentQrcode.jsp")
        logla('debug', 'WebView refresh oldu: https://giris.eba.gov.tr/EBA_GIRIS/studentQrcode.jsp.')

        # Klavyeyi kapat
        pid = subprocess.check_output("pgrep onboard", shell=True).decode().strip()
        if pid:
            os.system(f"kill {pid}")


    def __load_eventonline(self,webkit,event):
        link=webkit.get_uri()
        if "studentQrcode" in link:
            return
        elif "ders.eba.gov.tr" not in link:
            self.__webonline.load_uri("https://giris.eba.gov.tr/EBA_GIRIS/studentQrcode.jsp")
            return
        self.__webonline2.load_uri("https://uygulama-ebaders.eba.gov.tr/ders/FrontEndService//home/user/getuserinfo")

    def __load_eventonline2(self,webkit,event):
        #if event == WebKit2.LoadEvent.FINISHED:
        link=webkit.get_uri()
        resource = webkit.get_main_resource()
        if resource:
            resource.get_data(None,self.__response_dataonline,None)

    def __response_dataonline(self,resource,result,data=None):
        global ebaonlinepopover
        global userid_cacheonline
        global q1
        try:
            html = resource.get_data_finish(result)
            data = html.decode("utf-8")
            #if self.data_actiononline:
            persondata = json.loads(data)
        except:
            q1.refresh()
            return
        
        role=str(persondata["userInfoData"]["role"])
        userid=persondata["userInfoData"]["userId"]
        name=persondata["userInfoData"]["name"]
        surname=persondata["userInfoData"]["surname"]
        username = self.username_prepare(name+"-"+surname)

        logla('debug', f"loginType={self.loginType} icin WebView response verisi geldi. {username}:{userid}")

        if userid_cacheonline == userid:
            return
        #userid_cacheonline = userid
            
        if role == "2" or role == "300" or role == "301":
            #os.system("echo '"+self.loginType+" "+username+" "+userid+"'>/ortak-alan/test")
            os.system("echo '"+self.loginType+":"+username+":"+userid+"' | netcat localhost 7777 &")
            logla('debug', f"TCP:7777'ye {self.loginType}:{username}:{userid} verisi yazildi.")
        else:
            q1.refresh()
        ebaonlinepopover.hide()

    def username_prepare(self,u):
    	u = u.replace("ç","c")
    	u = u.replace("ı","i")
    	u = u.replace("ğ","g")
    	u = u.replace("ö","o")
    	u = u.replace("ş","s")
    	u = u.replace("ü","u")
    	u = u.replace("Ç","c")
    	u = u.replace("I","i")
    	u = u.replace("İ","i")
    	u = u.replace("Ğ","g")
    	u = u.replace("Ö","o")
    	u = u.replace("Ş","s")
    	u = u.replace("Ü","u")
    	u = u.replace(" ","-")
    	u = u.lower()
    	return u



#----------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------
 
def _ebaonline_button_event(widget):
    ebaonlinepopover.popup()
    GLib.idle_add(q1.refresh)


def module_init():
    global ebaonlinepopover
    global q1
    q1 = EbaonlineWidget()
    ebaonlinepopover = Gtk.Popover()
    q1.set_size_request(400,500)
    ebaonlinepopover.set_size_request(400,500)
    ebaonlinepopover.add(q1)
    button1 = Gtk.MenuButton(label="EBA-GIRIS", popover=ebaonlinepopover)
    button1.connect("clicked",_ebaonline_button_event)
    loginwindow.o("ui_box_bottom_left").pack_end(button1, False, True, 5)
    button1.get_style_context().add_class("icon")
    button1.show_all()
