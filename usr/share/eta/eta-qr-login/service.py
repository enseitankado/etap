#!/usr/bin/env python3
import uuid
import sys
import time
import os
import signal
import socket
import asyncio
import websockets
import json
import hashlib
import traceback
from passlib.hash import bcrypt
from unix_socket_service import UnixSocketService
import threading
import subprocess

sys.path.insert(0, "/usr/share/eta/eta-usb-login")

# import usb login user creation and login functions
from user import create_user, is_valid_user, find_by_ebaid
from pam import lightdm_trigger, allow_user

os.makedirs("/run/etap", exist_ok=True)

# Create unix socket service
socket_service = UnixSocketService("/run/etap/qr-trigger")

def get_mac():
    for dev in os.listdir("/sys/class/net"):
        if dev.startswith("e"):
            with open("/sys/class/net/{}/address".format(dev), "r") as f:
                ret = f.read().strip()
                print("##############")
                print("Mac address:{}".format(ret))
                return ret
    print("Failed to detect ethernet mac adress")
    return "00:00:00:00:00:00"

ws = None
current_qr = None
WS_NAME = "wss://qr-etap.eba.gov.tr/api/v1/ws/{}".format(get_mac())
if "debug" in sys.argv:
    WS_NAME="ws://127.0.0.1:8765/{}".format(get_mac())

async def listen(uri):
    """Function to handle messages from websocket"""
    global ws
    if ws is not None:
        return
    print("##############")
    print("Starting websocket listener...")
    async with websockets.connect(uri) as websocket:
        ws = websocket
        try:
            while True:
                msg = await websocket.recv()
                data = json.loads(msg)
                data["sender"] = "ws"
                event(data)
        except websockets.exceptions.ConnectionClosedOK:
            print("##############")
            print("Web Socket Connection finished")
            event({"sender":"ws","action":"timeout"})
        except Exception as e:
            print("##############")
            print("Web Socket Connection failed")
            event({"sender":"ws","action":"failed"})
        ws = None


def run_ws():
    """Create Web socket listener"""
    try:
        asyncio.run(listen(WS_NAME))
    except:
        event({"sender":"ws","action":"failed"})



def gen_username(u):
    u = u.replace("İ","I")
    u = u.lower()
    u = u.replace("ç","c")
    u = u.replace("ı","i")
    u = u.replace("ğ","g")
    u = u.replace("ö","o")
    u = u.replace("ş","s")
    u = u.replace("ü","u")
    u = u.replace(" ","")
    return u

def send_ws(data):
    """Send data to websocket"""
    if ws is None:
        threading.Thread(target=run_ws).start()
    while ws is None:  # TODO: remove this garbage solution
        time.sleep(0.1)
    try:
        print(">>>", data, file=sys.stderr)
        asyncio.run(ws.send(json.dumps(data)))
    except Exception as e:
        print(e,traceback.format_exc())


def send_lightdm(data):
    """Send data to lightdm"""
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect("/var/lib/lightdm/ebaqr")
        s.send(json.dumps(data).encode())
        s.close()
    except Exception as e:
        print(e,traceback.format_exc())


def user_create_login(data):
    if data["type"] == "validation" and "user_data" in data:
        user = data["user_data"]["uname"]
        eba_id = data["user_data"]["uid"]
        uname = gen_username(user)
        eba_uname = find_by_ebaid(eba_id)
        if eba_uname:
            uname = eba_uname
        else:
            # prevent same username with different ebaid
            i = 0
            new_user = uname
            while is_valid_user(new_user):
                new_user = uname + str(i)
                i+=1
            uname = new_user
        # generate password from eba_id md5
        passwd = hashlib.md5(eba_id.encode("utf-8")).hexdigest()
        if is_valid_user(uname):
            print(uname)
            allow_user(uname)
        else:
            create_user(uname, bcrypt.hash(passwd), user, eba_id)
            subprocess.run(["chage", "-d", "0", uname])
        lightdm_trigger(uname, passwd)

def event(data):
    """new message event"""
    ret = {}
    if "sender" not in data:
        return
    # print message for debug
    if os.path.isfile("/usr/share/eta/eta-qr-login/debug"):
        print("##############")
        print("<<<", data, file=sys.stderr)
    if "type" in data:
        user_create_login(data)
    if data["sender"] == "lightdm":
        data.pop("sender")
        send_ws(data)
    elif data["sender"] == "ws":
        data.pop("sender")
        send_lightdm(data)

socket_service.event = event


def main():

    socket_thread = threading.Thread(target=socket_service.run)
    socket_thread.start()
    socket_thread.join()


if __name__ == "__main__":
    main()
