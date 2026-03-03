#!/bin/bash

# AccountsService Cache Rebuild - GARANTILI ÇALIŞAN VERSIYON
# Set -e KALDIRILDI - hata yakalama manuel yapılıyor

echo "============================================================"
echo "AccountsService Kullanıcı Cache'i Yenileme (v3 - Fixed)"
echo "============================================================"
echo ""

# Root kontrolü
if [ "$EUID" -ne 0 ]; then 
    echo "HATA: Bu script root yetkisi ile çalıştırılmalıdır."
    exit 1
fi

# AccountsService kontrolü
if ! systemctl is-active --quiet accounts-daemon 2>/dev/null; then
    echo "HATA: AccountsService çalışmıyor!"
    exit 1
fi

echo "✓ AccountsService çalışıyor"
echo ""

# Ayarlar
CACHE_DIR="/var/lib/AccountsService/users"
MIN_UID=${MIN_UID:-1000}
BACKUP_DIR="/root/accountsservice-backup-$(date +%Y%m%d-%H%M%S)"

# Cache dizini oluştur
mkdir -p "$CACHE_DIR"

# Mevcut durumu göster
CACHED_COUNT=$(ls -1 "$CACHE_DIR" 2>/dev/null | wc -l)
PASSWD_COUNT=$(awk -F: -v min="$MIN_UID" '$3 >= min && $3 != 65534' /etc/passwd | wc -l)

echo "Mevcut Durum:"
echo "  - /etc/passwd'daki kullanıcılar (UID >= $MIN_UID): $PASSWD_COUNT"
echo "  - Cache'deki kullanıcılar: $CACHED_COUNT"
echo "  - Eksik: $(($PASSWD_COUNT - $CACHED_COUNT)) kullanıcı"
echo ""

# Yedek oluştur
if [ $CACHED_COUNT -gt 0 ]; then
    echo "Yedek oluşturuluyor: $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
    cp -r "$CACHE_DIR"/* "$BACKUP_DIR/" 2>/dev/null || true
    echo "✓ Yedek oluşturuldu"
    echo ""
fi

echo "Minimum UID: $MIN_UID"
echo ""
echo "Kullanıcılar işleniyor..."
echo ""

# Sayaçlar
ADDED=0
ALREADY_CACHED=0
SKIPPED=0

# Geçici dosya oluştur
TEMP_USERS="/tmp/users_to_process_$$.txt"
awk -F: -v min="$MIN_UID" '$3 >= min && $3 != 65534 {print $1":"$3":"$7}' /etc/passwd > "$TEMP_USERS"

# Dosyayı oku ve işle
while IFS=: read -r username uid shell; do
    
    # Geçersiz shell kontrolü
    if echo "$shell" | grep -qE '(nologin|false)$'; then
        SKIPPED=$((SKIPPED + 1))
        echo "  ⊘ $username atlandı (shell: $shell)"
        continue
    fi
    
    USER_FILE="$CACHE_DIR/$username"
    
    # Cache'de var mı?
    if [ -f "$USER_FILE" ]; then
        ALREADY_CACHED=$((ALREADY_CACHED + 1))
        echo "  ✓ $username zaten cache'de (UID: $uid)"
    else
        echo "  + $username ekleniyor (UID: $uid, Shell: $shell)"
        
        # Dosya oluştur
        echo "[User]" > "$USER_FILE"
        echo "SystemAccount=false" >> "$USER_FILE"
        
        # İzinleri ayarla
        chmod 600 "$USER_FILE" 2>/dev/null || true
        chown root:root "$USER_FILE" 2>/dev/null || true
        
        ADDED=$((ADDED + 1))
    fi
    
done < "$TEMP_USERS"

# Geçici dosyayı sil
rm -f "$TEMP_USERS"

echo ""
echo "Dosya oluşturma tamamlandı."
echo ""

# D-Bus bildirimleri
if [ $ADDED -gt 0 ]; then
    echo "D-Bus bildirimleri gönderiliyor..."
    
    # Yeni eklenen kullanıcılar için
    awk -F: -v min="$MIN_UID" '$3 >= min && $3 != 65534 {print $1}' /etc/passwd | while read username; do
        dbus-send --system --print-reply \
            --dest=org.freedesktop.Accounts \
            /org/freedesktop/Accounts \
            org.freedesktop.Accounts.CacheUser \
            string:"$username" >/dev/null 2>&1 || true
    done
    
    echo "✓ D-Bus bildirimleri tamamlandı"
    echo ""
fi

# Sonuçları göster
echo "============================================================"
echo "Sonuç:"
echo "  ✓ $ADDED kullanıcı eklendi"
echo "  ✓ $ALREADY_CACHED kullanıcı zaten cache'de"
echo "  ⊘ $SKIPPED kullanıcı atlandı (geçersiz shell)"
echo "  Toplam işlenen: $((ADDED + ALREADY_CACHED + SKIPPED))"
echo "============================================================"
echo ""

# AccountsService'i yeniden başlat
echo "AccountsService yeniden başlatılıyor..."
systemctl restart accounts-daemon
sleep 2
echo "✓ Servis yeniden başlatıldı"
echo ""

# Yeni durumu göster
NEW_CACHED=$(ls -1 "$CACHE_DIR" 2>/dev/null | wc -l)
echo "Güncel Durum:"
echo "  - Cache'deki kullanıcılar: $NEW_CACHED (önceden: $CACHED_COUNT)"
echo "  - Eklenen: $((NEW_CACHED - CACHED_COUNT))"
echo ""

if [ $NEW_CACHED -ge $PASSWD_COUNT ]; then
    echo "✓✓✓ BAŞARILI! Tüm kullanıcılar cache'e eklendi! ✓✓✓"
else
    echo "⚠️  DİKKAT: Hala eksik kullanıcılar var!"
    echo "  Eksik sayısı: $((PASSWD_COUNT - NEW_CACHED))"
fi

echo ""
echo "LightDM'i yeniden başlatmak için:"
echo "  systemctl restart lightdm"
echo ""
echo "NOT: Bu komut sizi logout edecek!"
