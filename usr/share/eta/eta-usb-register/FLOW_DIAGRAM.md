```mermaid
flowchart TD
    Start([Başlat]) --> RegisterOrLogin{Hangi Uygulama?}
    
    %% USB-REGISTER FLOW
    RegisterOrLogin -->|usb-register| SelectUSB[USB Seç]
    SelectUSB --> EBALogin[EBA'ya Giriş Yap<br/>WebView]
    EBALogin --> GetToken[Token Al<br/>JavaScript Callback]
    GetToken --> GetTeacherInfo[Öğretmen Bilgilerini Çek<br/>GET api.etap.org.tr]
    GetTeacherInfo --> EnterPassword[Yeni Şifre Belirle]
    EnterPassword --> ResetPassword[Şifre Sıfırla<br/>POST /UsbPasswordChangerV7]
    ResetPassword --> RegisterUSB[USB Kaydet<br/>POST /RegisterUsbUser]
    RegisterUSB --> CreateCred[Credential Oluştur<br/>JSON→Hex→Pickle]
    CreateCred --> WriteUSB[USB'ye Yaz<br/>.credentials]
    WriteUSB --> RegisterDone([Kayıt Tamamlandı])
    
    %% USB-LOGIN FLOW
    RegisterOrLogin -->|usb-login| USBPlugged[USB Takıldı<br/>Hardware Event]
    USBPlugged --> UDEVRule[UDEV Rule Tetiklendi]
    UDEVRule --> SendSocket[Unix Socket'e Gönder<br/>/run/etap/usb-trigger]
    SendSocket --> DaemonReceive[Daemon İsteği Aldı<br/>main.py]
    DaemonReceive --> CreateThread[Thread Oluştur]
    CreateThread --> MountUSB[USB'yi Mount Et]
    MountUSB --> ReadCred[.credentials Dosyasını Oku]
    ReadCred --> DecodeCred[Credential Decode<br/>Pickle→Hex→JSON]
    DecodeCred --> CheckUUID{USB Serial<br/>Eşleşiyor mu?}
    
    CheckUUID -->|Hayır| ShowError1[Hata Göster:<br/>USB Serial Mismatch]
    ShowError1 --> LoginFail([Giriş Başarısız])
    
    CheckUUID -->|Evet| EBACheck[EBA Doğrulama<br/>POST /GetUsbUser]
    EBACheck --> EBARetry{Başarılı mı?}
    
    EBARetry -->|Hayır + Retry < 10| Wait3Sec[3 Saniye Bekle]
    Wait3Sec --> EBACheck
    
    EBARetry -->|Hayır + Retry = 10| ShowError2[Hata Göster:<br/>İnternet Hatası]
    ShowError2 --> LoginFail
    
    EBARetry -->|Evet| FindUser{Kullanıcı<br/>Var mı?}
    FindUser -->|Evet| UpdateUser[Şifreyi Güncelle]
    FindUser -->|Hayır| CreateUser[Yeni Kullanıcı Oluştur<br/>useradd]
    
    UpdateUser --> CopyCred[Credential Kopyala<br/>/run/etap/uid/]
    CreateUser --> CopyCred
    
    CopyCred --> AllowPAM[PAM'a Bildir]
    AllowPAM --> TriggerLightDM[LightDM Tetikle<br/>Auto-login]
    TriggerLightDM --> LoginSuccess([Giriş Başarılı<br/>Desktop Açıldı])
    
    %% REMOVE EVENT
    USBPlugged -.->|USB Çıkarıldı| RemoveEvent[Remove Event]
    RemoveEvent --> FindCred[Credential Bul<br/>UUID ile]
    FindCred --> DeleteCred[Credential Sil]
    DeleteCred --> CheckAgent{Desktop<br/>Session Var mı?}
    CheckAgent -->|Evet| SendQuit[Agent'a Quit Gönder]
    CheckAgent -->|Hayır| RemoveDone([Temizlik Tamamlandı])
    SendQuit --> RemoveDone
    
    style Start fill:#90EE90
    style RegisterDone fill:#90EE90
    style LoginSuccess fill:#90EE90
    style LoginFail fill:#FFB6C6
    style RemoveDone fill:#ADD8E6
    style ShowError1 fill:#FFB6C6
    style ShowError2 fill:#FFB6C6
    style EBACheck fill:#FFD700
    style CheckUUID fill:#FFD700
    style EBARetry fill:#FFD700
```

