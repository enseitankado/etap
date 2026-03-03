#!/bin/bash

# Ortam değişkenlerini ayarla
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Başlangıç zamanı
BASLA=$(date +%s)

# Ağ aralığı
AG_ARALIGI=$(/usr/bin/php8.4 /var/www/html/eta/disa-aktar.php ET_AG_ARALIGI)
CIKTI_DOSYASI="/var/www/html/eta/betikler/et-agi-aktif-cihazlar.json"
GECMIS_DOSYASI="/var/www/html/eta/betikler/et-agi-aktif-cihazlar-gecmisi.json"

echo "Ağ taraması başlatılıyor: $AG_ARALIGI"

# Ağ taraması (sessiz mod)
/usr/bin/nmap -e eth1 -sn "$AG_ARALIGI" > /dev/null

# Geçici dosya
TMP_CIHAZLAR="/tmp/idare-cihazlar.jsonl"

rm "$TMP_CIHAZLAR"

# ARP tablosundan yalnızca 10.x.x.x adreslerini al
/usr/sbin/arp -an | /usr/bin/awk '/ether/ && $2 ~ /^[(]10\./ {
    gsub(/[()]/, "", $2);
    print $2 " " $4
}' | while read -r IP MAC; do
    /bin/ping -c 1 -W 1 "$IP" > /dev/null && echo "{\"ip\": \"$IP\", \"mac\": \"$MAC\"}" >> "$TMP_CIHAZLAR"
done

# Kayıt sayısını hesapla
KAYIT_SAYISI=$(/usr/bin/wc -l < "$TMP_CIHAZLAR")

# JSON dosyasını oluştur
echo "[" > "$CIKTI_DOSYASI"
sed '$!s/$/,/' "$TMP_CIHAZLAR" >> "$CIKTI_DOSYASI"
echo "]" >> "$CIKTI_DOSYASI"

# Bitiş zamanı ve süre
BITIS=$(date +%s)
SURE=$((BITIS - BASLA))

# Loglama
cat "$CIKTI_DOSYASI"
echo "JSON dosyası oluşturuldu: $CIKTI_DOSYASI"
echo "Toplam $KAYIT_SAYISI kayıt yazıldı."
echo "Toplam süre: ${SURE} saniye."

# **Yeni eklenen kısım: Geçmiş dosyasını güncelleme**

# Eğer geçmiş dosyası yoksa, başlatıyoruz
if [ ! -f "$GECMIS_DOSYASI" ]; then
    echo "[]" > "$GECMIS_DOSYASI"
fi

# Geçmiş dosyasını okuma ve MAC adreslerini bir diziye alalım
declare -A cihazlar
while IFS= read -r line; do
    MAC=$(echo "$line" | grep -oP '"mac":\s*"\K[^"]+')
    TIMESTAMPS=$(echo "$line" | grep -oP '"timestamps":\s*\[\K[^\]]+')
    cihazlar["$MAC"]=$TIMESTAMPS
done < <(cat "$GECMIS_DOSYASI" | grep -oP '\{.*?\}')

# Her cihaz için zaman damgası ekleyelim
while IFS= read -r line; do
    IP=$(echo "$line" | grep -oP '"ip":\s*"\K[^"]+')
    MAC=$(echo "$line" | grep -oP '"mac":\s*"\K[^"]+')

    # Şu anki zaman damgasını al
    TIMESTAMP=$(date +%s)

    # Cihaz geçmişte var mı kontrol et
    if [[ -n "${cihazlar["$MAC"]}" ]]; then
        # Eğer varsa, zaman damgasını zaten eklemiştik, sadece tekrar eklemiyoruz
        if [[ ! "${cihazlar["$MAC"]}" =~ "$TIMESTAMP" ]]; then
            # Yeni timestamp ekle
            cihazlar["$MAC"]="${cihazlar["$MAC"]},$TIMESTAMP"
            
            # Timestamp dizisinin uzunluğunu kontrol et
            timestamps_array=(${cihazlar["$MAC"]//,/ })
            if [ ${#timestamps_array[@]} -gt 10000 ]; then
                # Eğer 1000'den fazla timestamp varsa, en eski olanı kaldır
                timestamps_array=("${timestamps_array[@]:1}")
                cihazlar["$MAC"]=$(IFS=,; echo "${timestamps_array[*]}")
            fi
        fi
    else
        # Yoksa yeni cihaz olarak ekle
        cihazlar["$MAC"]="$TIMESTAMP"
    fi
done < "$TMP_CIHAZLAR"


# Geçmiş dosyasını güncelle
updated_json=""

first_entry=true
for MAC in "${!cihazlar[@]}"; do
    if [ "$first_entry" = true ]; then
        updated_json="{\"mac\": \"$MAC\", \"timestamps\": [${cihazlar[$MAC]}]}"
        first_entry=false
    else
        updated_json="$updated_json,{\"mac\": \"$MAC\", \"timestamps\": [${cihazlar[$MAC]}]}"
    fi
done

echo "[$updated_json]" > "$GECMIS_DOSYASI"

/usr/bin/php /var/www/html/eta/betikler/acik-kapali-ozetle.php /var/www/html/eta/betikler/et-agi-aktif-cihazlar-gecmisi.json /var/www/html/eta/betikler/et-agi-acik-kapali.json 300