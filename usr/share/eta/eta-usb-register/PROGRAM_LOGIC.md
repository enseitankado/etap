# ETA USB Login - Program Mantığı ve Akış Diyagramı

## 📋 Genel Bakış

Sistem **2 ana bileşenden** oluşuyor:

1. **usb-register** - USB'ye credential yazma (GUI uygulaması)
2. **usb-login** - USB'den credential okuyup giriş yapma (Daemon servisi)

---

## 🔷 BÖLÜM 1: USB-REGISTER (Kayıt Uygulaması)

### Amaç
Öğretmenin USB belleğini EBA kimlik bilgileriyle eşleştirmek.

### Ana Akış

```
[Başlat]
   ↓
[USB Listesini Göster]
   ↓
[USB Seç]
   ↓
[EBA'ya Giriş Yap (WebView)]
   ↓
[Token Al]
   ↓
[Öğretmen Bilgilerini Çek]
   ↓
[Yeni Şifre Belirle]
   ↓
[EBA'ya Şifre Sıfırlama İsteği]
   ↓
[USB'yi EBA'ya Kaydet]
   ↓
[Credential Dosyası Oluştur]
   ↓
[USB'ye Yaz: .credentials]
   ↓
[Bitti]
```

### Detaylı Adımlar

#### Adım 1: Başlangıç
```python
# Main.py
app = Application()
app.run()
  ↓
# MainWindow.py
window = MainWindow(application)
  ↓
# USB cihazları taranır
usb_manager = USBDeviceManager()
devices = usb_manager.get_usb_devices()
```

**Çıktı**: USB listesi
```python
[
    ['/dev/sdb1', '/media/usb', 'Kingston', '8.0 GB', '303E-3F39'],
    ['/dev/sdc1', '/media/usb2', 'SanDisk', '16.0 GB', 'ABCD-1234']
]
```

#### Adım 2: USB Seçimi
```python
# Kullanıcı combobox'tan seçer
selected_device = cmb_devices.get_active()
model.usb = list_devices[selected_device]

# USB bilgileri saklanır:
# model.usb = [device_path, mount_point, label, size, uuid]
```

#### Adım 3: EBA Girişi (WebView)
```python
# EBA giriş sayfası WebView'da açılır
webview.load_uri("https://giris.eba.gov.tr/EBA_GIRIS/Giris?uygulamaKodu=pardus&login=teacher")

# Kullanıcı TC/Şifre ile giriş yapar
# JavaScript ile token yakalanır
```

**JavaScript Kodu** (WebView içinde):
```javascript
// Giriş başarılı olunca
window.location.href = "callback://success?token=ABCD1234&url=http://api.etap.org.tr/..."
```

**Python tarafında yakalama**:
```python
def on_decide_policy(webview, decision, decision_type):
    uri = decision.get_request().get_uri()
    
    if uri.startswith("callback://success"):
        # Token'ı parse et
        params = parse_qs(urlparse(uri).query)
        model.token = params['token'][0]
        model.url = params['url'][0]
        
        # Öğretmen bilgilerini al
        get_ogretmen_info()
```

#### Adım 4: Öğretmen Bilgilerini Alma
```python
def get_ogretmen_info():
    # Token ile API'ye istek
    r = requests.get(model.url)
    
    data = r.json()
    # {
    #   "data": {
    #     "tckn": "12345678901",
    #     "uid": "ABC123",
    #     "uname": "Öğretmen Adı",
    #     "school_schoolName": "Test Okulu"
    #   }
    # }
    
    model.tckn = data['data']['tckn']
    model.eba_id = data['data']['uid']
    model.username = turkish_to_english(data['data']['uname'])
    # "Öğretmen Adı" → "ogretmen.adi"
```

#### Adım 5: Şifre Belirleme
```python
# Kullanıcı arayüzden şifre girer
password = entry_password.get_text()
password_again = entry_password_again.get_text()

# Şifre kontrolü
if password != password_again:
    show_error("Şifreler eşleşmiyor")
    return

if len(password) < 8:
    show_error("Şifre en az 8 karakter olmalı")
    return
```

