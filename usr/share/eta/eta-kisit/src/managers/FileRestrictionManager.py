import os
import subprocess
import pwd

PRIVILEGED_GROUP = "floppy"
PRIVILEGED_GROUP_ID = int(
    subprocess.check_output(["getent", "group", PRIVILEGED_GROUP])
    .decode()
    .split(":")[2]
)
UNPRIVILEGED_USER = "ogrenci"
UNPRIVILEGED_USER_ID = pwd.getpwnam(UNPRIVILEGED_USER).pw_uid


def check_user_privileged():
    if os.getuid() == 0:  # root user
        return True

    user_groups = os.getgroups()
    if PRIVILEGED_GROUP_ID in user_groups:  # not root but in the group
        return True

    return False


# Binary files
def restrict_bin_file(filepath):
    if filepath and os.path.isfile(filepath):
        os.chmod(filepath, 0o750)  # rwxr-x---
        os.chown(filepath, 0, PRIVILEGED_GROUP_ID)  # root:floppy


def unrestrict_bin_file(filepath):
    if filepath and os.path.isfile(filepath):
        os.chmod(filepath, 0o755)  # rwxr-xr-x
        os.chown(filepath, 0, 0)  # root:root


# Desktop files
def restrict_desktop_file(filepath):
    if filepath and os.path.isfile(filepath):
        os.chmod(filepath, 0o640)  # rw-r-----
        os.chown(filepath, 0, PRIVILEGED_GROUP_ID)  # root:floppy


def unrestrict_desktop_file(filepath):
    if filepath and os.path.isfile(filepath):
        os.chmod(filepath, 0o644)  # rw-r--r--
        os.chown(filepath, 0, 0)  # root:root


def unrestrict_local_desktop_file(filepath):
    if filepath and os.path.isfile(filepath):
        os.chmod(filepath, 0o775)  # rwxrwxr-x
        os.chown(
            filepath, UNPRIVILEGED_USER_ID, UNPRIVILEGED_USER_ID
        )  # ogrenci:ogrenci


# Conf files
def restrict_conf_file(filepath):
    restrict_desktop_file(filepath)  # same permission style


def unrestrict_conf_file(filepath):
    unrestrict_desktop_file(filepath)  # same permission style
