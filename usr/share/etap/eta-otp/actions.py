#!/usr/bin/env python3
import sys
import os
import json

config_file = "/etc/otp-secrets.json"
config = {}
try:
    if os.path.isfile(config_file):
        with open(config_file, "r") as f:
            config = json.load(f)

        os.chown(config_file, 0, 0)
        os.chmod(config_file, 0o600)

except:
    pass

def find_user(uid):
    with open("/etc/passwd", "r") as f:
        for line in f.read().split("\n"):
            cur = line.split(":")[2]
            if str(uid) == cur:
                return line.split(":")[0]
    return None

def save(user, secret="JBSWY3DPEHPK3PXP"):
    config[user] = secret
    with open(config_file, "w") as f:
        json.dump(config, f)
    os.chown(config_file, 0, 0)
    os.chmod(config_file, 0o600)

def load(user):
    if user in config:
        print(config[user])

def remove(user):
    if user in config:
        config.pop(user)
    with open(config_file, "w") as f:
        json.dump(config, f)
    os.chown(config_file, 0, 0)
    os.chmod(config_file, 0o600)

def status(user):
    return user in config

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if "PKEXEC_UID" in os.environ:
            user = find_user(os.environ["PKEXEC_UID"])
        else:
            user = input()
        if sys.argv[1] == "save":
            save(user, sys.argv[2])
        elif sys.argv[1] == "remove":
            remove(user)
        elif sys.argv[1] == "load":
            load(user)
        elif sys.argv[1] == "status":
            if status(user):
                print("true")
                sys.exit(0)
            else:
                print("false")
                sys.exit(1)
    else:
        print("actions.py [save|load|remove|status] (secret)")