#### Adım 6: EBA'ya Şifre Sıfırlama
```python
def reset_password_and_register():
    # 1. Şifreyi sıfırla
    r = requests.post(
        url="https://giris.eba.gov.tr/EBA_GIRIS/UsbPasswordChangerV7",
        headers={
            "content-type": "application/x-www-form-urlencoded",
            "origin": "http://api.etap.org.tr"
        },
        data={
            "authCode": model.token,
            "newPass": password,
            "repPass": password,
            "user_tckn": model.tckn
        }
    )
    
    if r.status_code != 200:
        show_error("Şifre sıfırlama başarısız")
        return False
```

#### Adım 7: USB'yi EBA'ya Kaydetme
```python
    # 2. USB'yi kaydet
    usb_uuid = model.usb[4]  # UUID
    
    r = requests.post(
        url="https://giris.eba.gov.tr/EBA_GIRIS/RegisterUsbUser",
        headers={
            "content-type": "application/x-www-form-urlencoded",
            "origin": "http://api.etap.org.tr"
        },
        json={
            "tckn": model.tckn,
            "password": password,
            "eba_id": model.eba_id,
            "usb_serial": usb_uuid,
            "username": model.username
        }
    )
    
    if r.status_code != 200:
        show_error("USB kayıt başarısız")
        return False
```

#### Adım 8: Credential Dosyası Oluşturma
```python
def save_credentials():
    # Şifreyi hash'le (bcrypt)
    password_hash = crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512))
    # Örnek: "$6$saltsalt$hashhash..."
    
    # Credential objesi oluştur
    credentials = {
        "username": model.username,      # "ogretmen.adi"
        "password": password_hash,       # "$6$..."
        "name": model.name,              # "Öğretmen Adı"
        "eba_id": model.eba_id,          # "ABC123XYZ"
        "usb_serial": usb_uuid           # "303E-3F39"
    }
    
    # Encode et (JSON → Hex → Pickle)
    json_data = json.dumps(credentials)
    hex_data = binascii.hexlify(json_data.encode("utf-8"))
    pickled = pickle.dumps(hex_data, pickle.HIGHEST_PROTOCOL)
    
    return pickled
```

#### Adım 9: USB'ye Yazma
```python
def write_to_usb():
    usb_mount_point = model.usb[1]  # "/media/usb"
    credential_file = os.path.join(usb_mount_point, ".credentials")
    
    with open(credential_file, "wb") as f:
        f.write(pickled_data)
    
    show_success("USB kaydedildi!")
```

### Veri Yapıları

#### Model Objesi
```python
class Model:
    # Kimlik Bilgileri
    tckn = "12345678901"           # TC Kimlik No
    eba_id = "G7n5P7bfP9n5P600"    # EBA Unique ID
    name = "Öğretmen Adı Soyadı"   # Tam ad
    username = "ogretmen.adi"      # Linux username
    
    # Güvenlik
    token = "eyJhbGciOiJIUzI1NiIs..." # Auth token
    url = "http://api.etap.org.tr/..." # Callback URL
    
    # USB
    usb = [
        "/dev/sdb1",               # Device path
        "/media/usb",              # Mount point
        "Kingston",                # Label
        "8.0 GB",                  # Size
        "303E-3F39"                # UUID (Serial)
    ]
    
    mode = "register"              # Mod (register/delete)
```

#### Credential Dosyası (.credentials)
```python
# Ham format:
{
    "username": "ogretmen.adi",
    "password": "$6$rounds=656000$YI/B2C4b...",
    "name": "Öğretmen Adı Soyadı",
    "eba_id": "G7n5P7bfP9n5P600x5N5c",
    "usb_serial": "303E-3F39"
}

# Encoding:
JSON → binascii.hexlify() → pickle.dumps() → .credentials file

# Dosyada:
b'\x80\x04\x95\xb1\x00\x00\x00...'  (binary pickle data)
```

---

## 🔶 BÖLÜM 2: USB-LOGIN (Giriş Servisi)

### Amaç
USB takıldığında otomatik olarak:
1. Credential'ı oku
2. EBA'dan doğrula
3. Kullanıcı oluştur
4. Sisteme giriş yap

### Servis Mimarisi