# ETA USB Login - Basit Akış Özeti

## 1. USB Kaydı (usb-register)

```
Kullanıcı USB'yi seçer
    ↓
EBA'ya WebView'da giriş yapar
    ↓
Token JavaScript ile yakalanır
    ↓
Öğretmen bilgileri API'den çekilir
    ↓
Yeni şifre belirlenir
    ↓
EBA'ya şifre sıfırlama isteği
    ↓
USB, EBA sistemine kaydedilir
    ↓
Credential dosyası oluşturulur (JSON→Hex→Pickle)
    ↓
USB'ye .credentials dosyası yazılır
```

## 2. USB ile Giriş (usb-login)

```
USB takılır (hardware event)
    ↓
UDEV kuralı çalışır
    ↓
Unix socket'e JSON gönderilir
    ↓
Daemon (main.py) isteği alır
    ↓
Thread oluşturulur (bloklamadan)
    ↓
USB mount edilir (read-only)
    ↓
.credentials dosyası okunur
    ↓
Credential decode edilir (Pickle→Hex→JSON)
    ↓
USB Serial kontrolü yapılır
    ├─ Eşleşmiyor → Hata mesajı → Çık
    └─ Eşleşiyor → Devam
        ↓
    EBA doğrulaması (POST /GetUsbUser)
    ├─ Başarısız → 3 saniye bekle → Tekrar (max 10)
    │   └─ 10 deneme de başarısız → Hata → Çık
    └─ Başarılı → Devam
        ↓
    Kullanıcı kontrolü
    ├─ Var → Şifre güncelle
    └─ Yok → Yeni kullanıcı oluştur (useradd)
        ↓
    Credential /run/etap/{uid}/ dizinine kopyalanır
        ↓
    PAM'a kullanıcı bildirilir
        ↓
    LightDM'e auto-login komutu gönderilir
        ↓
    Desktop oturumu açılır
```

## 3. USB Çıkarma

```
USB çıkarılır (hardware event)
    ↓
UDEV remove event
    ↓
Daemon UUID ile credential bulur
    ↓
/run/etap/{uid}/credentials silinir
    ↓
Eğer desktop session varsa:
    ├─ Agent'lara quit sinyali gönderilir
    └─ PID dosyaları silinir
```

## Kritik Dosyalar

| Dosya | Format | İçerik |
|-------|--------|--------|
| `/media/usb/.credentials` | Binary (Pickle) | Kullanıcı credential'ları |
| `/run/etap/usb-trigger` | Unix Socket | Daemon iletişim kanalı |
| `/run/etap/user` | Text | Son allow edilen username |
| `/run/etap/{uid}/credentials` | Binary (Pickle) | Kopyalanan credential |
| `/etc/passwd` | Text | GECOS'ta EBA hash var |

## Timing

- **Normal giriş**: ~5-6 saniye
- **Network yavaş**: ~8-10 saniye
- **Network timeout**: ~30 saniye (10 retry × 3 saniye)

## Güvenlik Kontrol Noktaları

1. ✅ USB Serial eşleşme kontrolü
2. ✅ EBA sunucu doğrulaması
3. ✅ LightDM çalışıyor mu kontrolü
4. ✅ Credential decode kontrolü
5. ❌ SSL sertifika pinning YOK
6. ❌ Socket authentication YOK
7. ❌ Credential encryption YOK
8. ❌ Replay attack koruması YOK
