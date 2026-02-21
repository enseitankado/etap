import qrcode
from io import BytesIO
import socket
import json
import sys
import time

import threading

from unix_socket_service import UnixSocketService

import gi
import os

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, GLib, GdkPixbuf

SOCK_PATH = "/run/etap/qr-trigger"
# FALLBACK_QR_ID = {"qrId":"0f51d96d-f870-4fb1-88ce-d5da3e8371e9"}
FALLBACK_QR_ID = None


class QrWidget:
    def __init__(self):
        self.img = Gtk.Image()
        self.label = Gtk.Label()
        self.label_msg = Gtk.Label()
        self.progressbar = Gtk.ProgressBar()
        self.timeout_handler = None
        self.data = None

        busdir = "/var/lib/lightdm/"
        self.listener = UnixSocketService("/{}/ebaqr".format(busdir))
        self.listener.event = self.listen_event
        th = threading.Thread(target=self.listener.run)
        th.start()

        # Progress bar styles
        css_provider = Gtk.CssProvider()
        css = b"""
        progressbar > trough > progress {
            background-color: lightgreen;
            min-height: 10px;
        }
        """
        css_provider.load_from_data(css)
        self.progressbar.get_style_context().add_provider(
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.time_begin = 0
        self.time_expire = 0
        self._update_qr_ui()
        self.set_qr(FALLBACK_QR_ID)

    def listen_event(self, data):
        if os.path.isfile("/usr/share/eta/eta-qr-login/debug"):
            print(">>>", data, file=sys.stderr)
        if "uuid" not in data:
            data["uuid"] = None
        GLib.idle_add(self.set_qr, data["uuid"])
        GLib.idle_add(self.label.set_label,
                      "Oturum açmak için EBA Mobil uygulamasından bu karekodu okutabilirsiniz.")


        if "action" in data:
            if data["action"] == "timeout":
                if self.timeout_handler:
                    GLib.idle_add(self.timeout_handler)
            elif data["action"] == "failed":
                GLib.idle_add(self.label.set_label,
                    "EBA QR Servisine bağlanılamadı. Lütfen daha sonra tekrar deneyin.")
                if self.fail_handler:
                    GLib.idle_add(self.fail_handler)

        if "expire_at" in data:
            self.time_expire = int(data["expire_at"])
            self.time_begin = time.time()

        if "message" in data:
            GLib.idle_add(self.label_msg.set_label, data["message"])

    def _get_qr_id_from_daemon(self):
        th = threading.Thread(target=self.send_server, args=[{"action": "register"}])
        th.start()

    def send_server(self, data):
        try:
            data["sender"] = "lightdm"
            if os.path.isfile("/usr/share/eta/eta-qr-login/debug"):
                print("<<<", data, file=sys.stderr)
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect(SOCK_PATH)
            s.send(json.dumps(data).encode())

        except Exception as e:
            print("Socket bağlantı hatası:", e, file=sys.stderr)
            GLib.idle_add(self.set_qr, None)
            GLib.idle_add(self.label.set_label, "Qr sistem servisine bağlanırken hata oluştu.")
        finally:
            s.close()

    def set_qr(self, data):
        self.data = data
        if data is None:
            self.img.set_from_icon_name("dialog-error-symbolic", 5)
            self.img.set_pixel_size(256)
            return
        self.img.set_pixel_size(-1)
        qr = qrcode.make(self.data)
        with BytesIO() as output:
            qr.save(output, format="PNG")
            output.seek(0)
            # Create a Gio.MemoryInputStream from the BytesIO object
            memory_stream = Gio.MemoryInputStream.new_from_data(
                output.getvalue(), None)
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream(memory_stream, None)
            self.img.set_from_pixbuf(pixbuf)

    def refresh(self, widget=None):
        GLib.idle_add(self.set_qr, None)
        GLib.idle_add(self.label.set_label, "Qr verisi alınıyor. Lütfen bekleyiniz ...")
        GLib.idle_add(self.label_msg.set_label, "")
        # Get qrId from local service
        self._get_qr_id_from_daemon()

    def _update_qr_ui(self):
        if self.time_expire <= 0 and self.time_begin <= 0:
            GLib.timeout_add(300, self._update_qr_ui)
            return
        cur = (self.time_expire - time.time()) / \
            (self.time_expire - self.time_begin)
        self.progressbar.set_fraction(cur)
        if cur <= 0:
            self.time_expire = 0
            self.time_begin = 0
            if self.timeout_handler:
                self.timeout_handler()
        GLib.timeout_add(300, self._update_qr_ui)
