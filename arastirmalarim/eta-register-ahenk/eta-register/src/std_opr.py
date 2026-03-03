import gi
from logger import logger

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Gdk, Gio
import time
import os
import locale
import subprocess
from enums import REQ

APPNAME_CODE = "eta-register"
TRANSLATIONS_PATH = "/usr/share/locale/"
locale.bindtextdomain(APPNAME_CODE, TRANSLATIONS_PATH)
locale.textdomain(APPNAME_CODE)
from locale import gettext as _


def start_prc(window, cmd, callback):
    logger.info(_("Starting process execution with command: {}").format(" ".join(cmd)))
    """
    Start a process asynchronously and handle its execution with a callback

    Args:
        window: The main window instance
        cmd (list): Command to execute
        callback (function): Callback function to handle process result
    """

    def async_process_execution():
        try:
            # Print debug information about the command
            logger.info(_("Executing command: {}").format(" ".join(map(str, cmd))))

            # Use GLib's async process execution
            pid, std_in, std_out, std_err = GLib.spawn_async(
                cmd,
                flags=GLib.SpawnFlags.DO_NOT_REAP_CHILD,
                standard_output=True,
                standard_error=True,
            )
            logger.info(_("Process started with PID: {}").format(pid))

            # Create IO channels for stdout and stderr
            stdout_channel = GLib.IOChannel(std_out)
            stderr_channel = GLib.IOChannel(std_err)

            # Capture stdout
            def on_stdout(channel, condition):
                if condition == GLib.IO_HUP:
                    return False
                try:
                    line = channel.readline().strip()
                    if line:
                        logger.info(_("STDOUT: {}").format(line))
                except Exception as e:
                    logger.error(_("Error reading stdout: {}").format(e))
                return True

            # Capture stderr
            def on_stderr(channel, condition):
                if condition == GLib.IO_HUP:
                    return False
                try:
                    line = channel.readline().strip()
                    if line:
                        logger.error(_("STDERR: {}").format(line))
                except Exception as e:
                    logger.error(_("Error reading stderr: {}").format(e))
                return True

            # Watch for process completion
            def child_watch_callback(pid, status):
                logger.info(
                    _("Process {} finished with status: {}").format(pid, status)
                )
                # Check process exit status
                if os.WIFEXITED(status):
                    exit_code = os.WEXITSTATUS(status)
                    success = exit_code == 0
                    logger.info(
                        _("Process exit code: {}, Success: {}").format(
                            exit_code, success
                        )
                    )

                    # Check for specific pkexec authentication dismissal
                    if not success:
                        logger.warning(_("Authentication was dismissed"))
                        # Run dialog in main thread
                        GLib.idle_add(show_auth_error_dialog)

                    # Call callback in main thread
                    GLib.idle_add(callback, success)
                else:
                    logger.error(_("Process did not exit normally"))
                    # Call callback in main thread
                    GLib.idle_add(callback, False)

            # Function to show authentication error dialog
            def show_auth_error_dialog():
                logger.info(_("Showing authentication error dialog"))
                dialog = Gtk.MessageDialog(
                    parent=window.ui_main_window,
                    flags=0,
                    message_type=Gtk.MessageType.WARNING,
                    buttons=Gtk.ButtonsType.OK,
                    text=_("Authentication Cancelled"),
                )
                dialog.format_secondary_text(
                    _(
                        "The operation requires administrator privileges. Please complete the authentication."
                    )
                )
                dialog.run()
                dialog.destroy()

                # Switch back to the main stack
                window.switch_main_stack(None, "main")

            # Add watches for stdout and stderr
            GLib.io_add_watch(stdout_channel, GLib.IO_IN | GLib.IO_HUP, on_stdout)
            GLib.io_add_watch(stderr_channel, GLib.IO_IN | GLib.IO_HUP, on_stderr)

            # Add child watch to track process completion
            GLib.child_watch_add(GLib.PRIORITY_DEFAULT, pid, child_watch_callback)

        except Exception as e:
            # Catch and report any unexpected errors
            logger.error(_("Unexpected error executing command: {}").format(e))
            # Call callback in main thread
            GLib.idle_add(callback, False, str(e))

    # Run the async execution
    GLib.idle_add(async_process_execution)


def on_process_stdout(src, cond, self):
    logger.info(_("Processing stdout"))
    if cond == GLib.IO_HUP:
        return False
    line = src.readline().strip()
    return True


def on_process_stderr(src, cond, self):
    logger.info(_("Processing stderr"))
    if cond == GLib.IO_HUP:
        return False
    line = src.readline().strip()
    return True


def on_process_stdext(pid, stat, self):
    logger.info(_("Process {} finished with status: {}").format(pid, stat))
    if stat == 0:
        logger.info(_("Ahenk installation successful"))
        self.ui_status_label.set_text(_("Ahenk installed successfully. Quitting"))
        self.switch_main_stack(None, "main")
        dialog_response = self.ui_registered_dialog.run()
        if dialog_response == Gtk.ResponseType.OK:
            self.application.quit()
    else:
        logger.error(_("Ahenk installation failed"))
        self.ui_status_label.set_text(
            _("An error occured while installing Ahenk. Quitting")
        )
        dialog_response = self.ui_error_dialog.run()
        if dialog_response == Gtk.ResponseType.OK:
            self.ui_error_dialog.hide()
            self.switch_main_stack(None, "main")
        elif dialog_response == Gtk.ResponseType.CANCEL:
            self.ui_error_dialog.destroy()
            self.application.quit()