```
[UDEV Rules]
   ↓ (USB takıldı)
[UDEV Event] → JSON
   ↓
[Unix Socket: /run/etap/usb-trigger]
   ↓
[main.py - Socket Server]
   ↓ (Thread)
[service.py - Event Handler]
   ↓
[usb.py - Mount & Read]
   ↓
[credentials.py - Decode]
   ↓
[user.py - EBA Check]
   ↓
[user.py - Create User]
   ↓
[pam.py - Login Trigger]
   ↓
[LightDM - Auto Login]
```

### Detaylı Akış

#### 1. UDEV Kuralı
```bash
# /etc/udev/rules.d/99-etap-usb.rules
ACTION=="add", SUBSYSTEM=="block", ENV{DEVTYPE}=="partition", \
    RUN+="/usr/bin/python3 /usr/share/etap/usb-trigger.py"
```

**USB takılınca:**
```bash
/usr/share/etap/usb-trigger.py
```

#### 2. UDEV Trigger Script
```python
# usb-trigger.py
import socket
import json
import os

# UDEV environment değişkenlerini al
udev_data = {
    "ACTION": os.environ.get("ACTION"),           # "add"
    "DEVNAME": os.environ.get("DEVNAME"),         # "/dev/sdb1"
    "ID_FS_UUID": os.environ.get("ID_FS_UUID"),   # "303E-3F39"
    "SUBSYSTEM": os.environ.get("SUBSYSTEM"),     # "block"
    "DEVTYPE": os.environ.get("DEVTYPE")          # "partition"
}

# Unix socket'e gönder
client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
client.connect("/run/etap/usb-trigger")
client.sendall(json.dumps(udev_data).encode())
client.close()
```

#### 3. Socket Server (main.py)
```python
# main.py - Systemd servisi olarak çalışır
import socket
import threading

# Socket oluştur
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind("/run/etap/usb-trigger")
server.listen(1)

print("USB Login servisi başlatıldı")

# Sonsuz döngü
while True:
    connection, client_address = server.accept()
    
    # Veriyi al
    data = connection.recv(1024**2)  # Max 1MB
    connection.close()
    
    # JSON parse et
    udev_data = json.loads(data.decode())
    # {
    #   "ACTION": "add",
    #   "DEVNAME": "/dev/sdb1",
    #   "ID_FS_UUID": "303E-3F39"
    # }
    
    # Thread'de işle (bloklamadan devam etsin)
    thread = threading.Thread(target=service.listen, args=[udev_data])
    thread.start()
```

#### 4. Event Handler (service.py)
```python
def listen(udata):
    if udata["ACTION"] == "add":
        return add_event(udata)
    elif udata["ACTION"] == "remove":
        return remove_event(udata)

def add_event(udata):
    print(f"USB eklendi: {udata['DEVNAME']}")
    
    # LightDM çalışıyor mu kontrol et
    if not os.path.exists("/var/lib/lightdm/pardus-greeter"):
        print("LightDM çalışmıyor, çıkılıyor")
        return
    
    # Partition adını al
    part = os.path.basename(udata["DEVNAME"])  # "sdb1"
    
    # USB'yi mount et ve .credentials dosyasını oku
    credential_data = usb.mount_and_check(part, ".credentials")
    
    if credential_data is None:
        print("Credential dosyası bulunamadı")
        return False
    
    # USB UUID'sini al
    usb_uuid = usb.get_uuid(part)  # "303E-3F39"
    
    # Credential'ı decode et
    credentials = credentials.read(credential_data)
    
    if credentials is None:
        print("Geçersiz credential formatı")
        return False
    
    # Credential yapısı:
    # {
    #   "username": "ogretmen.adi",
    #   "password": "$6$...",
    #   "name": "Öğretmen Adı",
    #   "eba_id": "ABC123",
    #   "usb_serial": "303E-3F39"
    # }
    
    # USB serial kontrolü
    if credentials["usb_serial"] != usb_uuid:
        pam.lightdm_print("USB Serial Mismatch")
        return False
    
    # LightDM'e mesaj göster
    pam.lightdm_print("Logging in, please wait...", block=True)
    
    # EBA doğrulaması
    [eba_ok, eba_message] = user.check_eba(
        credentials["eba_id"], 
        credentials["usb_serial"]
    )
    
    if not eba_ok:
        pam.lightdm_print(eba_message, block=False)
        return False
    
    # Kullanıcı var mı kontrol et (EBA ID'ye göre)
    existing_user = user.find_by_ebaid(credentials["eba_id"])
    
    if existing_user:
        # Varsa kullanıcı adını güncelle
        credentials["username"] = existing_user
    else:
        # Yoksa yeni kullanıcı adı belirle (çakışma kontrolü)
        base_username = credentials["username"]
        i = 0
        while user.is_valid_user(credentials["username"]):
            credentials["username"] = f"{base_username}{i}"
            i += 1
    
    # Kullanıcı oluştur/güncelle
    user.create_user(
        credentials["username"],
        credentials["password"],
        credentials["name"],
        credentials["eba_id"]
    )
    
    # UID bul
    uid = user.find_uid(credentials["username"])
    
    # Credential'ı /run/etap/{uid}/credentials dosyasına kopyala
    os.makedirs(f"/run/etap/{uid}/", exist_ok=True)
    
    with open(f"/run/etap/{uid}/credentials", "wb") as f:
        f.write(credential_data)
    
    os.chmod(f"/run/etap/{uid}", 0o700)
    os.chown(f"/run/etap/{uid}", int(uid), 0)
    
    # PAM'a kullanıcıyı bildir
    pam.allow_user(credentials["username"])
    
    # LightDM'e giriş komutu gönder
    pam.lightdm_trigger(credentials["username"])
    
    return True
```

