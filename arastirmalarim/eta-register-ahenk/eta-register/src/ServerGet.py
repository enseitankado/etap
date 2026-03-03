import gi
import json
import locale
import gettext
from logger import logger

gi.require_version("GLib", "2.0")
gi.require_version("Soup", "2.4")
from gi.repository import GLib, Gio, Soup
import constants as const

# Translation setup
APPNAME_CODE = "eta-register"
TRANSLATIONS_PATH = "/usr/share/locale/"
locale.bindtextdomain(APPNAME_CODE, TRANSLATIONS_PATH)
locale.textdomain(APPNAME_CODE)
gettext.bindtextdomain(APPNAME_CODE, TRANSLATIONS_PATH)
gettext.textdomain(APPNAME_CODE)

# Shortcut for translations
_ = gettext.gettext


class ServerGet(object):
    def __init__(self):
        # Store the application token
        # Create a Soup session for handling headers
        self.session = Soup.Session()

    def get(self, url, request):
        if url is None or "None" in url:
            return

        headers = const.secure_connection_header
        logger.info(f"GET Request URL: {url}")
        logger.info(f"GET Request Type: {request}")

        message = Soup.Message.new("GET", url)
        for key, value in headers.items():
            message.request_headers.append(key, value)

        cancellable = Gio.Cancellable()
        try:
            input_stream = self.session.send(message, cancellable)
            logger.info(f"GET Response Status Code: {message.status_code}")

            # Read all bytes correctly using chunks
            data_bytes = b""
            while True:
                chunk = input_stream.read_bytes(4096, cancellable)
                if not chunk or chunk.get_size() == 0:
                    break
                data_bytes += chunk.get_data()

            # Convert bytes to string
            data_str = data_bytes.decode("utf-8", errors="ignore")

            # Try to parse JSON
            try:
                # Attempt to parse as JSON first
                parsed_data = json.loads(data_str)
                self.ServerGet(parsed_data, request)
            except json.JSONDecodeError:
                # If not JSON, return as plain text
                self.ServerGet({"data": data_str}, request)

        except Exception as e:
            response = {
                "error": True,
                "message": _("Error in server request: {}").format(str(e)),
            }
            self.ServerGet(response, request)
            return response  # Added missing line to call ServerGet with response
        return

    def _open_stream(self, file, result, request):
        try:
            success, data, etag = file.load_contents_finish(result)
        except GLib.Error as error:
            logger.error(error)
            self.error_message = error.message
            logger.error(
                "{} _open_stream Error: {}".format(error.domain, error.message)
            )

            if error.domain == GLib.quark_to_string(Gio.tls_error_quark()):
                response = {
                    "error": True,
                    "tlserror": True,
                    "message": error.message,
                }
                self.ServerGet(response, request)  # Send to MainWindow
                return response

            response = {
                "error": True,
                "message": error.message,
            }
            self.ServerGet(response, request)  # Send to MainWindow
            return response

        if success:
            try:
                # Try to parse JSON
                parsed_data = json.loads(data.decode("utf-8"))
                self.ServerGet(parsed_data, request)
            except (json.JSONDecodeError, UnicodeDecodeError):
                # If not JSON, return as plain text
                self.ServerGet({"data": data.decode("utf-8", errors="ignore")}, request)
        else:
            logger.error("{} is not success".format(file))
            self.ServerGet(
                response={"error": True, "data": data.decode("utf-8", errors="ignore")}
            )  # Send to MainWindow
