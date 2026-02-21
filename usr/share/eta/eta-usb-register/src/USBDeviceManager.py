#!/usr/bin/python3

import os
import psutil
from glob import glob
from pyudev import Context, Monitor, Devices
from pyudev import MonitorObserver


class USBDeviceManager:
    def __init__(self):
        self.refreshSignal = lambda a: a  # this function is set by MainWindow
        self.context = Context()
        self.monitor = Monitor.from_netlink(self.context)
        self.monitor.filter_by(subsystem="block")

        def log_event(action, device):
            print(action, device)
            self.refreshSignal()

        self.observer = MonitorObserver(self.monitor, log_event)
        self.observer.start()

    def find_usb_devices(self):
        sdb_devices = list(map(os.path.realpath, glob("/sys/block/sd*")))
        usb_devices = []
        for dev in sdb_devices:
            for prop in dev.split("/"):
                if "usb" in prop:
                    usb_devices.append(os.path.basename(dev))

        return usb_devices

    def get_mount_point(self, device_path):
        for p in psutil.disk_partitions():
            if device_path == p.device:
                return p.mountpoint
        return None

    def get_usb_devices(self):
        device_list = []
        usb_devices = self.find_usb_devices()
        for block_name in usb_devices:
            try:
                device = Devices.from_path(
                    self.context, "/sys/block/{}".format(block_name)
                )

                label = device.get("ID_FS_LABEL", "")
                vendor = device.get("ID_VENDOR", "")
                model = device.get("ID_MODEL", "NO_MODEL")

                if label == "":
                    label = "{} {}".format(vendor, model)

                # Calculate USB Capacity
                block_count = int(
                    open("/sys/block/{}/size".format(block_name)).readline()
                )
                block_size = int(
                    open(
                        "/sys/block/{}/queue/logical_block_size".format(block_name)
                    ).readline()
                )
                total_size = "{}GB".format(
                    int((block_count * block_size) / 1000 / 1000 / 1000)
                )

                partitions = self.context.list_devices(
                    subsystem="block", DEVTYPE="partition", parent=device
                )

                has_partitions = False
                for p in partitions:
                    has_partitions = True
                    # Read Size of the partition:
                    partition_block_name = p.device_node.split("/")[-1]
                    with open(
                        f"/sys/block/{block_name}/{partition_block_name}/size", "r"
                    ) as f:
                        partition_block_count = int(f.read())
                        partition_size = (
                            (partition_block_count * block_size) / 1000 / 1000
                        )

                        if partition_size < 1000:
                            partition_size = f"{partition_size:.1f} MB"
                        else:
                            partition_size = f"{(partition_size / 1000):.1f} GB"

                    uuid = p.get("ID_FS_UUID", "")

                    mounted_path = self.get_mount_point(p.device_node)

                    device_info = [
                        p.device_node,
                        mounted_path,
                        label,
                        partition_size,
                        uuid,
                    ]  # ['sda', '/media/ef/Ventoy', 'TOSHIBA TransMemory-Mx', '31.1 GB', '223C-F3F8']

                    # Add device to list
                    if block_count > 0:
                        device_list.append(device_info)

                if not has_partitions:
                    print(
                        "Error: No partitions in usb:",
                        device.device_node,
                        label,
                        total_size,
                    )
                    device_info = [
                        device.device_node,  # 'sda'
                        "",  # '/mnt/USBPartitionPath'
                        label,  # 'TOSHIBA TransMemory-Mx'
                        total_size,  # '31.1 GB'
                        "",  # '223C-F3F8'
                    ]
                    device_list.append(device_info)
                    continue
            except Exception as e:
                print("Error on reading USB devices:", e)

        return device_list

    def set_usb_refresh_signal(self, signalfunc):
        self.refreshSignal = signalfunc
