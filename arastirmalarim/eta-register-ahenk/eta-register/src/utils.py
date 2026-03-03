import gi
import os
import opr
import threading
import time
import constants as const
import requests
import locale
import unicodedata
from logger import logger

default_time_sleep = 2
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
from locale import gettext as _

APPNAME_CODE = "eta-register"
TRANSLATIONS_PATH = "/usr/share/locale/"
locale.bindtextdomain(APPNAME_CODE, TRANSLATIONS_PATH)
locale.textdomain(APPNAME_CODE)
usb_vendor_path = "/sys/bus/usb/devices"

REQUEST_TIMEOUT = 10  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


def check_network_connection():
    url = const.get_check_connection_url()
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                url, headers=const.secure_connection_header, timeout=REQUEST_TIMEOUT
            )
            return response.status_code == 200
        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt == MAX_RETRIES - 1:
                logger.error(
                    _("Network connection failed after {} attempts: {}").format(
                        MAX_RETRIES, str(e)
                    )
                )
                return False
            time.sleep(RETRY_DELAY)
    return False


def asynchronous(func):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread

    return wrapper


def find_city_name(self):
    city_name = None

    def find_cn(objs):
        if self.city_id:
            return objs.get("id") == self.city_id

    if self.city_id:
        city_name = list(filter(find_cn, self.searched_cities))[0]["name"]
    return city_name


def find_town_name(self):
    town_name = None

    def find_tn(objs):
        if self.town_id:
            return objs.get("id") == self.town_id

    if self.town_id:
        town_name = list(filter(find_tn, self.searched_towns))[0]["name"]
    return town_name


def find_school_name(self):
    school_name = None

    def find_sn(objs):
        if self.school_code:
            return objs.get("code") == self.school_code

    if self.school_code:
        school_name = list(filter(find_sn, self.searched_schools))[0]["name"]
    return school_name


def change_path(window):
    path_parts = []
    if window.city_name:
        path_parts.append(window.city_name)
    if window.town_name:
        if window.city_name:
            path_parts.append(window.town_name)
    if window.school_name:
        if window.city_name and window.town_name:
            path_parts.append(window.school_name)

    if path_parts:
        path_text = _("Current Selection: {}").format(" > ".join(path_parts))
        window.ui_path_label.set_markup(path_text)
        window.ui_path_label.set_visible(True)
    else:
        window.ui_path_label.set_visible(False)


def check_register_button(self):
    self.ui_register_button.set_sensitive(
        self.city_id and self.town_id and self.school_code
    )


def check_args(self):
    usr = GLib.get_user_name()
    if usr != "etapadmin":
        logger.warning(_("User is not etapadmin. Exiting..."))
        Gtk.main_quit()
        return
    if "control" in self.args.keys():
        logger.info(_("Control arg found."))
        logger.info(_("Checking network connection..."))

        # Define retry intervals in seconds for -c parameter
        retry_intervals = [0, 60, 180, 600]  # 0s, 1min, 3min, 10min
        max_attempts = 4

        for attempt in range(max_attempts):
            logger.info(_("Network connection check attempt {}").format(attempt + 1))
            network_status = check_network_connection()

            if network_status:
                logger.info(_("Network connection is OK."))
                logger.info(_("Checking if device is registered..."))
                check_mac_url = const.get_check_mac_url()
                try:
                    response = requests.get(
                        check_mac_url,
                        headers=const.secure_connection_header,
                        timeout=REQUEST_TIMEOUT,
                    )
                    register_state = response.json()

                    logger.info(
                        _("Registration state response: {}").format(register_state)
                    )

                    # First check if device is registered (either registered or registered_ip)
                    is_registered = register_state.get("registered", False)
                    is_ip_registered = register_state.get("registered_ip", False)

                    # Check if Ahenk is installed
                    ahenk_installed = opr.is_ahenk_installed()

                    # If board is properly registered AND Ahenk is installed, exit application
                    if is_registered and ahenk_installed:
                        logger.info(
                            _("Device is already registered and Ahenk is installed.")
                        )
                        logger.info(_("Exiting..."))
                        Gtk.main_quit()
                        return

                    # If IP is registered but board is not, we should continue to show quick register screen
                    if is_ip_registered and not is_registered:
                        logger.info(
                            _(
                                "IP is registered but board is not. Showing quick register."
                            )
                        )
                        self.activate()
                        return

                    # If not registered or Ahenk not installed, continue normal flow
                    logger.info(
                        _("Device is not registered or Ahenk is not installed.")
                    )
                    logger.info(
                        _("Registration state: {}, Ahenk installed: {}").format(
                            is_registered, ahenk_installed
                        )
                    )
                    logger.info(_("Follow on screen instructions."))
                    self.activate()

                except (requests.ConnectionError, requests.Timeout) as e:
                    logger.error(
                        _("Error checking device registration: {}").format(str(e))
                    )
                    dialog = no_internet_dialog()
                    dialog_response = dialog.run()
                    if dialog_response:
                        dialog.destroy()
                        Gtk.main_quit()
                return  # Exit the function if we get here

            elif attempt < max_attempts - 1:  # If we haven't tried all attempts yet
                next_interval = retry_intervals[attempt + 1]
                logger.info(
                    _("Network connection failed. Next attempt in {} seconds").format(
                        next_interval
                    )
                )
                time.sleep(next_interval)
            else:  # All attempts failed
                logger.error(_("No network connection after all attempts."))
                Gtk.main_quit()
    else:
        logger.info(_("Control arg not found..."))
        logger.info(_("Starting application..."))
        self.activate()


def no_internet_dialog():
    dialog = Gtk.MessageDialog(
        parent=None,
        flags=0,
        message_type=Gtk.MessageType.WARNING,
        buttons=Gtk.ButtonsType.OK,
        text=_("🚫 Error! ⚠️"),
    )
    dialog.format_secondary_text(
        _("Cannot connect to internet. Check your network connections!")
    )
    return dialog


def sys_usb_vendors():
    arr = []
    for root, dirs, files in os.walk(usb_vendor_path):
        for dir in dirs:
            id_vendor_path = os.path.join(root, dir, "idVendor")
            if os.path.isfile(id_vendor_path):
                with open(id_vendor_path) as f:
                    line = f.readline().strip()
                    arr.append(int(line, base=16))
    return arr


def update_school_buttons(self):
    self.ui_prev_school_button.set_sensitive(self.school_page > 0)
    self.ui_next_school_button.set_sensitive(
        self.school_page + 1 < self.school_max_page
    )


def check_info(self):
    if self:
        self.ui_register_button.set_sensitive(
            self.city_id and self.town_id and self.school_code
        )


def get_real_ip():
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                "https://pardus.org.tr/ip.php?V1", timeout=REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                return response.text
        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt == MAX_RETRIES - 1:
                logger.error(
                    _("Failed to get real IP after {} attempts: {}").format(
                        MAX_RETRIES, str(e)
                    )
                )
                return "Not Available"
            time.sleep(RETRY_DELAY)
    return "Not Available"
