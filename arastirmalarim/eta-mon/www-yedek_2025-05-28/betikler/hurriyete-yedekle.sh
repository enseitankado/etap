#!/bin/bash

# --- Yedekleme Ayarları ---
SOURCE_DIR="/var/www/html"
# CIFS paylaşım yolu. Boşlukları tırnak içine alınarak belirtilir.
DEST_SHARE="//hurriyet.local/FTP Kişisel/Özgür Koca/istiklal-www-yedekler"
# Geçici olarak ağ paylaşımını bağlayacağımız yerel dizin
MOUNT_POINT="/mnt/backup_share_istiklal"
SMB_USER="softadmin"
SMB_PASS="soft0admin"
# Zip dosyasını önce yerelde oluşturmak için geçici dizin
TMP_DIR="/tmp"
# Log dosyası
LOG_FILE="/var/log/www_html_backup.log"

# --- Loglama Fonksiyonu ---
# Betiğin çıktısını hem konsola hem de log dosyasına yazar
exec > >(tee -a "$LOG_FILE")
exec 2>&1

echo "$(date '+%Y-%m-%d %H:%M:%S'): --- Yedekleme Başladı ---"

# --- Mount Noktasını ve Geçici Dizini Oluşturma ---
echo "$(date '+%Y-%m-%d %H:%M:%S'): Mount noktası ($MOUNT_POINT) ve geçici dizin ($TMP_DIR) oluşturuluyor..."
mkdir -p "$MOUNT_POINT" || { echo "$(date '+%Y-%m-%d %H:%M:%S'): Hata: Mount noktası dizini oluşturulamadı. Çıkılıyor."; exit 1; }
mkdir -p "$TMP_DIR" || { echo "$(date '+%Y-%m-%d %H:%M:%S'): Hata: Geçici dizin oluşturulamadı. Çıkılıyor."; exit 1; }

# --- Yedekleme Dosyası Adını Oluşturma (Tarih ve Saat) ---
DATE_TIME=$(date +'%Y%m%d_%H%M%S')
BACKUP_FILE="istiklal_www_backup_${DATE_TIME}.zip"
LOCAL_BACKUP_PATH="$TMP_DIR/$BACKUP_FILE"

# --- Yerel Zip Arşivini Oluşturma ---
echo "$(date '+%Y-%m-%d %H:%M:%S'): Yerel zip arşivi oluşturuluyor: $LOCAL_BACKUP_PATH"
# Kaynak dizine git ve içindekileri zip'le
cd "$SOURCE_DIR" || { echo "$(date '+%Y-%m-%d %H:%M:%S'): Hata: Kaynak dizin $SOURCE_DIR bulunamadı veya erişilemiyor. Çıkılıyor."; exit 1; }

# İçindekileri zip'lemek için './*' kullanıyoruz.
# Eğer html klasörünün kendisini de zip'lemek isterseniz:
# cd "$(dirname "$SOURCE_DIR")" || { echo "..."; exit 1; }
# zip -r "$LOCAL_BACKUP_PATH" "$(basename "$SOURCE_DIR")"
# cd - > /dev/null # Önceki dizine sessizce dön

zip -r "$LOCAL_BACKUP_PATH" ./*
ZIP_STATUS=$?
cd - > /dev/null # Önceki dizine sessizce dön

if [ $ZIP_STATUS -ne 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S'): Hata: Zip arşivi oluşturulurken bir sorun oluştu. Durum kodu: $ZIP_STATUS. Çıkılıyor."
    # Ağ paylaşımı henüz bağlanmadığı için unmount gerekmez
    exit 1
else
    echo "$(date '+%Y-%m-%d %H:%M:%S'): Yerel zip arşivi başarıyla oluşturuldu."
fi

# --- Uzak Paylaşımı Bağlama (Mount Etme) ---
echo "$(date '+%Y-%m-%d %H:%M:%S'): Uzak paylaşım bağlanıyor: $DEST_SHARE to $MOUNT_POINT"
# options: username, password, vers (SMB protokol versiyonu), nobrl (önerilen)
mount -t cifs "$DEST_SHARE" "$MOUNT_POINT" -o username="$SMB_USER",password="$SMB_PASS",vers=3.0,nobrl
MOUNT_STATUS=$?

if [ $MOUNT_STATUS -ne 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S'): Hata: Uzak paylaşım bağlanamadı. Mount durumu: $MOUNT_STATUS. Yerel zip dosyası siliniyor. Çıkılıyor."
    rm -f "$LOCAL_BACKUP_PATH" # Yerel zip dosyasını sil
    exit 1
else
    echo "$(date '+%Y-%m-%d %H:%M:%S'): Uzak paylaşım başarıyla bağlandı."
fi

# --- Zip Dosyasını Ağ Paylaşımına Kopyalama ---
echo "$(date '+%Y-%m-%d %H:%M:%S'): Zip dosyası ($LOCAL_BACKUP_PATH) ağ paylaşımına kopyalanıyor..."
cp "$LOCAL_BACKUP_PATH" "$MOUNT_POINT/"
COPY_STATUS=$?

if [ $COPY_STATUS -ne 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S'): Hata: Dosya ağ paylaşımına kopyalanırken bir sorun oluştu. Kopyalama durumu: $COPY_STATUS. Çıkılıyor."
    # Ağ paylaşımını çöz (unmount)
    umount "$MOUNT_POINT"
    rm -f "$LOCAL_BACKUP_PATH" # Yerel zip dosyasını sil
    exit 1
else
    echo "$(date '+%Y-%m-%d %H:%M:%S'): Dosya başarıyla ağ paylaşımına kopyalandı."
fi

# --- Ağ Paylaşımını Çözme (Unmount Etme) ---
echo "$(date '+%Y-%m-%d %H:%M:%S'): Ağ paylaşımı çözülüyor: $MOUNT_POINT"
umount "$MOUNT_POINT"
UMOUNT_STATUS=$?

if [ $UMOUNT_STATUS -ne 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S'): Uyarı: Ağ paylaşımı çözülürken bir sorun oluştu. Unmount durumu: $UMOUNT_STATUS."
    # Unmount başarısız olsa bile yedekleme tamamlandı, devam edelim ama uyarıyı loglayalım.
else
    echo "$(date '+%Y-%m-%d %H:%M:%S'): Ağ paylaşımı başarıyla çözüldü."
fi

# --- Yerel Geçici Zip Dosyasını Temizleme ---
echo "$(date '+%Y-%m-%d %H:%M:%S'): Yerel geçici zip dosyası siliniyor: $LOCAL_BACKUP_PATH"
rm -f "$LOCAL_BACKUP_PATH"

echo "$(date '+%Y-%m-%d %H:%M:%S'): --- Yedekleme Tamamlandı ---"

exit 0 # Betik başarıyla tamamlandı
