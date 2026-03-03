import gi
import os
import locale
import etainfo
from ServerGet import ServerGet
from constants import (
    get_city_url,
    get_town_url,
    get_school_url,
    get_check_school_code_url,
    get_school_without_limit,
)
from enums import REQ
from utils import check_info
from logger import logger

gi.require_version("Gtk", "3.0")
gi.require_version("Polkit", "1.0")


from gi.repository import Gtk, GObject, GLib
from locale import gettext as _
from utils import change_path, check_register_button

APPNAME_CODE = "eta-register"
TRANSLATIONS_PATH = "/usr/share/locale/"
locale.bindtextdomain(APPNAME_CODE, TRANSLATIONS_PATH)
locale.textdomain(APPNAME_CODE)
from constants import BACKEND_URL, BACKEND_IP, BACKEND_PORT

cur_path = os.path.dirname(os.path.abspath(__file__))
opr_file = "/opr.py"


class SchoolCode:
    def __init__(self, ctx):
        self.ctx = ctx
        self.window = self.ctx.get_ui("ui_code_box")
        self.server = ServerGet()
        self.server.ServerGet = self.ServerGet
        self.init_ui()

    def init_ui(self):
        self.ctx.ui_check_code_button.connect(
            "clicked", self.on_check_code_button_clicked
        )

    def get_ui(self, object_name: str):
        return self.ctx.gtk_builder.get_object(object_name)

    def on_check_code_button_clicked(self, button):
        code = self.ctx.ui_code_entry.get_text().strip()
        if code and len(code) > 0:
            # Disable button and set waiting message on MainWindow's path label
            self.ctx.ui_check_code_button.set_sensitive(False)
            self.ctx.ui_path_label.set_markup(_("<i>Please wait, checking school code...</i>"))
            self.ctx.ui_path_label.set_visible(True)

            url = get_check_school_code_url(code)
            GLib.idle_add(self.server.get, url, REQ.CHECK_SCHOOL_CODE)
        else:
            # If code is empty, re-enable button (in case it was disabled by a previous orphaned request)
            # and clear path label or set an appropriate message.
            self.ctx.ui_check_code_button.set_sensitive(True)
            # Optionally, provide feedback if the code entry is empty when button is clicked
            self.ctx.ui_path_label.set_markup(_("Please enter a school code to check."))
            self.ctx.ui_path_label.set_visible(True)

    def ServerGet(self, response, request):
        logger.info(f"Request: {request}, Raw Response: {response}")

        # Always re-enable button if it was a school code check attempt
        if request in [REQ.CHECK_SCHOOL_CODE, REQ.GET_CITIES_FOR_CODE, REQ.GET_TOWNS_FOR_CODE]:
            self.ctx.ui_check_code_button.set_sensitive(True)

        if "error" in response.keys() or not isinstance(response, dict):
            error_message = "Invalid response structure from server."
            if isinstance(response, dict):
                error_message = response.get("message", "An unknown error occurred.")
            logger.error(f"Error for request {request}: {error_message} | Response: {response}")
            self.ctx.ui_path_label.set_markup(_("<i>Error: {}</i>").format(error_message))
            self.ctx.ui_path_label.set_visible(True)
            self.ctx.city_id = None; self.ctx.city_name = None
            self.ctx.town_id = None; self.ctx.town_name = None
            self.ctx.school_code = None; self.ctx.school_name = None
            check_register_button(self.ctx)
            return

        # --- Successful responses --- 
        if request == REQ.CHECK_SCHOOL_CODE:
            if response.get("msg_type") == "Warning": # School not found
                self.ctx.ui_path_label.set_label(
                    _("School code doesn't match. Re-enter correct school code.")
                )
                self.ctx.ui_path_label.set_visible(True)
                self.ctx.city_id = None; self.ctx.city_name = None
                self.ctx.town_id = None; self.ctx.town_name = None
                self.ctx.school_code = None; self.ctx.school_name = None
                check_register_button(self.ctx)
                return
            else: # School found (msg_type == "Success")
                data = response.get("data")
                if not data: # Should not happen if Success
                    logger.error(f"REQ.CHECK_SCHOOL_CODE success but no data: {response}")
                    self.ctx.ui_path_label.set_markup(_("<i>Error: Incomplete school data received.</i>"))
                    return
                self.ctx.city_id = data.get("city_id")
                self.ctx.town_id = data.get("town_id")
                self.ctx.school_code = data.get("code")
                self.ctx.school_name = data.get("name")
                
                if not all([self.ctx.city_id, self.ctx.town_id, self.ctx.school_code, self.ctx.school_name]):
                    logger.error(f"Missing critical IDs/Name from REQ.CHECK_SCHOOL_CODE: {data}")
                    self.ctx.ui_path_label.set_markup(_("<i>Error: Incomplete school data from server.</i>"))
                    return

                logger.info("School code found. Fetching cities to get city name.")
                # Path label should still be "Please wait..." set by on_check_code_button_clicked
                url = get_city_url()
                GLib.idle_add(self.server.get, url, REQ.GET_CITIES_FOR_CODE)

        elif request == REQ.GET_CITIES_FOR_CODE:
            self.ctx.cities = response.get("data", [])
            # self.ctx.cities.sort(key=lambda x: locale.strxfrm(x["name"])) # Not strictly needed as not displayed
            
            found_city = next((city for city in self.ctx.cities if city.get("id") == self.ctx.city_id), None)
            if found_city:
                self.ctx.city_name = found_city.get("name")
                logger.info(f"City name found: {self.ctx.city_name}. Fetching towns.")
                url = get_town_url(self.ctx.city_id)
                GLib.idle_add(self.server.get, url, REQ.GET_TOWNS_FOR_CODE)
            else:
                logger.error(f"City ID {self.ctx.city_id} not found in cities list.")
                self.ctx.ui_path_label.set_markup(_("<i>Error: Could not retrieve city details.</i>"))
                self.ctx.city_name = None; self.ctx.town_name = None; # Clear subsequent names
                check_register_button(self.ctx)

        elif request == REQ.GET_TOWNS_FOR_CODE:
            self.ctx.towns = response.get("data", [])
            # self.ctx.towns.sort(key=lambda x: locale.strxfrm(x["name"])) # Not strictly needed

            found_town = next((town for town in self.ctx.towns if town.get("id") == self.ctx.town_id), None)
            if found_town:
                self.ctx.town_name = found_town.get("name")
                logger.info(f"Town name found: {self.ctx.town_name}. Updating UI.")
                change_path(self.ctx) 
                check_register_button(self.ctx)
                # UI does NOT change stack here. Stays on the main page.
            else:
                logger.error(f"Town ID {self.ctx.town_id} not found for city {self.ctx.city_id}.")
                self.ctx.ui_path_label.set_markup(_("<i>Error: Could not retrieve town details.</i>"))
                self.ctx.town_name = None;
                check_register_button(self.ctx)
        
        # NOTE: The old REQ.GET_CITIES, REQ.GET_TOWNS, REQ.GET_SCHOOL_WITHOUT_LIMIT 
        # handlers that switched stacks and populated listboxes are removed from this ServerGet.
        # That functionality, if used by "Register with Selecting", must be handled by MainWindow.py's own ServerGet.