#### 5. USB Mount ve Okuma (usb.py)
```python
def mount_and_check(part, file):
    """
    USB partition'ı mount et ve dosyayı oku
    """
    # Device hazır mı bekle
    while not os.path.exists(f"/dev/{part}"):
        print(f"Bekleniyor: {part}")
        time.sleep(0.1)
    
    # Mount noktası oluştur
    mount_point = f"/run/etap/{part}"
    os.makedirs(mount_point, exist_ok=True)
    
    # Mount et (read-only)
    subprocess.run([
        "/usr/bin/mount", 
        "-o", "ro",              # Read-only
        f"/dev/{part}",
        mount_point
    ])
    
    # Dosya var mı kontrol et
    credential_path = f"{mount_point}/{file}"
    
    if os.path.exists(credential_path):
        with open(credential_path, "rb") as f:
            data = f.read().strip()
    else:
        data = None
    
    # Unmount et
    subprocess.run(["umount", mount_point])
    os.rmdir(mount_point)
    
    return data

def get_uuid(part):
    """
    Partition UUID'sini bul
    """
    for uuid in os.listdir("/dev/disk/by-uuid"):
        link = os.readlink(f"/dev/disk/by-uuid/{uuid}")
        if part == os.path.basename(link):
            return uuid
    return None
```

#### 6. Credential Decode (credentials.py)
```python
def read(ctx):
    if ctx is None:
        return None
    
    try:
        # Pickle'dan çöz
        loaded = pickle.loads(ctx)
        
        # Hex'ten çöz
        loaded = binascii.unhexlify(loaded)
        
        # JSON'dan çöz
        loaded = json.loads(loaded.decode("utf-8"))
        
        return loaded
        
    except Exception as e:
        print(f"Credential decode hatası: {e}")
        return None
```

#### 7. EBA Doğrulama (user.py)
```python
def check_eba(eba_id, usb_serial):
    """
    EBA sunucusundan kullanıcıyı doğrula
    """
    url = "https://giris.eba.gov.tr/EBA_GIRIS/GetUsbUser"
    body = {
        "eba_id": eba_id,
        "usb_serial": usb_serial
    }
    
    # 10 deneme
    for i in range(10):
        try:
            response = requests.post(url, json=body)
            
            # Boş yanıt kontrolü
            if len(response.text.strip()) == 0:
                return [False, "Servis yavaş, tekrar deneyin"]
            
            # Başarı kontrolü
            if "EBA.001" in response.text:
                return [True, "Başarılı"]
            else:
                return [False, "EBA Doğrulama Başarısız"]
                
        except Exception as e:
            print(f"EBA isteği hatası: {e}")
            time.sleep(3)
    
    # Tüm denemeler başarısız
    return [False, "İnternet bağlantısı kontrol edin"]
```

