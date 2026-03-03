#!/usr/bin/python3
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import requests
import uuid
from urllib.parse import urlencode
from urllib.parse import quote

# Yapılandırma
SUNUCU_AD = 'istiklal.local'

# /var/log/eta.log yanında sunucuya da loglama yap
SUNUCU_LOG_ETKIN = False

# Loglama için merkezi fonksiyon
def logla(seviye, mesaj):    
    log_dizini = "/var/log"
    os.makedirs(log_dizini, exist_ok=True)
    log_dosyasi = os.path.join(log_dizini, "eta.log")

    logger = logging.getLogger("eta")
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)
        handler = RotatingFileHandler(log_dosyasi, maxBytes=10 * 1024 * 1024, backupCount=5)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    sev = seviye.lower()
    if sev == 'hata':
        logger.error(mesaj)
    elif sev == 'uyari':
        logger.warning(mesaj)
    elif sev == 'bilgi':
        logger.info(mesaj)
    elif sev == 'debug':
        logger.debug(mesaj)
    else:
        logger.info(f"Bilinmeyen seviye: {seviye} - {mesaj}")
        
    # -------------------------------------------------------
    # Sunucuya logla
    # -------------------------------------------------------
    global SUNUCU_AD
    global SUNUCU_LOG_ETKIN
    
    if SUNUCU_LOG_ETKIN:
        mac_adresi = get_mac_address()
        params = {
            "islem": "log",
            "seviye": str(seviye),
            "log": quote(mesaj, safe=":/"),  # Doğrudan mesajı buraya koyuyoruz
            "mac": mac_adresi
        }
        url = f"http://{SUNUCU_AD}/eta/index.php"
        response = requests.get(url, params=params, timeout=3) 
        if response.status_code != 200:
           print(f"{url} adresine baglanamadi. Status code: {response.status_code}")     


def get_mac_address():
    mac = uuid.getnode()  # Cihazın MAC adresini al
    return ':'.join(f'{(mac >> ele) & 0xff:02x}' for ele in range(40, -1, -8))
    
    
# Komut satırından çağırma desteği
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Kullanım: logla.py <seviye> <mesaj>")
        sys.exit(1)

    seviye = sys.argv[1]
    mesaj = " ".join(sys.argv[2:])
    logla(seviye, mesaj)