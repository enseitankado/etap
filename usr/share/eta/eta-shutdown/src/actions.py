#!/usr/bin/env python3
import os
import sys
import subprocess
if os.getuid() != 0:
    subprocess.run(["pkexec", __file__])

def poweroff():
    with open("/proc/sys/kernel/sysrq", "w") as f:
        f.write("1")
    with open("/proc/sysrq-trigger", "w") as f:
        f.write("_reisuo")
        f.flush()

def reboot():
    with open("/proc/sys/kernel/sysrq", "w") as f:
        f.write("1")
    with open("/proc/sysrq-trigger", "w") as f:
        f.write("_reisub")
        f.flush()

if "poweroff" in sys.argv:
    poweroff()

if "reboot" in sys.argv:
    reboot()
