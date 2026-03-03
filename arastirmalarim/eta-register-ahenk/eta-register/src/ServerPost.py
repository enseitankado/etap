#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep 18 14:53:00 2020

@author: fatih
"""

import json
import locale
import gettext
from logger import logger
import traceback

import gi

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


class ServerPost(object):
    def __init__(self):
        self.session = Soup.Session(user_agent="application/json")

    def send(self, uri, dic, type):
        headers = const.secure_connection_header
        logger.info(_("POST Request URL: {}").format(uri))
        logger.info(_("POST Request Type: {}").format(type))

        message = Soup.Message.new("POST", uri)

        for key, value in headers.items():
            message.request_headers.append(key, value)
        message.set_request(
            "application/json", Soup.MemoryUse.COPY, json.dumps(dic).encode("utf-8")
        )
        self.session.send_async(message, None, self.on_finished, message, type)

    def on_finished(self, session, result, message, type):
        try:
            # Get response status
            status_code = message.status_code
            logger.info(_("Server Post Response (Status {})").format(status_code))

            # Read the response
            input_stream = session.send_finish(result)

            # Check status code and handle errors
            if status_code != 200:
                error_message = _("Server returned error {}").format(status_code)
                if input_stream:
                    try:
                        data = input_stream.read_bytes(4096, None).get_data()
                        error_data = json.loads(data.decode("utf-8"))
                        error_message = error_data.get("msg", error_message)
                    except:
                        pass
                logger.error(_("Error: {}").format(error_message))
                return

            # Read response data
            if input_stream:
                try:
                    data_input_stream = Gio.DataInputStream.new(input_stream)
                    line, length = data_input_stream.read_line_utf8()
                    logger.info(_("Response line: {}").format(line))

                    # Safely parse JSON or log raw response
                    try:
                        if line:
                            parsed_data = json.loads(line)
                            logger.info(_("Parsed Response: {}").format(parsed_data))
                            self.on_success(parsed_data, type)
                        else:
                            logger.warning(_("Empty response line"))
                            error_message = _("Empty response received")
                            self.on_error(error_message)
                    except json.JSONDecodeError as json_error:
                        logger.error(_("JSON Decode Error: {}").format(json_error))
                        logger.error(_("Raw response: {}").format(line))
                        error_message = _("JSON parsing error: {}").format(json_error)
                        self.on_error(error_message)
                except Exception as read_error:
                    logger.error(_("Error reading input stream: {}").format(read_error))
                    logger.error(traceback.format_exc())
                    error_message = _("Input stream read error: {}").format(read_error)
                    self.on_error(error_message)
            else:
                logger.error(_("No input stream received"))
                error_message = _("No input stream received")
                self.on_error(error_message)

        except Exception as e:
            logger.error(_("Error in ServerPost: {}").format(e))
            logger.error(traceback.format_exc())
            error_message = _("Unexpected error: {}").format(e)
            self.on_error(error_message)
        finally:
            # Always close input stream
            if input_stream:
                try:
                    input_stream.close(None)
                except Exception as close_error:
                    logger.error(
                        _("Error closing input stream: {}").format(close_error)
                    )
                finally:
                    try:
                        input_stream = None
                    except Exception as error:
                        logger.error(_("Error closing stream: {}").format(error))

    def _close_stream(self, session, result, data):
        try:
            session.close_finish(result)
        except GLib.Error as error:
            logger.error(_("Error closing stream: {}").format(error))

    def ServerPost(self, response, data, type):
        # Placeholder method to be overridden by subclasses
        logger.info(
            _("ServerPost called with response: {} data: {} type: {}").format(
                response, data, type
            )
        )
