import os
import re
import subprocess

from . import PCIManager
from . import USBManager
from . import DiskManager
from . import PrinterManager
from . import SerioManager
from . import MonitorManager


UDEV_HWDB = (
    "/usr/lib/udev/hwdb.d/"
    if os.path.exists("/usr/lib/udev/hwdb.d/")
    else "/lib/udev/hwdb.d/"
)


def extract_vendor_product(hwdb_file, vendor_text, product_text):
    if not os.path.isfile(hwdb_file):
        return None, None
    with open(hwdb_file, encoding="utf-8") as file:
        hwdb_output = file.read()

        if vendor_text in hwdb_output:
            rest = hwdb_output.split(vendor_text, 1)[1]
            vendor_name = rest.split("\n", 1)[0]
            if product_text in hwdb_output:
                product_name = rest.split(product_text, 1)[1].split("\n", 1)[0]
                return vendor_name, product_name
            elif product_text not in hwdb_output:
                return vendor_name, None
    return None, None


def get_vendor_product_name_from_udev(key, vendor_text, product_text):
    if not os.path.exists(UDEV_HWDB):
        print("{} file not found".format(UDEV_HWDB))
        return None, None

    file_name = f"20-{key}-vendor-model.hwdb"

    return extract_vendor_product(UDEV_HWDB + file_name, vendor_text, product_text)


def lookup_ids_file(file_path):
    temp_vendor = ""
    ids_lib = {}

    if not os.path.isfile(file_path):
        return ids_lib

    try:
        with open(file_path, "r", encoding="utf-8") as file_ids:
            for line in file_ids:
                # If line is tabbed or contains an hashtag skips
                if line.startswith("\t\t") or line.startswith("#"):
                    continue
                if line[:1] not in ["\t", "\n"]:
                    temp_vendor = line.split()[0]
                    ids_lib[temp_vendor] = {"name": line[6:-1]}

                if line.startswith("\t"):
                    ids_lib[temp_vendor][line.split()[0]] = {
                        "name": "{}".format(" ".join(line.split()[1:]))
                    }

    except FileNotFoundError:
        print(f"{file_path} file not found.")
        return None

    return ids_lib


def get_vendor_product_name(key, vendor, product):
    files_path = [
        os.path.dirname(os.path.abspath(__file__))+f"/../data/{key}.ids",
        f"/usr/share/misc/{key}.ids",
        f"/usr/share/hwdata/{key}.ids",
    ]
    for file_path in files_path:
        ids_lib = lookup_ids_file(file_path)
        if ids_lib != {}:
            break

    if not ids_lib:
        return None, None

    if vendor in ids_lib and product in ids_lib[vendor]:
        return ids_lib[vendor]["name"], ids_lib[vendor][product]["name"]

    return None, None


def wildcard_to_regex(pattern):
    """
    Converts a wildcard pattern (as found in the modules.alias file) to a regular expression (such as 'pci:v00008086d000027D8*').
    """
    escaped = re.escape(pattern)
    regex = "^" + escaped.replace(r"\*", ".*") + "$"
    return regex


def find_drivers(modalias):
    p = subprocess.run(
        ["/sbin/modinfo", modalias, "-F", "name"], capture_output=True, text=True
    )

    available_drivers = set(p.stdout.splitlines())

    return list(available_drivers)


hardware_info = None


def get_hardware_info():
    global hardware_info
    if hardware_info:
        return hardware_info

    pci_dev_info = PCIManager.get_pci_devices()
    usb_dev_info = USBManager.get_usb_devices()
    serio_dev_info = SerioManager.get_serio_devices()
    disks = DiskManager.get_disks()
    printers = PrinterManager.get_printers()
    displays = MonitorManager.scan_monitors()

    # HID devices
    hid_devices = USBManager.get_hid_devices()
    keyboards = [x for x in hid_devices if x["type"] == "keyboard"]
    mouses = [x for x in hid_devices if x["type"] == "mouse"]
    touchpads = [x for x in hid_devices if x["type"] == "touchpad"]
    touchscreens = [x for x in hid_devices if x["type"] == "touchscreen"]

    # Remove unnecessary "type" key:
    for d in keyboards:
        d.pop("type", None)

    for d in mouses:
        d.pop("type", None)

    for d in touchpads:
        d.pop("type", None)

    for d in touchscreens:
        d.pop("type", None)

    hardware_info = {
        "wifi": [],
        "ethernet": [],
        "bluetooth": [],
        "graphics": [],
        "camera": [],
        "audio": [],
        "fingerprint": [],
        "usb": [],
        "pci": [],
        "display": displays,
        "printer": printers,
        "storage": disks,
        "keyboard": keyboards,
        "mouse": mouses,
        "touchpad": touchpads,
        "touchscreen": touchscreens,
    }

    # Add devices from pci and usb to the categories
    for c in hardware_info:
        if c in pci_dev_info:
            hardware_info[c] += pci_dev_info[c]

        if c in usb_dev_info:
            hardware_info[c] += usb_dev_info[c]

        if c in serio_dev_info:
            hardware_info[c] += serio_dev_info[c]

    return hardware_info
