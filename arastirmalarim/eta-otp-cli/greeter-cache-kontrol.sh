#!/bin/bash

echo "==================================="
echo "AccountsService Durumu Kontrolü"
echo "==================================="
echo ""

# AccountsService çalışıyor mu?
echo "1. AccountsService Servisi:"
if systemctl is-active --quiet accounts-daemon; then
    echo "   ✓ AccountsService ÇALIŞIYOR"
    echo "   (Bu kullanıcı listesini yönetiyor)"
else
    echo "   ✗ AccountsService çalışmıyor"
fi
echo ""

# Kullanıcı cache dosyaları
echo "2. AccountsService Kullanıcı Cache Dosyaları:"
if [ -d /var/lib/AccountsService/users ]; then
    user_count=$(ls -1 /var/lib/AccountsService/users 2>/dev/null | wc -l)
    echo "   Dizin: /var/lib/AccountsService/users"
    echo "   Cache'deki kullanıcı sayısı: $user_count"
    echo ""
    echo "   Cache'deki kullanıcılar:"
    ls -1 /var/lib/AccountsService/users 2>/dev/null | head -20
    if [ $user_count -gt 20 ]; then
        echo "   ... ve $(($user_count - 20)) kullanıcı daha"
    fi
else
    echo "   ✗ Cache dizini bulunamadı"
fi
echo ""

# Sistem kullanıcıları
echo "3. /etc/passwd'daki Gerçek Kullanıcılar (UID >= 1000):"
real_users=$(awk -F: '$3 >= 1000 && $3 != 65534 {print $1}' /etc/passwd | wc -l)
echo "   Toplam kullanıcı sayısı: $real_users"
echo ""
echo "   İlk 20 kullanıcı:"
awk -F: '$3 >= 1000 && $3 != 65534 {printf "   - %s (UID: %s)\n", $1, $3}' /etc/passwd | head -20
if [ $real_users -gt 20 ]; then
    echo "   ... ve $(($real_users - 20)) kullanıcı daha"
fi
echo ""

# D-Bus üzerinden kullanıcı listesi
echo "4. D-Bus API'den Kullanıcı Listesi:"
dbus_users=$(busctl call org.freedesktop.Accounts /org/freedesktop/Accounts org.freedesktop.Accounts ListCachedUsers 2>/dev/null | grep -o "User[0-9]*" | wc -l)
if [ $dbus_users -gt 0 ]; then
    echo "   D-Bus'tan görünen kullanıcı sayısı: $dbus_users"
else
    echo "   ✗ D-Bus sorgusu başarısız"
fi
echo ""

# Fark analizi
echo "5. Sorun Analizi:"
echo "   /etc/passwd kullanıcıları: $real_users"
echo "   AccountsService cache: $user_count"
echo "   FARK: $(($real_users - $user_count)) kullanıcı eksik!"
echo ""

if [ $(($real_users - $user_count)) -gt 10 ]; then
    echo "   ⚠️ SORUN BULUNDU: AccountsService cache'i eksik kullanıcı içeriyor!"
fi
