#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib, Gdk
import sys
import os
import locale
import gettext
import apt
import apt_pkg
import subprocess
from config import APPNAME, PACKAGE_TO_INSTALL, TRANSLATIONS_PATH, SERVICE_TO_ENABLE

# Basic Translation Setup
try:
    locale.bindtextdomain(APPNAME, TRANSLATIONS_PATH)
    gettext.bindtextdomain(APPNAME, TRANSLATIONS_PATH)
    gettext.textdomain(APPNAME)
    _ = gettext.gettext
except Exception as e:
    print(f"Error setting up translation: {e}")
    _ = str

class InstallerApp(Gtk.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, application_id="tr.org.pardus.eta-register.installer", **kwargs)
        self.window = None
        # It's good practice to initialize apt_pkg early.
        apt_pkg.init_config()
        apt_pkg.init_system()

    def do_activate(self):
        if not self.window:
            self.window = InstallerWindow(self)
        self.window.present()

class InstallerWindow:
    def __init__(self, app):
        self.app_ref = app
        self.builder = Gtk.Builder()
        self.builder.set_translation_domain(APPNAME)
        self.installation_in_progress = False
        
        ui_path = "ui/window.glade"
        if not os.path.exists(ui_path):
            ui_path = "/usr/share/pardus/eta-register/ui/window.glade"

        try:
            self.builder.add_from_file(ui_path)
            self.main_window = self.builder.get_object("main_window")
            self.main_window.set_application(app)
            
            self.stack = self.builder.get_object("main_stack")
            self.log_view = self.builder.get_object("log_view")
            self.install_info_label = self.builder.get_object("install_info_label")
            self.log_buffer = self.log_view.get_buffer()

            # New UI elements for installer status
            self.install_spinner = self.builder.get_object("install_spinner")
            self.install_status_label = self.builder.get_object("install_status_label")
            self.install_close_button = self.builder.get_object("install_close_button")
            self.copy_logs_button = self.builder.get_object("copy_logs_button")
            self.copy_logs_label = self.builder.get_object("copy_logs_label")


            self.install_close_button.connect("clicked", lambda w: self.app_ref.quit())
            self.copy_logs_button.connect("clicked", self.on_copy_logs_clicked)
            self.retry_attempted = False


            # --- Dynamically find the path for opr.py ---
            # Check for development environment path first
            action_path = os.path.join(os.path.dirname(__file__), "opr.py")
            if not os.path.exists(action_path):
                # Fallback to installed system path
                action_path = "/usr/share/pardus/eta-register/src/opr.py"
            
            self.action_id = action_path


            self.main_window.connect("destroy", lambda w: self.app_ref.quit())
            self.main_window.connect("delete-event", self.on_window_delete_event)
            # Connect to the 'show' signal to ensure the window is visible before starting
            self.main_window.connect("show", self._on_window_show)

            # Set the initial state
            self.stack.set_visible_child_name("install")
            self.install_info_label.set_text(_("Your board has been registered to Pardus. The Central Management Application (LiderAhenk) will be installed."))

        except GLib.Error as e:
            print(_("Error loading UI for installer: {e}").format(e=e))
            sys.exit(1)

    def present(self):
        self.main_window.present()

    def _on_window_show(self, widget):
        # Start installation only after the window is shown to ensure
        # the UI is responsive.
        GLib.idle_add(self._start_installation)

    def on_window_delete_event(self, widget, event):
        """
        Prevents the window from being closed. Instead, it minimizes (iconifies) it.
        This stops the user from accidentally aborting the installation.
        """
        self.main_window.iconify()
        return True # True prevents the event from propagating, thus stopping the close

    def _start_installation(self):
        """Starts the installation process by calling the helper script with pkexec."""
        self.installation_in_progress = True
        if self.retry_attempted:
            self._append_to_log(_("\nRetrying installation..."))
        else:
            self._append_to_log(_("Starting installation..."))
        
        self.install_spinner.start()
        self.install_status_label.set_text(_("Updating package lists..."))
        self.install_close_button.set_sensitive(False)
        self.copy_logs_button.set_sensitive(False)

        command = ["/usr/bin/pkexec", self.action_id]

        try:
            self.process = Gio.Subprocess.new(
                command,
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE
            )
            
            # Use DataInputStream for easier async line-by-line reading
            stdout_stream = Gio.DataInputStream.new(self.process.get_stdout_pipe())
            stderr_stream = Gio.DataInputStream.new(self.process.get_stderr_pipe())
            
            self._read_stream(stdout_stream)
            self._read_stream(stderr_stream)
            
            self.process.wait_check_async(None, self._on_update_finished)
        except GLib.Error as e:
            self._append_to_log(_("\n{_('Error starting update process')}: {e_message}").format(e_message=e.message))
            self._show_failure_state()

    def _on_update_finished(self, proc, result):
        """Callback for when 'apt update' is finished."""
        try:
            proc.wait_check_finish(result)
            self._append_to_log(_("Package lists updated successfully.\n"))
            self._run_installation()
        except GLib.Error as e:
            self._append_to_log(f"\n{_('apt update failed')}: {e.message}")
            self._show_failure_state()

    def _run_installation(self):
        """Starts the installation of the specific package."""
        self.install_status_label.set_text(_("Installing '{pkg}'...").format(pkg=PACKAGE_TO_INSTALL))
        self._append_to_log(_("\nInstalling package..."))
        
        command = ["/usr/bin/pkexec", self.action_id]

        try:
            self.process = Gio.Subprocess.new(
                command,
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE
            )

            stdout_stream = Gio.DataInputStream.new(self.process.get_stdout_pipe())
            stderr_stream = Gio.DataInputStream.new(self.process.get_stderr_pipe())
            
            self._read_stream(stdout_stream)
            self._read_stream(stderr_stream)

            self.process.wait_check_async(None, self._on_install_finished)
        except GLib.Error as e:
            self._append_to_log(_("\n{_('Error starting installation process')}: {e_message}").format(e_message=e.message))
            self._show_failure_state()

    def _read_stream(self, stream):
        # Asynchronously read one line
        stream.read_line_async(GLib.PRIORITY_DEFAULT, None, self._on_line_read, stream)

    def _on_line_read(self, stream, result, user_data):
        try:
            line, _ = stream.read_line_finish_utf8(result)
            if line is not None:
                self._append_to_log(line + "\n")
                self._read_stream(stream) # Continue reading the next line
        except GLib.Error:
            # This can happen when the stream is closed, it's not a critical error.
            pass

    def _on_install_finished(self, proc, result):
        try:
            # We use wait_check_finish to see if it errored, but we don't assume success.
            # The final verification is the source of truth.
            proc.wait_check_finish(result)
            self._append_to_log(_("Installation command finished.\n"))
        except GLib.Error as e:
            self._append_to_log(f"\n{_('Installation command failed')}: {e.message}\n")
        
        # Always verify, regardless of the command's exit status.
        GLib.idle_add(self.verify_installation)
    
    def verify_installation(self):
        """
        Checks the state of the package using the apt cache. This is the main
        decision point for success, retry, or failure.
        """
        self.install_status_label.set_text(_("Verifying installation..."))
        try:
            # Re-read cache to get the latest state, do NOT run update() here as it requires root.
            cache = apt.Cache()
            package = cache[PACKAGE_TO_INSTALL]
            
            # A package is only truly installed if it's in the CURSTATE_INSTALLED state.
            # package.is_installed can be true for half-configured packages.
            is_fully_installed = (package._pkg.current_state == apt_pkg.CURSTATE_INSTALLED)
            
            if is_fully_installed:
                self._append_to_log(_("Verification successful: '{pkg}' is installed correctly.").format(pkg=PACKAGE_TO_INSTALL))
                self._start_service_via_helper()
            else:
                self._append_to_log(_("Verification failed: Package is not in a correctly installed state."))
                # If we have already tried recovery and a full reinstall, we fail now.
                if self.retry_attempted:
                    self._show_failure_state()
                else:
                    # This is the first failure. Start the recovery process.
                    self.handle_recovery()

        except Exception as e:
            self._append_to_log(_("\nError verifying installation: {e}").format(e=e))
            if self.retry_attempted:
                self._show_failure_state()
            else:
                self.handle_recovery()
        
        return GLib.SOURCE_REMOVE

    def _start_service_via_helper(self):
        """Calls the opr.py helper script to enable and start the service."""
        self.install_status_label.set_text(_("Enabling and starting the service..."))
        self._append_to_log(_("\nEnabling and starting the service..."))

        command = [
            "/usr/bin/pkexec", 
            self.action_id, 
            "start-service", 
            SERVICE_TO_ENABLE
        ]

        try:
            process = Gio.Subprocess.new(
                command,
                # We don't need to pipe output here as opr.py logs to a file
                Gio.SubprocessFlags.NONE
            )
            process.wait_check_async(None, self._on_service_helper_finished)
        except GLib.Error as e:
            # This error is for if the process fails to even start
            self._append_to_log(_("Failed to run the service helper script. Error: {error}").format(error=str(e)))
            self._show_failure_state()

    def _on_service_helper_finished(self, process, result):
        """Callback for when the opr.py service helper finishes."""
        try:
            process.wait_check_finish(result)
            # If wait_check_finish succeeds, the script exited with 0
            self._append_to_log(_("Service started successfully.\n"))
            self.install_status_label.set_text(_("Installation successful. You can close the window."))
            self.installation_in_progress = False
        except GLib.Error as e:
            # If wait_check_finish fails, the script exited with a non-zero code
            self._append_to_log(_("The helper script failed to start the service. See log file for details. Error: {error}\n").format(error=str(e)))
            # As per user request, treat this as a success with a warning, not a total failure.
            self.install_status_label.set_text(_("Installation successful, but service start failed."))
        
        # In all cases, the process is finished, so finalize the UI
        self.install_spinner.stop()
        self.install_close_button.set_sensitive(True)
        self.copy_logs_button.set_sensitive(True)

    def handle_recovery(self):
        """
        Handles the first installation failure. It runs 'dpkg --configure -a'
        and then re-verifies. If still not installed, it triggers a full reinstall.
        """
        self.retry_attempted = True
        self._append_to_log(_("\nAttempting to fix broken packages with 'dpkg --configure -a'..."))
        self.install_status_label.set_text(_("Attempting to fix system packages..."))
        
        try:
            configure_command = ["/usr/bin/pkexec", "dpkg", "--configure", "-a"]
            process = Gio.Subprocess.new(
                configure_command,
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE
            )
            process.wait_check_async(None, self._on_dpkg_configure_finished)
        except GLib.Error as e:
            self._append_to_log(_("Failed to run 'dpkg --configure -a'. Error: {error}").format(error=str(e)))
            # If dpkg fails to start, go straight to the full reinstall retry.
            self._start_installation()

    def _on_dpkg_configure_finished(self, process, result):
        """Callback for when 'dpkg --configure -a' finishes."""
        try:
            process.wait_check_finish(result)
            self._append_to_log(_("'dpkg --configure -a' completed successfully.\n"))
        except GLib.Error as e:
            self._append_to_log(_("'dpkg --configure -a' failed. Error: {error}\n").format(error=str(e)))
        
        # After trying to fix, verify again.
        self._append_to_log(_("Re-verifying installation after dpkg..."))
        GLib.idle_add(self.verify_after_dpkg)

    def verify_after_dpkg(self):
        """
        A second verification step after running dpkg. If the package is now
        installed, we succeed. If not, we trigger the final, full reinstall attempt.
        """
        try:
            cache = apt.Cache()
            package = cache[PACKAGE_TO_INSTALL]
            is_fully_installed = (package._pkg.current_state == apt_pkg.CURSTATE_INSTALLED)

            if is_fully_installed:
                self._append_to_log(_("Verification successful after dpkg run.\n"))
                self._start_service_via_helper()
            else:
                self._append_to_log(_("Package still not installed after dpkg. Retrying full installation process...\n"))
                self._start_installation()
        except Exception as e:
            self._append_to_log(_("\nError during re-verification: {e}. Retrying full installation...").format(e=e))
            self._start_installation()
        
        return GLib.SOURCE_REMOVE

    def _show_failure_state(self):
        """Configures the UI to show that the installation has failed."""
        self._append_to_log(_("\nInstallation failed after all attempts."))
        self.install_status_label.set_text(_("Installation failed. Please check the log."))
        self.install_spinner.stop()
        self.install_close_button.set_sensitive(True)
        self.copy_logs_button.set_sensitive(True) # Also enable copy button on failure
        self.installation_in_progress = False
        return GLib.SOURCE_REMOVE


    def on_copy_logs_clicked(self, widget):
        """Copies the content of the log_view to the clipboard."""
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        buffer = self.log_view.get_buffer()
        start, end = buffer.get_bounds()
        log_text = buffer.get_text(start, end, False)
        clipboard.set_text(log_text, -1)

        # Provide visual feedback to the user
        self.copy_logs_label.set_text(_("Copied!"))

    def _schedule_app_quit(self):
        """Schedules the application to quit after a short delay."""
        # This is no longer the primary way to exit, but kept for potential future use.
        GLib.timeout_add_seconds(3, self.app_ref.quit)

    def _append_to_log(self, text):
        GLib.idle_add(self.__append_to_log_thread_safe, text)

    def __append_to_log_thread_safe(self, text):
        buffer = self.log_view.get_buffer()
        buffer.insert(buffer.get_end_iter(), text, -1)
        adj = self.log_view.get_parent().get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())
        return GLib.SOURCE_REMOVE

if __name__ == "__main__":
    app = InstallerApp()
    app.run(sys.argv)
