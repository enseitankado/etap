#!/usr/bin/env python3

import json
import subprocess
import sys


def main():
    fstype_command = {
        "vfat": ["fsck.vfat", "-a"],
        "exfat": ["fsck.exfat", "-a"],
        "ext4": ["fsck.ext4", "-p"],
        "ntfs": ["ntfsfix"],
        "fat32": ["fsck.vfat", "-a"],
    }

    def fix_partition(partition, fstype):
        command = fstype_command.get(fstype)
        if command:
            subprocess.call(command + [f"/dev/{partition}"])
            subprocess.call(["sync"])
        else:
            print(f"Unknown filesystem type: {fstype}")
            print("eta-usb-fix: {} Unknown filesystem type {}".format("404", fstype), file=sys.stderr)

    def unmount_partition(partition):
        subprocess.call(["sync"])
        subprocess.call(["umount", "-q", f"/dev/{partition}"])

    def eject_usb(usb):
        subprocess.call(["eject", "-m", f"/dev/{usb}"])
        subprocess.call(["eject", "-t", f"/dev/{usb}"])

    if len(sys.argv) > 2:
        device = sys.argv[1]
        device_parts = json.loads(sys.argv[2])
        for part in device_parts:
            unmount_partition(part[0])
            fix_partition(part[0], part[1])
        eject_usb(device)


if __name__ == "__main__":
    main()
