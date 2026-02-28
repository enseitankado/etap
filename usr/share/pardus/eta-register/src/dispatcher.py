#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import sys
import os
import requests
import time
import urllib3

# Suppress InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from config import SECURE_HEADER, PACKAGE_TO_INSTALL
from checks import is_package_installed, get_device_check_url, interpret_device_status, ConnectionError, is_vm, is_correct_user, check_touch_vendor
import vm_detect
from logger import logger
import locale
import gettext
from config import APPNAME, PACKAGE_TO_INSTALL, TRANSLATIONS_PATH, VENDOR_LIST_URL


try:
    locale.bindtextdomain(APPNAME, TRANSLATIONS_PATH)
    gettext.bindtextdomain(APPNAME, TRANSLATIONS_PATH)
    gettext.textdomain(APPNAME)
    _ = gettext.gettext
except Exception as e:
    print("Error setting up translation: {e}")
    _ = str

PACKAGE_TO_CHECK = PACKAGE_TO_INSTALL
MAX_RETRIES = 30
DELAYS = 20

def check_device_status_with_retries():
    """
    Checks for general internet, then device registration status, with a retry mechanism.
    Retries up to MAX_RETRIES times with increasing delays if any network error occurs.
    """
    url = get_device_check_url()
    if not url:
        logger.error("Could not get MAC address for status check.")
        return "error-no-mac", None

    for attempt in range(MAX_RETRIES):
        logger.info(f"Attempt {attempt + 1} of {MAX_RETRIES} to check connections...")
        try:
            # 1. First, check for a general internet connection AND fetch vendor list.
            logger.info("Checking general internet connectivity and fetching vendor list...")
            # Disable SSL verification for development/testing environments
            response = requests.get(VENDOR_LIST_URL, timeout=10, verify=False)
            
            # Use the response to check for valid vendors
            vendor_list = response.json()
            if not check_touch_vendor(vendor_list):
                logger.error("Touch vendor check failed. Device not supported.")
                return "error-vendor", None

            logger.info("General internet connectivity and vendor check successful.")

            # 2. If successful, check the device status from the ETA server.
            logger.info("Checking device status from ETA server...")
            response = requests.get(url, headers=SECURE_HEADER, timeout=10, verify=False)
            response_body = response.json()
            status_result = interpret_device_status(response.status_code, response_body)
            
            # If we get here, both connections were successful.
            logger.info("Successfully connected to the ETA server and got status.")
            return "ok", status_result['registered']

        except (requests.RequestException, ConnectionError) as e:
            logger.warning(f"Attempt {attempt + 1} failed during connection check: {e}")
            if attempt < MAX_RETRIES - 1:
                logger.info(f"Waiting for {DELAYS} seconds before retrying...")
                time.sleep(DELAYS)
            else:
                logger.error("All attempts to connect failed.")
                return "error-no-connection", None
        except ValueError:
            # This happens if response.json() fails, indicating a server-side issue.
            # We should not retry for this.
            logger.error("Failed to parse server response (not valid JSON).")
            return "error-server-issue", None
            
    return "error-no-connection", None # Fallback, in case loop finishes unexpectedly


def main():
    logger.info("--- Dispatcher Starting ---")
    
    # --- Pre-flight Checks ---
    # These checks run before the dispatcher decides to launch the installer.

    # 1. Virtual Machine Check
    if is_vm():
        error_msg = "Error: Application cannot be run in a virtual machine. Exiting."
        logger.error(error_msg)
        print(error_msg, file=sys.stderr)
        sys.exit(1)

    # 2. User Check
    correct_user, current_user = is_correct_user()
    if not correct_user:
        error_msg = "Error: This application must be run by the 'etapadmin' user, but it is run by '{current_user}'. Exiting.".format(current_user=current_user)
        logger.error(error_msg)
        print(error_msg, file=sys.stderr)
        sys.exit(1)

    # Get the directory where the dispatcher script is located
    dispatcher_dir = os.path.dirname(os.path.abspath(__file__))
    main_gui_path = os.path.join(dispatcher_dir, "Main.py")
    installer_gui_path = os.path.join(dispatcher_dir, "installer.py")

    # --- Logic Flow ---
    # 3. Internet and Registration Check with Retries
    status, is_registered = check_device_status_with_retries()

    if status != "ok":
        # If status is not "ok", it means we couldn't determine the registration status.
        # The GUI can handle "error-no-mac", "error-no-connection", and "error-vendor".
        # We launch the GUI with the specific error status so it can inform the user.
        logger.error(f"Dispatcher exiting due to status: {status}. Launching GUI to show error.")
        subprocess.run(["python3", main_gui_path, "--status", status])
        sys.exit(1)

    # 4. Application Check (only if registered)
    if is_registered:
        if not is_package_installed():
            logger.info("Device is registered, but required package is not installed. Launching installer...")
            subprocess.run(["python3", installer_gui_path])
            sys.exit(0)
        else:
            logger.info("Device is registered and package is installed. Exiting.")
            sys.exit(0)
    else:
        # If not registered, launch the main GUI for the user to register.
        logger.info("Device not registered. Launching registration GUI...")
        subprocess.run(["python3", main_gui_path, "--status", "not-registered"])
        sys.exit(0)


if __name__ == "__main__":
    main()
