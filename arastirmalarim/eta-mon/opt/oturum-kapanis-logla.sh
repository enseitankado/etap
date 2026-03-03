#!/bin/bash
username=$(cat /tmp/oturum-acan-kullanici-adi.txt)
rm -f /tmp/oturum-acan-kullanici-adi.txt
/usr/bin/python3 /opt/logla.py bilgi "$username oturumu kapaniyor (/usr/share/lighdm/lightdm.conf.d/90-kapanis-logla.conf, un /tmp'den getirildi)"

