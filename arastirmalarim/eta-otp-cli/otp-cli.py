#!/usr/bin/env python3
"""
OTP Yönetim Aracı - Terminal tabanlı OTP gizli anahtar yönetimi
Kullanım: python3 otp-cli.py [komut] [seçenekler]
"""

import sys
import os
import json
import base64
import argparse
import pyotp
import qrcode
import time
from io import StringIO

AYAR_DOSYASI = "/etc/otp-secrets.json"

class OTPYoneticisi:
    def __init__(self):
        self.ayarlar = {}
        self.ayarlari_yukle()
    
    def ayarlari_yukle(self):
        """Ayarları dosyadan yükle"""
        try:
            if os.path.isfile(AYAR_DOSYASI):
                with open(AYAR_DOSYASI, "r") as f:
                    self.ayarlar = json.load(f)
        except Exception as e:
            print(f"Uyarı: Ayarlar yüklenemedi: {e}")
    
    def ayarlari_kaydet(self):
        """Ayarları dosyaya kaydet"""
        try:
            with open(AYAR_DOSYASI, "w") as f:
                json.dump(self.ayarlar, f, indent=2, ensure_ascii=False)
            os.chown(AYAR_DOSYASI, 0, 0)
            os.chmod(AYAR_DOSYASI, 0o600)
            return True
        except Exception as e:
            print(f"Hata: Ayarlar kaydedilemedi: {e}")
            return False
    
    def gizli_anahtar_olustur(self, rastgele_veri=None):
        """Yeni base32 gizli anahtar oluştur"""
        if rastgele_veri is None:
            rastgele_veri = os.urandom(10)
        return base64.b32encode(rastgele_veri).decode("utf-8")
    
    def base32_mi(self, veri):
        """String'in geçerli base32 olup olmadığını kontrol et"""
        if len(veri) % 4 > 0:
            return False
        alfabe = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567="
        return all(c in alfabe for c in veri)
    
    def anahtar_olustur(self, kullanici_adi, gizli_anahtar=None, anahtardan=None):
        """Kullanıcı için yeni gizli anahtar oluştur ve kaydet"""
        if anahtardan:
            # Kullanıcı anahtarından gizli anahtar oluştur
            if self.base32_mi(anahtardan):
                gizli_anahtar = anahtardan
            else:
                gizli_anahtar = self.gizli_anahtar_olustur(anahtardan.encode("utf-8"))
        elif not gizli_anahtar:
            # Rastgele gizli anahtar oluştur
            gizli_anahtar = self.gizli_anahtar_olustur()
        
        self.ayarlar[kullanici_adi] = gizli_anahtar
        if self.ayarlari_kaydet():
            print(f"✓ Kullanıcı için gizli anahtar oluşturuldu: {kullanici_adi}")
            print(f"Gizli Anahtar: {gizli_anahtar}")
            return gizli_anahtar
        return None
    
    def anahtar_getir(self, kullanici_adi):
        """Kullanıcının gizli anahtarını getir"""
        if kullanici_adi in self.ayarlar:
            return self.ayarlar[kullanici_adi]
        return None
    
    def anahtar_sil(self, kullanici_adi):
        """Kullanıcının gizli anahtarını sil"""
        if kullanici_adi in self.ayarlar:
            # Silme onayı iste
            print(f"⚠️  UYARI: '{kullanici_adi}' kullanıcısının gizli anahtarı silinecek!")
            onay = input("Devam etmek istiyor musunuz? (evet/hayır): ").strip().lower()
            
            if onay in ['evet', 'e', 'yes', 'y']:
                self.ayarlar.pop(kullanici_adi)
                if self.ayarlari_kaydet():
                    print(f"✓ Kullanıcının gizli anahtarı silindi: {kullanici_adi}")
                    return True
            else:
                print("İşlem iptal edildi.")
                return False
        else:
            print(f"✗ Kullanıcı bulunamadı: {kullanici_adi}")
        return False
    
    def kullanicilari_listele(self):
        """Gizli anahtarı olan tüm kullanıcıları listele"""
        if not self.ayarlar:
            print("Yapılandırılmış kullanıcı yok.")
            return
        
        print("OTP gizli anahtarı olan kullanıcılar:")
        print("-" * 40)
        for kullanici_adi in self.ayarlar.keys():
            print(f"  • {kullanici_adi}")
        print("-" * 40)
        print(f"Toplam: {len(self.ayarlar)} kullanıcı")
    
    def qr_goster(self, kullanici_adi):
        """Kullanıcı için QR kod göster"""
        gizli_anahtar = self.anahtar_getir(kullanici_adi)
        if not gizli_anahtar:
            print(f"✗ Kullanıcı bulunamadı: {kullanici_adi}")
            return
        
        # TOTP URI oluştur
        totp = pyotp.TOTP(gizli_anahtar)
        uri = totp.provisioning_uri(
            f"{kullanici_adi}@etap", 
            issuer_name="pardus-etap"
        )
        uri += "&algorithm=SHA1&digits=6&period=30"
        
        # QR kod oluştur
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=2,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        # QR kodu terminale yazdır
        print(f"\n{kullanici_adi} için QR Kodu:")
        print("=" * 50)
        f = StringIO()
        qr.print_ascii(out=f, invert=True)
        print(f.getvalue())
        print("=" * 50)
        print(f"Gizli Anahtar: {gizli_anahtar}")
        print(f"URI: {uri}")
        print("\nBu QR kodu Google Authenticator veya benzeri bir uygulama ile tarayın")
    
    def kodu_dogrula(self, kullanici_adi, kod):
        """Kullanıcı için OTP kodunu doğrula"""
        gizli_anahtar = self.anahtar_getir(kullanici_adi)
        if not gizli_anahtar:
            print(f"✗ Kullanıcı bulunamadı: {kullanici_adi}")
            return False
        
        totp = pyotp.TOTP(gizli_anahtar)
        if totp.verify(kod):
            print(f"✓ Kod GEÇERLİ (kullanıcı: {kullanici_adi})")
            return True
        else:
            print(f"✗ Kod GEÇERSİZ (kullanıcı: {kullanici_adi})")
            return False
    
    def guncel_kodu_getir(self, kullanici_adi):
        """Kullanıcı için güncel OTP kodunu getir"""
        gizli_anahtar = self.anahtar_getir(kullanici_adi)
        if not gizli_anahtar:
            print(f"✗ Kullanıcı bulunamadı: {kullanici_adi}")
            return None
        
        totp = pyotp.TOTP(gizli_anahtar)
        kod = totp.now()
        
        # Kalan süreyi hesapla (30 saniyelik döngü)
        kalan_saniye = 30 - (int(time.time()) % 30)
        
        print(f"{kullanici_adi} için Güncel OTP: {kod}")
        print(f"(~{kalan_saniye} saniye geçerli)")
        return kod
    
    def anahtari_disa_aktar(self, kullanici_adi, dosya_adi):
        """Gizli anahtarı dosyaya aktar (Base64)"""
        gizli_anahtar = self.anahtar_getir(kullanici_adi)
        if not gizli_anahtar:
            print(f"✗ Kullanıcı bulunamadı: {kullanici_adi}")
            return False
        
        try:
            if not dosya_adi.endswith(".totp"):
                dosya_adi += ".totp"
            
            # Base64 formatında kaydet
            veri = {
                "gizli_anahtar": gizli_anahtar,
                "kullanici": kullanici_adi,
                "versiyon": "1.0"
            }
            json_veri = json.dumps(veri, ensure_ascii=False)
            base64_veri = base64.b64encode(json_veri.encode("utf-8")).decode("utf-8")
            
            with open(dosya_adi, "w") as f:
                f.write(base64_veri)
            
            print(f"✓ Gizli anahtar dışa aktarıldı: {dosya_adi}")
            return True
        except Exception as e:
            print(f"✗ Dışa aktarma başarısız: {e}")
            return False
    
    def anahtari_ice_aktar(self, kullanici_adi, dosya_adi):
        """Gizli anahtarı dosyadan içe aktar (Base64)"""
        try:
            with open(dosya_adi, "r") as f:
                base64_veri = f.read().strip()
            
            # Base64'ten çöz
            json_veri = base64.b64decode(base64_veri).decode("utf-8")
            veri = json.loads(json_veri)
            
            gizli_anahtar = veri["gizli_anahtar"]
            orijinal_kullanici = veri.get("kullanici", "bilinmiyor")
            
            self.ayarlar[kullanici_adi] = gizli_anahtar
            if self.ayarlari_kaydet():
                print(f"✓ Gizli anahtar içe aktarıldı: {kullanici_adi}")
                print(f"  (Orijinal kullanıcı: {orijinal_kullanici})")
                return True
        except Exception as e:
            print(f"✗ İçe aktarma başarısız: {e}")
            return False
    
    def tum_kullanicilari_disa_aktar(self, dosya_adi):
        """Tüm kullanıcıları dosyaya aktar"""
        if not self.ayarlar:
            print("✗ Dışa aktarılacak kullanıcı yok.")
            return False
        
        try:
            if not dosya_adi.endswith(".totp"):
                dosya_adi += ".totp"
            
            # Base64 formatında kaydet
            veri = {
                "kullanicilar": self.ayarlar,
                "versiyon": "1.0",
                "toplam": len(self.ayarlar)
            }
            json_veri = json.dumps(veri, ensure_ascii=False, indent=2)
            base64_veri = base64.b64encode(json_veri.encode("utf-8")).decode("utf-8")
            
            with open(dosya_adi, "w") as f:
                f.write(base64_veri)
            
            print(f"✓ {len(self.ayarlar)} kullanıcı dışa aktarıldı: {dosya_adi}")
            return True
        except Exception as e:
            print(f"✗ Dışa aktarma başarısız: {e}")
            return False
    
    def tum_kullanicilari_ice_aktar(self, dosya_adi, ustune_yaz=False):
        """Tüm kullanıcıları dosyadan içe aktar"""
        try:
            with open(dosya_adi, "r") as f:
                base64_veri = f.read().strip()
            
            # Base64'ten çöz
            json_veri = base64.b64decode(base64_veri).decode("utf-8")
            veri = json.loads(json_veri)
            
            yeni_kullanicilar = veri.get("kullanicilar", {})
            
            if not yeni_kullanicilar:
                print("✗ Dosyada kullanıcı bulunamadı.")
                return False
            
            # Üstüne yazma kontrolü
            if not ustune_yaz:
                cakisan = [k for k in yeni_kullanicilar.keys() if k in self.ayarlar]
                if cakisan:
                    print(f"⚠️  Uyarı: Aşağıdaki kullanıcılar zaten mevcut:")
                    for k in cakisan:
                        print(f"  • {k}")
                    onay = input("Mevcut kullanıcıların üstüne yaz? (evet/hayır): ").strip().lower()
                    if onay not in ['evet', 'e', 'yes', 'y']:
                        print("İşlem iptal edildi.")
                        return False
            
            # Kullanıcıları ekle
            eklenen = 0
            for kullanici, anahtar in yeni_kullanicilar.items():
                self.ayarlar[kullanici] = anahtar
                eklenen += 1
            
            if self.ayarlari_kaydet():
                print(f"✓ {eklenen} kullanıcı içe aktarıldı")
                return True
            
        except Exception as e:
            print(f"✗ İçe aktarma başarısız: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(
        description="OTP Yönetim Aracı - Kullanıcılar için TOTP gizli anahtarlarını yönetin",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  # Kullanıcı için yeni rastgele gizli anahtar oluştur
  sudo python3 otp-cli.py olustur tankado

  # Belirli bir anahtar kullan
  sudo python3 otp-cli.py olustur tankado --anahtar JBSWY3DPEHPK3PXP

  # Özel bir şifreden anahtar oluştur
  sudo python3 otp-cli.py olustur tankado --anahtardan "benim-gizli-sifrem"

  # QR kod göster
  sudo python3 otp-cli.py goster tankado

  # Güncel OTP kodunu al
  sudo python3 otp-cli.py kod tankado

  # OTP kodunu doğrula
  sudo python3 otp-cli.py dogrula tankado 123456

  # Gizli anahtarı dosyaya aktar
  sudo python3 otp-cli.py disari-aktar tankado yedek.totp

  # Gizli anahtarı dosyadan içe aktar
  sudo python3 otp-cli.py iceri-aktar tankado yedek.totp

  # Tüm kullanıcıları dışa aktar
  sudo python3 otp-cli.py tumu-disari-aktar tum-yedek.totp

  # Tüm kullanıcıları içe aktar
  sudo python3 otp-cli.py tumu-iceri-aktar tum-yedek.totp

  # Tüm kullanıcıları listele
  sudo python3 otp-cli.py listele

  # Gizli anahtarı sil
  sudo python3 otp-cli.py sil tankado
        """
    )
    
    subparsers = parser.add_subparsers(dest='komut', help='Kullanılabilir komutlar')
    
    # Oluştur komutu
    olustur_parser = subparsers.add_parser('olustur', help='Kullanıcı için yeni gizli anahtar oluştur')
    olustur_parser.add_argument('kullanici', help='Kullanıcı adı')
    olustur_parser.add_argument('--anahtar', help='Kullanılacak belirli anahtar (base32)')
    olustur_parser.add_argument('--anahtardan', help='Özel anahtar/şifreden gizli anahtar oluştur')
    
    # Göster komutu
    goster_parser = subparsers.add_parser('goster', help='QR kod ve gizli anahtarı göster')
    goster_parser.add_argument('kullanici', help='Kullanıcı adı')
    
    # Kod komutu
    kod_parser = subparsers.add_parser('kod', help='Güncel OTP kodunu al')
    kod_parser.add_argument('kullanici', help='Kullanıcı adı')
    
    # Doğrula komutu
    dogrula_parser = subparsers.add_parser('dogrula', help='OTP kodunu doğrula')
    dogrula_parser.add_argument('kullanici', help='Kullanıcı adı')
    dogrula_parser.add_argument('kod', help='6 haneli OTP kodu')
    
    # Dışarı aktar komutu
    disari_parser = subparsers.add_parser('disari-aktar', help='Gizli anahtarı dosyaya aktar')
    disari_parser.add_argument('kullanici', help='Kullanıcı adı')
    disari_parser.add_argument('dosya', help='Çıktı dosya yolu')
    
    # İçeri aktar komutu
    iceri_parser = subparsers.add_parser('iceri-aktar', help='Gizli anahtarı dosyadan içe aktar')
    iceri_parser.add_argument('kullanici', help='Kullanıcı adı')
    iceri_parser.add_argument('dosya', help='Giriş dosya yolu')
    
    # Tümünü dışarı aktar komutu
    tumu_disari_parser = subparsers.add_parser('tumu-disari-aktar', help='Tüm kullanıcıları dosyaya aktar')
    tumu_disari_parser.add_argument('dosya', help='Çıktı dosya yolu')
    
    # Tümünü içeri aktar komutu
    tumu_iceri_parser = subparsers.add_parser('tumu-iceri-aktar', help='Tüm kullanıcıları dosyadan içe aktar')
    tumu_iceri_parser.add_argument('dosya', help='Giriş dosya yolu')
    tumu_iceri_parser.add_argument('--ustune-yaz', action='store_true', help='Onay istemeden mevcut kullanıcıların üstüne yaz')
    
    # Listele komutu
    listele_parser = subparsers.add_parser('listele', help='Gizli anahtarı olan tüm kullanıcıları listele')
    
    # Sil komutu
    sil_parser = subparsers.add_parser('sil', help='Kullanıcının gizli anahtarını sil')
    sil_parser.add_argument('kullanici', help='Kullanıcı adı')
    
    # Getir komutu (sadece anahtarı göster)
    getir_parser = subparsers.add_parser('getir', help='Kullanıcının gizli anahtarını getir')
    getir_parser.add_argument('kullanici', help='Kullanıcı adı')
    
    args = parser.parse_args()
    
    if not args.komut:
        parser.print_help()
        sys.exit(1)
    
    # Root yetkisi kontrolü
    if os.geteuid() != 0 and args.komut in ['olustur', 'sil', 'iceri-aktar', 'tumu-iceri-aktar']:
        print("✗ Hata: Bu komut root yetkisi gerektirir (sudo kullanın)")
        sys.exit(1)
    
    yonetici = OTPYoneticisi()
    
    if args.komut == 'olustur':
        yonetici.anahtar_olustur(args.kullanici, args.anahtar, args.anahtardan)
    
    elif args.komut == 'goster':
        yonetici.qr_goster(args.kullanici)
    
    elif args.komut == 'kod':
        yonetici.guncel_kodu_getir(args.kullanici)
    
    elif args.komut == 'dogrula':
        sonuc = yonetici.kodu_dogrula(args.kullanici, args.kod)
        sys.exit(0 if sonuc else 1)
    
    elif args.komut == 'disari-aktar':
        yonetici.anahtari_disa_aktar(args.kullanici, args.dosya)
    
    elif args.komut == 'iceri-aktar':
        yonetici.anahtari_ice_aktar(args.kullanici, args.dosya)
    
    elif args.komut == 'tumu-disari-aktar':
        yonetici.tum_kullanicilari_disa_aktar(args.dosya)
    
    elif args.komut == 'tumu-iceri-aktar':
        yonetici.tum_kullanicilari_ice_aktar(args.dosya, args.ustune_yaz)
    
    elif args.komut == 'listele':
        yonetici.kullanicilari_listele()
    
    elif args.komut == 'sil':
        yonetici.anahtar_sil(args.kullanici)
    
    elif args.komut == 'getir':
        anahtar = yonetici.anahtar_getir(args.kullanici)
        if anahtar:
            print(f"{args.kullanici} için Gizli Anahtar: {anahtar}")
        else:
            print(f"✗ Kullanıcı bulunamadı: {args.kullanici}")
            sys.exit(1)

if __name__ == "__main__":
    main()
