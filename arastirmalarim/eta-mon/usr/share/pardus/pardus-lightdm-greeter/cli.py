#!/usr/bin/env python3
import json
import os
import sys

sys.path.append("/opt") # Aksi takdirde /etc/environment'daki patikadan haberi olmuyor
from logla import logla

if os.getuid() != 0:
    print("You must be root!", file=sys.stderr);
    exit(1)

def login(username=None, password=None, session=None):
    if not os.path.exists("/var/lib/lightdm/pardus-greeter"):
        print("Failed to connect pardus lightdm greeter")
        logla('debug', f"Greeter FIFO (/var/lib/lightdm/pardus-greeter) mevcut degil. Yazma basarisiz.")
        exit(2)
    data = {}
    data["username"] = str(username)
    data["password"] = str(password)
    if session != None:
        data["session"] = str(session)

    with open("/var/lib/lightdm/pardus-greeter", "a") as f:
        print(json.dumps(data))
        f.write(json.dumps(data))
        f.flush()
    
    logla('debug', f"Login FIFO'suna (/var/lib/lightdm/pardus-greeter) JSON olarak {username},{password},{session} yazildi.")

if __name__ == "__main__":

    if len(sys.argv) < 3:
        print("Usage: pardus-login [username] [password]", file=sys.stderr)
        exit(1)
    session=None
    if len(sys.argv) > 3:
        session = sys.argv[3]
    login(sys.argv[1], sys.argv[2], session)
