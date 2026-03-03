#!/bin/bash
ACTION=$1
DEVBASE=$2
DEVICE="/dev/${DEVBASE}"
MOUNT_POINT=$(/bin/mount | /bin/grep ${DEVICE} | /usr/bin/awk '{ print $3 }')  # See if this drive is already mounted
case "${ACTION}" in
    add)
		/usr/bin/python3 /opt/logla.py debug "USB baglandi (usb-baglandi.sh)"				
        ;;
    remove)
        /usr/bin/python3 /opt/logla.py debug "USB ayrildi (usb-ayrildi.sh)"
        ;;
esac