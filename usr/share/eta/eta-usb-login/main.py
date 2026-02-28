#/usr/bin/env python3
import os
import sys
import json
import socket
import traceback

import threading

sys.path.insert(0,os.path.dirname(__file__))

print("##### Starting Eta Usb Login #####")

import service

os.makedirs("/run/etap/", exist_ok=True)

if os.path.exists("/run/etap/usb-trigger"):
    os.unlink("/run/etap/usb-trigger")

server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server.bind("/run/etap/usb-trigger")
server.listen(1)

while True:
    connection, client_address = server.accept()
    try:
        data = connection.recv(1024**2) # read max 1mb
        print("<<<", data.decode())
        connection.close()
        udata = json.loads(data.decode())
        print(udata)
        th = threading.Thread(target=service.listen, args=[udata])
        th.start()
    except Exception as e:
        print(traceback.format_exc())

