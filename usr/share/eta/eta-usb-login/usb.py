import subprocess
import os, sys
import time

def list_usb_parts():
    """
    list mbrs and return removable partitions
    """
    ret = []
    for mbr in os.listdir("/sys/block/"):
        with open("/sys/block/{}/removable".format(mbr),"r") as removable:
            if removable.read().strip() == "1":
                for part in os.listdir("/sys/block/{}/".format(mbr)):
                    if part.startswith(mbr):
                        ret.append(part)
    print("########")
    print("Parts:", ret)
    return ret

def mount_and_check(part, file):
    """
    mount a part and check file exists.
    return file content. If file does not exists return None
    """
    while not os.path.exists("/dev/{}".format(part)):
        print("Wait: "+part)
        time.sleep(0.1)
    os.makedirs("/run/etap/{}".format(part), exist_ok=True)
    print("########")
    print("Mount:", part)
    sb = subprocess.run(
        ["/usr/bin/mount", "-o", "ro", "/dev/{}".format(part), "/run/etap/{}".format(part)],
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    if sb.returncode != 0:
        print("failed to mount {}".format(part))
        return None
    ret = None
    if os.path.exists("/run/etap/{}/{}".format(part,file)):
        with open("/run/etap/{}/{}".format(part,file), "rb") as f:
            ret = f.read().strip()

    print("########")
    print("Umount:",part)
    subprocess.run(
        ["umount", "/run/etap/{}".format(part)]
    )
    os.rmdir("/run/etap/{}".format(part))
    return ret


def get_uuid(part):
    """
    get uuid by part
    """
    if part == None:
        return None
    for uuid in os.listdir("/dev/disk/by-uuid"):
        link = os.readlink("/dev/disk/by-uuid/{}".format(uuid))
        if part == os.path.basename(link):
            print("########")
            print("UUID:", part, uuid)
            return uuid
    return None

def get_file(path):
    """
    scan removable parts and and read file content
    if file not found return None
    """
    for disk in list_usb_parts():
        ctx = mount_and_check(disk, path)
        if ctx:
            print("########")
            print("Get File",disk, ctx)
            return ctx, disk
    return None, None