#### 8. Kullanıcı Oluşturma (user.py)
```python
def create_user(username, password_hash, realname, ebaid):
    """
    Linux kullanıcısı oluştur
    """
    # EBA ID'yi hash'le (bulma amaçlı)
    eba_hash = hashlib.md5(str(ebaid).encode()).hexdigest()
    
    # Kullanıcı var mı kontrol et
    if is_valid_user(username):
        # Varsa sadece şifreyi güncelle
        return update_passwd(username, password_hash)
    
    # Kullanıcı grupları
    groups = [
        "cdrom", "floppy", "audio", "video", 
        "plugdev", "bluetooth", "scanner", 
        "netdev", "dip", "lpadmin"
    ]
    
    # useradd komutu
    subprocess.run([
        "useradd",
        "-p", password_hash,          # Şifre hash'i
        "-s", "/bin/bash",            # Shell
        "-c", f"{realname},,,,{eba_hash}",  # GECOS (ad + EBA hash)
        "-m",                         # Home directory oluştur
        username
    ])
    
    # Gruplara ekle
    for group in groups:
        subprocess.run(["usermod", "-a", "-G", group, username])
    
    return True

def find_by_ebaid(ebaid):
    """
    EBA ID'ye göre kullanıcı bul
    """
    eba_hash = hashlib.md5(str(ebaid).encode()).hexdigest()
    
    with open("/etc/passwd", "r") as f:
        for line in f:
            if ":" not in line:
                continue
            
            # GECOS alanından EBA hash'i al
            gecos = line.split(":")[4]
            
            if ",,,," in gecos:
                stored_hash = gecos.split(",")[-1]
                if stored_hash == eba_hash:
                    return line.split(":")[0]  # Username
    
    return None
```

#### 9. LightDM Tetikleme (pam.py)
```python
def allow_user(username):
    """
    Kullanıcıyı PAM için yaz
    """
    os.makedirs("/run/etap", exist_ok=True)
    
    with open("/run/etap/user", "w") as f:
        f.write(username)

def lightdm_trigger(username, password=""):
    """
    LightDM'e otomatik giriş komutu gönder
    """
    if not os.path.exists("/var/lib/lightdm/pardus-greeter"):
        return
    
    data = {
        "username": username,
        "password": password  # Boş (PAM modülü halleder)
    }
    
    # LightDM socket'ine gönder
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.connect("/var/lib/lightdm/pardus-greeter")
    client.sendall(json.dumps(data).encode())
    client.close()

def lightdm_print(message, block=None):
    """
    LightDM ekranında mesaj göster
    """
    if not os.path.exists("/var/lib/lightdm/pardus-greeter"):
        return
    
    data = {"message": message}
    
    if block == True:
        data["event"] = "block-gui"
    elif block == False:
        data["event"] = "unblock-gui"
    
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.connect("/var/lib/lightdm/pardus-greeter")
    client.sendall(json.dumps(data).encode())
    client.close()
```

#### 10. USB Çıkarma (remove_event)
```python
def remove_event(udata):
    """
    USB çıkarıldığında
    """
    uuid = udata.get("ID_FS_UUID")
    
    # /run/etap/ altındaki tüm kullanıcıları kontrol et
    for uid in os.listdir("/run/etap/"):
        credential_file = f"/run/etap/{uid}/credentials"
        
        if not os.path.isfile(credential_file):
            continue
        
        # Credential'ı oku
        with open(credential_file, "rb") as f:
            cred = credentials.read(f.read())
        
        # UUID eşleşiyor mu?
        if cred and cred.get("usb_serial") == uuid:
            # Credential dosyasını sil
            os.remove(credential_file)
            
            # Eğer desktop session varsa, agent'a quit sinyali gönder
            if os.path.exists("/var/lib/lightdm/pardus-greeter"):
                continue
            
            # Agent PID'lerini bul ve quit sinyali gönder
            for pid in os.listdir(f"/run/etap/{uid}/"):
                if os.path.isdir(f"/proc/{pid}"):
                    # Agent çalışıyor, quit komutu gönder
                    with open(f"/run/etap/{uid}/{pid}", "w") as f:
                        f.write(json.dumps({"action": "quit"}))
                
                # PID dosyasını sil
                os.remove(f"/run/etap/{uid}/{pid}")
```

