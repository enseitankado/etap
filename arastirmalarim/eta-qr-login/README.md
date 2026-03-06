# Pardus-23.4-ETAP-20260212-1645-amd64.iso DAĞITIMINDAKİ LPE AÇIĞI

> ⚠️ **Bu depo bir güvenlik açığı araştırmasının bulgusudur. İçerik yalnızca eğitim ve belgeleme amacıyla paylaşılmaktadır.**

Kısıtlı bir kullanıcı oturumundan (örn. `ogrenci`) yeni bir yerel hesap oluşturmak için `/run/etap/qr-trigger` Unix soketine JSON mesajı gönderen Python 3 betiği.

## Nasıl Çalışır

`/run/etap/qr-trigger` soketi, **lightdm** tarafından dinlenmekte olup yazma yetkisi kısıtlı kullanıcılara da açık bırakılmıştır. Betik bu sokete `register` tipinde bir doğrulama mesajı göndererek hesap oluşturma akışını tetikler ve oluşturulan parolanın MD5 hash'ini `stdout`'a yazar.

```
ogrenci@makine:~$ python3 etap_register.py yeni_kullanici
5f4dcc3b5aa765d61d8327deb882cf99
```

## Gereksinimler

- Python 3.6+
- `/run/etap/qr-trigger` soketine yazma erişimi
- Ek bağımlılık yok (yalnızca standart kütüphane)

## Kullanım

```bash
python3 etap_register.py <kullanici_adi>
```

Başarılı olursa oluşturulan parolanın MD5 hash'i yazdırılır. Hata durumunda betik `exit code 1` ile sonlanır.

### Parametreler

| Parametre | Açıklama |
|---|---|
| `kullanici_adi` | Oluşturulacak hesabın kullanıcı adı (büyük harfe çevrilir) |

## Örnek

```bash
$ python3 etap_register.py ahmet
a1b2c3d4e5f6...   # parolanın MD5 hash'i
```

## Dosyalar

| Dosya | Açıklama |
|---|---|
| `etap_register.py` | Hesap oluşturma betiği |
| `vuln1.py` | Güvenlik açığını kullanan PoC (Proof of Concept) exploit kodu |
| `vuln1.mp4` | Exploitin çalışmasını gösteren demo videosu |

## Demo

https://github.com/USER/REPO/raw/main/vuln1.mp4

> Videoyu indirerek veya GitHub üzerinden görüntüleyebilirsiniz.

## Güvenlik Açığının Özeti

`/run/etap/qr-trigger` Unix soketine yazma yetkisi kısıtlı kullanıcılara (örn. `ogrenci`) açık bırakılmıştır. Bu durum, kısıtlı bir oturumdan sisteme yeni yerel hesaplar eklenmesine olanak tanır.

**Bulunan:** 15 Şubat 2026 — Özgür Koca  
**Raporlandı:** Etap Pardus geliştirici ekibine sorumlu açıklama (responsible disclosure) çerçevesinde bildirildi  
**Yamalandı:** 16 Şubat 2026 — `Pardus-23.4-ETAP-20260216-1444-amd64.iso` güncellemesiyle kapatıldı; yapılan yamalama [`usr/share/eta/eta-qr-login/unix_socket_service.py` kaynak kodunun 50. satırında](https://github.com/enseitankado/etap/commit/1c11c9caf820c40ca93c72d73856f5088294dedc#diff-9b30ba4640c7d06f13d07eedb2f5f2547ccd029e9ed4ac708f9598ff3a3661a9) görülebilir

**Etkilenen bileşen:** `lightdm` / etap QR tetikleyici soketi  
**Etki:** Yetkisiz hesap oluşturma (privilege boundary bypass)  
**Öneri:** Soket izinleri yalnızca yetkili servis kullanıcılarıyla sınırlandırılmalıdır.

## Notlar

- Parola `secrets.token_hex(16)` ile rastgele üretilir; sokete gönderilen `uid` alanı bu değeri taşır.
- Oluşturulan hesabın rolü `TESTUSER` olarak işaretlenir (`utype`).
- Soket bağlantısı 5 saniyelik zaman aşımına tabidir.

## Lisans

MIT
