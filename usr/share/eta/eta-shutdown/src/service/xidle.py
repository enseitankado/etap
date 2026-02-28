#!/usr/bin/env python3
# https://github.com/g0hl1n/xprintidle/blob/master/xprintidle.c
import ctypes
class XScreenSaverInfo( ctypes.Structure ):
    _fields_ = [("window",     ctypes.c_ulong),
                ("state",      ctypes.c_int),
                ("kind",       ctypes.c_int),
                ("since",      ctypes.c_ulong),
                ("idle",       ctypes.c_ulong),
                ("event_mask", ctypes.c_ulong)]

def get_idle_time(display=None):
    xlib = ctypes.cdll.LoadLibrary("libX11.so.6")
    xss = ctypes.cdll.LoadLibrary("libXss.so.1")
    if xss is None or xlib is None:
        return 0
    display = xlib.XOpenDisplay(bytes(display, 'ascii'))
    if display <= 0:
        return 0
    xss.XScreenSaverAllocInfo.restype = ctypes.POINTER(XScreenSaverInfo)
    xssinfo = xss.XScreenSaverAllocInfo()
    window = xlib.XDefaultRootWindow(display)
    if xssinfo is None or window <= 0:
        return 0
    xss.XScreenSaverQueryInfo(display, window, xssinfo)

    return xssinfo.contents.idle

if __name__ == "__main__":
    import os
    idle_time = -1
    for display in os.listdir("/tmp/.X11-unix/"):
        idle = get_idle_time(f":{display[1:]}")
        if idle_time < idle or idle_time < 0:
            idle_time = idle
    print("idle_time: {}".format(idle_time))
