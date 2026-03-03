#!/usr/bin/env python3
import os
import apt
import sys
import json
from etainfo import network
import gi
import logging
from datetime import datetime
import traceback
import configparser
from logger import logger

gi.require_version("GLib", "2.0")
gi.require_version("Soup", "2.4")
from gi.repository import GLib, Gio, Soup

import constants as const
import subprocess
import apt.cache
import locale
import requests
import etainfo.unit as unit
from locale import gettext as _


messaging_conf_src = "/etc/ahenk/config.d/messaging.conf"
ahenk_conf_src = "/etc/ahenk/ahenk.conf"
registration_url = "register-liderahenk.eba.gov.tr"
app_name = "ahenk"
cur_path = os.path.dirname(__file__)


APPNAME_CODE = "eta-register"
TRANSLATIONS_PATH = "/usr/share/locale/"
locale.bindtextdomain(APPNAME_CODE, TRANSLATIONS_PATH)
locale.textdomain(APPNAME_CODE)


def is_ahenk_installed():
    logger.info(_("Checking if ahenk is installed"))
    try:
        cache = apt.cache.Cache()
        app = cache[app_name]
        cache.close()
        is_installed = app.is_installed
        logger.info(_("Ahenk installation status: {}").format(is_installed))
        return is_installed
    except Exception as ex:
        logger.error(_("Error checking ahenk installation: {}").format(ex))
        return False


def sys_update():
    logger.info(_("Starting system update"))
    subprocess.call(["apt", "update", "-yq"], env={**os.environ})
    logger.info(_("System update completed"))


def check_ahenk_conf():
    logger.info(_("Checking ahenk configuration"))
    if os.path.isfile(ahenk_conf_src):
        config = configparser.ConfigParser()
        config.read(ahenk_conf_src)
        conf_uid = config.get("CONNECTION", "uid").strip()
        messaging_config = configparser.ConfigParser()
        messaging_config.read(messaging_conf_src)
        conf_host = messaging_config.get("REGISTRATION", "registration_url").strip()
        if config.has_section("CONNECTION") and not conf_uid:
            if not conf_host:
                messaging_config.set(
                    "REGISTRATION", "registration_url", registration_url
                )
            with open(messaging_conf_src, "w") as configfile:
                messaging_config.write(configfile)

            logger.info(_("Starting ahenk service"))
            #            subprocess.call(["/usr/bin/python3", "/usr/share/ahenk/ahenkd.py", "start"])
            subprocess.call(["systemctl", "enable", "ahenk"])
            subprocess.call(["systemctl", "start", "ahenk"])
        else:
            logger.info(_("Ahenk registered already"))


def sys_install():
    logger.info(_("Starting ahenk installation"))
    subprocess.call(["apt", "install", "-yq", app_name], env={**os.environ})
    logger.info(_("Ahenk installation completed"))
    check_ahenk_conf()


def set_unit_name(name):
    logger.info(_("Setting unit name to: {}").format(name))
    unit.set(name)


def register_board(opr_name, city_id, town_id, school_code, unit_name):
    logger.info(_("Starting board registration process: {}").format(opr_name))
    logger.info(
        _("Registration parameters - City: {}, Town: {}, School: {}, Unit: {}").format(
            city_id, town_id, school_code, unit_name
        )
    )
    main_loop = GLib.MainLoop()
    register_success = False
    error_message = None

    def on_finished(session, result, message):
        nonlocal register_success, error_message
        try:
            # Get response status
            status_code = message.status_code
            logger.info(_("Register Board Response (Status {})").format(status_code))
            logger.info(_("Detailed Request Information:"))
            logger.info(_("Operation: {}").format(opr_name))
            logger.info(_("City ID: {}").format(city_id))
            logger.info(_("Town ID: {}").format(town_id))
            logger.info(_("School Code: {}").format(school_code))
            logger.info(_("Unit Name: {}").format(unit_name))

            # Read the response
            input_stream = session.send_finish(result)

            # Check status code explicitly
            if status_code not in [200, 201]:
                error_message = _("Registration failed with status code {}").format(
                    status_code
                )
                logger.error(error_message)
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
                            register_success = True
                        else:
                            logger.warning(_("Empty response line"))
                            error_message = _("Empty response received")
                    except json.JSONDecodeError as json_error:
                        logger.error(_("JSON Decode Error: {}").format(json_error))
                        logger.error(_("Raw response: {}").format(line))
                        error_message = _("JSON parsing error: {}").format(json_error)
                except Exception as read_error:
                    logger.error(_("Error reading input stream: {}").format(read_error))
                    logger.error(traceback.format_exc())
                    error_message = _("Input stream read error: {}").format(read_error)
            else:
                logger.error(_("No input stream received"))
                error_message = _("No input stream received")

        except Exception as e:
            logger.error(_("Error registering board: {}").format(e))
            logger.error(traceback.format_exc())
            error_message = _("Unexpected error: {}").format(e)
        finally:
            # Always quit the main loop
            main_loop.quit()

    # Prepare board registration body
    body = const.get_register_board_info(city_id, town_id, school_code, unit_name)
    sec_con_header = const.secure_connection_header

    # Determine correct URL based on operation name
    if opr_name == "register-board":
        url = const.get_register_board_url()
    else:
        url = const.get_update_board_url()

    # Create session and message
    session = Soup.Session(user_agent="application/json")
    message = Soup.Message.new("POST", url)

    # Set headers
    for key, value in sec_con_header.items():
        message.request_headers.append(key, value)

    # Set request body
    message.set_request(
        "application/json", Soup.MemoryUse.COPY, json.dumps(body).encode("utf-8")
    )

    # Send async request
    session.send_async(message, None, on_finished, message)

    # Run the main loop
    main_loop.run()

    # Perform system update and ahenk checks only if registration was successful
    if register_success:
        sys_update()
        if not is_ahenk_installed():
            logger.info(_("Installing ahenk"))
            sys_install()
        else:
            check_ahenk_conf()

    return register_success, error_message


