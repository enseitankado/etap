import subprocess
import json


disks = []


def get_disks():
    global disks
    if disks:
        return disks

    p = subprocess.run(
        ["lsblk", "-bdJ", "-o", "MODEL,SIZE,TRAN,TYPE,SERIAL,RM"],
        capture_output=True,
        text=True,
    )
    if p.returncode == 0:
        output = json.loads(p.stdout)
        for d in output["blockdevices"]:
            if d["type"] != "disk":
                continue

            # Removable device, dont add to list
            if d["rm"]:
                continue

            size = int(d["size"]) / 1000 / 1000 / 1000
            size_name = "GB"
            if size > 1000:
                size = size / 1000
                size_name = "TB"
                if size > 1000:
                    size = size / 1000
                    size_name = "PB"

            size = int(size)

            disk = {
                "model": d["model"],
                "serial": d["serial"],  # private
                "type": d["tran"],
                "size": f"{size} {size_name}",
            }

            disks.append(disk)

    return disks
