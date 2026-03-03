#!/usr/bin/env python3
import pyudev
import datetime
import os
import base64
import hashlib
import json
import sys
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

LOG_FILE = "/tmp/usb.log"

def check_root():
    """Root yetkisi kontrolü yapar."""
    if os.geteuid() != 0:
        print("Bu programı çalıştırmak için root yetkilerine sahip olmalısınız.")
        sys.exit(1)

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
    
    return log_entry, unique_id


def list_connected_devices(context):
    """Bağlı olan USB cihazlarını listeler."""
    devices = {}
    for device in context.list_devices(subsystem="block", DEVTYPE="partition"):
        if device.get("ID_BUS") == "usb":
            disk_name = device.get("DEVNAME").rstrip("1234567890")  # Ana disk adı (örneğin, /dev/sdb)
            if disk_name not in devices:
                vendor = device.get("ID_VENDOR_FROM_DATABASE", device.get("ID_VENDOR", "Bilinmiyor"))
                model = device.get("ID_MODEL_FROM_DATABASE", device.get("ID_MODEL", "Bilinmiyor"))
                devices[disk_name] = (disk_name, vendor, model)
    return list(devices.values())


def list_partitions(context, disk_name):
    """Seçilen diskteki bölümleri listeler."""
    partitions = []
    for device in context.list_devices(subsystem="block", DEVTYPE="partition"):
        if device.get("DEVNAME").rstrip("1234567890") == disk_name:
            partition_name = device.get("DEVNAME")
            fs_label = device.get("ID_FS_LABEL", "Etiket Yok")
            size_sectors = int(device.get("ID_PART_ENTRY_SIZE", 0))
            size_gb = size_sectors * 512 / (1024 ** 3)  # Sektör boyutunu GB'ye çevir
            fs_type = device.get("ID_FS_TYPE", "Bilinmiyor")
            partitions.append((partition_name, fs_label, size_gb, fs_type))
    return partitions


def encrypt_data(data, key):
    """Veriyi AES ile şifreler."""
    key = key.encode("utf-8")[:32].ljust(32, b'\0')  # 32 byte anahtar (256 bit)
    cipher = AES.new(key, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(data.encode("utf-8"), AES.block_size))
    return base64.b64encode(cipher.iv + ct_bytes).decode("utf-8")


def create_tahta_anahtar(partition_path, unique_id):
    """Seçilen bölümde .tahta_anahtar dosyası oluşturur ve bilgileri şifreleyerek kaydeder."""
    file_path = os.path.join(partition_path, ".tahta_anahtar")
    data = {
        "unique_id": unique_id,
        "username": "ozgur-koca",
        "password": "parola"
    }
    json_data = json.dumps(data, indent=4)
    encrypted_data = encrypt_data(json_data, unique_id)  # JSON verisini şifrele
    with open(file_path, "w") as f:
        f.write(encrypted_data)
    print(f"{file_path} dosyası oluşturuldu ve bilgiler şifrelenerek kaydedildi.\n")


def main():
    check_root()  # Root yetkisi kontrolü
    context = pyudev.Context()

    # Bağlı olan USB cihazlarını listele
    devices = list_connected_devices(context)
    if not devices:
        print("Bağlı USB cihazı bulunamadı.")
        return

    print("Bağlı USB cihazları:")
    for i, (disk_name, vendor, model) in enumerate(devices, start=1):
        print(f"{i}. {disk_name} - {vendor} {model}")

    # Kullanıcıdan cihaz seçmesini iste
    try:
        choice = int(input("Lütfen bir cihaz seçin (numara girin): ")) - 1
        if choice < 0 or choice >= len(devices):
            print("Geçersiz seçim!")
            return
    except ValueError:
        print("Geçersiz giriş!")
        return

    # Seçilen cihazın bilgilerini al
    selected_disk_name = devices[choice][0]
    for device in context.list_devices(subsystem="block", DEVTYPE="partition"):
        if device.get("DEVNAME").rstrip("1234567890") == selected_disk_name:
            log_entry, unique_id = log_usb_event("add", device)
            print("\n\nSeçilen cihazın bilgileri:")
            print(log_entry + "\n")
            break

    # Seçilen cihazın bölümlerini listele
    partitions = list_partitions(context, selected_disk_name)
    if not partitions:
        print("\nSeçilen cihazda bölüm bulunamadı.\n")
        return

    print("\nSeçilen cihazın bölümleri:")
    print(f"{'No':<5} {'Bölüm':<10} {'Etiket':<20} {'Boyut (GB)':<15} {'Dosya Sistemi':<15}")
    print("-" * 65)
    for i, (partition_name, fs_label, size_gb, fs_type) in enumerate(partitions, start=1):
        print(f"{i:<5} {partition_name:<10} {fs_label:<20} {size_gb:.2f} GB{'':<5} {fs_type:<15}")

    # Kullanıcıdan bölüm seçmesini iste
    try:
        partition_choice = int(input("\nLütfen bir bölüm seçin (numara girin): ")) - 1
        if partition_choice < 0 or partition_choice >= len(partitions):
            print("Geçersiz seçim!\n")
            return
    except ValueError:
        print("Geçersiz giriş!\n")
        return

    # Seçilen bölümde .tahta_anahtar dosyası oluştur
    selected_partition = partitions[partition_choice][0]
    mount_point = f"/mnt/{selected_partition.split('/')[-1]}"
    os.makedirs(mount_point, exist_ok=True)
    os.system(f"mount {selected_partition} {mount_point}")
    create_tahta_anahtar(mount_point, unique_id)
    os.system(f"umount {mount_point}")
    os.rmdir(mount_point)


if __name__ == "__main__":
    if not os.path.exists(LOG_FILE):
        open(LOG_FILE, "w").close()
    
    main()