def update_board(uri, dic):
    logger.info(_("Starting board update process with URI: {}").format(uri))
    logger.info(_("Update parameters: {}").format(dic))
    main_loop = GLib.MainLoop()
    update_success = False
    error_message = None

    def on_finished(session, result, message):
        nonlocal update_success, error_message
        try:
            # Read the response
            input_stream = session.send_finish(result)

            # Get response status
            status_code = message.status_code
            logger.info(_("Update Board Response (Status {})").format(status_code))

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
                            update_success = True
                        else:
                            logger.warning(_("Empty response line"))
                            error_message = _("Empty response received")
                    except json.JSONDecodeError as json_error:
                        logger.error(_("JSON Decode Error: {}").format(json_error))
                        logger.error(_("Raw response: {}").format(line))
                        error_message = _("JSON parsing error: {}").format(json_error)
                except Exception as read_error:
                    logger.error(_("Error reading input stream: {}").format(read_error))
                    logger.error(traceback.format_exc())
                    error_message = _("Input stream read error: {}").format(read_error)
            else:
                logger.error(_("No input stream received"))
                error_message = _("No input stream received")

        except Exception as e:
            logger.error(_("Error updating board: {}").format(e))
            logger.error(traceback.format_exc())
            error_message = _("Unexpected error: {}").format(e)
        finally:
            # Always quit the main loop
            main_loop.quit()

    # Create session and message
    session = Soup.Session(user_agent="application/json")
    message = Soup.Message.new("POST", uri)

    # Set headers
    headers = const.secure_connection_header
    for key, value in headers.items():
        message.request_headers.append(key, value)

    # Set request body
    message.set_request(
        "application/json", Soup.MemoryUse.COPY, json.dumps(dic).encode("utf-8")
    )

    # Send async request
    session.send_async(message, None, on_finished, message)

    # Run the main loop
    main_loop.run()

    # Perform system update and ahenk checks only if update was successful
    if update_success:
        sys_update()
        if not is_ahenk_installed():
            logger.info(_("Installing ahenk"))
            sys_install()
        else:
            check_ahenk_conf()

    return update_success, error_message


if __name__ == "__main__":
    # Ensure logging is set up

    args = sys.argv
    if len(args) > 1:
        opr_name = args[1]
        logger.info(_("Starting operation: {}").format(opr_name))

        if opr_name == "register-board":
            # register-board requires 5 arguments: opr_name, city_id, town_id, school_code, unit_name
            if len(args) < 6:
                logger.error(_("Insufficient arguments for register-board"))
                logger.error(_("Insufficient arguments for register-board"))
                logger.error(
                    _(
                        "Usage: ./opr.py register-board <city_id> <town_id> <school_code> <unit_name>"
                    )
                )
                sys.exit(1)

            city_id = args[2]
            town_id = args[3]
            school_code = args[4]
            unit_name = args[5]

            logger.info(_("Starting board registration process..."))
            register_success, error_message = register_board(
                opr_name, city_id, town_id, school_code, unit_name
            )
            if not register_success:
                logger.error(_("Registration failed: {}").format(error_message))
                sys.exit(1)
            else:
                logger.info(_("Board registration completed successfully."))

        elif opr_name == "update-board":
            # update-board requires 4 arguments: opr_name, school_code, board_id, unit_name
            if len(args) < 5:
                logger.error(_("Insufficient arguments for update-board"))
                logger.error(
                    _(
                        "Usage: ./opr.py update-board <school_code> <board_id> <unit_name>"
                    )
                )
                sys.exit(1)

            school_code = args[2]
            board_id = args[3]
            unit_name = args[4]

            logger.info(_("Starting board update process..."))
            # Format data properly for update
            network_device = network.get()
            update_data = {
                "id": int(board_id),
                "school_code": int(school_code),
                "unit_name": unit_name,
                "mac_id": network_device.mac,  # Add MAC for verification
            }
            logger.info(_("Sending update request with data: {}").format(update_data))

            update_success, error_message = update_board(
                const.get_update_board_url(), update_data
            )
            if not update_success:
                logger.error(_("Update failed: {}").format(error_message))
                sys.exit(1)
            else:
                logger.info(_("Board update completed successfully."))
                logger.info(_("Board update completed successfully."))

        elif opr_name == "install-ahenk":
            logger.info(_("Starting Ahenk installation process..."))
            sys_update()
            if not is_ahenk_installed():
                logger.info(_("Installing ahenk"))
                logger.info(_("Installing ahenk"))
                sys_install()
            else:
                logger.info(_("Ahenk is already installed. Checking configuration..."))
                logger.info(_("Ahenk is already installed. Checking configuration..."))
                check_ahenk_conf()
            logger.info(_("Ahenk installation process completed."))
            logger.info(_("Ahenk installation process completed."))

    else:
        logger.error(_("No argument passed"))
        logger.error(_("No argument passed"))
        logger.error(_("Available commands:"))
        logger.error(
            _("  register-board <city_id> <town_id> <school_code> <unit_name>")
        )
        logger.error(_("  update-board <school_code> <board_id> <unit_name>"))
        logger.error(_("  install-ahenk"))
