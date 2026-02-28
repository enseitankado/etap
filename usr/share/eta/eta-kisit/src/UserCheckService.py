#!/usr/bin/python3

import threading
from managers import LinuxUserManager
from Logger import log
import subprocess


def set_interval(func, sec):
    def func_wrapper():
        set_interval(func, sec)
        func()

    t = threading.Timer(sec, func_wrapper)
    t.start()
    return t


last_active_session = None


def check_active_session():
    global last_active_session

    try:
        active_session = LinuxUserManager.get_active_session_username()
    except Exception as e:
        log("Exception on get_active_session: {}".format(e))

    if active_session == "root":
        active_session = None

    if last_active_session != active_session:
        # Session changed.
        log(
            "Active Session Changed: {} -> {}".format(
                last_active_session, active_session
            )
        )
        last_active_session = active_session

        if active_session:
            try:
                subprocess.run(["eta-kisit", "--user-login", active_session])
            except Exception as e:
                log("Exception on eta-kisit --user-login call: {}".format(e))


t = set_interval(check_active_session, 1)  # check every 1 seconds
t.join()
