# 🔐 OTP Yönetim Aracı (`otp-cli`)

Terminal tabanlı, kullanıcı odaklı TOTP (Time-based One-Time Password) gizli anahtar yönetim aracı. Google Authenticator ve benzeri OTP uygulamalarıyla tam uyumludur.

---

## 📋 İçindekiler

- [Özellikler](#-özellikler)
- [Gereksinimler](#-gereksinimler)
- [Kurulum](#-kurulum)
- [Kullanım](#-kullanım)
  - [Komutlar](#komutlar)
  - [Örnekler](#örnekler)
- [Güvenlik](#-güvenlik)
- [Katkıda Bulunma](#-katkıda-bulunma)
- [Lisans](#-lisans)

---

## ✨ Özellikler

- 🔑 Rastgele veya özel gizli anahtar oluşturma (Base32)
- 📱 Terminalde QR kod görüntüleme
- ✅ OTP kodu doğrulama
- 📤 Tekil veya toplu kullanıcı dışa/içe aktarma (`.totp` formatı)
- 👥 Kullanıcı listeleme ve silme
- 🛡️ Root yetkisi gerektiren işlemler için erişim kontrolü
- 🔒 Gizli anahtarlar `600` izniyle `/etc/otp-secrets.json` dosyasında güvenle saklanır

---

## 📦 Gereksinimler

- Python 3.6+
- Aşağıdaki Python kütüphaneleri:

```
pyotp
qrcode
```

---

## 🚀 Kurulum

**1. Depoyu klonlayın:**

```bash
git clone https://github.com/kullanici-adi/otp-cli.git
cd otp-cli
```

**2. Gerekli bağımlılıkları yükleyin:**

```bash
pip install pyotp qrcode
```

**3. Betiği çalıştırılabilir yapın (isteğe bağlı):**

```bash
chmod +x otp-cli.py
```

---

## 📖 Kullanım

```bash
sudo python3 otp-cli.py [komut] [seçenekler]
```

> ⚠️ `olustur`, `sil`, `iceri-aktar` ve `tumu-iceri-aktar` komutları `/etc/otp-secrets.json` dosyasına yazma yaptığından **root yetkisi** gerektirir.

---

### Komutlar

| Komut | Açıklama | Root Gerekir mi? |
|---|---|---|
| `olustur <kullanici>` | Kullanıcı için yeni gizli anahtar oluşturur | ✅ |
| `goster <kullanici>` | QR kodu ve gizli anahtarı gösterir | ❌ |
| `kod <kullanici>` | Güncel OTP kodunu ve kalan süreyi gösterir | ❌ |
| `dogrula <kullanici> <kod>` | Girilen OTP kodunu doğrular | ❌ |
| `getir <kullanici>` | Kullanıcının gizli anahtarını görüntüler | ❌ |
| `listele` | Kayıtlı tüm kullanıcıları listeler | ❌ |
| `sil <kullanici>` | Kullanıcının gizli anahtarını siler | ✅ |
| `disari-aktar <kullanici> <dosya>` | Gizli anahtarı `.totp` dosyasına aktarır | ❌ |
| `iceri-aktar <kullanici> <dosya>` | Gizli anahtarı `.totp` dosyasından yükler | ✅ |
| `tumu-disari-aktar <dosya>` | Tüm kullanıcıları tek dosyaya aktarır | ❌ |
| `tumu-iceri-aktar <dosya>` | Tüm kullanıcıları dosyadan toplu yükler | ✅ |

---

### Örnekler

**Rastgele gizli anahtar oluşturma:**
```bash
sudo python3 otp-cli.py olustur tankado
```

**Belirli bir Base32 anahtarı kullanarak oluşturma:**
```bash
sudo python3 otp-cli.py olustur tankado --anahtar JBSWY3DPEHPK3PXP
```

**Özel bir şifreden anahtar türetme:**
```bash
sudo python3 otp-cli.py olustur tankado --anahtardan "benim-gizli-sifrem"
```

**QR kodu terminalde görüntüleme:**
```bash
sudo python3 otp-cli.py goster tankado
```

> Çıktı olarak terminale ASCII QR kodu, gizli anahtar ve `otpauth://` URI'si yazdırılır. Bu QR kodu Google Authenticator, Authy veya benzeri uygulamalarla taranabilir.

**Güncel OTP kodunu alma:**
```bash
python3 otp-cli.py kod tankado
# Çıktı: tankado için Güncel OTP: 482910  (~23 saniye geçerli)
```

**OTP kodunu doğrulama:**
```bash
python3 otp-cli.py dogrula tankado 482910
# Başarılı → çıkış kodu: 0
# Başarısız → çıkış kodu: 1
```

**Gizli anahtarı dosyaya yedekleme:**
```bash
python3 otp-cli.py disari-aktar tankado tankado-yedek.totp
```

**Gizli anahtarı dosyadan geri yükleme:**
```bash
sudo python3 otp-cli.py iceri-aktar tankado tankado-yedek.totp
```

**Tüm kullanıcıları toplu yedekleme:**
```bash
python3 otp-cli.py tumu-disari-aktar tum-kullanicilar.totp
```

**Tüm kullanıcıları toplu geri yükleme:**
```bash
sudo python3 otp-cli.py tumu-iceri-aktar tum-kullanicilar.totp
# Çakışan kullanıcılar varsa onay sorar. Onaysız geçmek için:
sudo python3 otp-cli.py tumu-iceri-aktar tum-kullanicilar.totp --ustune-yaz
```

**Kayıtlı kullanıcıları listeleme:**
```bash
python3 otp-cli.py listele
```

**Kullanıcı silme:**
```bash
sudo python3 otp-cli.py sil tankado
# Silme öncesi onay istenir.
```

---

## 🔒 Güvenlik

- Gizli anahtarlar `/etc/otp-secrets.json` dosyasında saklanır. Bu dosya otomatik olarak `root:root` sahipliğiyle ve `600` (`rw-------`) izniyle ayarlanır; yalnızca root okuyabilir.
- Yazma gerektiren tüm komutlar `sudo` ile çalıştırılmalıdır.
- `.totp` yedek dosyaları Base64 kodlamalıdır; şifreleme içermez. Bu nedenle yedek dosyalarınızı güvenli bir ortamda saklayın.
- Silme işlemlerinde kullanıcı onayı zorunludur (ya da `--ustune-yaz` bayrağıyla geçilebilir).

---

## 🤝 Katkıda Bulunma

Katkılarınızı bekliyoruz! Lütfen şu adımları izleyin:

1. Bu depoyu fork'layın
2. Yeni bir dal oluşturun: `git checkout -b ozellik/yeni-ozellik`
3. Değişikliklerinizi commit'leyin: `git commit -m 'Yeni özellik eklendi'`
4. Dalı push'layın: `git push origin ozellik/yeni-ozellik`
5. Pull Request açın

---

## 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır.
