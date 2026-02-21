# -*- coding: utf-8 -*-

import apt
from etainfo import network, info
from config import BACKEND_URL
from logger import logger
import subprocess
from logger import logger
import vm_detect
import pwd
import os
import locale
import gettext
from config import REQUIRED_USER, PACKAGE_TO_INSTALL, APPNAME, TRANSLATIONS_PATH, VENDOR_LIST_URL

# Basic Translation Setup
try:
    locale.bindtextdomain(APPNAME, TRANSLATIONS_PATH)
    gettext.bindtextdomain(APPNAME, TRANSLATIONS_PATH)
    gettext.textdomain(APPNAME)
    _ = gettext.gettext
except Exception as e:
    print(f"Error setting up translation: {e}")
    _ = str


# --- URL Generators ---

def get_device_check_url():
    """Returns the URL to check if the current device is registered."""
    mac_address = get_mac_address()
    if not mac_address:
        return None
    return f"{BACKEND_URL}/board/check?mac={mac_address}"

def get_school_code_url(code):
    """Returns the URL to verify a school code."""
    return f"{BACKEND_URL}/school/code/{code}"

def get_register_device_url():
    """Returns the URL for the device registration endpoint."""
    return f"{BACKEND_URL}/board"

def get_update_device_url():
    """Returns the URL for the device update endpoint."""
    return f"{BACKEND_URL}/board/update"

def get_cities_url():
    """Returns the URL to fetch all cities."""
    return f"{BACKEND_URL}/city"

def get_towns_url(city_id):
    """Returns the URL to fetch towns for a given city."""
    return f"{BACKEND_URL}/town/id/{city_id}"

def get_schools_url(city_id, town_id):
    """Returns the URL to fetch schools for a given town."""
    return f"{BACKEND_URL}/school/no-limit/{city_id}/{town_id}"

# --- Payload/Data Generators ---

def get_register_payload(school_data, unit_name):
    """
    Constructs the JSON payload for device registration using
    system information from etainfo.
    """
    sys_info = info.get()
    mac_address = get_mac_address()
    if not mac_address or not sys_info:
        logger.error("Could not generate registration payload due to missing MAC address or system info.")
        return None

    # Unit name is now required
    if not unit_name or not unit_name.strip():
        logger.error("Could not generate registration payload: unit_name is required but was not provided.")
        return None

    payload = {
        "city_id": int(school_data.get("city_id")),
        "town_id": int(school_data.get("town_id")),
        "school_code": int(school_data.get("code")),
        "mac_id": mac_address,
        "usb": sys_info.get("usb"),
        "gpu": sys_info.get("gpu"),
        "cpu": sys_info.get("cpu"),
        "net": sys_info.get("net"),
        "mobo": sys_info.get("mobo"),
        "disk": sys_info.get("disk"),
        "unit_name": unit_name.strip(),
    }
    return payload

def get_update_payload(board_id, school_data, unit_name):
    """
    Constructs the JSON payload for device update, matching the old API's requirements.
    """
    mac_address = get_mac_address()
    if not mac_address:
        logger.error("Could not generate update payload due to missing MAC address.")
        return None
    
    # Unit name is now required
    if not unit_name or not unit_name.strip():
        logger.error("Could not generate update payload: unit_name is required but was not provided.")
        return None
    
    payload = {
        "id": board_id,
        "school_code": int(school_data.get("code")),
        "unit_name": unit_name.strip(),
        "mac_id": mac_address,
    }
    return payload

# --- System Checks ---

def get_mac_address():
    """
    Retrieves the MAC address of the primary network device.
    """
    try:
        net_info = network.get()
        mac = net_info.mac
        logger.info("Retrieved MAC address: {mac}".format(mac=mac))
        return mac
    except Exception as e:
        logger.error("Error getting MAC address: {e}".format(e=e))
        return None

def get_current_user():
    """
    Safely retrieves the current user's login name.
    Tries os.getlogin() first, falls back to pwd.getpwuid() for environments
    without a controlling TTY.
    """
    try:
        return os.getlogin()
    except OSError:
        logger.warning("os.getlogin() failed, falling back to pwd.getpwuid()")
        return pwd.getpwuid(os.getuid())[0]


def is_correct_user():
    """
    Checks if the current user is the required user specified in the config.
    Returns:
        tuple: (bool, str) where bool is True if the user is correct,
               and str is the current username.
    """
    current_user = get_current_user()
    is_correct = (current_user == REQUIRED_USER)
    if not is_correct:
        logger.error("User check failed. Required: '{REQUIRED_USER}', Found: '{current_user}'.".format(REQUIRED_USER=REQUIRED_USER, current_user=current_user))
    return is_correct, current_user


def is_vm():
    """
    Checks if the application is running inside a virtual machine.
    """
    is_vm_status = vm_detect.is_vm()
    if is_vm_status:
        logger.error("Application cannot be run in a virtual machine.")
    return is_vm_status


