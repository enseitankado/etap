#!/usr/bin/env python3
import os
import pwd
import grp
import traceback

f=open("/var/log/pam_etap.log","a")

def chown_recursive(path, uid, gid):
    for sub in os.listdir(path):
       if os.path.isdir(f"{path}/{sub}"):
           chown_recursive(f"{path}/{sub}", uid, gid)
       else:
           os.chown(f"{path}/{sub}", uid, gid)
    os.chown(path, uid, gid)

def log(*args):
    print(args, file=f)
    f.flush()

def pam_sm_setcred(pamh, flags, argv):
  return pamh.PAM_SUCCESS

def pam_sm_authenticate(pamh, flags, argv):
    # fetch username
    try:
        user = pamh.get_user(None)
    except pamh.exception as e:
        log(e, traceback.format_exc())
        return e.pam_result

    # fetch uid and gid
    try:
        pwent = pwd.getpwnam(user)
        grent = grp.getgrnam(user)
    except Exception as e:
        log(e, traceback.format_exc())
        return pamh.PAM_USER_UNKNOWN
    uid = pwent.pw_uid
    gid = grent.gr_gid

    # create user directory
    try:
        os.makedirs(f"/run/etap/{uid}", exist_ok=True)
        os.chown(f"/run/etap/{uid}", uid, 0)
    except Exception as e:
        log(e, traceback.format_exc())
        return pamh.PAM_AUTH_ERR

    # wine prefix chown
    try:
        chown_recursive("/var/lib/wine-prefix", uid, gid)
    except Exception as e:
        log(e, traceback.format_exc())

    # permit ogrenci user
    if user == "ogrenci":
        return pamh.PAM_SUCCESS

    # chech autouser file
    if not os.path.isfile("/run/etap/user"):
        return pamh.PAM_AUTH_ERR
    # read autouser
    try:
        with open("/run/etap/user", "r") as f:
            autouser = f.read().strip()
        os.unlink("/run/etap/user")
    except Exception as e:
        log(e, traceback.format_exc())
        return pamh.PAM_AUTH_ERR

    if user == autouser:
        return pamh.PAM_SUCCESS

