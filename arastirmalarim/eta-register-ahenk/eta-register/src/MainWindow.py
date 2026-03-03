# Set up localization
import locale
import etainfo.network
import gi
import os
import opr
import std_opr
import constants as const
from enums import REQ
import time
from logger import logger
import sys
import json

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, GObject

from utils import (
    no_internet_dialog,
    change_path,
    check_info,
    check_register_button,
)
from ServerGet import ServerGet
from ServerPost import ServerPost
from SchoolCode import SchoolCode
import unicodedata

APPNAME_CODE = "eta-register"
TRANSLATIONS_PATH = "/usr/share/locale/"
locale.bindtextdomain(APPNAME_CODE, TRANSLATIONS_PATH)
locale.textdomain(APPNAME_CODE)
from locale import gettext as _


cur_path = os.path.dirname(os.path.abspath(__file__))
opr_file = "/opr.py"


class MainWindow(object):
    def __init__(self, application):
        self.ui_interface_file = os.path.dirname(__file__) + "/../ui/ui.glade"
        try:
            self.gtk_builder = Gtk.Builder.new_from_file(self.ui_interface_file)
            self.gtk_builder.connect_signals(self)
        except GObject.GError:
            logger.error("Error while creating user interface from glade file")
            return False

        self.server_get = ServerGet()
        self.server_get.ServerGet = self.ServerGet
        self.server_post = ServerPost()
        self.server_post.ServerPost = self.ServerPost
        self.application = application
        self.registered_board_id = None

        # Add request tracking
        self._pending_requests = set()
        self._is_closing = False

        self.city_name = None
        self.town_name = None
        self.school_name = None
        self.city_id = None
        self.town_id = None
        self.unit_name = None
        self.school_code = None
        self.network_device = etainfo.network.get()
        self.cities = []
        self.searched_cities = []
        self.school_search_text = ""
        self.schools = []
        self.searched_schools = []
        self.board_register_state = False

        self.init_ui()

    def get_ui(self, object_name: str):
        return self.gtk_builder.get_object(object_name)

    def register_board(self, button):
        logger.info("register_board function called")
        txt = ""
        txt += f"{_('City')}: {self.find_city_name(self.city_id)}\n"
        txt += f"{_('Town')}: {self.find_town_name(self.town_id)}\n"
        txt += f"{_('School')}: {self.find_school_name(self.school_code)}\n"
        txt += f"{_('Mac')}: {self.network_device.mac}\n"
        if self.unit_name and len(self.unit_name) > 0:
            txt += f"{_('Unit Name')}: {self.unit_name}"
        self.ui_register_info_label.set_markup(txt)
        GLib.idle_add(self.switch_main_stack, None, "confirm")
        # After registration, restore the board_register_state if there was a previous registration
        if "data" in self.board_state.keys() and self.board_state.get(
            "registered", False
        ):
            self.board_register_state = True
        # self.switch_main_stack(None, "confirm")

    def on_destroy(self, *args):
        logger.info("on_destroy function called")
        self._is_closing = True
        # Cancel any pending requests
        for request in self._pending_requests.copy():
            try:
                request.cancel()
            except:
                pass
        self._pending_requests.clear()
        Gtk.main_quit()

    def safe_request(self, func, *args):
        if self._is_closing:
            return

        # Generate a unique request ID based on the function and its arguments
        request_id = f"{id(func)}_{args}"
        logger.info(f"Making request with ID: {request_id}")

        # If this exact request is already pending, don't make it again
        if request_id in self._pending_requests:
            logger.info(f"Request {request_id} already pending, skipping")
            return

        self._pending_requests.add(request_id)
        logger.info(f"Added request {request_id} to pending requests")

        def wrapped_func(*wrapped_args):
            if not self._is_closing:
                try:
                    logger.info(f"Executing request {request_id}")
                    result = func(*wrapped_args)
                    return result
                except Exception as e:
                    logger.error(f"Request {request_id} failed: {str(e)}")
                    return None
                finally:
                    # Always remove the request from pending, regardless of success or failure
                    if request_id in self._pending_requests:
                        logger.info(
                            f"Removing request {request_id} from pending requests"
                        )
                        self._pending_requests.remove(request_id)
            return None

        GLib.idle_add(wrapped_func, *args)
        return True

    def on_confirm_cancel_button_clicked(self, button):
        logger.info("on_confirm_cancel_button_clicked function called")
        GLib.idle_add(self.switch_main_stack, None, "main")

    def on_school_search_button_clicked(self, button):
        logger.info("on_school_search_button_clicked function called")
        self.school_page = 0
        self.get_school_url = const.get_school_url(
            self.city_id, self.town_id, self.school_page, self.school_search_text
        )
        self.safe_request(self.server_get.get, self.get_school_url, REQ.GET_SCHOOLS)

    def on_register_selection_clicked(self, button, widget):
        logger.info("on_register_selection_clicked function called")
        if widget == self.ui_selection_box:
            self.get_city_url = const.get_city_url()
            self.safe_request(self.server_get.get, self.get_city_url, REQ.GET_CITIES)
        self.ui_register_selection_stack.set_visible_child(widget)
        self.create_listbox_rows(self.searched_schools, self.ui_school_listbox, is_school=True)
        self.ui_main_window.show_all()

    def on_city_selected(self, action, name):
        logger.info("on_city_selected function called")
        if name: # A row is selected
            city_index = name.get_index()
            new_city_id = self.searched_cities[city_index]["id"]
            new_city_name = self.searched_cities[city_index]["name"]

            # Always clear town and school when a new city is effectively chosen
            self.town_id = None
            self.town_name = None
            self.school_code = None
            self.school_name = None

            self.city_id = new_city_id
            self.city_name = new_city_name
            
            self.get_town_url = const.get_town_url(self.city_id)
            change_path(self) # Update path label to show only city
            self.ui_register_button.set_sensitive(False)
            self.safe_request(self.server_get.get, self.get_town_url, REQ.GET_TOWNS)

    def on_city_search_changed(self, entry):
        self.city_search_text = entry.get_text().strip().lower()
        text = self.remove_turkish_chars(self.city_search_text.lower())
        self.searched_cities = [
            city
            for city in self.cities
            if text in self.remove_turkish_chars(city["name"].lower())
        ]
        self.create_listbox_rows(self.searched_cities, self.ui_city_listbox)
        self.ui_main_window.show_all()

    def on_listbox_item_activated(self, listbox, event):
        row = listbox.get_row_at_y(int(event.y))
        if row:
            if listbox.get_selected_row() != row:
                # If a different row is pressed, select it. 
                # This will naturally fire the 'row-selected' signal and call the specific on_..._selected handler.
                listbox.select_row(row) 
            else:
                # Row is already selected, 'row-selected' might not fire again for a simple tap.
                # Manually trigger the action associated with selection for the specific listbox.
                logger.info(f"Re-activating already selected row in listbox: {listbox.get_name()} - Row: {row.get_child().get_label()}")
                if listbox is self.ui_city_listbox:
                    self.on_city_selected(listbox, row)
                elif listbox is self.ui_town_listbox:
                    self.on_town_selected(listbox, row)
                elif listbox is self.ui_school_listbox:
                    self.on_school_selected(listbox, row)
        return False # Allow other handlers to process the event if necessary

    def remove_turkish_chars(self, text):
        text = unicodedata.normalize("NFD", text)
        text = text.encode("ascii", "ignore").decode("utf-8")
        return text

    def on_town_selected(self, action, name):
        logger.info("on_town_selected function called")
        if name:
            town_index = name.get_index()
            # Only reset school_code if the selected town is different
            if self.town_id != self.searched_towns[town_index]["id"]:
                if self.school_code:
                    self.school_code = None
                    self.school_name = None

            self.town_id = self.searched_towns[town_index]["id"]
            self.town_name = self.searched_towns[town_index]["name"]
            change_path(self)
            self.ui_register_button.set_sensitive(False)
            url = const.get_school_without_limit(self.city_id, self.town_id)
            self.safe_request(self.server_get.get, url, REQ.GET_SCHOOLS)

    def on_town_search_changed(self, entry):
        self.town_search_text = entry.get_text().strip().lower()
        text = self.remove_turkish_chars(self.town_search_text.lower())
        self.searched_towns = [
            town
            for town in self.towns
            if text in self.remove_turkish_chars(town["name"].lower())
        ]
        self.create_listbox_rows(self.searched_towns, self.ui_town_listbox)
        self.ui_main_window.show_all()

    def on_school_selected(self, action, name):
        logger.info("on_school_selected function called")
        if name:
            index = name.get_index()
            school = self.searched_schools[index]
            self.school_code = school["code"]
            self.school_name = school["name"]
            change_path(self)
            check_info(self)

    def on_school_search_changed(self, entry):
        self.school_search_text = entry.get_text().strip().lower()
        text_to_search = self.remove_turkish_chars(self.school_search_text)
        if not self.schools: # Guard against empty list before filtering
            self.searched_schools = []
        else:
            self.searched_schools = [
                school
                for school in self.schools
                if text_to_search in self.remove_turkish_chars(school["name"].lower())
            ]
        self.create_listbox_rows(self.searched_schools, self.ui_school_listbox, is_school=True)
        self.ui_main_window.show_all()

    def on_prev_next_btn_clicked(self, button, type):
        logger.info(f"on_prev_next_btn_clicked function called with type: {type}")
        if type == "prev":
            self.school_page -= 1
        elif type == "next":
            self.school_page += 1
        self.update_school_buttons()
        if self.school_page >= 0 or self.school_page <= self.school_max_page:
            self.get_school_url = const.get_school_url(
                self.city_id, self.town_id, self.school_page, self.school_search_text
            )
            self.safe_request(self.server_get.get, self.get_school_url, REQ.GET_SCHOOLS)

    def on_confirm_ok_button_clicked(self, button):
        logger.info("on_confirm_ok_button_clicked function called")
        # Explicitly set values from board_state if not already set
        if self.board_state and "data" in self.board_state:
            data = self.board_state["data"]
            logger.info(f"DEBUG: City Name: {self.city_name}")
            logger.info(f"DEBUG: Town Name: {self.town_name}")
            logger.info(f"DEBUG: School Name: {self.school_name}")
            logger.info(f"DEBUG: Unit Name: {self.unit_name}")
            logger.info(f"DEBUG: Board ID: {data.get('id')}")
            logger.info(f"DEBUG: School Code: {data.get('school_code')}")
            logger.info(f"DEBUG: MAC ID: {data.get('mac_id')}")
            logger.info(f"DEBUG: Board State: {self.board_state}")

            # Set city details
            if not self.city_id:
                self.city_id = data.get("city_id")
            if not self.city_name:
                self.city_name = data.get("city_name")

            # Set town details
            if not self.town_id:
                self.town_id = data.get("town_id")
            if not self.town_name:
                self.town_name = data.get("town_name")

            # Set school details
            if not self.school_code:
                self.school_code = data.get("school_code")
            if not self.school_name:
                self.school_name = data.get("school_name")

        # Fallback to find methods if names are still None
        if not self.city_name and self.city_id:
            self.city_name = self.find_city_name(self.city_id)

        if not self.town_name and self.town_id:
            self.town_name = self.find_town_name(self.town_id)

        if not self.school_name and self.school_code:
            self.school_name = self.find_school_name(self.school_code)

        # Debug print
        logger.info(f"DEBUG: City Name: {self.city_name}")
        logger.info(f"DEBUG: Town Name: {self.town_name}")
        logger.info(f"DEBUG: School Name: {self.school_name}")

        # Prepare markup for confirm page
        print("#########################")
        print("#########################")
        print("#########################")
        print("#########################")
        print(self.unit_name)
        print("#########################")
        print("#########################")
        print("#########################")
        print("#########################")
        markup = (
            "<b>"
            + _("City:")
            + "</b> "
            + (self.city_name or _("Not Selected"))
            + "\n"
            + "<b>"
            + _("Town:")
            + "</b> "
            + (self.town_name or _("Not Selected"))
            + "\n"
            + "<b>"
            + _("School:")
            + "</b> "
            + (self.school_name or _("Not Selected"))
            + "\n"
            + "<b>"
            + _("Unit:")
            + "</b> "
            + (self.unit_name or _("Not Entered"))
        )

        # Update confirm page label
        self.ui_register_info_label.set_markup(markup)

        GLib.idle_add(self.switch_main_stack, None, "spinner")
        self.ui_status_label.set_text(_("Registering board. Please wait"))

        def process_workflow(success, error_msg=None):
            # If operation fails, show connection error dialog and exit
            if not success:
                dialog = Gtk.MessageDialog(
                    parent=self.ui_main_window,
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text=_("Connection Error"),
                )
                dialog.format_secondary_text(
                    _(
                        "Unable to connect to the backend service. Please check your network connection."
                    )
                )
                dialog.run()
                dialog.destroy()

                # Exit the application
                self.application.quit()
                return

            # Successful registration
            dialog = Gtk.MessageDialog(
                parent=self.ui_main_window,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=_("Success"),
            )
            dialog.format_secondary_text(_("Board registered successfully"))
            dialog.run()
            dialog.destroy()

            # Quit application
            self.application.quit()

        # Single command for registration or update
        if self.registered_board_id:
            cmd = [
                "/usr/bin/pkexec",
                cur_path + opr_file,
                "update-board",
                str(self.school_code),
                str(self.registered_board_id),
                str(self.unit_name) if self.unit_name is not None else "",
            ]
        else:
            cmd = [
                "/usr/bin/pkexec",
                cur_path + opr_file,
                "register-board",
                str(self.city_id),
                str(self.town_id),
                str(self.school_code),
                str(self.unit_name) if self.unit_name is not None else "",
            ]

        logger.info(f"DEBUG: Final Command: {cmd}")
        # Single process start with simplified callback
        std_opr.start_prc(self, cmd, process_workflow)

    def show_workflow_result_dialog(self, is_success, message):
        # Determine dialog type based on success/failure
        message_type = Gtk.MessageType.INFO if is_success else Gtk.MessageType.ERROR

        # Create dialog
        dialog = Gtk.MessageDialog(
            parent=self.ui_main_window,  # Use ui_main_window instead of window
            flags=0,
            message_type=message_type,
            buttons=Gtk.ButtonsType.OK,
            text=_("Success") if is_success else _("Error"),
        )
        dialog.format_secondary_text(message)

        # Run dialog
        dialog.run()
        dialog.destroy()

        # Switch to appropriate stack based on success/failure
        stack = "registered" if is_success else "uncompleted"
        GLib.idle_add(self.switch_main_stack, None, stack)
        if is_success:
            self.application.quit()

    def switch_main_stack(self, button, stack):
        logger.info(f"switch_main_stack function called with stack: {stack}")
        stacks = {
            "main": self.ui_main_page,
            "confirm": self.ui_confirm_page,
            "spinner": self.ui_spinner_page,
            "registered": self.ui_registered_page,
            "uncompleted": self.ui_uncompleted_page,
            "quick": self.ui_quick_register_page,
        }
        self.ui_main_stack.set_visible_child(stacks[stack])
        self.ui_main_window.show_all()

    def on_edit_board_button_clicked(self, button):
        logger.info("on_edit_board_button_clicked function called")

        if "data" in self.board_state.keys():
            data = self.board_state["data"]
            registration_text = _("Already registered: {} > {} > {}").format(
                data["city_name"], data["town_name"], data["school_name"]
            )

            # Pre-populate the values from board state
            self.city_id = data["city_id"]
            self.city_name = data["city_name"]
            self.town_id = data["town_id"]
            self.town_name = data["town_name"]
            self.school_code = data["school_code"]
            self.school_name = data["school_name"]
            self.unit_name = data["unit_name"]

            if self.unit_name:
                self.ui_unit_save_entry.set_text(self.unit_name)

            # Set the values in the listboxes and ensure they are selected
            city_data = [{"id": self.city_id, "name": self.city_name}]
            town_data = [{"id": self.town_id, "name": self.town_name}]
            school_data = [{"code": self.school_code, "name": self.school_name}]

            self.searched_cities = city_data
            self.searched_towns = town_data
            self.searched_schools = school_data

            self.create_listbox_rows(city_data, self.ui_city_listbox)
            self.create_listbox_rows(town_data, self.ui_town_listbox)
            self.create_listbox_rows(school_data, self.ui_school_listbox, True)

            # Select the first row in each listbox to trigger the selection events
            if self.ui_city_listbox.get_children():
                self.ui_city_listbox.select_row(self.ui_city_listbox.get_children()[0])
            if self.ui_town_listbox.get_children():
                self.ui_town_listbox.select_row(self.ui_town_listbox.get_children()[0])
            if self.ui_school_listbox.get_children():
                self.ui_school_listbox.select_row(
                    self.ui_school_listbox.get_children()[0]
                )

            # Enable the register button since we have all required values
            self.ui_register_button.set_sensitive(True)

        self.ui_path_label.set_visible(True)
        self.ui_path_label.show()
        self.ui_main_window.show_all()

        if button:
            GLib.idle_add(self.switch_main_stack, None, "main")

        # Make these requests regardless of the board register state so we can edit the selection
        url = const.get_city_url()
        self.safe_request(self.server_get.get, url, REQ.GET_CITIES)
        url = const.get_town_url(self.city_id)
        self.safe_request(self.server_get.get, url, REQ.GET_TOWNS)
        url = const.get_school_without_limit(self.city_id, self.town_id)
        self.safe_request(self.server_get.get, url, REQ.GET_SCHOOLS)

        # Temporarily set board_register_state to False during editing
        self.board_register_state = False
        check_register_button(self)

    def create_listbox_rows(self, searched_data, listbox, is_school=False):
        self.clean_listbox(listbox)
        tmp_data = searched_data
        for item in tmp_data:
            label = Gtk.Label(label=item["name"])
            label.set_xalign(0)
            listboxrow = Gtk.ListBoxRow()
            listboxrow.add(label)
            listbox.add(listboxrow)
        self.ui_main_window.show_all()

    def clean_listbox(self, listbox):
        children = listbox.get_children()
        for child in children:
            listbox.remove(child)

    def update_school_buttons(self):
        self.ui_prev_school_button.set_sensitive(self.school_page > 0)
        self.ui_next_school_button.set_sensitive(
            self.school_page + 1 < self.school_max_page
        )

    def control_check(self):
        self.ui_main_window.show_all()
        self.ui_status_label.set_text(_("Checking your internet connection."))
        self.switch_main_stack(None, "spinner")
        self.check_connection_url = const.get_check_connection_url()
        self.safe_request(
            self.server_get.get, self.check_connection_url, REQ.CHECK_CONNECTION
        )

    def on_retry_button_clicked(self, button):
        logger.info("on_retry_button_clicked function called")
        data = self.board_state["data"]
        txt = _("Are you sure? \n")
        txt += f"{_('City')}: {data['city_name']}\n"
        txt += f"{_('Town')}: {data['town_name']}\n"
        txt += f"{_('School')}: {data['school_name']}\n"
        txt += f"{_('Mac')}: {self.network_device.mac}\n"
        if self.unit_name and len(self.unit_name) > 0:
            txt += f"{_('Unit')}: {self.unit_name}"
        self.ui_register_info_label.set_markup(txt)
        GLib.idle_add(self.switch_main_stack, None, "main")

    def check_state(self):
        self.ui_register_button.set_sensitive(not self.board_register_state)

    def ServerGet(self, response, request):
        # Handle connection errors
        if "error" in response.keys():
            if request == REQ.CHECK_CONNECTION:
                self.ui_status_label.set_text(_("No internet connection."))
                dialog = no_internet_dialog()
                dialog_response = dialog.run()
                if dialog_response:
                    dialog.destroy()
                    self.application.quit()
                return
            elif request == REQ.CHECK_MAC:
                # For MAC check errors, just set unregistered state and continue
                self.board_state = response
                self.board_register_state = False
                self.board_ip_state = False
                self.ui_path_label.set_text(
                    _("Device is not registered. Please register your device.")
                )
                self.ui_path_label.set_visible(True)
                self.ui_path_label.show()
                GLib.idle_add(self.switch_main_stack, None, "main")
                return

        if request == REQ.CHECK_CONNECTION:
            logger.info("Connection check successful, proceeding to MAC check")
            self.ui_status_label.set_text(_("Checking your board."))
            self.check_mac_url = const.get_check_mac_url()
            # Create a request ID for the MAC check
            mac_check_id = (
                f"{id(self.server_get.get)}_{(self.check_mac_url, REQ.CHECK_MAC)}"
            )
            logger.info(f"MAC check request ID: {mac_check_id}")
            logger.info(f"Pending requests: {self._pending_requests}")

            # Only make the MAC check request if we haven't already
            if mac_check_id not in self._pending_requests:
                logger.info("Making MAC check request")
                self.safe_request(
                    self.server_get.get, self.check_mac_url, REQ.CHECK_MAC
                )
            else:
                logger.info("MAC check request already pending, skipping")

        elif request == REQ.CHECK_MAC:
            self.board_state = response
            logger.info(self.board_state)

            # Store registered and registered_ip states
            is_registered = response.get("registered", False)
            is_ip_registered = response.get("registered_ip", False)
            self.board_register_state = is_registered
            self.board_ip_state = is_ip_registered

            # Handle 'no registration' case - neither board nor IP registered
            if not is_registered and not is_ip_registered:
                self.ui_path_label.set_text(
                    _("Device is not registered. Please register your device.")
                )
                GLib.idle_add(
                    self.ui_path_label.set_text,
                    _("Device is not registered. Please register your device."),
                )
                self.ui_path_label.set_visible(True)
                self.ui_path_label.show()
                GLib.idle_add(self.switch_main_stack, None, "main")

                return

            # Handle case where board is registered
            if is_registered:
                # Update path label with registration info
                if "data" in response:
                    data = response["data"]
                    registration_text = _(
                        "<b>Already registered:</b> {} > {} > {}"
                    ).format(data["city_name"], data["town_name"], data["school_name"])
                    self.ui_path_label.set_markup(registration_text)
                else:
                    self.ui_path_label.set_text(_("Device is already registered."))
                    self.ui_path_label.set_visible(True)
                    self.ui_path_label.show()

                if opr.is_ahenk_installed():
                    data = self.board_state["data"]
                    self.registered_board_id = data["board_id"]
                    self.city_id = data["city_id"]
                    self.city_name = data["city_name"]
                    self.town_id = data["town_id"]
                    self.town_name = data["town_name"]
                    self.school_code = data["school_code"]
                    self.school_name = data["school_name"]
                    self.unit_name = data["unit_name"]

                    # Set unit save entry to unit_name if present
                    if self.unit_name:
                        self.ui_unit_save_entry.set_text(self.unit_name)

                    markup = (
                        "<b>"
                        + _(
                            "Your board is already registered with the following information:"
                        )
                        + "</b>"
                        + "\n"
                        + "<b>"
                        + _("City:")
                        + "</b>"
                        + f" {self.city_name}\n"
                        + "<b>"
                        + _("Town:")
                        + "</b>"
                        + f" {self.town_name}\n"
                        + "<b>"
                        + _("School:")
                        + "</b>"
                        + f" {self.school_name}\n"
                    )

                    # Only add unit line if unit_name exists
                    if self.unit_name:
                        markup += "<b>" + _("Unit:") + "</b>" + f" {self.unit_name}\n"

                    self.ui_registered_info.set_markup(markup)
                    GLib.idle_add(self.switch_main_stack, None, "registered")
                else:
                    GLib.idle_add(self.switch_main_stack, None, "uncompleted")

            # Handle case where IP is registered but board is not
            elif is_ip_registered and not is_registered:
                # Extract data from the response
                data = self.board_state["data"]

                # Pre-populate fields for quick registration
                self.city_id = data.get("city_id")
                self.city_name = data.get("city_name")
                self.town_id = data.get("town_id")
                self.town_name = data.get("town_name")
                self.school_code = data.get("school_code")
                self.school_name = data.get("school_name")
                self.unit_name = data.get("unit_name", "")

                # Set unit save entry if unit_name is available
                if self.unit_name:
                    self.ui_unit_save_entry.set_text(self.unit_name)

                # Prepare markup for quick register info label
                markup = (
                    "<b>"
                    + _("City:")
                    + "</b>"
                    + f" {self.city_name}\n"
                    + "<b>"
                    + _("Town:")
                    + "</b>"
                    + f" {self.town_name}\n"
                "<b>" + _("School:") + "</b>" + f" {self.school_name}\n"
                )

                # Only add unit line if unit_name exists
                if self.unit_name:
                    markup += "<b>" + _("Unit:") + "</b>" + f" {self.unit_name}\n"

                self.ui_quick_register_info_label.set_markup(markup)
                GLib.idle_add(self.switch_main_stack, None, "quick")
            else:
                # Fallback case - should not occur but handle gracefully
                self.ui_path_label.set_text(
                    _(
                        "Your board is not registed on the system. Please register your board."
                    )
                )
                GLib.idle_add(self.switch_main_stack, None, "main")
                self.get_city_url = const.get_city_url()
                self.safe_request(
                    self.server_get.get, self.get_city_url, REQ.GET_CITIES
                )

        elif request == REQ.GET_CITIES:
            if "data" in response.keys():
                self.cities = response["data"]
                self.cities.sort(key=lambda x: locale.strxfrm(x["name"]))
            else:
                self.cities = [] # Ensure self.cities is a list
            self.searched_cities = self.cities
            self.create_listbox_rows(self.searched_cities, self.ui_city_listbox)
            self.switch_selection_stacks(None, "city")
            self.ui_main_window.show_all()
        elif request == REQ.GET_TOWNS:
            if "data" in response.keys():
                self.towns = response["data"]
                self.towns.sort(key=lambda x: locale.strxfrm(x["name"]))
            else:
                self.towns = [] # Ensure self.towns is a list
            self.searched_towns = self.towns
            self.create_listbox_rows(self.searched_towns, self.ui_town_listbox)
            self.switch_selection_stacks(None, "town")
            self.ui_main_window.show_all()
        elif request == REQ.GET_SCHOOLS:
            if "error" in response.keys() or ("message" in response.keys() and response["message"] != "OK") : # Keep error checking, adjust if necessary for new API
                logger.error(f"Error fetching schools: {response.get('error', response.get('message'))}")
                self.schools = [] # Clear schools on error
            else:
                # Assuming response is directly the list of schools from the new API
                # If the new API still returns { "data": [...] }, then it should be response["data"]
                self.schools = response if isinstance(response, list) else response.get("data", [])
                if isinstance(self.schools, list): # Ensure it's a list before sorting
                    self.schools.sort(key=lambda x: locale.strxfrm(x["name"]))
                else: # Should not happen if API is consistent, but good to guard
                    self.schools = []
            
            self.searched_schools = self.schools[:] # Make a copy for searching
            self.create_listbox_rows(
                self.searched_schools, self.ui_school_listbox, True
            )
            # self.update_school_buttons() # Remove this call
            self.ui_main_window.show_all()
            self.switch_selection_stacks(None, "school")

    def ServerPost(self, status_code, data, type):
        if type == REQ.REGISTER_BOARD or type == REQ.UPDATE_BOARD:
            logger.info(data, status_code)
            if data["msg_type"] == "Success":
                self.ui_status_label.set_text(
                    _("Board has been successfully registered.")
                )
                # Update the board_register_state to reflect the new registration status
                self.board_register_state = True
                self.ui_status_label.set_text(_("Installing Ahenk with dependencies."))
                cmd = ["/usr/bin/pkexec", cur_path + opr_file, "install-ahenk"]

                std_opr.start_prc(self, cmd)
            else:
                self.ui_status_label.set_text(
                    _("An error occured while registering board.")
                )
                dialog_response = self.ui_error_dialog.run()
                if dialog_response:
                    self.application.quit()

        if status_code != 200:
            error_message = _("Server returned error {}").format(status_code)
            if data:
                try:
                    error_data = json.loads(data.decode("utf-8"))
                    error_message = error_data.get("msg", error_message)
                except:
                    pass
            logger.error(_("Error: {}").format(error_message))

    def switch_selection_stacks(self, button, stack):
        logger.info(f"switch_selection_stacks function called with stack: {stack}")
        stacks = {
            "city": self.ui_city_box,
            "town": self.ui_town_box,
            "school": self.ui_school_box,
        }

        # Reset values for the selected stack
        if stack == "city":
            self.city_id = None
            self.town_id = None
            self.school_code = None
            change_path(self)
            self.ui_register_button.set_sensitive(False)
        elif stack == "town":
            self.town_id = None
            self.school_code = None
            change_path(self)
            self.ui_register_button.set_sensitive(False)
        elif stack == "school":
            self.school_code = None
            change_path(self)
            if self.school_code:
                self.ui_register_button.set_sensitive(True)
        self.ui_stack.set_visible_child(stacks[stack])

    def on_unit_save_entry_changed(self, entry):
        logger.info("on_unit_save_entry_changed function called")
        unit_text = entry.get_text().strip()

        if unit_text and len(unit_text) > 10:
            entry.set_icon_from_icon_name(
                Gtk.EntryIconPosition.SECONDARY, "dialog-warning-symbolic"
            )
            entry.set_icon_tooltip_text(
                Gtk.EntryIconPosition.SECONDARY,
                _("Unit name must be at most 10 characters long"),
            )
            self.unit_name = None
            self.ui_register_button.set_sensitive(False)
        else:
            self.unit_name = unit_text if unit_text else ""
            entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, None)

            # During edit, ensure we maintain the city_id, town_id, and school_code from board_state
            if (
                self.board_state.get("registered", False)
                and "data" in self.board_state
                and not self.city_id
            ):
                data = self.board_state["data"]
                self.city_id = data.get("city_id")
                self.town_id = data.get("town_id")
                self.school_code = data.get("school_code")

            print(self.city_id, self.town_id, self.school_code, self.unit_name)
            self.ui_register_button.set_sensitive(
                self.city_id and self.town_id and self.school_code
            )

    def on_quick_register_edit_button_clicked(self, button):
        logger.info("on_quick_register_edit_button_clicked function called")
        self.ui_path_label.set_text(
            _("Device is not registered. Please register your device.")
        )
        GLib.idle_add(self.switch_main_stack, None, "main")

    def init_ui(self):
        self.ui_main_window = self.get_ui("ui_main_window")
        self.ui_stack = self.get_ui("ui_stack")
        self.ui_main_stack = self.get_ui("ui_main_stack")
        self.ui_selection_box = self.get_ui("ui_selection_box")
        self.ui_code_box = self.get_ui("ui_code_box")

        self.ui_main_page = self.get_ui("ui_main_page")
        self.ui_spinner_page = self.get_ui("ui_spinner_page")
        self.ui_confirm_page = self.get_ui("ui_confirm_page")
        self.ui_uncompleted_page = self.get_ui("ui_uncompleted_page")
        self.ui_quick_register_page = self.get_ui("ui_quick_register_page")
        self.ui_quick_register_info_label = self.get_ui("ui_quick_register_info_label")
        self.ui_quick_register_button = self.get_ui("ui_quick_register_button")
        self.ui_quick_register_button.connect(
            "clicked", self.on_confirm_ok_button_clicked
        )
        self.ui_quick_register_edit_button = self.get_ui(
            "ui_quick_register_edit_button"
        )
        self.ui_quick_register_edit_button.connect(
            "clicked", self.on_quick_register_edit_button_clicked
        )
        self.ui_retry_button = self.get_ui("ui_retry_button")
        self.ui_retry_button.connect("clicked", self.on_retry_button_clicked)

        self.ui_status_label = self.get_ui("ui_status_label")
        self.ui_code_entry = self.get_ui("ui_code_entry")
        self.ui_check_code_button = self.get_ui("ui_check_code_button")

        self.ui_register_selection_stack = self.get_ui("ui_register_selection_stack")
        self.ui_register_code_button = self.get_ui("ui_register_code_button")
        self.ui_register_code_button.connect(
            "clicked", self.on_register_selection_clicked, SchoolCode(self).window
        )
        self.ui_registered_info = self.get_ui("ui_registered_info")
        self.ui_registered_page = self.get_ui("ui_registered_page")
        self.ui_register_selection_button = self.get_ui("ui_register_selection_button")
        self.ui_register_selection_button.connect(
            "clicked", self.on_register_selection_clicked, self.ui_selection_box
        )

        self.ui_city_box = self.get_ui("ui_city_box")
        self.ui_town_box = self.get_ui("ui_town_box")
        self.ui_school_box = self.get_ui("ui_school_box")

        self.ui_city_search = self.get_ui("ui_city_search")
        self.ui_city_search.connect("changed", self.on_city_search_changed)
        self.ui_city_listbox = self.get_ui("ui_city_listbox")
        self.ui_city_listbox.connect("row-selected", self.on_city_selected)
        self.ui_city_listbox.connect("button-press-event", self.on_listbox_item_activated)

        self.ui_town_search = self.get_ui("ui_town_search")
        self.ui_town_search.connect("changed", self.on_town_search_changed)
        self.ui_town_listbox = self.get_ui("ui_town_listbox")
        self.ui_town_listbox.connect("row-selected", self.on_town_selected)
        self.ui_town_listbox.connect("button-press-event", self.on_listbox_item_activated)

        self.ui_school_search = self.get_ui("ui_school_search")
        self.ui_school_search.connect("changed", self.on_school_search_changed)

        self.ui_school_listbox = self.get_ui("ui_school_listbox")
        self.ui_school_listbox.connect("row-selected", self.on_school_selected)
        self.ui_school_listbox.connect("button-press-event", self.on_listbox_item_activated)

        self.ui_registered_dialog = self.get_ui("ui_registered_dialog")
        self.ui_error_dialog = self.get_ui("ui_error_dialog")

        self.ui_register_info_label = self.get_ui("ui_register_info_label")
        self.ui_path_label = self.get_ui("ui_path_label")
        self.ui_already_registered_label = self.get_ui("ui_already_registered_label")
        self.ui_register_button = self.get_ui("ui_register_button")
        self.ui_register_button.connect("clicked", self.register_board)
        self.ui_confirm_ok_button = self.get_ui("ui_confirm_ok_button")
        self.ui_confirm_ok_button.connect("clicked", self.on_confirm_ok_button_clicked)
        self.ui_confirm_cancel_button = self.get_ui("ui_confirm_cancel_button")
        self.ui_confirm_cancel_button.connect(
            "clicked", self.on_confirm_cancel_button_clicked
        )

        self.ui_edit_board_button = self.get_ui("ui_edit_board_button")
        self.ui_edit_board_button.connect("clicked", self.on_edit_board_button_clicked)

        self.ui_city_switcher_button = self.get_ui("ui_city_switcher_button")
        self.ui_town_switcher_button = self.get_ui("ui_town_switcher_button")
        self.ui_school_switcher_button = self.get_ui("ui_school_switcher_button")

        self.ui_unit_save_entry = self.get_ui("ui_unit_save_entry")
        self.ui_unit_save_entry.connect("changed", self.on_unit_save_entry_changed)

        self.ui_city_switcher_button.connect(
            "clicked", self.switch_selection_stacks, "city"
        )
        self.ui_town_switcher_button.connect(
            "clicked", self.switch_selection_stacks, "town"
        )
        self.ui_school_switcher_button.connect(
            "clicked", self.switch_selection_stacks, "school"
        )

        self.listbox_items = []
        self.ui_main_window.set_application(self.application)

        self.searched_cities = []

        self.towns = []
        self.searched_towns = []

        self.schools = []
        self.searched_schools = []

        self.create_listbox_rows(self.searched_cities, self.ui_city_listbox)

        self.ui_main_window.set_title(_("Eta Register"))
        self.ui_main_window.show_all()
        self.control_check()

    def find_city_name(self, city_id):
        """
        Find city name by city_id using existing data sources

        Priority:
        1. Current board_state
        2. Searched cities list
        3. Return None
        """
        # Check board_state first
        if self.board_state and "data" in self.board_state:
            board_data = self.board_state["data"]
            if board_data.get("city_id") == city_id:
                return board_data.get("city_name")

        # Check searched_cities list
        if hasattr(self, "searched_cities"):
            for city in self.searched_cities:
                if city.get("id") == city_id:
                    return city.get("name")
        if self.city_name:
            return self.city_name
        return None

    def find_town_name(self, town_id):
        """
        Find town name by town_id using existing data sources

        Priority:
        1. Current board_state
        2. Searched towns list
        3. Return None
        """
        # Check board_state first
        if self.board_state and "data" in self.board_state:
            board_data = self.board_state["data"]
            if board_data.get("town_id") == town_id:
                return board_data.get("town_name")

        # Check searched_towns list
        if hasattr(self, "searched_towns"):
            for town in self.searched_towns:
                if town.get("id") == town_id:
                    return town.get("name")
        if self.town_name:
            return self.town_name
        return None

    def find_school_name(self, school_code):
        """
        Find school name by school_code using existing data sources

        Priority:
        1. Current board_state
        2. Searched schools list
        3. Return None
        """
        # Check board_state first
        if self.board_state and "data" in self.board_state:
            board_data = self.board_state["data"]
            if board_data.get("school_code") == school_code:
                return board_data.get("school_name")

        # Check searched_schools list
        if hasattr(self, "searched_schools"):
            for school in self.searched_schools:
                if school.get("code") == school_code:
                    return school.get("name")
        if self.school_name:
            return self.school_name
        return None