def is_package_installed():
    """
    Checks if the required package (specified in config.py) is installed
    using the apt library.
    """
    cache = apt.Cache()
    try:
        package = cache[PACKAGE_TO_INSTALL]
        if package.is_installed:
            logger.info("'{PACKAGE_TO_INSTALL}' package is installed.".format(PACKAGE_TO_INSTALL=PACKAGE_TO_INSTALL))
            return True
        else:
            logger.info("'{PACKAGE_TO_INSTALL}' package is not installed.".format(PACKAGE_TO_INSTALL=PACKAGE_TO_INSTALL))
            return False
    except KeyError:
        logger.warning("'{PACKAGE_TO_INSTALL}' package not found in apt cache. Assuming not installed.".format(PACKAGE_TO_INSTALL=PACKAGE_TO_INSTALL))
        return False


def check_general_connectivity_async(callback):
    """
    Checks for internet connection and fetches the vendor list.
    """
    import network  # Local import to avoid circular dependencies
    # Using VENDOR_LIST_URL to check connection and get the list simultaneously.
    # The header is explicitly disabled for this external request.
    network.get_async(VENDOR_LIST_URL, callback, send_secure_header=False)


def check_touch_vendor(allowed_vendors):
    """
    Checks if any of the connected USB devices match the allowed vendors list.
    """
    try:
        # sys_info = info.get()
        # Ensure sys_info is valid
        # if not sys_info:
        #     logger.error("Could not retrieve system info.")
        #     return False

        # usb_devices = sys_info.get("usb", [])
        usb_devices = get_connected_usb_devices_list()
        
        # Log detected devices for debugging
        # logger.info(f"Detected USB devices: {usb_devices}")
        # logger.info(f"Allowed vendors: {allowed_vendors}")

        if not allowed_vendors:
             logger.warning("Allowed vendor list is empty.")
             return False

        # Normalize allowed_vendors to a list of strings
        normalized_allowed_vendors = []
        if isinstance(allowed_vendors, list):
            for v in allowed_vendors:
                if isinstance(v, str):
                    normalized_allowed_vendors.append(v)
                elif isinstance(v, dict) and "vendor" in v:
                    normalized_allowed_vendors.append(str(v["vendor"]))

        for device in usb_devices:
            # Extract the vendor ID from the device dictionary
            device_vendor = device.get('vendor', '').lower()
            
            for vendor in normalized_allowed_vendors:
                allowed_vendor = vendor.lower()
                if (allowed_vendor == device_vendor) or \
                   (allowed_vendor.startswith("0x") and allowed_vendor[2:] == device_vendor) or \
                   (device_vendor.startswith("0x") and device_vendor[2:] == allowed_vendor):
                    
                    logger.info("Matched vendor '{vendor}' in device '{device}'".format(vendor=vendor, device=device))
                    return True
        
        logger.warning("No matching touch vendor found.")
        return False

    except Exception as e:
        logger.error("Error checking touch vendor: {e}".format(e=e))
        return False

# --- USB Listing Logic ---

USB_IDS_PATHS = [
    "/usr/share/misc/usb.ids",
    "/usr/share/hwdata/usb.ids",
    "/var/lib/usbutils/usb.ids"
]

def load_usb_ids():
    """
    Parses the usb.ids file into a dictionary for fast lookup.
    """
    usb_db = {}
    path = None
    for p in USB_IDS_PATHS:
        if os.path.exists(p):
            path = p
            break
            
    if not path:
        return {}

    current_vendor_id = None
    try:
        with open(path, 'r', encoding='latin-1') as f:
            for line in f:
                line = line.rstrip()
                if not line or line.startswith('#'): continue
                
                # Check for Vendor
                if line[0] != '\t' and len(line) > 4:
                    parts = line.split(maxsplit=1)
                    if len(parts) == 2:
                        vid = parts[0].lower()
                        name = parts[1]
                        usb_db[vid] = {'name': name, 'products': {}}
                        current_vendor_id = vid
                    else:
                        current_vendor_id = None
                        
                # Check for Product
                elif line.startswith('\t') and len(line) > 5 and current_vendor_id:
                    parts = line.strip().split(maxsplit=1)
                    if len(parts) == 2:
                        pid = parts[0].lower()
                        name = parts[1]
                        if current_vendor_id in usb_db:
                            usb_db[current_vendor_id]['products'][pid] = name
    except Exception:
        return {}
    return usb_db

