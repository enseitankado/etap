#!/usr/bin/python3

import os
import gi
from passlib.hash import bcrypt
import requests

gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.0")

from gi.repository import Gio, Gtk, WebKit2  # noqa
from gi.repository.WebKit2 import WebView, Settings  # noqa

from USBDeviceManager import USBDeviceManager
import CredentialsManager
import Dialogs

EBA_URL = "https://giris.eba.gov.tr/EBA_GIRIS/Giris?uygulamaKodu=pardus&login=teacher"
EBA_PASSWORD_RESET_URL = "https://giris.eba.gov.tr/EBA_GIRIS/UsbPasswordChangerV7"
EBA_REGISTER_USB_URL = "https://giris.eba.gov.tr/EBA_GIRIS/RegisterUsbUser"
EBA_DELETE_USB_URL = "https://giris.eba.gov.tr/EBA_GIRIS/DeleteUsbUser"


class Model:
    # Credentials
    name = ""
    username = ""
    token = ""
    url = ""

    # Identity
    tckn = ""
    eba_id = ""

    # USB
    usb = None
    mode = "delete"  # delete, register


class MainWindow:
    def __init__(self, application):
        # Gtk Builder
        self.builder = Gtk.Builder()
        self.application = application

        # Import UI file:
        self.builder.add_from_file(
            os.path.dirname(os.path.abspath(__file__)) + "/../ui/MainWindow.glade"
        )
        self.builder.connect_signals(self)

        # Window
        self.window = self.builder.get_object("window")
        self.window.set_application(application)
        self.window.connect("destroy", self.on_destroy)

        # UI Components
        self.define_components()

        # Variables
        self.define_variables()

        # Get USB Devices
        self.get_usb_devices()

        # Show Screen:
        self.window.show_all()

    # Window methods:
    def on_destroy(self, _action):
        self.window.get_application().quit()

    def define_components(self):
        def UI(s):
            return self.builder.get_object(s)

        self.stack = UI("stack")

        # Main Page

        # USB Selection Page
        self.list_devices = UI("list_devices")
        self.cmb_devices = UI("cmb_devices")
        self.btn_select_usb = UI("btn_select_usb")

        # EBA Web Page
        self.webview = UI("webview")
        self.window_webview = UI("window_webview")
        self.webview_stack = UI("webview_stack")

        # Credentials
        self.stack_usb_warning = UI("stack_usb_warning")
        self.lbl_username = UI("lbl_username")
        self.entry_password = UI("entry_password")
        self.entry_password_again = UI("entry_password_again")
        self.btn_register_usb = UI("btn_register_usb")
        self.lbl_usb_path = UI("lbl_usb_path")

        # Dialog:
        self.dialog_about = UI("dialog_about")

    def define_variables(self):
        self.model = Model()
        self.cmb_current_usb = None

    # == FUNCTIONS ==
    # USB Methods
    def get_usb_devices(self):
        self.usb_manager = USBDeviceManager()
        self.usb_manager.set_usb_refresh_signal(self.list_usb_devices)
        self.list_usb_devices()

    def list_usb_devices(self):
        devices = self.usb_manager.get_usb_devices()

        self.btn_register_usb.set_sensitive(len(devices) != 0)

        self.list_devices.clear()
        for device in devices:
            self.list_devices.append(device)

        self.cmb_devices.set_active(0)

    # Web Requests
    def load_eba_website(self):
        self.webview_stack.set_visible_child_name("spinner")

        self.webview.get_context().clear_cache()
        self.webview.get_context().get_cookie_manager().delete_all_cookies()

        self.webview.load_uri(EBA_URL)

    def get_ogretmen_info(self, task, source_object, task_data, cancellable):
        url = self.model.url

        if not url:
            self.stack.set_visible_child_name("start")
            return False

        try:
            print("Ogretmen Info Get Request URL:", url)
            r = requests.get(url)
        except Exception as e:
            print("Error on request EBA account api:", e)
            Dialogs.info("Hata! EBA sunucusuna atılan istek başarısız.", f"{e}")
            self.stack.set_visible_child_name("start")
            return False

        """Example json response:
Success => {'msg_type': 'Success', 'msg': 'Process is successful', 'data': {'resultCode': 'EBA.001', 'resultText': 'Process is successful', 'hasRole': '0', 'isEmailVerify': '0', 'isForeign': '0', 'isGuardian': '0', 'school_boroughId': '6', 'school_cityId': '6', 'school_cityName': 'ANKARA', 'school_schoolId': '88870301', 'school_schoolName': 'test lise 301', 'tckn': '88884062115', 'uid': 'G7n5P7bfP9n5P600x5N5c', 'uname': 'Kullanici 88884062115', 'utype': 'TESTTEACHER'}}
Error => {'msg_type': 'Error', 'msg': 'Error occured while getting information', 'data': {'resultCode': 'EBA.004', 'resultText': 'Wrong authentication code'}}
        """
        if r.status_code != 200:
            print(r.status_code)
            print(r.text)
            Dialogs.info(
                "Hata! EBA sunucusu hatalı kod döndürdü:",
                f"Kod:{r.status_code}\n{r.text}",
            )
            self.stack.set_visible_child_name("start")
            return False

        obj = r.json()
        data = obj["data"]
        result_code = data["resultCode"]
        result_text = data["resultText"]
        if obj["msg_type"] != "Success":
            Dialogs.info(
                "Hata! EBA'ya yapılan istek başarısız oldu",
                f"Kod:{result_code}\n{result_text}",
            )
            self.stack.set_visible_child_name("start")
            return False

        # Set Model Variables
        self.model.name = data["uname"]
        self.model.username = CredentialsManager.turkish_to_english(data["uname"])

        self.model.tckn = data["tckn"]
        self.model.eba_id = data["uid"]

        # Setup UI
        self.lbl_username.set_text(self.model.username)

        if self.model.mode == "delete":
            response = Dialogs.ask(
                "Emin misiniz?",
                "EBA'daki Akıllı Tahta USB ile giriş kaydınız silinecek.",
            )

            if response == Gtk.ResponseType.OK:
                self.delete_usb_record()

            self.stack.set_visible_child_name("start")
        elif self.model.mode == "register":
            # Go to Register page
            self.lbl_usb_path.set_text(
                f"{self.model.usb[2]} {self.model.usb[3]} - {self.model.usb[1]}"
            )
            self.stack.set_visible_child_name("register")

    # USB Operations
    def delete_usb_record(self):
        if not self.model.tckn:
            Dialogs.info(
                "TC Kimlik No bulunamadı", "EBA'ya giriş yaptığınızdan emin olun."
            )
            return False

        data = {"tckn": self.model.tckn}
        try:
            r = requests.post(url=EBA_DELETE_USB_URL, params=(data))
            print("EBA_DELETE_USB_URL:", r.status_code)
            print(r.text)

        except Exception as e:
            print("Error on EBA_DELETE_USB_URL request:", e)
            Dialogs.info("USB silme işlemi isteği esnasında bir hata oluştu", f"{e}")

            return False

        # Try to remove file if exists
        if r.status_code != 200:
            Dialogs.info(
                "Hata! EBA sunucusu hatalı kod döndürdü:",
                f"Kod:{r.status_code}\n{r.text}",
            )

            return False

        obj = r.json()
        result_code = obj["resultCode"]
        result_text = obj["resultText"]
        code = result_code.split(".")[1]

        if code == "001":
            Dialogs.info("Başarılı", "EBA Hesabınızdaki USB Kaydı silindi.")
        elif code == "006":
            Dialogs.info("Başarısız!", "USB daha önce eklenmemiş.")
        else:
            Dialogs.info(
                "USB kaydı silinme işlemi başarısız oldu.",
                f"Hata: {result_text} ({result_code})",
            )

    def register_usb(self):
        password = self.entry_password.get_text()
        if not password:
            Dialogs.info("Başarısız!", "Parola girmeyi unutmayınız.")
            return False

        if not self.model.username:
            Dialogs.info(
                "Başarısız!",
                "Kullanıcı Adı bilgisi eksik. EBA'ya giriş yaptığınızdan emin olunuz.",
            )
            return False

        print(self.model.usb)
        if not self.model.usb:
            Dialogs.info("Seçili USB Bellek yok.", "USB'yi seçtiğinizden emin olun.")
            return False

        partition = self.model.usb[1]
        uuid = self.model.usb[4]
        if not partition or not uuid:
            Dialogs.info(
                "Seçili USB Bellek Bölümsüz.",
                "Seçili USB Bellek formatlanmamış veya bağlanmamış.\nLütfen USB'yi sisteme bağlayın veya diskiniz formatlanmamış ise formatlayın.",
            )
            return False

        # Send request
        return self.send_register_usb_request()

    def send_register_usb_request(self):
        # These variables checked at register_usb() and valid here:
        password = self.entry_password.get_text()
        usb_uuid = self.model.usb[4]

        headers = {
            "origin": "http://api.etap.org.tr",
        }

        try:
            # Reset Password
            r = requests.post(
                url=EBA_PASSWORD_RESET_URL,
                headers=headers,
                data={
                    "authCode": self.model.token,
                    "newPass": password,
                    "repPass": password,
                    "user_tckn": self.model.tckn,
                },
            )
            print("EBA_PASSWORD_RESET_URL:", r.status_code)
            print(r.text)

            if r.status_code != 200:
                Dialogs.info("EBA'ya yapılan istek hatalı dönüş yaptı", f"{r.text}")
                return False
        except Exception as e:
            print("Error on EBA_PASSWORD_RESET_URL request:")
            print(e)
            Dialogs.info("Şifre isteği sırasında bir hata oluştu", f"{e}")
            return False

        try:
            # Register USB
            r = requests.post(
                url=EBA_REGISTER_USB_URL,
                headers=headers,
                json={
                    "tckn": self.model.tckn,
                    "password": password,
                    "eba_id": self.model.eba_id,
                    "usb_serial": usb_uuid,
                    "username": self.model.username,
                },
            )

            print("EBA_REGISTER_USB_URL:", r.status_code)
            print(r.text)

            if r.status_code != 200:
                Dialogs.info("EBA'ya yapılan istek hatalı dönüş yaptı", f"{r.text}")
                return False

        except Exception as e:
            print("Error on EBA_REGISTER_USB_URL request:")
            print(e)
            Dialogs.info("USB Cihazın kayıt isteği sırasında bir hata oluştu", f"{e}")
            return False

        obj = r.json()
        result_code = obj["resultCode"]
        result_text = obj["resultText"]
        code = result_code.split(".")[1]

        if code == "001":
            usb_credentials_content = {
                "eba_id": self.model.eba_id,
                "username": self.model.username,
                "usb_serial": usb_uuid,
                "password": bcrypt.hash(password),
                "name": self.model.name,
            }
            partition = self.model.usb[1]
            filepath = os.path.join(partition, ".credentials")
            (write_result, error) = CredentialsManager.save_credentials_file(
                filepath, usb_credentials_content
            )

            if write_result:
                Dialogs.info(
                    "Başarılı",
                    "EBA Hesabınızdaki USB Kaydı yenilendi ve yeni USB'nize kaydedildi.",
                )
                return True

            Dialogs.info(
                "Başarısız!",
                f"EBA Hesabınızdaki USB Kaydı yenilendi, fakat hesap bilgileri USB'nize kaydedilemedi!\n\nHata:{error}",
            )

            # Save to home
            home = os.environ.get("HOME", "")
            filepath = os.path.join(home, "1.credentials")
            (write_result, error) = CredentialsManager.save_credentials_file(
                filepath, usb_credentials_content
            )
            if write_result:
                Dialogs.info(
                    "Dikkat!",
                    "Hesap bilgileri, Ev dizinine '1.credentials' ismiyle kaydedildi.\nLütfen dosyayı USB'nize kopyalayın ve başındaki 1'i silin.",
                )
                return True

            Dialogs.info(
                "Başarısız!",
                f"Hesap bilgileri, USB'ye veya Ev dizinine('{filepath}') kaydedilemedi.Hata:\n\n{error}",
            )
            return False

        elif code == "003":
            Dialogs.info("Başarısız!", "USB parolası doğru değil.")
        else:
            Dialogs.info("USB kaydedilemedi.", f"Çıktı: {result_text} ({result_code})")

        return False

    # == CALLBACKS ==

    # = Main Page =
    def on_cmb_devices_changed(self, combobox):
        self.cmb_current_usb = None

        selected_usb = combobox.get_active_iter()
        if selected_usb:
            model = combobox.get_model()
            device_info = model[selected_usb][:]

            # Update usb warning visibility
            partition = device_info[1]
            if partition:
                self.stack_usb_warning.set_visible_child_name("empty")
                self.cmb_current_usb = device_info
            else:
                self.stack_usb_warning.set_visible_child_name("warning")

            print("device_info", device_info)

        self.btn_select_usb.set_sensitive(self.cmb_current_usb is not None)

    def on_btn_delete_clicked(self, btn):
        self.model = Model()
        self.model.mode = "delete"

        self.load_eba_website()
        self.window_webview.show_all()

    def on_btn_register_clicked(self, btn):
        self.model = Model()
        self.model.mode = "register"

        self.stack.set_visible_child_name("usb_select")

    # = USB Selection Page =
    def on_btn_back_to_start_clicked(self, btn):
        self.stack.set_visible_child_name("start")

    def on_btn_select_usb_clicked(self, btn):
        self.model.usb = self.cmb_current_usb

        self.load_eba_website()
        self.window_webview.show_all()

    # = Eba Web Page =
    def on_webview_load_changed(self, webview, load_event):
        if load_event == WebKit2.LoadEvent.FINISHED:
            self.webview_stack.set_visible_child_name("webview")
            url = webview.get_uri()

            # Make user login in EBA and return and API address with token to fetch information
            # e.g. url: http://api.etap.org.tr/v1/webhooks/anahtar?token=TOKEN-UUID
            if "api" in url and "token=" in url:
                self.stack.set_visible_child_name("spinner")
                self.window_webview.hide()

                # Got token:
                self.model.url = url
                self.model.token = url.split("token=")[1].strip()
                print("token=", self.model.token)

                task = Gio.Task()
                task.run_in_thread(self.get_ogretmen_info)

    def on_window_webview_delete_event(self, window, event):
        window.hide()

        return True  # Return true to prevent deleting the window

    # = Credentials Page =
    def on_btn_register_usb_clicked(self, btn):
        if self.entry_password.get_text() != self.entry_password_again.get_text():
            Dialogs.info("Uyarı", "Parolalar aynı değil.")
            return

        if self.entry_password.get_text() == "":
            Dialogs.info("Uyarı", "Parola boş olamaz.")
            return

        text = """Yazdığınız kullanıcı adı ve parola bilgisiyle bu <b>tahta üzerinde bir hesap oluşturulacaktır.</b>

USB Belleğiniz olmadan da hesabınıza erişebilmek için <b>parolanızı not etmeyi</b> unutmayınız.

Hesabınız EBA'ya kaydedilecektir, USB belleği kullanarak hesabınıza giriş yapabilirsiniz.
        """
        text = text.format(self.model.username, self.entry_password.get_text())

        response = Dialogs.ask("Emin misiniz?", text, use_markup=True)
        if response == Gtk.ResponseType.OK:
            register_result = self.register_usb()
            if register_result:
                self.stack.set_visible_child_name("start")

    def on_btn_generate_password_clicked(self, btn):
        password = CredentialsManager.generate_random_password()
        self.entry_password.set_text(password)

    def on_entry_password_icon_release(self, entry, icon_pos, event):
        state = entry.get_visibility()

        entry.set_visibility(not state)
        self.entry_password_again.set_visibility(not state)

        new_icon = "view-reveal-symbolic" if state else "view-conceal-symbolic"
        entry.set_icon_from_icon_name(1, new_icon)

    # About Window
    def on_btn_about_clicked(self, btn):
        self.dialog_about.run()
        self.dialog_about.hide()
