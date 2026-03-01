# -*- coding: utf-8 -*-
import gi
gi.require_version('Soup', '2.4')
from gi.repository import Gio, GLib, Soup
import json
import os
from config import SECURE_HEADER, APPNAME_CODE, TRANSLATIONS_PATH
import locale
import gettext
from logger import logger

# Translation setup
try:
    locale.bindtextdomain(APPNAME_CODE, TRANSLATIONS_PATH)
    gettext.bindtextdomain(APPNAME_CODE, TRANSLATIONS_PATH)
    gettext.textdomain(APPNAME_CODE)
    _ = gettext.gettext
except Exception as e:
    print(f"Error setting up translation: {e}")
    _ = str


# Create a single, reusable session for the application
# Make sure the session respects system-wide proxy settings by manually checking
# environment variables, which is what `requests` does automatically.
resolver = None
proxy_env = os.environ.get("http_proxy") or os.environ.get("HTTP_PROXY")

if proxy_env:
    logger.info("DEBUG: Using http_proxy from environment: {proxy_env}".format(proxy_env=proxy_env))
    proxy_uri = Soup.URI.new(proxy_env)
    resolver = Soup.ProxyURIResolver.new(proxy_uri)
else:
    # Fallback to the default system resolver (which might use gsettings)
    resolver = Gio.ProxyResolver.get_default()

# Set proxy resolver during construction.
_session = Soup.Session(proxy_resolver=resolver)
# Disable strict SSL checking to avoid issues with some certificates (e.g., missing intermediates)
_session.set_property("ssl-strict", False)

# Also handle no_proxy environment variable
# NOTE: libsoup should handle the no_proxy environment variable automatically
# if the GProxyResolver is used correctly. We don't need to set it manually.

_session.set_property("timeout", 15)  # Add a 15-second timeout to all requests

def get_async(url, callback, send_secure_header=True):
    """
    Performs an asynchronous GET request using the modern, recommended
    Gio/Soup async pattern.
    """
    logger.info("GET request initiated for URL: {url}".format(url=url))
    message = Soup.Message.new('GET', url)
    if not message:
        logger.error("Invalid URL provided for GET request: {url}".format(url=url))
        GLib.idle_add(callback, _("Invalid URL"), None, 0)
        return

    # Add headers only if requested
    if send_secure_header:
        for key, value in SECURE_HEADER.items():
            message.request_headers.append(key, value)
    
    # Explicitly state that we accept a JSON response. This can solve
    # issues with servers that are strict about content negotiation.
    message.request_headers.append("Accept", "application/json")
    message.request_headers.append("User-Agent", "eta-register client")

    cancellable = Gio.Cancellable()
    _session.send_async(message, cancellable, _on_request_finished, (message, callback))

def post_async(url, data, callback):
    """
    Performs an asynchronous POST request with JSON data using the modern,
    recommended Gio/Soup async pattern.
    """
    logger.info("POST request initiated for URL: {url}".format(url=url))
    message = Soup.Message.new('POST', url)
    if not message:
        logger.error("Invalid URL provided for POST request: {url}".format(url=url))
        GLib.idle_add(callback, _("Invalid URL"), None)
        return

    # Add headers
    for key, value in SECURE_HEADER.items():
        message.request_headers.append(key, value)

    json_data = json.dumps(data).encode('utf-8')
    message.set_request("application/json", Soup.MemoryUse.COPY, json_data)

    cancellable = Gio.Cancellable()
    # Pass status_code to the callback for post requests as well
    _session.send_async(message, cancellable, _on_request_finished, (message, callback))


def _on_request_finished(session, result, user_data):
    """
    Internal callback that processes the response by calling session.send_finish().
    This version reads the stream in chunks to ensure the entire response is read
    without causing memory corruption.
    """
    message, user_callback = user_data
    try:
        input_stream = session.send_finish(result)
        status_code = message.status_code
        logger.info("Request to {message_get_uri} finished with status: {status_code}".format(message_get_uri=message.get_uri(), status_code=status_code))
        response_body = None

        # Read the stream in chunks to get the full response body.
        data_bytes_list = []
        while True:
            chunk = input_stream.read_bytes(4096, None) # Read in 4KB chunks
            if not chunk or chunk.get_size() == 0:
                break
            data_bytes_list.append(chunk.get_data())
        
        full_data_bytes = b"".join(data_bytes_list)

        if full_data_bytes:
            try:
                # The server may claim UTF-8, but the bytes suggest a different encoding.
                response_text = full_data_bytes.decode('utf-8')
                response_body = json.loads(response_text)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error("Failed to decode response from {message_get_uri}: {e}".format(message_get_uri=message.get_uri(), e=e))
                # Keep raw body for display when status is 200 (e.g. vendor list returned non-JSON)
                raw_display = full_data_bytes.decode('utf-8', errors='replace')
                response_body = {"_raw_body": raw_display, "_json_error": True}
        
        if 200 <= status_code < 300:
            GLib.idle_add(user_callback, None, response_body, status_code)
        else:
            error_msg = _("API Error: Status {status_code}").format(status_code=status_code)
            if response_body and isinstance(response_body, dict) and 'msg' in response_body:
                error_msg += _(" - {response_body_get_msg}").format(response_body_get_msg=response_body.get('msg'))
            logger.warning("Request to {message_get_uri} failed: {error_msg}".format(message_get_uri=message.get_uri(), error_msg=error_msg))
            GLib.idle_add(user_callback, error_msg, response_body, status_code)

    except GLib.Error as e:
        # This catches network errors (e.g., connection refused, timeout)
        logger.error("Network error for {message_get_uri}: {e}".format(message_get_uri=message.get_uri(), e=e))
        GLib.idle_add(user_callback, str(e), None, 0) # 0 for status_code indicates network error
    except (json.JSONDecodeError, TypeError):
        # This catches errors if the response is not valid JSON or data is None
        logger.error("JSON decode error for {message_get_uri}".format(message_get_uri=message.get_uri()))
        GLib.idle_add(user_callback, _("Failed to decode JSON from response"), None, 500) # Assume 500 for bad JSON
