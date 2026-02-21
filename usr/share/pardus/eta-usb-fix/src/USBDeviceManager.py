#!/usr/bin/python3

"""
USBDeviceManager.py copied from pardus-usb-formatter
adapted for eta-usb-fix project
added get_partitions_with_fstype method
by Yusuf Düzgün <yusuf.duzgun@pardus.org.tr>
"""

import os
from glob import glob

from pyudev import Context, Monitor, Devices
from pyudev import MonitorObserver, DeviceNotFoundAtPathError


class USBDeviceManager:
    def __init__(self):
        self.refreshSignal = lambda a: a  # this function is set by MainWindow
        self.context = Context()
        self.monitor = Monitor.from_netlink(self.context)
        self.monitor.filter_by(subsystem="block", device_type="disk")

        def log_event(action, device):
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

    def getUSBDevices(self):
        deviceList = []
        usb_devices = self.find_usb_devices()
        for blockName in usb_devices:
            try:
                device = Devices.from_path(self.context, f"/sys/block/{blockName}")
                deviceInfo = []
                # 'sda'
                deviceInfo.append(blockName)

                # 'MYDISK Sandisk Cruzer Glide'
                deviceLabel = device.get("ID_FS_LABEL", "")
                if deviceLabel:
                    device_name = deviceLabel
                else:
                    deviceVendor = device.get("ID_VENDOR", "")
                    deviceModel = device.get("ID_MODEL", "NO_MODEL")
                    device_name = f"{deviceVendor} {deviceModel}"

                # '4GB'
                blockCount = int(open(f"/sys/block/{blockName}/size").readline())
                blockSize = int(
                    open(f"/sys/block/{blockName}/queue/logical_block_size").readline()
                )
                deviceInfo.append(f"{device_name} {int((blockCount * blockSize) / 1000 / 1000 / 1000)}GB")

                # deviceInfo example data: ['sda', 'MYDISK Sandisk Cruzer Glide 4GB']

                # Add device to list
                if blockCount > 0:
                    deviceList.append(deviceInfo)
            except DeviceNotFoundAtPathError:
                print(f"Device {blockName} not found")

        return deviceList

    def get_partitions_with_fstype(self, device_name):
        try:
            device = Devices.from_path(self.context, f"/sys/block/{device_name}")
            partitions = []
            for child in device.children:
                if child.device_type == "partition":
                    part_info = (
                        child.sys_name,
                        child.get("ID_FS_TYPE", "Unknown")
                    )
                    partitions.append(part_info)
            return partitions
        except DeviceNotFoundAtPathError:
            print(f"Device {device_name} not found")
            return []

    def setUSBRefreshSignal(self, signalfunc):
        self.refreshSignal = signalfunc
