#!/usr/bin/env python3
import os
import sys
import time
import json
import shutil

sys.path.insert(0,os.path.dirname(__file__))

import usb
import credentials
import user
import pam


try:
    import locale
    from locale import gettext as _

    # Translation Constants:
    APPNAME = "eta-usb-login"
    TRANSLATIONS_PATH = "/usr/share/locale"
    SYSTEM_LANGUAGE = os.environ.get("LANG")
    locale.setlocale(locale.LC_ALL, SYSTEM_LANGUAGE)
    locale.bindtextdomain(APPNAME, TRANSLATIONS_PATH)
    locale.textdomain(APPNAME)
except Exception as e:
    print("failed to load locale")
    print(e)
    # locale load fallback
    def _(msg):
        return msg

user._ = _


def listen(udata):
    if udata["ACTION"] == "add":
        return add_event(udata)
    elif udata["ACTION"] == "remove":
        return remove_event(udata)

def remove_event(udata):
    print("######## {} ########".format(time.time()))
    uuid = None
    if "ID_FS_UUID" in udata:
        uuid = udata["ID_FS_UUID"]
    for id in os.listdir("/run/etap/"):
        if not os.path.isfile("/run/etap/{}/credentials".format(id)):
            continue
        # check uuid is same
        if uuid != None:
            with open("/run/etap/{}/credentials".format(id), "rb") as f:
                data = credentials.read(f.read())
                if "usb_serial" not in data:
                    continue
                if data["usb_serial"] != uuid:
                    continue
        os.remove("/run/etap/{}/credentials".format(id))
        if os.path.exists("/var/lib/lightdm/pardus-greeter"):
            continue
        # trigger agent
        if os.path.isdir("/run/etap/{}/".format(id)):
            print("UID: "+id)
            for pid in os.listdir("/run/etap/{}/".format(id)):
                # check agent is running
                if os.path.isdir("/proc/{}".format(pid)):
                    print("PID: "+pid)
                    with open("/run/etap/{}/{}".format(id, pid), "w") as f:
                        data = {}
                        data["action"] = "quit"
                        f.write(json.dumps(data))
                        f.flush()
                print("Remove pid: "+pid)
                os.remove("/run/etap/{}/{}".format(id, pid))


def add_event(udata):
    print(udata["DEVNAME"])
    print("######## {} ########".format(time.time()))
    if not pam.lightdm_check():
        exit(0)
    # Read data from usb
    part = os.path.basename(udata["DEVNAME"])
    #ctx, part = usb.get_file(".credentials")
    ctx = usb.mount_and_check(part, ".credentials")
    uuid = usb.get_uuid(part)
    data = credentials.read(ctx)
    # Check data is valid
    if data == None:
        print("########")
        print("Invalid data:")
        return False
    # Check matching usb uuid and credential uuid
    if "usb_serial" in data:
        if data["usb_serial"] != uuid:
            print("########")
            pam.lightdm_print(_("USB Serial Mismatch"))
            return False
    else:
        return False
    pam.lightdm_print(_("Logging in, please wait."), block=True)
    # check from eba
    [eba_status, eba_message] = user.check_eba(data["eba_id"], data["usb_serial"])
    if not eba_status:
        pam.lightdm_print(eba_message, block=False)
        return False
    # check ebaid related user exists
    ebaid_user = user.find_by_ebaid(data["eba_id"])
    if ebaid_user:
        data["username"] = ebaid_user
    else:
        # check prevent same username with different ebaid
        i = 0
        new_user = data["username"]
        while user.is_valid_user(new_user):
            new_user = data["username"] + str(i)
            i+=1
        data["username"] = new_user
    # Check data has username and hash
    if "username" not in data or "password" not in data:
        print("########")
        pam.lightdm_print(_("Failed to create user."))
        print("username not found in data")
        return False
    # fallback mechanism for old credentials
    if "name" not in data:
        data["name"] = data["username"]
    # Check user exist and create
    user.create_user(
        data["username"],
        data["password"],
        data["name"].strip(),
        data["eba_id"])
    # Write credential
    uid = user.find_uid(data["username"])
    os.makedirs("/run/etap/{}/".format(uid), exist_ok=True)
    with open("/run/etap/{}/credentials".format(uid), "wb") as f:
        print("########")
        print("Copy Credential")
        f.write(ctx)
        f.flush()
    os.chmod("/run/etap/{}".format(uid), 0o700)
    os.chown("/run/etap/{}".format(uid), int(uid), 0)
    # Write pam user
    pam.allow_user(data["username"])
    pam.lightdm_trigger(data["username"])
    return True
