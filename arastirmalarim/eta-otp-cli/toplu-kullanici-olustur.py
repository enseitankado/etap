#!/usr/bin/env python3

import sys
import os
import json
import base64
import argparse
import subprocess
from pathlib import Path

AYAR_DOSYASI = "/etc/otp-secrets.json"
ACCOUNTS_CACHE_DIR = "/var/lib/AccountsService/users"


def turkish_to_english(text):
    replacements = {
        "â": "a", "Â": "A",
        "ç": "c", "Ç": "C",
        "ğ": "g", "Ğ": "G",
        "ı": "i", "î": "i", "İ": "I", "Î": "I",
        "ö": "o", "ô": "o", "Ö": "O", "Ô": "O",
        "ş": "s", "Ş": "S",
        "ü": "u", "Ü": "U", "Û": "U", "û": "u",
    }

    text = text.strip()

    for tr_char, en_char in replacements.items():
        text = text.replace(tr_char, en_char)

    text = "".join([c for c in text if c.isalnum() or c == " "])

    return text.lower().replace(" ", "")


class AccountsServiceHelper:
    """AccountsService cache yönetimi için yardımcı sınıf"""
    
    @staticmethod
    def cache_dizini_olustur():
        """Cache dizinini oluştur"""
        cache_dir = Path(ACCOUNTS_CACHE_DIR)
        if not cache_dir.exists():
            cache_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(cache_dir, 0o755)
    
    @staticmethod
    def kullaniciyi_cache_ekle(kullanici):
        """Kullanıcıyı AccountsService cache'ine ekle"""
        try:
            # Cache dizini var mı kontrol et
            AccountsServiceHelper.cache_dizini_olustur()
            
            user_file = Path(ACCOUNTS_CACHE_DIR) / kullanici
            
            # Kullanıcı zaten cache'de mi?
            if user_file.exists():
                print(f"  ℹ️  {kullanici} zaten AccountsService cache'inde")
                return True
            
            # Cache dosyası oluştur
            with open(user_file, 'w') as f:
                f.write("[User]\n")
                f.write("SystemAccount=false\n")
            
            # İzinleri ayarla
            os.chmod(user_file, 0o600)
            os.chown(user_file, 0, 0)  # root:root
            
            # D-Bus üzerinden bildir
            AccountsServiceHelper.dbus_bildir(kullanici)
            
            print(f"  ✓ {kullanici} AccountsService cache'ine eklendi")
            return True
            
        except Exception as e:
            print(f"  ⚠️  {kullanici} cache'e eklenirken hata: {e}")
            return False
    
    @staticmethod
    def kullaniciyi_cache_sil(kullanici):
        """Kullanıcıyı AccountsService cache'inden sil"""
        try:
            user_file = Path(ACCOUNTS_CACHE_DIR) / kullanici
            
            if user_file.exists():
                user_file.unlink()
                print(f"  ✓ {kullanici} AccountsService cache'inden silindi")
                return True
            
            return False
            
        except Exception as e:
            print(f"  ⚠️  {kullanici} cache'den silinirken hata: {e}")
            return False
    
    @staticmethod
    def dbus_bildir(kullanici):
        """D-Bus üzerinden AccountsService'e kullanıcıyı bildir"""
        try:
            subprocess.run([
                "dbus-send",
                "--system",
                "--print-reply",
                "--dest=org.freedesktop.Accounts",
                "/org/freedesktop/Accounts",
                "org.freedesktop.Accounts.CacheUser",
                f"string:{kullanici}"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
        except:
            pass  # D-Bus hatalarını sessizce göz ardı et
    
    @staticmethod
    def servisi_yenile():
        """AccountsService servisini yeniden başlat"""
        try:
            subprocess.run(["systemctl", "restart", "accounts-daemon"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except:
            return False


class OTPYoneticisi:
    def __init__(self):
        self.ayarlar = {}
        self.yukle()

    def yukle(self):
        if os.path.isfile(AYAR_DOSYASI):
            with open(AYAR_DOSYASI, "r") as f:
                self.ayarlar = json.load(f)

    def kaydet(self):
        with open(AYAR_DOSYASI, "w") as f:
            json.dump(self.ayarlar, f, indent=2, ensure_ascii=False)
        os.chown(AYAR_DOSYASI, 0, 0)
        os.chmod(AYAR_DOSYASI, 0o600)

    def gizli_anahtar_olustur(self):
        return base64.b32encode(os.urandom(10)).decode()

    def anahtar_olustur(self, kullanici):
        gizli = self.gizli_anahtar_olustur()
        self.ayarlar[kullanici] = gizli
        print(f"✓ OTP oluşturuldu: {kullanici}")

    def dosyadan_isle(self, dosya, kullanicilari_olustur=False):
        if not os.path.isfile(dosya):
            print("Dosya bulunamadı")
            return

        with open(dosya, "r", encoding="utf-8") as f:
            satirlar = f.readlines()

        eklenen_sayisi = 0
        cache_eklenen = 0

        for satir in satirlar:
            tam_ad = satir.strip()
            if not tam_ad:
                continue

            kullanici = turkish_to_english(tam_ad)

            if kullanicilari_olustur:
                print(f"\n🔧 Linux kullanıcı oluşturuluyor: {kullanici}")

                # Kullanıcı zaten var mı kontrol et
                kullanici_var = subprocess.run(
                    ["id", kullanici],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                ).returncode == 0

                if kullanici_var:
                    print(f"  ℹ️  {kullanici} zaten mevcut")
                else:
                    # Grup var mı kontrol et
                    grup_var = subprocess.run(
                        ["getent", "group", kullanici],
                        stdout=subprocess.DEVNULL
                    ).returncode == 0

                    if not grup_var:
                        subprocess.run(["groupadd", kullanici],
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)

                    # Kullanıcı oluştur
                    result = subprocess.run([
                        "useradd",
                        "-m",
                        "-s", "/bin/bash",
                        "-c", tam_ad,
                        "-g", kullanici,
                        kullanici
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                    if result.returncode == 0:
                        print(f"  ✓ Kullanıcı oluşturuldu: {kullanici}")
                        eklenen_sayisi += 1

                        # Ek gruplara ekle
                        gruplar = [
                            "cdrom", "floppy", "audio", "video", "plugdev", "bluetooth",
                            "scanner", "netdev", "dip", "lpadmin"
                        ]

                        subprocess.run([
                            "usermod",
                            "-aG",
                            ",".join(gruplar),
                            kullanici
                        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        print(f"  ✗ Kullanıcı oluşturulamadı: {kullanici}")
                        continue

                # AccountsService cache'ine ekle
                if AccountsServiceHelper.kullaniciyi_cache_ekle(kullanici):
                    cache_eklenen += 1

            # OTP oluştur
            self.anahtar_olustur(kullanici)

        self.kaydet()
        
        print("\n" + "="*60)
        print("İşlem Özeti:")
        if kullanicilari_olustur:
            print(f"  ✓ {eklenen_sayisi} yeni kullanıcı oluşturuldu")
            print(f"  ✓ {cache_eklenen} kullanıcı AccountsService cache'ine eklendi")
        print(f"  ✓ {len(satirlar)} OTP anahtarı oluşturuldu")
        print("="*60)
        
        # AccountsService'i yenile
        if kullanicilari_olustur and cache_eklenen > 0:
            print("\nAccountsService servisi yenileniyor...")
            if AccountsServiceHelper.servisi_yenile():
                print("✓ Servis yenilendi")
                print("\nℹ️  Kullanıcılar LightDM login ekranında görünmesi için:")
                print("   sudo systemctl restart lightdm")
            else:
                print("⚠️  Servis yenilenemedi (manuel yenileyin)")

    def kullanicilari_sil(self, dosya):
        if not os.path.isfile(dosya):
            print("İsim listesi dosyası bulunamadı")
            return

        if not self.ayarlar:
            print("OTP dosyasında kullanıcı yok")
            return

        with open(dosya, "r", encoding="utf-8") as f:
            satirlar = f.readlines()

        silinecekler = []

        for satir in satirlar:
            tam_ad = satir.strip()
            if not tam_ad:
                continue

            kullanici = turkish_to_english(tam_ad)

            # Sadece her iki yerde de varsa sil
            if kullanici in self.ayarlar:
                silinecekler.append(kullanici)

        if not silinecekler:
            print("Her iki dosyada da bulunan kullanıcı yok")
            return

        silinen_sayisi = 0
        cache_silinen = 0

        for kullanici in silinecekler:
            print(f"\n🗑️  Siliniyor: {kullanici}")

            # Önce oturumları kapat
            subprocess.run(["pkill", "-u", kullanici],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)

            # Kullanıcıyı sil
            result = subprocess.run([
                "deluser",
                "--remove-home",
                kullanici
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            if result.returncode == 0:
                print(f"  ✓ Linux kullanıcısı silindi")
                silinen_sayisi += 1

            # AccountsService cache'den sil
            if AccountsServiceHelper.kullaniciyi_cache_sil(kullanici):
                cache_silinen += 1

            # OTP kaydını sil
            if kullanici in self.ayarlar:
                del self.ayarlar[kullanici]
                print(f"  ✓ OTP kaydı silindi")

        self.kaydet()
        
        print("\n" + "="*60)
        print("Silme İşlemi Özeti:")
        print(f"  ✓ {silinen_sayisi} kullanıcı silindi")
        print(f"  ✓ {cache_silinen} cache kaydı silindi")
        print(f"  ✓ {len(silinecekler)} OTP kaydı silindi")
        print("="*60)
        
        # AccountsService'i yenile
        if cache_silinen > 0:
            print("\nAccountsService servisi yenileniyor...")
            if AccountsServiceHelper.servisi_yenile():
                print("✓ Servis yenilendi")
            else:
                print("⚠️  Servis yenilenemedi")


def yardim_goster():
    print("""
OTP CLI – Toplu OTP ve Kullanıcı Yönetim Aracı (AccountsService Destekli)

KULLANIM:

  Dosyadan OTP anahtarları oluştur:
    sudo python3 toplu-kullanici-ekle.py isimler.txt

  Dosyadan OTP + Linux kullanıcıları oluştur + AccountsService cache:
    sudo python3 toplu-kullanici-ekle.py isimler.txt --kullanicilari-olustur

  Dosyadaki ve OTP dosyasındaki ortak kullanıcıları sil:
    sudo python3 toplu-kullanici-ekle.py isimler.txt --kullanicilari-sil

ÖZELLİKLER:
  ✓ Türkçe karakterleri otomatik İngilizce'ye çevirir
  ✓ Kullanıcıları uygun gruplarla oluşturur
  ✓ OTP anahtarları üretir
  ✓ AccountsService cache'ine otomatik ekler
  ✓ LightDM login ekranında kullanıcılar görünür olur

NOT:
  - AccountsService cache desteği eklendi
  - Kullanıcılar artık otomatik olarak LightDM'de görünecek
  - --kullanicilari-olustur ile eklenen kullanıcılar cache'e de eklenir
  - --kullanicilari-sil ile silinen kullanıcılar cache'den de silinir
""")


def main():
    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument("dosya", nargs="?", help="İsim listesi dosyası")
    parser.add_argument("--kullanicilari-olustur", action="store_true")
    parser.add_argument("--kullanicilari-sil", action="store_true")
    parser.add_argument("-h", "--help", action="store_true")

    args = parser.parse_args()

    if args.help or (not args.dosya and not args.kullanicilari_sil):
        yardim_goster()
        sys.exit(0)

    if os.geteuid() != 0:
        print("Root yetkisi gerekli (sudo)")
        sys.exit(1)

    yonetici = OTPYoneticisi()

    if args.kullanicilari_sil:
        if not args.dosya:
            print("Silme için isim listesi dosyası gerekli")
            sys.exit(1)

        yonetici.kullanicilari_sil(args.dosya)
        return

    yonetici.dosyadan_isle(args.dosya, args.kullanicilari_olustur)


if __name__ == "__main__":
    main()