---

## 📊 Veri Akış Diyagramı

### USB Kayıt (usb-register)

```
┌─────────────────────┐
│   Kullanıcı         │
│   (Öğretmen)        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  USB Seç            │
│  ComboBox           │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  EBA Giriş          │
│  WebView            │
│  TC + Şifre         │
└──────────┬──────────┘
           │ JavaScript
           ▼
┌─────────────────────┐
│  Token Yakalama     │
│  callback://success │
└──────────┬──────────┘
           │ requests.get()
           ▼
┌─────────────────────┐
│  Öğretmen Bilgileri │
│  GET api.etap.org.tr│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Model Doldurma     │
│  tckn, eba_id, etc. │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Şifre Girişi       │
│  Entry widgets      │
└──────────┬──────────┘
           │ requests.post()
           ▼
┌─────────────────────┐
│  Şifre Sıfırlama    │
│  POST /PasswordChanger
└──────────┬──────────┘
           │ requests.post()
           ▼
┌─────────────────────┐
│  USB Kayıt          │
│  POST /RegisterUsb  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Credential Encode  │
│  JSON→Hex→Pickle    │
└──────────┬──────────┘
           │ write()
           ▼
┌─────────────────────┐
│  USB'ye Yaz         │
│  .credentials       │
└─────────────────────┘
```

### USB Giriş (usb-login)

```
┌─────────────────────┐
│   USB Takıldı       │
│   Hardware Event    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   UDEV Rule         │
│   99-etap-usb.rules │
└──────────┬──────────┘
           │ RUN+=
           ▼
┌─────────────────────┐
│   Trigger Script    │
│   usb-trigger.py    │
└──────────┬──────────┘
           │ socket.send()
           ▼
┌─────────────────────┐
│   Unix Socket       │
│   /run/etap/trigger │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Socket Server     │
│   main.py (daemon)  │
└──────────┬──────────┘
           │ threading.Thread()
           ▼
┌─────────────────────┐
│   Event Handler     │
│   service.listen()  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   USB Mount         │
│   usb.mount_and_check
└──────────┬──────────┘
           │ read()
           ▼
┌─────────────────────┐
│   .credentials      │
│   Binary File       │
└──────────┬──────────┘
           │ pickle.loads()
           ▼
┌─────────────────────┐
│   Credential Decode │
│   Pickle→Hex→JSON   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   UUID Kontrolü     │
│   Match check       │
└──────────┬──────────┘
           │ requests.post()
           ▼
┌─────────────────────┐
│   EBA Doğrulama     │
│   POST /GetUsbUser  │
└──────────┬──────────┘
           │ (10 retry)
           ▼
┌─────────────────────┐
│   User Kontrolü     │
│   find_by_ebaid()   │
└──────────┬──────────┘
           │ useradd
           ▼
┌─────────────────────┐
│   User Oluştur      │
│   create_user()     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Credential Kopyala│
│   /run/etap/{uid}/  │
└──────────┬──────────┘
           │ socket.send()
           ▼
┌─────────────────────┐
│   LightDM Trigger   │
│   Auto-login        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Desktop Login     │
│   Session başladı   │
└─────────────────────┘
```

---

## 🔄 Durum Makinesi (State Machine)

### usb-register States

