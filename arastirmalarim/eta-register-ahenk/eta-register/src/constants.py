from etainfo import network, info

BACKEND_IP = "api-etap.eba.gov.tr"
# BACKEND_IP = "161.9.194.180"
# BACKEND_IP = "172.16.102.248"
BACKEND_PORT = 1000
# BACKEND_PORT = 3000
BACKEND_URL = f"http://{BACKEND_IP}:{BACKEND_PORT}/api"
default_timeout = 2
node_url = f"http://{BACKEND_IP}:{BACKEND_PORT}"
network_device = network.get()


def get_check_connection_url():
    return node_url


def get_city_url():
    return BACKEND_URL + "/city"


def get_town_url(city_id):
    return BACKEND_URL + f"/town/id/{city_id}"


def get_school_url(city_id, town_id, page, search=""):
    return BACKEND_URL + f"/school/{city_id}/{town_id}?page={page}&search={search}"


def get_school_without_limit(city_id, town_id):
    return BACKEND_URL + f"/school/no-limit/{city_id}/{town_id}"


def get_check_mac_url():
    return BACKEND_URL + f"/board/check?mac={network_device.mac}"


def get_check_school_code_url(code):
    return BACKEND_URL + f"/school/code/{code}"


def get_register_board_info(city_id, town_id, school_code, unit_name):
    sys_info = info.get()
    body = {
        "city_id": int(city_id),
        "town_id": int(town_id),
        "school_code": int(school_code),
        "mac_id": network_device.mac,
        "usb": sys_info["usb"],
        "gpu": sys_info["gpu"],
        "cpu": sys_info["cpu"],
        "net": sys_info["net"],
        "mobo": sys_info["mobo"],
        "disk": sys_info["disk"],
        "unit_name": unit_name,
    }
    return body


def get_register_board_url():
    return BACKEND_URL + f"/board"


def get_update_board_url():
    return BACKEND_URL + f"/board/update"


secure_connection_header = {"etap-app-code": "eta_register!"}
