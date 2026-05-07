import os


def get_serio_devices():
    def _read_file(path):
        # print(path)
        if os.path.isfile(path):
            with open(path, "r") as f:
                return f.read().strip()
        return ""

    data = {"mouse": [], "keyboard": []}
    for dev in os.listdir("/sys/bus/serio/devices"):
        dev_name = dev
        dev = f"/sys/bus/serio/devices/{dev}"
        if not "input" in os.listdir(dev):
            continue

        driver = os.readlink(f"{dev}/driver").split("/")[-1]
        for finput in os.listdir(f"{dev}/input"):
            if not finput.startswith("input"):
                continue

            info = {
                "name": _read_file(f"{dev}/input/{finput}/name"),
                "vendor_id": _read_file(f"{dev}/input/{finput}/id/vendor"),
                "product_id": _read_file(f"{dev}/input/{finput}/id/product"),
                "driver": driver,
                "bus": "serio",
                "bus_adress": dev_name,
                "input_device": finput,
            }

            if driver == "psmouse":
                data["mouse"].append(info)
            else:
                data["keyboard"].append(info)
    return data


if __name__ == "__main__":
    print(get_serio_devices())
