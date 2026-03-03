#!/bin/bash

# Kaynak ve hedef dizinler
KAYNAK_DIZIN="/var/www/html/eta"
YEDEK_DIZIN="/root/yedekler"

# Tarih etiketli dosya adı
TARIH=$(date +%F)
YEDEK_ADI="yedek_$TARIH.tar.gz"
YEDEK_YOLU="$YEDEK_DIZIN/$YEDEK_ADI"

# Yedekleme işlemi
tar -czf "$YEDEK_YOLU" -C "$KAYNAK_DIZIN" .

# Başarılıysa loglara mesaj düş
if [ $? -eq 0 ]; then
    logger "Yedekleme başarılı: $YEDEK_YOLU"
else
    logger "Yedekleme HATASI: $KAYNAK_DIZIN -> $YEDEK_YOLU"
fi