```
[IDLE]
  │
  ├─► [USB_SELECTION]
  │     │
  │     ├─► [WEBVIEW_LOADING]
  │     │     │
  │     │     ├─► [WEBVIEW_LOGIN] ◄─┐
  │     │     │     │                │
  │     │     │     ├─► [TOKEN_RECEIVED]
  │     │     │     │     │
  │     │     │     │     ├─► [FETCHING_INFO]
  │     │     │     │     │     │
  │     │     │     │     │     ├─► [PASSWORD_INPUT]
  │     │     │     │     │     │     │
  │     │     │     │     │     │     ├─► [REGISTERING]
  │     │     │     │     │     │     │     │
  │     │     │     │     │     │     │     ├─► [SUCCESS]
  │     │     │     │     │     │     │     │
  │     │     │     │     │     │     │     └─► [ERROR] ─┐
  │     │     │     │     │     │     │                   │
  │     │     │     │     │     │     └───────────────────┤
  │     │     │     │     │     └─────────────────────────┤
  │     │     │     │     └───────────────────────────────┤
  │     │     │     └─────────────────────────────────────┘
  │     │     │
  │     │     └─► [ERROR]
  │     │
  │     └─► [ERROR]
  │
  └─► [EXIT]
```

### usb-login States

```
[DAEMON_RUNNING]
  │
  ├─► [WAITING_EVENT]
  │     │
  │     ├─── USB_ADD ───► [PROCESSING_ADD]
  │     │                   │
  │     │                   ├─► [MOUNTING]
  │     │                   │     │
  │     │                   │     ├─► [READING_CRED]
  │     │                   │     │     │
  │     │                   │     │     ├─► [VALIDATING]
  │     │                   │     │     │     │
  │     │                   │     │     │     ├─► [EBA_CHECK] (retry 10x)
  │     │                   │     │     │     │     │
  │     │                   │     │     │     │     ├─► [USER_CREATE]
  │     │                   │     │     │     │     │     │
  │     │                   │     │     │     │     │     ├─► [LOGIN_TRIGGER]
  │     │                   │     │     │     │     │     │     │
  │     │                   │     │     │     │     │     │     └─► [SUCCESS]
  │     │                   │     │     │     │     │     │
  │     │                   │     │     │     │     │     └─► [FAIL]
  │     │                   │     │     │     │     │
  │     │                   │     │     │     │     └─► [FAIL]
  │     │                   │     │     │     │
  │     │                   │     │     │     └─► [FAIL]
  │     │                   │     │     │
  │     │                   │     │     └─► [FAIL]
  │     │                   │     │
  │     │                   │     └─► [UNMOUNTING]
  │     │                   │
  │     │                   └─► [WAITING_EVENT]
  │     │
  │     └─── USB_REMOVE ──► [PROCESSING_REMOVE]
  │                           │
  │                           ├─► [CLEANUP]
  │                           │     │
  │                           │     └─► [AGENT_QUIT]
  │                           │
  │                           └─► [WAITING_EVENT]
  │
  └─► [SHUTDOWN]
```

---

## 🎯 Kritik Karar Noktaları

### 1. Kullanıcı Adı Belirleme
```
EBA ID'ye göre kullanıcı var mı?
├─── EVET → Mevcut kullanıcı adını kullan
└─── HAYIR → Yeni kullanıcı adı belirle
              ├─── Username benzersiz mi?
              │    ├─── EVET → Kullan
              │    └─── HAYIR → Sayı ekle (username0, username1...)
              │
              └─── Tekrar kontrol et
```

### 2. EBA Doğrulama
```
EBA'ya POST isteği
├─── HTTP 200 + "EBA.001" → Başarılı
├─── HTTP 200 + Diğer → Başarısız
├─── HTTP != 200 → Başarısız
├─── Network Timeout → Retry (max 10)
│                      └─── 10. deneme → Başarısız
└─── Exception → Retry (max 10)
                 └─── 10. deneme → Başarısız
```

### 3. USB Serial Eşleşme
```
Credential'daki USB serial == Gerçek USB serial?
├─── EVET → Devam et
└─── HAYIR → "USB Serial Mismatch" → İptal
```

### 4. Credential Geçerliliği
```
Credential dosyası okunabildi mi?
├─── EVET → Pickle decode başarılı mı?
│           ├─── EVET → Hex decode başarılı mı?
│           │           ├─── EVET → JSON parse başarılı mı?
│           │           │           ├─── EVET → Gerekli alanlar var mı?
│           │           │           │           ├─── EVET → GEÇERLİ
│           │           │           │           └─── HAYIR → GEÇERSİZ
│           │           │           └─── HAYIR → GEÇERSİZ
│           │           └─── HAYIR → GEÇERSİZ
│           └─── HAYIR → GEÇERSİZ
└─── HAYIR → GEÇERSİZ
```

