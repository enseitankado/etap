import subprocess
import sys
import requests
import time

import hashlib

def is_valid_user(user):
    print("########")
    print("Check User:", user)
    with open("/etc/passwd","r") as f:
        for line in f.read().split("\n"):
            if user == line.split(":")[0]:
                return True
    return False

def create_user(user, hash, realname, ebaid):
    eba_hash = hashlib.md5(str(ebaid).encode("utf-8")).hexdigest()
    if is_valid_user(user):
        return update_passwd(user, hash)
    print("########")
    print("Create user:",user, hash)
    groups = ["cdrom","floppy","audio","video","plugdev","bluetooth",
              "scanner", "netdev", "dip", "lpadmin"]
    sp = subprocess.run(
        ["useradd", "-p", hash, "-s" , "/bin/bash",
            "-c", realname+",,,,"+eba_hash, "-m", user]
    )
    if sp.returncode == 0:
        for grp in groups:
            subprocess.run(["usermod", "-a", "-G", grp, user])
    return sp.returncode == 0

def update_passwd(user, hash):
    print("########")
    print("Update user:",user, hash)
    sp = subprocess.run(
        ["usermod", "-p", hash, user]
    )
    return sp.returncode == 0

def check_eba(eba_id, usb_serial):
    url = "https://giris.eba.gov.tr/EBA_GIRIS/GetUsbUser"
    body = {"eba_id": eba_id, "usb_serial": usb_serial}
    i=0
    while i < 10:
        try:
            x = requests.post(url, json = body)
            print(x.text)
            if len(x.text.strip()) == 0:
                return [False, _("There may be a slowdown in the service infrastructure, please try again later.")]
            return ["EBA.001" in x.text, _("EBA Authentication Failed")]
        except Exception as e:
            print(e)
            i+=1
            time.sleep(3)
    return [False, _("Login failed, please check your internet connection.")]

def find_by_ebaid(ebaid):
    eba_hash = hashlib.md5(str(ebaid).encode("utf-8")).hexdigest()
    with open("/etc/passwd","r") as f:
        for line in f.read().split("\n"):
            if ":" not in line:
                continue
            realname = line.split(":")[4]
            if ",,,," in realname:
                if realname.split(",")[-1] == eba_hash:
                   return line.split(":")[0]
    return None

def find_uid(user):
    with open("/etc/passwd","r") as f:
        for line in f.read().split("\n"):
            data = line.split(":")
            if data[0] == user:
                return data[2]
    return None
