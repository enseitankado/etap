import os
from . import HardwareDetector


def read_file(filepath):
    """Reads the first line of a file. Returns None if the file is not found."""
    try:
        with open(filepath) as f:
            return f.readline().strip()
    except FileNotFoundError:
        print(f"File not found: {filepath}")
    return None


def get_interface_info(device_path):
    info = {"driver_link": "", "interface_id": "", "modalias_id": ""}
    # Scan interfaces
    for device_file in os.listdir(device_path):
        if ":" in device_file:
            iface_dir = os.path.join(device_path, device_file)

            driver_link_path = os.path.join(device_path, iface_dir, "driver")
            # MODALIAS=usb:v048Dp600Bd0003dc00dsc00dp00ic03isc00ip00in01
            modalias_id = read_file(os.path.join(device_path, iface_dir, "modalias"))
            # Read interface class subclass protocol f exist
            i_class = ""
            i_subclass = ""
            i_protocol = ""
            if modalias_id:
                ic_index = modalias_id.index("ic")
                if ic_index:
                    i_class = modalias_id[ic_index + 2 :][0:2]
                    i_subclass = modalias_id[ic_index + 7 :][0:2]
                    i_protocol = modalias_id[ic_index + 11 :][0:2]

            if i_class and i_class != "FF" and i_class != "FE":
                info["driver_link"] = driver_link_path
                info["interface_id"] = (
                    i_class + " " + i_subclass + " " + i_protocol
                ).strip()
                info["modalias_id"] = modalias_id

                return info

    return info


def get_sys_bus_uevent():
    """
    Reads USB device information such as driver, vendor, product, and class ID
    from /sys/bus/usb/devices

    Returns:
        list: A list of dictionaries containing driver, vendor, product, and class_id
    """
    dev_path = "/sys/bus/usb/devices"
    infos = []

    if not os.path.exists(dev_path):
        return infos  # Return empty list if path doesn't exist

    for entry in os.listdir(dev_path):
        if ":" in entry:
            continue  # Skip interface subdirectories like 1-8:1.0
        if "usb" in entry:
            continue  # Skip interface subdirectories like usb1, usb2
        device_path = os.path.join(dev_path, entry)

        vendor_id = read_file(os.path.join(device_path, "idVendor"))
        product_id = read_file(os.path.join(device_path, "idProduct"))
        dev_class = read_file(os.path.join(device_path, "bDeviceClass"))
        dev_protocol = read_file(os.path.join(device_path, "bDeviceProtocol"))
        dev_subclass = read_file(os.path.join(device_path, "bDeviceSubClass"))
        busnum = read_file(os.path.join(device_path, "busnum"))
        devnum = read_file(os.path.join(device_path, "devnum"))

        product_file = os.path.join(device_path, "product")
        product = None
        if os.path.exists(product_file):
            product = read_file(product_file)

        # Construct the interface directory name (e.g., 1-8:1.0)
        # Scan interfaces:
        interface_info = get_interface_info(device_path)
        driver_link_path = interface_info["driver_link"]

        driver = None
        if os.path.exists(driver_link_path):
            try:
                driver = os.readlink(driver_link_path).split("/")[-1]
            except OSError as e:
                print(f"Failed to read symlink: {driver_link_path} → {e}")

        # Create a fresh dictionary per device
        info = {
            "driver": driver,
            "vendor_id": vendor_id,
            "product_id": product_id,
            "modalias_id": interface_info["modalias_id"],
            "class_id": " ".join([dev_class, dev_protocol, dev_subclass]),
            "interface_id": interface_info["interface_id"],
            "product": product,
            "busnum": busnum,
            "devnum": devnum,
        }

        infos.append(info)
        # print(info)  # Debug output

    return infos


def get_hid_input_name(input_path):
    name_path = os.path.join(input_path, "name")
    if not os.path.exists(name_path):
        return ""

    with open(name_path, "r") as f:
        return f.read()

    return ""


def get_hid_input_type(input_path):
    modalias_path = os.path.join(input_path, "modalias")
    if not os.path.exists(modalias_path):
        return ""

    with open(modalias_path, "r") as f:
        data = f.read()
        capabilities = data.split("-")[1]
        events = []
        keys = []
        others = []

        current_arr = events
        current_value = ""
        for c in capabilities:
            if c == ",":
                current_arr.append(current_value)
                current_value = ""
                continue

            if c.islower() and c.isalpha():
                if c == "e":
                    current_arr = events
                elif c == "k":
                    current_arr = keys
                else:
                    current_arr = others
            else:
                current_value += c

        # print("---hid---")
        # print("modalias:", modalias_path)
        # print("events:", events)
        # print("keys:", keys)

        BTN_TOUCH = "14A" in keys  # touch support
        BTN_RIGHT = "111" in keys  # mouse right click
        EV_REL = "2" in events  # mouse, relative movement
        # EV_ABS = "3" in events # touch, absolute position
        EV_REP = (
            "14" in events
        )  # keyboard detection, repeat key strokes on pressed down

        if BTN_TOUCH:
            if BTN_RIGHT:
                return "touchpad"
            else:
                return "touchscreen"
        elif BTN_RIGHT and EV_REL:
            return "mouse"
        elif EV_REP:
            return "keyboard"

    return ""


hid_devices = []