def get_connected_usb_devices_as_string():
    """
    Scans /sys/bus/usb/devices/ and resolves names using usb.ids file logic.
    Returns a formatted string table.
    """
    base_path = "/sys/bus/usb/devices"
    devices_output = []
    
    # Load DB
    usb_db = load_usb_ids()
    
    # Header
    header = f"{'VENDOR':<10} {'DEVICE':<10} {'NAME'}"
    devices_output.append(header)
    devices_output.append("-" * 60)

    if not os.path.exists(base_path):
        return _("Error: USB subsystem not found.")

    try:
        entries = sorted(os.listdir(base_path))
    except OSError:
        return _("Error: Cannot access USB devices.")

    for entry in entries:
        if ':' in entry: continue
        device_path = os.path.join(base_path, entry)
        
        try:
            vid_path = os.path.join(device_path, "idVendor")
            if not os.path.exists(vid_path): continue
            with open(vid_path, 'r') as f:
                vendor_id = f.read().strip().lower()

            pid_path = os.path.join(device_path, "idProduct")
            if not os.path.exists(pid_path): continue
            with open(pid_path, 'r') as f:
                product_id = f.read().strip().lower()

            vendor_name = ""
            product_name = ""
            
            # DB Lookup
            if vendor_id in usb_db:
                vendor_name = usb_db[vendor_id]['name']
                if product_id in usb_db[vendor_id]['products']:
                    product_name = usb_db[vendor_id]['products'][product_id]
            
            # SysFS Fallback
            if not vendor_name:
                man_path = os.path.join(device_path, "manufacturer")
                if os.path.exists(man_path):
                    with open(man_path, 'r') as f:
                         vendor_name = f.read().strip()
            if not product_name:
                prod_path = os.path.join(device_path, "product")
                if os.path.exists(prod_path):
                    with open(prod_path, 'r') as f:
                        product_name = f.read().strip()

            final_name = ""
            if vendor_name and product_name:
                 final_name = f"{vendor_name} {product_name}"
            elif vendor_name:
                final_name = vendor_name
            elif product_name:
                final_name = product_name
            else:
                final_name = _("Unknown Device")

            line = f"{vendor_id:<10} {product_id:<10} {final_name}"
            devices_output.append(line)

        except OSError:
            continue

    if len(devices_output) <= 2:
        return _("No USB devices found.")

    return "\n".join(devices_output)

def get_connected_usb_devices_list():
    """
    Scans /sys/bus/usb/devices/ and resolves names using usb.ids file logic.
    Returns a list of dictionaries: [{'vendor': '...', 'device': '...', 'name': '...'}]
    """
    base_path = "/sys/bus/usb/devices"
    devices_list = []
    
    # Load DB
    usb_db = load_usb_ids()
    
    if not os.path.exists(base_path):
        return []

    try:
        entries = sorted(os.listdir(base_path))
    except OSError:
        return []

    for entry in entries:
        if ':' in entry: continue
        device_path = os.path.join(base_path, entry)
        
        try:
            vid_path = os.path.join(device_path, "idVendor")
            if not os.path.exists(vid_path): continue
            with open(vid_path, 'r') as f:
                vendor_id = f.read().strip().lower()

            pid_path = os.path.join(device_path, "idProduct")
            if not os.path.exists(pid_path): continue
            with open(pid_path, 'r') as f:
                product_id = f.read().strip().lower()

            vendor_name = ""
            product_name = ""
            
            # DB Lookup
            if vendor_id in usb_db:
                vendor_name = usb_db[vendor_id]['name']
                if product_id in usb_db[vendor_id]['products']:
                    product_name = usb_db[vendor_id]['products'][product_id]
            
            # SysFS Fallback
            if not vendor_name:
                man_path = os.path.join(device_path, "manufacturer")
                if os.path.exists(man_path):
                    with open(man_path, 'r') as f:
                         vendor_name = f.read().strip()
            if not product_name:
                prod_path = os.path.join(device_path, "product")
                if os.path.exists(prod_path):
                    with open(prod_path, 'r') as f:
                        product_name = f.read().strip()

            final_name = ""
            if vendor_name and product_name:
                 final_name = f"{vendor_name} {product_name}"
            elif vendor_name:
                final_name = vendor_name
            elif product_name:
                final_name = product_name
            else:
                final_name = _("Unknown Device")

            devices_list.append({
                'vendor': vendor_id,
                'device': product_id,
                'name': final_name
            })

        except OSError:
            continue

    return devices_list

# --- Status Interpretation ---

class ConnectionError(Exception):
    """Custom exception for network-related errors during status check."""
    pass

def interpret_device_status(status_code, response_body):
    """
    Interprets the HTTP response from the device check endpoint.
    It prioritizes finding a 'registered' key in the response body,
    even if the HTTP status code indicates an error.
    """
    logger.info("Interpreting device status. Status code: {status_code}".format(status_code=status_code))

    # First, check if the response body contains the registration status,
    # regardless of the HTTP status code. This handles cases where the server
    # sends an error code (like 500) but still provides a meaningful payload.
    if isinstance(response_body, dict) and 'registered' in response_body:
        registered = response_body.get('registered', False)
        logger.info("Found 'registered' key in response. Status: {registered}".format(registered=registered))
        return {'registered': registered}

    # If the 'registered' key is not in the response, we treat any non-200
    # status as a connection/server error.
    logger.warning("Response did not contain a 'registered' key. Analyzing status code.")
    if status_code == 200:
        # We got a 200 OK, but the body was invalid.
        logger.error("Invalid response body received for status 200: {response_body}".format(response_body=response_body))
        raise ConnectionError(_("Invalid response from server: {response_body}").format(response_body=response_body))

    # For all other non-200 cases where the key was not found.
    error_message = _("Server returned status {status_code}").format(status_code=status_code)
    if isinstance(response_body, dict) and response_body.get("msg"):
        error_message += _(": {msg}").format(msg=response_body.get('msg'))
    raise ConnectionError(error_message)
