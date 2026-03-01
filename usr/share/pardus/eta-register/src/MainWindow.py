#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import sys
import gettext
import subprocess
import locale
from locale import gettext as _

import checks
from checks import interpret_device_status, ConnectionError
import network
from config import PACKAGE_TO_INSTALL, APPNAME_CODE, TRANSLATIONS_PATH
from logger import logger

locale.bindtextdomain(APPNAME_CODE, TRANSLATIONS_PATH)
locale.textdomain(APPNAME_CODE)

class MainWindow:
    def __init__(self, app, status):
        logger.info("MainWindow initialized with status: '{status}'".format(status=status))
        self.app_ref = app
        self.builder = Gtk.Builder()
        self.builder.set_translation_domain(APPNAME_CODE)
        self.device_info = None
        
        # Determine UI file path
        ui_path = "ui/window.glade" # Relative path for development
        if not os.path.exists(ui_path):
            # Path for installed application
            ui_path = "/usr/share/pardus/eta-register/ui/window.glade"

        try:
            self.builder.add_from_file(ui_path)
            self.main_window = self.builder.get_object("main_window")
            self.main_window.set_application(app)
            self.main_window.connect("destroy", self.on_destroy)

            # Get UI components
            self.stack = self.builder.get_object("main_stack")
            self.school_code_entry = self.builder.get_object("school_code_entry")
            self.info_label = self.builder.get_object("info_label")
            self.subtitle_label = self.builder.get_object("subtitle_label")
            
            # Widgets from the new confirm page (after code entry)
            self.confirm_grid_city_label = self.builder.get_object("confirm_grid_city_label")
            self.confirm_grid_town_label = self.builder.get_object("confirm_grid_town_label")
            self.confirm_grid_school_label = self.builder.get_object("confirm_grid_school_label")
            self.confirm_grid_code_label = self.builder.get_object("confirm_grid_code_label")
            self.confirm_unit_name_entry = self.builder.get_object("confirm_unit_name_entry")
            self.loading_status_label = self.builder.get_object("loading_status_label")

            # Widgets for selection-based registration
            self.province_search_entry = self.builder.get_object("province_search_entry")
            self.district_search_entry = self.builder.get_object("district_search_entry")
            self.school_search_entry = self.builder.get_object("school_search_entry")
            self.province_list_box = self.builder.get_object("province_list_box")
            self.district_list_box = self.builder.get_object("district_list_box")
            self.school_list_box = self.builder.get_object("school_list_box")
            self.selection_confirm_button = self.builder.get_object("selection_confirm_button")
            self.selection_stack = self.builder.get_object("selection_stack")


            # Widgets for selection summary on the main register page
            self.register_box = self.builder.get_object("register_box")
            selection_register_button = self.builder.get_object("selection_register_button")
            self.selection_register_box = selection_register_button.get_parent()
            self.register_confirm_box = self.builder.get_object("confirm_box")
            self.summary_grid_city_label = self.builder.get_object("summary_grid_city_label")
            self.summary_grid_town_label = self.builder.get_object("summary_grid_town_label")
            self.summary_grid_school_label = self.builder.get_object("summary_grid_school_label")
            self.summary_grid_code_label = self.builder.get_object("summary_grid_code_label")
            self.summary_unit_name_entry = self.builder.get_object("unit_name_entry")

            # Widgets for the info page
            self.info_province_label = self.builder.get_object("info_province_label")
            self.info_district_label = self.builder.get_object("info_district_label")
            self.info_school_label = self.builder.get_object("info_school_label")
            self.info_unit_label = self.builder.get_object("info_unit_label")
            self.info_unit_row = self.builder.get_object("info_unit_row")
            self.info_code_label = self.builder.get_object("info_code_label")

            # Selection column boxes for visibility control
            self.district_selection_box = self.builder.get_object("district_selection_box")
            self.school_selection_box = self.builder.get_object("school_selection_box")
            self.log_view = self.builder.get_object("log_view")

            self.loading_dialog = None
            self.selected_city_id = None
            self.selected_province_name = None
            self.selected_district_name = None

            logger.info("UI components initialized, connecting signals.")
            self.connect_signals()
            
            logger.info("Handling initial status passed from dispatcher: '{status}'".format(status=status))
            self.handle_initial_status(status)


        except GLib.Error as e:
            print(_("Error loading UI: {e}.").format(e=e))
            sys.exit(1)

    def connect_signals(self):
        """Connects GTK signals to methods."""
        self.builder.get_object("register_button").connect("clicked", self.on_register_button_clicked)
        self.builder.get_object("confirm_change_button").connect("clicked", self.on_change_school_button_clicked)
        self.builder.get_object("confirm_register_button_final").connect("clicked", self.on_confirm_register_button_clicked)
        self.builder.get_object("confirm_cancel_button").connect("clicked", self.on_confirm_cancel_button_clicked)
        self.builder.get_object("info_edit_button").connect("clicked", self.on_info_edit_button_clicked)
        self.builder.get_object("summary_back_button").connect("clicked", self.on_summary_back_button_clicked)
        self.builder.get_object("change_school_button").connect("clicked", self.on_summary_change_button_clicked)
        self.builder.get_object("confirm_register_button").connect("clicked", self.on_summary_confirm_button_clicked)
        self.builder.get_object("selection_register_button").connect("clicked", self.on_selection_register_button_clicked)
        self.builder.get_object("back_to_register_button").connect("clicked", self.on_back_to_register_button_clicked)
        self.province_list_box.connect("row-activated", self.on_province_selected)
        self.district_list_box.connect("row-activated", self.on_district_selected)
        self.school_list_box.connect("row-selected", self.on_school_selected)
        self.selection_confirm_button.connect("clicked", self.on_selection_confirm_button_clicked)
        self.province_search_entry.connect("search-changed", self.on_search_changed)
        self.district_search_entry.connect("search-changed", self.on_search_changed)
        self.school_search_entry.connect("search-changed", self.on_search_changed)
        logger.info("All signals connected.")

    def on_register_button_clicked(self, widget):
        logger.info("Register button (by school code) clicked.")
        school_code = self.school_code_entry.get_text()
        if not school_code.isdigit():
            logger.warning("Invalid school code entered: '{school_code}'".format(school_code=school_code))
            return

        url = checks.get_school_code_url(school_code)
        if not url: return # Should not happen

        self.show_loading_dialog(_("Verifying school code..."))
        network.get_async(url, self._on_verification_complete)

    def _on_verification_complete(self, error, school_info, status_code):
        """Callback for school code verification."""
        self.hide_loading_dialog()
        
        # We can use the status_code for more precise error checking if needed,
        # but for now, checking `error` and `school_info` is sufficient.
        if error or not school_info.get('data'):
            logger.error("Failed to verify school code. Error: {error}".format(error=error or 'Invalid data'))
            error_dialog = Gtk.MessageDialog(
                transient_for=self.main_window,
                modal=True,
                destroy_with_parent=True,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=_("Invalid School Code"),
            )
            error_dialog.format_secondary_text(
                _("The entered school code could not be found. Please check the code and try again.")
            )
            error_dialog.connect("response", lambda d, r: d.destroy())
            error_dialog.show()
            self.school_code_entry.set_text("")
            return

        logger.info("School code verification successful.")
        self.verified_school_data = school_info['data']
        logger.debug("Verified school data: {verified_school_data}".format(verified_school_data=self.verified_school_data))

        # Populate the new confirmation page with data
        self.confirm_grid_school_label.set_text(self.verified_school_data.get('name', 'N/A'))
        self.confirm_grid_code_label.set_text(str(self.verified_school_data.get('code', 'N/A')))
        self.confirm_grid_town_label.set_text(self.verified_school_data.get('town_name', 'N/A'))
        self.confirm_grid_city_label.set_text(self.verified_school_data.get('city_name', 'N/A'))

        # Switch to the confirmation page
        logger.info("Switching to 'confirm' page.")
        self.stack.set_visible_child_name("confirm")

    def handle_initial_status(self, status):
        """Determines what to do based on the initial status."""
        logger.info("Handling initial status: {status}".format(status=status))
        if status == "unknown":
            self.stack.set_visible_child_name("loading")
            self.start_status_checks()
        elif status == "not-registered":
            self.stack.set_visible_child_name("register")
        elif status in ["error-no-mac", "error-no-connection"]:
            self.stack.set_visible_child_name("loading") # Show loading page
            error_title = _("Configuration Error") if status == "error-no-mac" else _("No Internet Connection")
            error_message = _("Your wired network device may be missing or not loaded.\n\nMAC address could not be retrieved. ETA Register performs board registration using the wired network device's MAC address.") if status == "error-no-mac" else _("Please check your network connection and try again.")
            # Show the error immediately and then quit
            self.show_error_dialog_and_exit(error_title, error_message)
        elif status == "error-vendor":
            self.stack.set_visible_child_name("loading")
            self.show_vendor_error_dialog()
        elif status == "install-required":
            self.stack.set_visible_child_name("install")
            install_info_label = self.builder.get_object("install_info_label")
            install_info_label.set_text(
                _("The '{}' package is not installed on your system.").format(
                    PACKAGE_TO_INSTALL
                )
            )
        elif status == "registered":
            self.stack.set_visible_child_name("register") # Placeholder for info page
        else:
            # This case should ideally not be reached if the dispatcher works correctly,
            # but as a fallback, we can show a message and exit.
            self.app_ref.quit()

    def _show_info_page(self, registration_data):
        """Populates and shows the final information page."""
        logger.info("Populating and switching to the 'info' page.")
        self.info_province_label.set_text(registration_data.get('city_name', 'N/A'))
        self.info_district_label.set_text(registration_data.get('town_name', 'N/A'))
        self.info_school_label.set_text(registration_data.get('school_name', 'N/A'))
        self.info_code_label.set_text(str(registration_data.get('school_code', 'N/A')))
        
        unit_name = registration_data.get('unit_name')
        if unit_name:
            self.info_unit_label.set_text(unit_name)
            self.info_unit_row.show()
        else:
            self.info_unit_row.hide()

        self.stack.set_visible_child_name("info")

    def on_info_edit_button_clicked(self, widget):
        """
        Handles the click of the 'Edit' button on the info page.
        Switches back to the main registration page in its initial state
        with updated labels to reflect "edit mode".
        """
        logger.info("Edit button clicked on info page. Switching to edit mode.")
        # Update the labels for "edit mode"
        self.info_label.set_text(_("Update Registration"))
        self.subtitle_label.set_text(_("You can update your registration information below."))

        # Pre-fill unit name if it exists
        if self.device_info and self.device_info.get('data'):
            unit_name = self.device_info['data'].get('unit_name')
            if unit_name:
                self.summary_unit_name_entry.set_text(unit_name)
                # Also pre-fill the other entry in case the user switches to school code entry
                self.confirm_unit_name_entry.set_text(unit_name)

        # Reset the view to its initial state (hide summary, show entry boxes)
        self.on_summary_change_button_clicked(widget)
        
        # Switch to the register page
        logger.info("Switching to 'register' page for editing.")                 
        self.stack.set_visible_child_name("register")

    def start_status_checks(self):
        """
        Starts the chained check process.
        1. Check for general internet connectivity.
        2. If successful, check for backend status.
        """
        logger.info("Starting initial status checks.")
        self._do_general_connectivity_check()

    def _do_general_connectivity_check(self):
        """Helper function to initiate the general connectivity check."""
        self.loading_status_label.set_text(_("Checking connection..."))
        checks.check_general_connectivity_async(self._on_general_connectivity_checked)

    def _on_general_connectivity_checked(self, error, response_data, status_code):
        """Callback for the general internet connection check."""
        logger.info("General connectivity check finished. Status code: {status_code}".format(status_code=status_code))
        
        # status_code == 0 indicates a network transport error
        if status_code == 0 or error:
            logger.error("General connectivity check failed. Error: {error}".format(error=error))
            self.show_error_dialog_and_exit(
                _("No Internet Connection"),
                _("Please check your network connection and try again."),
                add_retry_button=True
            )
            return
        
        # 200 but response was not valid JSON (e.g. vendor list URL returned HTML/plain text)
        if status_code == 200 and isinstance(response_data, dict) and response_data.get("_json_error") and response_data.get("_raw_body"):
            self._show_raw_response_dialog(response_data["_raw_body"])
            return
        
        # Connectivity is OK, now check for allowed touch vendors
        logger.info("Connectivity OK. Checking touch vendor...")
        
        allowed_vendors = response_data
        
        if checks.check_touch_vendor(allowed_vendors):
             logger.info("Touch vendor check passed. Proceeding to check backend status.")
             self._check_backend_status_async()
        else:
             logger.error("Touch vendor check failed.")
             self.show_vendor_error_dialog()

    def _show_raw_response_dialog(self, raw_text):
        """
        Shows the raw response body when server returned 200 but body was not valid JSON.
        User can click OK to close and exit.
        """
        dialog = Gtk.Dialog(
            title=_("Invalid Server Response"),
            transient_for=self.main_window,
            modal=True,
            destroy_with_parent=True
        )
        dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
        dialog.set_default_size(560, 380)
        
        content = dialog.get_content_area()
        content.set_spacing(8)
        content.set_margin_top(10)
        content.set_margin_bottom(10)
        content.set_margin_start(10)
        content.set_margin_end(10)
        
        label = Gtk.Label(label=_("Server returned 200 but the response was not valid JSON. Raw body:"))
        label.set_line_wrap(True)
        label.set_xalign(0)
        content.pack_start(label, False, False, 0)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_min_content_height(200)
        
        textview = Gtk.TextView()
        textview.set_editable(False)
        textview.set_cursor_visible(False)
        textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        textview.get_buffer().set_text(raw_text)
        textview.set_left_margin(6)
        textview.set_right_margin(6)
        scrolled.add(textview)
        content.pack_start(scrolled, True, True, 0)
        
        dialog.show_all()
        dialog.run()
        dialog.destroy()
        self.app_ref.quit()

    def show_vendor_error_dialog(self):
        """
        Displays a custom dialog with a table of connected USB devices
        when the touch panel vendor is not supported.
        """
        from config import VENDOR_CONTACT_EMAIL
        
        dialog = Gtk.Dialog(
            title=_("Unsupported Device"),
            transient_for=self.main_window,
            modal=True,
            destroy_with_parent=True
        )
        dialog.add_button(_("Close"), Gtk.ResponseType.CLOSE)
        dialog.set_default_size(600, 400)
        
        # Main content area
        content_area = dialog.get_content_area()
        content_area.set_spacing(10)
        content_area.set_margin_top(10)
        content_area.set_margin_bottom(10)
        content_area.set_margin_start(10)
        content_area.set_margin_end(10)
        
        # Error Message
        msg_label = Gtk.Label()
        msg_label.set_markup(
            _("Your touch panel vendor is not in the allowed list.\n\nPlease report your vendor ID to: <b>{}</b>").format(VENDOR_CONTACT_EMAIL)
        )
        msg_label.set_line_wrap(True)
        msg_label.set_xalign(0)
        content_area.pack_start(msg_label, False, False, 0)
        
        # Label for the table
        table_label = Gtk.Label(label=_("Detected USB Devices:"))
        table_label.set_xalign(0)
        table_label.set_margin_top(10)
        content_area.pack_start(table_label, False, False, 0)
        
        # ListStore: Vendor, Device, Name
        store = Gtk.ListStore(str, str, str)
        devices_list = checks.get_connected_usb_devices_list()
        
        if not devices_list:
            store.append(["-", "-", _("No USB devices found.")])
        else:
            for dev in devices_list:
                store.append([dev['vendor'], dev['device'], dev['name']])
        
        # TreeView
        treeview = Gtk.TreeView(model=store)
        
        # Disable row selection
        treeview.get_selection().set_mode(Gtk.SelectionMode.NONE)
        
        # Column 1: Vendor
        renderer_text = Gtk.CellRendererText()
        column_vendor = Gtk.TreeViewColumn(_("Vendor"), renderer_text, text=0)
        treeview.append_column(column_vendor)
        
        # Column 2: Device
        column_device = Gtk.TreeViewColumn(_("Device"), renderer_text, text=1)
        treeview.append_column(column_device)
        
        # Column 3: Name
        column_name = Gtk.TreeViewColumn(_("Name"), renderer_text, text=2)
        column_name.set_expand(True) # Expand to fill space
        treeview.append_column(column_name)
        
        # ScrolledWindow for the TreeView
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_vexpand(True)
        scrolled_window.set_hexpand(True)
        scrolled_window.add(treeview)
        
        content_area.pack_start(scrolled_window, True, True, 0)
        
        dialog.show_all()
        
        # Wait for response
        dialog.run()
        dialog.destroy()
        self.app_ref.quit()

    def _check_backend_status_async(self):
        """Initiates an async check for the device's registration status with the backend."""
        self.loading_status_label.set_text(_("Connecting to ETA server..."))
        url = checks.get_device_check_url()
        if not url:
            logger.error("Could not get device check URL (MAC address missing).")
            self.show_error_dialog_and_exit(
                _("Configuration Error"),
                _("Your wired network device may be missing or not loaded.\n\nMAC address could not be retrieved. ETA Register performs board registration using the wired network device's MAC address.")
            )
            return
        network.get_async(url, self._on_device_status_checked)

    def _on_device_status_checked(self, error, response_data, status_code):
        """Callback for the initial device status check."""
        try:
            # A status code of 0 is our signal from network.py for a true network error
            if status_code == 0:
                raise ConnectionError(error or _("Network connection failed."))

            # For all other cases (including 500), let the centralized function decide.
            status_result = interpret_device_status(status_code, response_data)
            self.handle_status_result(
                is_registered=status_result['registered'],
                registration_data=response_data.get('data')
            )

        except ConnectionError as e:
            # This block now catches both real network errors and unhandled server errors
            logger.error("Status check failed. Error: {e}".format(e=e)) # Log the actual error
            self.show_error_dialog_and_exit(
                _("No Internet Connection"),
                _("Could not connect to the ETA server. Please try again later."),
                add_retry_button=True
            )

    def handle_status_result(self, is_registered, registration_data):
        logger.info(f"Handling device status. Registered: {is_registered}")
        
        # Store the device info for later use (e.g., for updates)
        self.device_info = {
            'registered': is_registered,
            'data': registration_data
        }

        if is_registered:
            # If the application is launched via the desktop, always show the info page
            # regardless of whether the package is installed. The autostart dispatcher
            # will handle the installation in the background.
            logger.info("Device is registered. Showing info page for desktop session.")
            self._show_info_page(registration_data)
        else:
            logger.info("Device is not registered. Showing register page.")
            self.stack.set_visible_child_name("register")


    def show_vendor_error_dialog(self):
        """
        Displays a custom dialog with a table of connected USB devices
        when the touch panel vendor is not supported.
        """
        from config import VENDOR_CONTACT_EMAIL
        
        dialog = Gtk.Dialog(
            title=_("Unsupported Device"),
            transient_for=self.main_window,
            modal=True,
            destroy_with_parent=True
        )
        dialog.add_button(_("Close"), Gtk.ResponseType.CLOSE)
        dialog.set_default_size(600, 400)
        
        # Main content area
        content_area = dialog.get_content_area()
        content_area.set_spacing(10)
        content_area.set_margin_top(10)
        content_area.set_margin_bottom(10)
        content_area.set_margin_start(10)
        content_area.set_margin_end(10)
        
        # Error Message
        msg_label = Gtk.Label()
        msg_label.set_markup(
            _("Your touch panel vendor is not in the allowed list.\n\nPlease report your vendor ID to: <b>{}</b>").format(VENDOR_CONTACT_EMAIL)
        )
        msg_label.set_line_wrap(True)
        msg_label.set_xalign(0)
        content_area.pack_start(msg_label, False, False, 0)
        
        # Label for the table
        table_label = Gtk.Label(label=_("Detected USB Devices:"))
        table_label.set_xalign(0)
        table_label.set_margin_top(10)
        content_area.pack_start(table_label, False, False, 0)
        
        # ListStore: Vendor, Device, Name
        store = Gtk.ListStore(str, str, str)
        devices_list = checks.get_connected_usb_devices_list()
        
        if not devices_list:
            store.append(["-", "-", _("No USB devices found.")])
        else:
            for dev in devices_list:
                store.append([dev['vendor'], dev['device'], dev['name']])
        
        # TreeView
        treeview = Gtk.TreeView(model=store)
        
        # Disable row selection
        treeview.get_selection().set_mode(Gtk.SelectionMode.NONE)
        
        # Column 1: Vendor
        renderer_text = Gtk.CellRendererText()
        column_vendor = Gtk.TreeViewColumn(_("Vendor"), renderer_text, text=0)
        treeview.append_column(column_vendor)
        
        # Column 2: Device
        column_device = Gtk.TreeViewColumn(_("Device"), renderer_text, text=1)
        treeview.append_column(column_device)
        
        # Column 3: Name
        column_name = Gtk.TreeViewColumn(_("Name"), renderer_text, text=2)
        column_name.set_expand(True) # Expand to fill space
        treeview.append_column(column_name)
        
        # ScrolledWindow for the TreeView
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_vexpand(True)
        scrolled_window.set_hexpand(True)
        scrolled_window.add(treeview)
        
        content_area.pack_start(scrolled_window, True, True, 0)
        
        dialog.show_all()
        
        # Wait for response
        dialog.run()
        dialog.destroy()
        self.app_ref.quit()

    def show_error_dialog_and_exit(self, title, message, add_retry_button=False, use_markup=False):
        """
        Displays a modal error dialog.
        If add_retry_button is True, it shows 'Retry' and 'Close' buttons.
        Otherwise, it shows a single 'OK' button and exits.
        """
        dialog = Gtk.MessageDialog(
            transient_for=self.main_window,
            modal=True,
            destroy_with_parent=True,
            message_type=Gtk.MessageType.ERROR,
            text=title,
        )
        
        if use_markup:
            dialog.format_secondary_markup(message)
        else:
            dialog.format_secondary_text(message)

        if add_retry_button:
            dialog.add_button(_("Retry"), Gtk.ResponseType.APPLY)
            dialog.add_button(_("Close"), Gtk.ResponseType.CLOSE)
        else:
            dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)

        def on_response(d, response_id):
            if response_id == Gtk.ResponseType.APPLY:
                d.destroy()
                self.start_status_checks()
            else: # OK, CLOSE, or window manager close
                self.app_ref.quit()

        dialog.connect("response", on_response)
        dialog.show()

    def show_error_dialog(self, title, message):
        """Displays a modal error dialog."""
        error_dialog = Gtk.MessageDialog(
            transient_for=self.main_window,
            modal=True,
            destroy_with_parent=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=title,
        )
        error_dialog.format_secondary_text(message)
        error_dialog.connect("response", lambda d, r: d.destroy())
        error_dialog.show()

    def on_change_school_button_clicked(self, widget):
        """Hides the confirmation and shows the entry box again."""
        logger.info("Change school button clicked on confirmation page.")
        self.school_code_entry.set_text("") # Clear the old entry
        self.stack.set_visible_child_name("register")

    def on_confirm_cancel_button_clicked(self, widget):
        """Returns to the initial state of the registration page."""
        self.on_summary_change_button_clicked(widget) # Resets the view
        self.stack.set_visible_child_name("register")

    def _clear_list_box(self, list_box):
        """Removes all children from a Gtk.ListBox."""
        for child in list_box.get_children():
            list_box.remove(child)

    def on_selection_register_button_clicked(self, widget):
        """Switches to the selection-based registration page, resets the view, and fetches provinces if needed."""
        logger.info("Register by selection button clicked. Switching to selection page and resetting state.")

        # Reset the entire selection flow to its initial state
        self.selection_stack.set_visible_child_name("provinces")
        self._clear_list_box(self.district_list_box)
        self._clear_list_box(self.school_list_box)
        self.province_search_entry.set_text("")
        self.district_search_entry.set_text("")
        self.school_search_entry.set_text("")
        self.selection_confirm_button.set_sensitive(False)
        self.selected_city_id = None
        self.selected_province_name = None
        self.selected_district_name = None

        self.stack.set_visible_child_name("selection_register")
        # Only fetch if the list is empty to avoid refetching on page switch
        if not self.province_list_box.get_children():
            self._fetch_provinces()

    def on_back_to_register_button_clicked(self, widget):
        """Handles back navigation within the selection stack or to the main register page."""
        current_page = self.selection_stack.get_visible_child_name()
        logger.info("Back button clicked on selection page. Current view: {current_page}".format(current_page=current_page))

        if current_page == "schools":
            self.selection_stack.set_visible_child_name("districts")
            self._clear_list_box(self.school_list_box)
            self.school_search_entry.set_text("")
            self.selection_confirm_button.set_sensitive(False)
        elif current_page == "districts":
            self.selection_stack.set_visible_child_name("provinces")
            self._clear_list_box(self.district_list_box)
            self.district_search_entry.set_text("")
            self.selection_confirm_button.set_sensitive(False)
        else:  # On provinces page, go back to the main registration page
            self.stack.set_visible_child_name("register")

    def _fetch_provinces(self):
        """Fetches the list of provinces from the backend."""
        logger.info("Fetching provinces...")
        self.show_loading_dialog(_("Fetching provinces..."))

        def do_fetch():
            url = checks.get_cities_url()
            network.get_async(url, self._on_provinces_fetched)
            return False

        GLib.timeout_add_seconds(1, do_fetch)

    def _on_provinces_fetched(self, error, response_data, status_code):
        """Callback for when the province list has been fetched."""
        self.hide_loading_dialog()
        if error or status_code != 200:
            logger.error("Failed to fetch provinces. Status: {status_code}, Error: {error}".format(status_code=status_code, error=error))
            self.show_error_dialog_and_exit(
                _("Error Fetching Data"),
                _("Could not fetch the list of provinces. Please check your connection and try again.")
            )
            return

        logger.info("Successfully fetched provinces.")
        provinces = response_data.get("data", [])
        
        # Sort by name, respecting locale
        provinces.sort(key=lambda p: locale.strxfrm(p.get("name", "")))

        for province in provinces:
            row = Gtk.Label(label=province.get("name"))
            row.set_halign(Gtk.Align.START)
            row.set_margin_start(10)
            listbox_row = Gtk.ListBoxRow()
            listbox_row.add(row)
            # Store the full data dictionary in the row object for later retrieval
            listbox_row.province_data = province
            self.province_list_box.add(listbox_row)
        
        self.province_list_box.set_filter_func(self._filter_listbox, self.province_search_entry)
        self.province_list_box.show_all()

    def on_province_selected(self, listbox, row):
        """Handles province selection to fetch corresponding districts."""
        if not row: return
        
        province_data = row.province_data
        self.selected_city_id = province_data.get("id")
        self.selected_province_name = province_data.get("name")
        logger.info("Province selected: {selected_province_name} (ID: {selected_city_id})".format(selected_province_name=self.selected_province_name, selected_city_id=self.selected_city_id))
        
        # Clear subsequent lists and disable them
        self._clear_list_box(self.district_list_box)
        self._clear_list_box(self.school_list_box)
        self.selection_confirm_button.set_sensitive(False)

        if self.selected_city_id:
            self._fetch_districts(self.selected_city_id)

    def _fetch_districts(self, province_id):
        """Fetches districts for a given province ID."""
        logger.info("Fetching districts for province ID: {province_id}".format(province_id=province_id))
        self.show_loading_dialog(_("Fetching districts..."))

        def do_fetch():
            url = checks.get_towns_url(province_id)
            network.get_async(url, self._on_districts_fetched)
            return False

        GLib.timeout_add_seconds(1, do_fetch)

    def _on_districts_fetched(self, error, response_data, status_code):
        """Callback for when districts have been fetched."""
        self.hide_loading_dialog()
        if error or status_code != 200:
            logger.error("Failed to fetch districts. Status: {status_code}, Error: {error}".format(status_code=status_code, error=error))
            self.show_error_dialog_and_exit(
                _("Error Fetching Data"),
                _("Could not fetch the list of districts. Please try again.")
            )
            return

        logger.info("Successfully fetched districts.")
        districts = response_data.get("data", [])
        districts.sort(key=lambda d: locale.strxfrm(d.get("name", "")))

        self._clear_list_box(self.district_list_box) # Clear previous results
        for district in districts:
            row = Gtk.Label(label=district.get("name"))
            row.set_halign(Gtk.Align.START)
            row.set_margin_start(10)
            listbox_row = Gtk.ListBoxRow()
            listbox_row.add(row)
            listbox_row.district_data = district
            self.district_list_box.add(listbox_row)

        # Activate the district list and search
        self.district_list_box.set_filter_func(self._filter_listbox, self.district_search_entry)
        self.district_list_box.set_sensitive(True)
        self.selection_stack.set_visible_child_name("districts")
        self.district_list_box.show_all()

    def on_district_selected(self, listbox, row):
        """Handles district selection to fetch corresponding schools."""
        if not row: return

        district_data = row.district_data
        district_id = district_data.get("id")
        self.selected_district_name = district_data.get("name")
        logger.info("District selected: {selected_district_name} (ID: {district_id})".format(selected_district_name=self.selected_district_name, district_id=district_id))

        # Clear school list and disable it
        self._clear_list_box(self.school_list_box)
        self.selection_confirm_button.set_sensitive(False)
        
        if district_id:
            self._fetch_schools(self.selected_city_id, district_id)

    def _fetch_schools(self, city_id, district_id):
        """Fetches schools for a given district ID."""
        logger.info("Fetching schools for city ID: {city_id}, district ID: {district_id}".format(city_id=city_id, district_id=district_id))
        self.show_loading_dialog(_("Fetching schools..."))

        def do_fetch():
            url = checks.get_schools_url(city_id, district_id)
            network.get_async(url, self._on_schools_fetched)
            return False

        GLib.timeout_add_seconds(1, do_fetch)

    def _on_schools_fetched(self, error, response_data, status_code):
        """Callback for when schools have been fetched."""
        self.hide_loading_dialog()
        if error or status_code != 200:
            logger.error("Failed to fetch schools. Status: {status_code}, Error: {error}".format(status_code=status_code, error=error))
            self.show_error_dialog_and_exit(
                _("Error Fetching Data"),
                _("Could not fetch the list of schools. Please try again.")
            )
            return
        
        logger.info("Successfully fetched schools.")
        schools = response_data.get("data", [])
        schools.sort(key=lambda s: locale.strxfrm(s.get("name", "")))

        self._clear_list_box(self.school_list_box)
        for school in schools:
            # We create a Gtk.Label that supports wrapping for long school names
            label = Gtk.Label(label=school.get("name"))
            label.set_halign(Gtk.Align.START)
            label.set_margin_start(10)
            label.set_line_wrap(True)
            label.set_max_width_chars(30)

            listbox_row = Gtk.ListBoxRow()
            listbox_row.add(label)
            listbox_row.school_data = school
            self.school_list_box.add(listbox_row)

        self.school_list_box.set_filter_func(self._filter_listbox, self.school_search_entry)
        self.school_list_box.set_sensitive(True)
        self.selection_stack.set_visible_child_name("schools")
        self.school_list_box.show_all()

    def on_school_selected(self, listbox, row):
        """Activates the final confirm button when a school is selected."""
        if row:
            logger.debug("School row selected: {school_name}".format(school_name=row.school_data.get('name')))
        self.selection_confirm_button.set_sensitive(row is not None)

    def on_search_changed(self, search_entry):
        """Filters the corresponding listbox based on the search text."""
        list_box = None
        if search_entry == self.province_search_entry:
            list_box = self.province_list_box
        elif search_entry == self.district_search_entry:
            list_box = self.district_list_box
        elif search_entry == self.school_search_entry:
            list_box = self.school_list_box

        if list_box:
            list_box.invalidate_filter()

    def _normalize_for_search(self, text):
        """Normalizes text for Turkish-aware, case-insensitive, and accent-insensitive search."""
        # Turkish-specific case folding
        text = text.replace("I", "ı").replace("İ", "i")
        text = text.lower()

        # Accent removal for other common Turkish characters
        replacements = str.maketrans("çğöşü", "cgosu")
        text = text.translate(replacements)
        return text

    def _filter_listbox(self, row, search_entry):
        """The actual filter function for the ListBoxes."""
        search_text = self._normalize_for_search(search_entry.get_text().strip())
        if not search_text:
            return True # Show all if search is empty
        
        # The child of the ListBoxRow is the Gtk.Label
        label_widget = row.get_child()
        if isinstance(label_widget, Gtk.Label):
            row_text = self._normalize_for_search(label_widget.get_text())
            return search_text in row_text
        return False

    def on_selection_confirm_button_clicked(self, widget):
        """
        Triggered when the confirm button on the selection page is clicked.
        Switches to the register page and shows the summary of the selection.
        """
        selected_row = self.school_list_box.get_selected_row()
        if not selected_row:
            logger.warning("Selection confirmation clicked, but no school row was selected.")
            return

        self.verified_school_data = selected_row.school_data
        logger.info("School selection confirmed: {school_name}".format(school_name=self.verified_school_data.get('name')))
        
        # Populate summary labels
        school_name = self.verified_school_data.get('name', 'N/A')
        school_code = self.verified_school_data.get('code', 'N/A')
        town_name = self.selected_district_name or 'N/A'
        city_name = self.selected_province_name or 'N/A'
        
        # Using the labels from the `confirm_box` on the `register_page`
        self.summary_grid_city_label.set_text(city_name)
        self.summary_grid_town_label.set_text(town_name)
        self.summary_grid_school_label.set_text(school_name)
        self.summary_grid_code_label.set_text(str(school_code))

        # Hide entry widgets and show the confirmation box
        self.register_box.hide()
        self.selection_register_box.hide()
        self.info_label.hide()
        self.subtitle_label.hide()
        self.register_confirm_box.show()
        
        # Switch to the main register page
        self.stack.set_visible_child_name("register")

    def on_summary_change_button_clicked(self, widget):
        """Hides the summary and goes back to the main registration page."""
        logger.info("Summary 'Change' button clicked. Returning to main registration view.")
        self.register_confirm_box.hide()
        self.register_box.show()
        self.selection_register_box.show()
        self.info_label.show()
        self.subtitle_label.show()

    def on_summary_back_button_clicked(self, widget):
        """Returns to the school selection page from the summary view."""
        logger.info("Summary 'Back' button clicked. Returning to school selection.")
        self.stack.set_visible_child_name("selection_register")

    def on_summary_confirm_button_clicked(self, widget):
        """Initiates final registration from the summary view."""
        logger.info("Summary 'Confirm' button clicked.")
        unit_name = self.summary_unit_name_entry.get_text().strip()
        self._initiate_registration(unit_name)

    def on_confirm_register_button_clicked(self, widget):
        logger.info("Final 'Confirm' button clicked on school code page.")
        unit_name = self.confirm_unit_name_entry.get_text().strip()
        self._initiate_registration(unit_name)

    def _initiate_registration(self, unit_name):
        # This is where we decide whether to register or update.
        is_update = self.device_info and self.device_info.get('registered', False)
        
        # Unit name is now required for both registration and update
        if not unit_name or not unit_name.strip():
            logger.warning("Unit name is required but was not provided.")
            if is_update:
                self.show_error_dialog(
                    _("Unit Name Required"),
                    _("The unit name (room name) is required and cannot be empty for update.")
                )
            else:
                self.show_error_dialog(
                    _("Unit Name Required"),
                    _("The unit name (room name) is required and cannot be empty for registration.")
                )
            return
        
        unit_name = unit_name.strip()
        if len(unit_name) < 2 or len(unit_name) > 12:
            logger.warning("Invalid unit name entered: '{unit_name}'".format(unit_name=unit_name))
            self.show_error_dialog(
                _("Invalid Unit Name"),
                _("The unit name must be between 2 and 12 characters long.")
            )
            return
        
        url = None
        payload = None

        if is_update:
            self.show_loading_dialog(_("Updating... Please wait."))
            logger.info("Device is already registered. Initiating an UPDATE.")
            board_id = self.device_info.get('data', {}).get('board_id')
            if not board_id:
                self.hide_loading_dialog()
                self.show_error_dialog(
                    _("Update Failed"), 
                    _("Could not find the board ID for the update operation.")
                )
                return
            
            url = checks.get_update_device_url()
            # For an update, we might only need a subset of data.
            # We pass the full school data, and the payload function will pick what it needs.
            payload = checks.get_update_payload(board_id, self.verified_school_data, unit_name)

        else:
            self.show_loading_dialog(_("Registering... Please wait."))
            logger.info("Device is not registered. Initiating a NEW registration.")
            url = checks.get_register_device_url()
            payload = checks.get_register_payload(self.verified_school_data, unit_name)

        if not payload or not url:
            self.hide_loading_dialog()
            self.show_error_dialog(
                _("Registration Failed"), 
                _("Could not generate the necessary data for registration.")
            )
            return

        # Use the dispatcher to send the request
        network.post_async(url, payload, self.on_registration_finished)

    def on_registration_finished(self, error, response, status_code):
        """
        Callback for when the registration or update POST request is complete.
        """
        self.hide_loading_dialog()
        
        # The `error` parameter from network.py indicates a network issue or a non-2xx HTTP status.
        # If it's None, the request was successful on the transport level, which we consider a success
        # for registration, as confirmed by database logs.
        if error:
            logger.error("Registration failed. Status: {status_code}, Error: {error}, Response: {response}".format(status_code=status_code, error=error, response=response))
            
            # Construct a more user-friendly error message
            user_error_message = _("An unexpected error occurred during registration.")
            if response and isinstance(response, dict) and 'msg' in response:
                # Use the specific error message from the server if available
                user_error_message = response['msg']
            elif error:
                # Fallback to the network error
                user_error_message = _("Could not connect to the registration server. Please check your internet connection and try again.")

            error_dialog = Gtk.MessageDialog(
                transient_for=self.main_window,
                modal=True,
                destroy_with_parent=True,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text=_("Registration Failed"),
            )
            # Provide a more specific error message to the user
            error_dialog.format_secondary_text(user_error_message)
            error_dialog.connect("response", lambda d, r: d.destroy())
            error_dialog.show()
            return
        
        # If we are here, registration is considered successful.
        logger.info("Registration/update API call successful.")
        success_dialog = Gtk.MessageDialog(
            transient_for=self.main_window,
            modal=True,
            destroy_with_parent=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=_("Pardus Registration Successful"),
        )
        success_dialog.format_secondary_text(
            _("Your device has been registered with Pardus. The central management application (LiderAhenk) will now be installed.")
        )
        success_dialog.connect("response", lambda d, r: self.on_successful_registration())
        success_dialog.show()

    def on_successful_registration(self):
        # This function is now separate to be called from the dialog response
        # After successful registration, launch the installer
        script_dir = os.path.dirname(os.path.abspath(__file__))
        installer_path = os.path.join(script_dir, "installer.py")
        if os.path.exists(installer_path):
            logger.info("Launching installer: {installer_path}".format(installer_path=installer_path))
            subprocess.Popen(["python3", installer_path])
        else:
            logger.error("Error: Installer script not found at {installer_path}".format(installer_path=installer_path))
            # TODO: Maybe show an error to the user?
        
        self.app_ref.quit()


    def on_install_button_clicked(self, widget):
        pass

    def show_loading_dialog(self, text):
        if self.loading_dialog:
            self.hide_loading_dialog()

        self.loading_dialog = Gtk.MessageDialog(
            transient_for=self.main_window,
            modal=True,
            destroy_with_parent=True,
            message_type=Gtk.MessageType.INFO,
            text=text,
        )
        self.loading_dialog.set_deletable(False) # Make it non-closable
        spinner = Gtk.Spinner()
        spinner.start()
        box = self.loading_dialog.get_content_area()
        box.pack_start(spinner, True, True, 0)
        spinner.show()
        self.loading_dialog.show()

    def hide_loading_dialog(self):
        if self.loading_dialog:
            self.loading_dialog.destroy()
            self.loading_dialog = None

    def present(self):
        logger.info("Presenting main window.")
        self.main_window.present()

    def on_destroy(self, widget):
        logger.info("Main window destroyed, application quitting.")
        pass