def get_hid_devices():
    global hid_devices
    if hid_devices:
        return hid_devices

    """
    Reads HID device information from keyboards, mouses etc.
    from /sys/bus/hid/devices

    Returns:
        list: A list of dictionaries containing name, address etc. of device
    """
    dev_path = "/sys/bus/hid/devices"

    if not os.path.exists(dev_path):
        return hid_devices  # Return empty list if path doesn't exist

    for entry in os.listdir(dev_path):
        device_path = os.path.join(dev_path, entry)

        # Create a fresh dictionary per device
        info = {
            "name": "",
            "driver": "",
            "vendor_id": "",
            "product_id": "",
            "bus": "",
            "bus_address": "",
            "type": "",
            "input_device": "",
        }

        # Base HID device informations
        with open(os.path.join(device_path, "uevent"), "r") as f:
            data = f.read()
            for line in data.splitlines():
                key, value = line.split("=")
                if key == "DRIVER":
                    info["driver"] = value
                elif key == "HID_NAME":
                    info["name"] = value
                elif key == "HID_ID":
                    bus, vendor, product = value.split(":")
                    info["bus_address"] = f"0x{int(bus, base=16):01X}"
                    info["vendor_id"] = f"0x{int(vendor, base=16):01X}"
                    info["product_id"] = f"0x{int(product, base=16):01X}"
                elif key == "HID_PHYS":
                    if "usb-" in value:
                        # example data: usb-0000:00:14.0-6.2.5/input0
                        info["bus"] = "usb"
                    elif "i2c-" in value:
                        # example data: i2c-UNIW0001:00
                        info["bus"] = "i2c"
                    elif len(value.split(":")) == 6 and len(value) == 17:
                        # example bluetooth address: 64:6c:80:3f:d6:ae
                        info["bus"] = "bluetooth"

        # is input device? (mouse, keyboard, touch)
        input_dir = os.path.join(device_path, "input")
        if os.path.exists(input_dir):
            for input_device in os.listdir(input_dir):
                info_input = info.copy()
                input_device_path = os.path.join(input_dir, input_device)

                # Get Type and name
                input_type = get_hid_input_type(input_device_path)
                input_name = get_hid_input_name(input_device_path).strip()

                if input_name:
                    info_input["name"] = input_name

                # print("type", info_input["type"])
                if input_type != "":
                    info_input["type"] = input_type
                    info_input["input_device"] = input_device
                    # print(info_input["name"], input_device)

                    hid_devices.append(info_input)

    return hid_devices


def match_class_with_category(class_id):
    device_classes = {
        "02": "ethernet",
        "01": "audio",
        "e0 01 01": "bluetooth",
        "ef 01": "camera",
        "0e": "camera",
        "ff ff": "fingerprint",
        "e0 02": "wifi",
        "2c 06": "ethernet",
        "07": "printer",
    }

    for key, value in device_classes.items():
        if class_id.startswith(key):
            return value
    return None


def match_driver_with_category(driver):
    device_classes = {
        "btusb": "bluetooth",
        "uvcvideo": "camera",
        "cdc_ether": "ethernet",
    }

    if driver in device_classes:
        return device_classes[driver]

    return None


usb_devices = None


def is_hid_device(usb):
    def match(var1, var2):
        return var1.lower() == "0x"+var2.lower()
    for hid in get_hid_devices():
        if match(hid["vendor_id"] ,usb["vendor_id"]) and \
            match(hid["product_id"], usb["product_id"]):
            return True
    return False


def get_usb_devices():
    global usb_devices
    if usb_devices:
        return usb_devices

    dev_info = get_sys_bus_uevent()

    data = {}
    for usb in dev_info:
        if usb.get("class_id", "").startswith("09"):
            # USB BUS, Skip
            continue

        class_category = match_class_with_category(usb.get("class_id", ""))
        driver_category = match_driver_with_category(usb.get("driver", ""))
        interface_category = match_class_with_category(usb.get("interface_id", ""))

        # print("---------")
        # print("product:", usb.get("product", ""))
        # print("class_id:", usb.get("class_id", ""))
        # print("interface_id:", usb.get("interface_id", ""))

        if driver_category:
            category = driver_category
        elif class_category:
            category = class_category
        elif interface_category:
            category = interface_category
        elif is_hid_device(usb):
            category = "usb-hid"
        else:
            category = "usb"

        if category not in data:
            data[category] = []

        available_drivers = HardwareDetector.find_drivers(usb["modalias_id"])
        vendor, name = HardwareDetector.get_vendor_product_name(
            "usb", usb["vendor_id"], usb["product_id"]
        )

        vendor_upper = usb["vendor_id"].upper()
        product_upper = usb["product_id"].upper()

        if name is None or vendor is None:
            vendor_text = f"usb:v{vendor_upper}*\n ID_VENDOR_FROM_DATABASE="
            product_text = (
                f"usb:v{vendor_upper}p{product_upper}*\n ID_MODEL_FROM_DATABASE="
            )

            vendor, name = HardwareDetector.get_vendor_product_name_from_udev(
                "usb", vendor_text, product_text
            )

        if name is None:
            name = usb["product"]

        device_id = f"{vendor_upper}:{product_upper}"

        busnum = f"{int(usb['busnum']):04}"
        devnum = f"{int(usb['devnum']):04}"
        bus_address = f"{busnum}:{devnum}"

        if not vendor:
            vendor = ""

        # Big corp renaming:
        if "INTEL" in vendor.upper():
            vendor = "Intel"

        device = {
            "device_id": device_id,
            "name": name,
            "vendor": vendor,
            "driver": usb["driver"],
            "available_drivers": available_drivers,
            "bus": "usb",
            "bus_address": bus_address,
        }

        for k in device.keys():
            if device[k] is None:
                device[k] = ""

        data[category].append(device)

    usb_devices = data
    return usb_devices