---

## 📦 Dosya Yapısı ve Lokasyonlar

### Runtime Dosyaları
```
/run/etap/
├── usb-trigger                    # Unix socket (daemon ile iletişim)
├── user                           # Son allow edilen kullanıcı adı
├── {uid}/                         # Kullanıcı ID klasörü
│   ├── credentials                # Kopyalanan credential (binary)
│   └── {pid}                      # Agent PID dosyaları (quit sinyali için)
└── {partition}/                   # Geçici mount noktaları
    └── .credentials               # USB'den okunan dosya (mount sırasında)
```

### USB Dosyaları
```
/media/{username}/{uuid}/
└── .credentials                   # Gizli credential dosyası (binary)
```

### Sistem Dosyaları
```
/etc/passwd                        # Kullanıcı listesi (EBA hash GECOS'ta)
/etc/udev/rules.d/
└── 99-etap-usb.rules             # UDEV kuralı
/var/lib/lightdm/
└── pardus-greeter                 # LightDM socket
/usr/share/etap/
├── main.py                        # Daemon ana dosyası
├── service.py                     # Event handler
├── usb.py                         # USB işlemleri
├── credentials.py                 # Credential decode
├── user.py                        # Kullanıcı işlemleri
└── pam.py                         # PAM/LightDM entegrasyonu
```

---

## ⏱️ Timing ve Performance

### USB Takma → Giriş Süresi
```
USB Takıldı (t=0)
  ↓ ~100ms
UDEV Event
  ↓ ~50ms
Socket Trigger
  ↓ ~10ms
Thread Başlatıldı
  ↓ ~500ms
Mount + Read
  ↓ ~100ms
Decode
  ↓ ~50ms
UUID Check
  ↓ ~2000ms (network)
EBA Check
  ↓ ~500ms
User Create
  ↓ ~100ms
Credential Copy
  ↓ ~200ms
LightDM Trigger
  ↓ ~2000ms
Desktop Login
─────────────
TOPLAM: ~5-6 saniye
```

### EBA Doğrulama Timeout Senaryoları
```
Başarılı (ilk denemede):
  → ~2 saniye

Network yavaş (3. denemede):
  → ~8 saniye (3×3 saniye bekleme)

Tamamen başarısız:
  → ~30 saniye (10×3 saniye bekleme)
```

---

## 🔐 Güvenlik Kontrolleri

### USB-Register
```
1. EBA Token doğrulama (WebView callback)
2. API yanıt kontrolü (HTTP 200)
3. TC kimlik kontrolü (TCKN formatı)
4. Şifre uzunluk kontrolü (min 8 karakter)
5. Şifre eşleşme kontrolü
6. USB mount kontrolü
7. Dosya yazma yetkisi kontrolü
```

### USB-Login
```
1. LightDM çalışıyor mu? → Hayırsa çık
2. Credential dosyası var mı? → Yoksa çık
3. Credential decode edilebiliyor mu? → Hayırsa çık
4. USB serial eşleşiyor mu? → Hayırsa çık
5. EBA doğrulaması geçiyor mu? → Hayırsa çık
6. Kullanıcı oluşturulabiliyor mu? → Hayırsa çık
7. LightDM tetiklenebiliyor mu? → Hayırsa loglanıyor
```

---

## 🐛 Hata Senaryoları ve Tepkileri

| Hata | Konum | Tepki |
|------|-------|-------|
| LightDM çalışmıyor | service.py | Sessizce çık (log) |
| Credential yok | usb.py | Return None |
| Decode hatası | credentials.py | Return None, log |
| UUID mismatch | service.py | LightDM'e mesaj göster |
| EBA timeout | user.py | 10 deneme, sonra hata mesajı |
| EBA auth fail | user.py | LightDM'e hata mesajı |
| User create fail | user.py | Return False, log |
| Mount fail | usb.py | Return None, log |

---

Bu programın tam mantığı budur. Her adım, veri akışı ve karar noktası detaylı olarak açıklandı.
