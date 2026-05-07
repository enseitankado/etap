#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import sys
import os

def usage():
    print("Usage ./Actions.py ...")


def find_user(uid):
    with open("/etc/passwd", "r") as f:
        for line in f.read().split("\n"):
            cur = line.split(":")[2]
            if str(uid) == cur:
                return line.split(":")[0]
    return None

def find_uid(user):
    with open("/etc/passwd", "r") as f:
        for line in f.read().split("\n"):
            cur = line.split(":")[0]
            if user == cur:
                return line.split(":")[2]
    return None


def change(passwd):
    if "PKEXEC_UID" in os.environ:
        user = find_user(os.environ["PKEXEC_UID"])
    else:
        user = input()
    sp = subprocess.run(["openssl", "passwd", "-6", passwd],capture_output=True)
    phash = sp.stdout.decode("utf-8").strip()
    subprocess.run(["usermod", "-p", phash, user])
    expire_file = "/var/lib/eta/expire-uid/{}".format(find_uid(user))
    if os.path.isfile(expire_file):
        os.unlink(expire_file)

if __name__ == "__main__":
    is_expired = False
    if "PKEXEC_UID" in os.environ:
        pkexec_uid = int(os.environ["PKEXEC_UID"])
        is_expired = os.path.isfile("/var/lib/eta/expire-uid/{}".format(pkexec_uid))
    if not is_expired:
        sys.exit(1)
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)
    change(sys.argv[1])
