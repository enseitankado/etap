#!/usr/bin/env python3
# file: virt_detect.py
# Pure-Python virtualization detection (systemd-detect-virt compatible outputs)

import os
from pathlib import Path

# ---- Helpers ---------------------------------------------------------------

def _read_text(path):
    try:
        return Path(path).read_text(errors="ignore").strip()
    except Exception:
        return ""

def _any_file_contains(paths, needles):
    needles = [n.lower() for n in needles]
    for p in paths:
        s = _read_text(p).lower()
        if s and any(n in s for n in needles):
            return True
    return False

# ---- Container detection (matches systemd-detect-virt) ---------------------

_KNOWN_CONTAINERS = {
    "docker", "podman", "lxc", "lxc-libvirt", "lxd",
    "systemd-nspawn", "openvz", "rkt", "wsl", "bubblewrap",
}

def _detect_container():
    """
    Returns a container type string (e.g. 'docker') or None.
    """
    c = _read_text("/run/systemd/container").lower()
    if c:
        return c if c in _KNOWN_CONTAINERS else "container-other"
    return None

# ---- WSL (Windows Subsystem for Linux) -------------------------------------

def _detect_wsl():
    # systemd-detect-virt specifically marks WSL
    # typical indicators: kernel osrelease or version contains "Microsoft"
    if "microsoft" in _read_text("/proc/sys/kernel/osrelease").lower():
        return "wsl"
    if "microsoft" in _read_text("/proc/version").lower():
        return "wsl"
    return None

# ---- DMI/SMBIOS-based detection -------------------------------------------

# Map “needle list” -> systemd-detect-virt identifier
_DMI_DB = [
    (["kvm", "rhev"],                 "kvm"),        # KVM / RHEV
    (["qemu"],                        "qemu"),       # pure QEMU
    (["vmware"],                      "vmware"),
    (["virtualbox", "innotek"],       "oracle"),     # Oracle VirtualBox
    (["hyper-v", "microsoft"],        "microsoft"),  # Hyper-V / Azure
    (["xen"],                         "xen"),
    (["parallels"],                   "parallels"),
    (["bhyve"],                       "bhyve"),
    (["bochs"],                       "bochs"),
    (["zvm", "ibm z", "s/390", "s390"], "zvm"),
]

_DMI_PATHS = [
    "/sys/class/dmi/id/sys_vendor",
    "/sys/class/dmi/id/product_name",
    "/sys/class/dmi/id/board_vendor",
    "/sys/class/dmi/id/bios_vendor",
]

def _detect_dmi():
    blob = "\n".join(_read_text(p).lower() for p in _DMI_PATHS if os.path.exists(p))
    if not blob:
        return None
    for needles, ident in _DMI_DB:
        if any(n in blob for n in needles):
            return ident
    # UUID pattern: all 0 or f -> typically found on VMs
    uuid = _read_text("/sys/class/dmi/id/product_uuid").lower()
    if uuid.startswith("00000000") or uuid.startswith("ffffffff"):
        # if manufacturer is unknown, we accept generic KVM/QEMU for better match
        return "kvm"
    return None

# ---- PCI (virtio) heuristic ------------------------------------------------
# Red Hat/virtio vendor id: 0x1af4 (typical for QEMU/KVM)
def _detect_pci_virtio():
    devices = Path("/sys/bus/pci/devices")
    try:
        for dev in devices.iterdir():
            vid = _read_text(dev / "vendor").lower()
            if vid == "0x1af4":
                return "kvm"
    except Exception:
        pass
    return None

# ---- CPU flag: hypervisor --------------------------------------------------

def _detect_cpu_flag():
    try:
        for line in _read_text("/proc/cpuinfo").splitlines():
            if line.lower().startswith("flags") and "hypervisor" in line.lower():
                # Vendor ayrımı yapmadan generic kabul: KVM/QEMU en olası
                return "kvm"
    except Exception:
        pass
    return None

# ---- Public API ------------------------------------------------------------

def detect_virt():
    """
    Returns a string like systemd-detect-virt:
      - 'docker', 'podman', 'lxc', 'systemd-nspawn', ... (containers)
      - 'kvm', 'qemu', 'vmware', 'oracle', 'microsoft', 'xen', 'parallels',
        'bhyve', 'bochs', 'zvm', 'wsl'
      - 'none' if bare metal
      - 'container-other' for unknown containers
    """
    # 1) Container - specific for systemd-detect-virt
    c = _detect_container()
    if c:
        return c

    # 2) WSL - specific for WSL
    w = _detect_wsl()
    if w:
        return w

    # 3) DMI/SMBIOS-based detection 
    dmi = _detect_dmi()
    if dmi:
        return dmi

    # 4) PCI (virtio) heuristic
    pci = _detect_pci_virtio()
    if pci:
        return pci

    # 5) CPU flag: hypervisor
    cpu = _detect_cpu_flag()
    if cpu:
        return cpu

    return "none"

def is_vm():
    """
    Returns True/False (True if you consider containers as 'virt' as well).
    False for bare metal.
    """
    t = detect_virt()
    return t != "none"
