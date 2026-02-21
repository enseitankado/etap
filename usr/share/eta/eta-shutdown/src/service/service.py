import os
import sys
import time
import subprocess
import threading
import configparser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime

from xidle import get_idle_time
from logger import log

"""
[AUTO_SHUTDOWN]
enabled = False
hour = 01
minute = 00

[TIMED_MODE]
mode = "shutdown"
hour = 00
minute = 00
"""

CONFIG_FILE = "/etc/pardus/eta-shutdown.conf"
config = configparser.ConfigParser()
config.read(CONFIG_FILE)

def check_time(hour, minute, delay):
    now = datetime.now()
    nex = datetime(now.year, now.month, now.day, hour, minute)
    print(now, nex, delay)
    return nex.timestamp() - delay - now.timestamp() < 0


def check_x11(disp):
    sp = subprocess.run(["env", "DISPLAY={}".format(disp), "xset", "-q"], capture_output=True)
    return sp.returncode == 0

ret = None
def send_notify(message, yes_msg, no_msg, timeout):
    global ret
    def send_notify_disp(disp):
        global ret
        cmd = ["timeout", str(timeout),
            "env", "DISPLAY={}".format(disp),
            "notify-send", "-w",
            "-A", "true={}".format(yes_msg),
            "-A", "false={}".format(no_msg),
            "-t", str(timeout*1000), message]
        log(cmd)
        sp = subprocess.run(cmd, capture_output=True)
        if ret == None:
            ret = (sp.stdout.decode("utf-8").strip() == "true")
    ths = []
    ret = None
    for display in os.listdir("/tmp/.X11-unix/"):
        if check_x11(f":{display[1:]}"):
            th = threading.Thread(target=send_notify_disp, args=[f":{display[1:]}"])
            ths.append(th)
    for th in ths:
        th.start()
    for th in ths:
        th.join()
    print(ret)
    return ret

message_shown = False
delay = 0
init=False
ignore_auto=False

def service():
    global message_shown
    global delay
    global init
    global ignore_auto

    # variables
    auto_hour = int(config["AUTO_SHUTDOWN"]["hour"])
    auto_minute = int(config["AUTO_SHUTDOWN"]["minute"])
    hour = int(config["TIMED_MODE"]["hour"])
    minute = int(config["TIMED_MODE"]["minute"])
    # first boot check
    if not init:
        init = True
        if check_time(auto_hour, auto_minute, 0):
            ignore_auto = True

    log("###### Eta Shutdown {} ######".format(time.time()))
    idle_time = -1
    for display in os.listdir("/tmp/.X11-unix/"):
        idle = get_idle_time(f":{display[1:]}")
        if idle_time < idle or idle_time < 0:
            idle_time = idle
    print("idle_time: {}".format(idle_time))
    # timed shutdown
    mode = config["TIMED_MODE"]["mode"]
    if mode != "none":
        req_idle = (hour*3600 + minute * 60)*1000
        if req_idle < 5*60*1000:
            req_idle = 5*60*1000
        print("req_idle:", req_idle)
        if idle_time > req_idle:
            if mode == "shutdown":
                os.system("poweroff -f")
            elif mode == "suspend":
                os.system("systemctl suspend")
    # auto shutdown
    if ignore_auto:
        print("Ignore auto shutdown")
    elif config["AUTO_SHUTDOWN"]["enabled"].lower() == "true":
        if check_time(auto_hour, auto_minute, (600)):
            if not message_shown:
                message_shown = True
                if send_notify("Sistem 10dk sonra kapatılacak.", "1 saat ertele", "Tamam", 30):
                    delay -= 60*60
                    message_shown = False
        if check_time(auto_hour, auto_minute, delay):
            print("auto shutdown")
            os.system("poweroff -f")

if __name__ == "__main__":
    send_notify(sys.argv[1], "Yes", "No", 10)
