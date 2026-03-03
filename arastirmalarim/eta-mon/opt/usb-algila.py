#!/usr/bin/env python3
import pyudev
import datetime
import os
import base64
import hashlib

LOG_FILE = "/tmp/usb.log"

def log_usb_event(action, device):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "BAĞLANDI" if action == "add" else "AYRILDI"
    
    # Tüm Detaylı Bilgiler
    device_name = device.get("DEVNAME", "Bilinmiyor")
    vendor = device.get("ID_VENDOR_FROM_DATABASE", device.get("ID_VENDOR", "Bilinmiyor"))
    model = device.get("ID_MODEL_FROM_DATABASE", device.get("ID_MODEL", "Bilinmiyor"))
    serial = device.get("ID_SERIAL_SHORT", device.get("ID_SERIAL", "Bilinmiyor"))
    fs_type = device.get("ID_FS_TYPE", "Bilinmiyor")
    fs_uuid = device.get("ID_FS_UUID", device.get("ID_PART_ENTRY_UUID", "Bilinmiyor"))
    bus_id = device.get("ID_BUS", "Bilinmiyor")
    revision = device.get("ID_REVISION", "Bilinmiyor")
    size = device.get("ID_PART_ENTRY_SIZE", device.get("ID_ATA_SATA", "Bilinmiyor"))
    device_type = device.get("ID_TYPE", "Bilinmiyor")
    device_path = device.get("ID_PATH", "Bilinmiyor")
    partition_number = device.get("ID_PART_ENTRY_NUMBER", "Bilinmiyor")

    # vendor, model, serial ve revision bilgilerini birleştir
    unique_string = f"{vendor}{model}{serial}{revision}"

    # Base64 ile kodla
    encoded_string = base64.b64encode(unique_string.encode("utf-8")).decode("utf-8")

    # MD5 hash'ini üret
    unique_id = hashlib.md5(encoded_string.encode("utf-8")).hexdigest()

    # Log entry'e unique_id ekle
    log_entry = (
        f"[{timestamp}] USB {status}:\n"
        f"  - Cihaz: {device_name} (Disk: /dev/{device.get('DEVNAME').rstrip('1234567890')}, Partition: {partition_number})\n"
        f"  - Üretici: {vendor}\n"
        f"  - Model: {model}\n"
        f"  - Seri No: {serial}\n"
        f"  - Boyut: {size} Sektör\n"
        f"  - Dosya Sistemi: {fs_type}\n"
        f"  - UUID: {fs_uuid}\n"
        f"  - Revision: {revision}\n"
        f"  - Bus ID: {bus_id}\n"
        f"  - Tür: {device_type}\n"
        f"  - Fiziksel Yol: {device_path}\n"
        f"  - Tekil ID: {unique_id}\n"  # Tekil ID log entry'e eklendi
        "----------------------------------------"
    )
    
    print(log_entry + "\n")
    


def main():
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem="block", device_type="disk")
    
    print("USB olayları dinleniyor... (Çıkmak için Ctrl+C)")
    
    for device in iter(monitor.poll, None):
        if device.action in ("add", "remove"):
            log_usb_event(device.action, device)

if __name__ == "__main__":
    if not os.path.exists(LOG_FILE):
        open(LOG_FILE, "w").close()
    
    try:
        main()
    except KeyboardInterrupt:
        print("\nBetik sonlandırıldı.")