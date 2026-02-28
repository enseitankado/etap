import json
import os, sys

import socket

def allow_user(name):
    print("########")
    print("Allowed pam user:", name)
    os.makedirs("/run/etap", exist_ok=True)
    with open("/run/etap/user", "w") as f:
        f.write(name)
        f.flush()

def __send_sock(data):
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.connect("/var/lib/lightdm/pardus-greeter")
    client.sendall(data.encode())
    client.close()

def lightdm_check():
    return os.path.exists("/var/lib/lightdm/pardus-greeter")

def lightdm_trigger(name, password=""):
    print("########")
    print("Lightdm trigger", name)
    if not os.path.exists("/var/lib/lightdm/pardus-greeter"):
        return
    data = {}
    data["username"] = name
    data["password"] = password
    __send_sock(json.dumps(data))

def lightdm_print(msg, *msgs, block=None):
    print("########")
    print("Lightdm send message", msg, msgs)
    if not os.path.exists("/var/lib/lightdm/pardus-greeter"):
        return
    data = {}
    data["message"] = str(msg)
    if block == True:
        data["event"] = "block-gui"
    elif block == False:
        data["event"] = "unblock-gui"
    for m in msgs:
        data["message"] += " " + str(m)
    __send_sock(json.dumps(data))
