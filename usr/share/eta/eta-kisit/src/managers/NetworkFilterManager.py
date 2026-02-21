import subprocess

from managers import SmartdnsManager
from managers import BrowserManager

RESOLV_CONF_PATH = "/etc/resolv.conf"


RESOLV_CONF_CONTENT = """# This file is generated & locked by eta-kisit app. Please do not change.

nameserver 127.0.0.1

"""

ALWAYS_ALLOWED_DOMAINS = ["ntp.org", "eba.gov.tr", "etap.org.tr"]

ALLOWLIST_DOMAIN_GROUPS = {
    "youtubekids.com": [
        "google.com",
        "gstatic.com",
        "googleapis.com",
        "googlevideo.com",
        "ytimg.com",
        "googleusercontent.com",
    ],
    "turkiye.gov.tr": [
        "e-devlet.gov.tr",
    ],
}


def read_resolvconf_dns_servers():
    dns_servers = []
    with open(RESOLV_CONF_PATH, "r") as file1:
        for line in file1.readlines():
            uncommented_line = line.strip().split("#")[0]

            if "nameserver" in line:
                server = uncommented_line.strip().split(" ")[-1]
                dns_servers.append(server)

    return dns_servers


def is_resolvconf_generated_by_eta_kisit():
    with open(RESOLV_CONF_PATH, "r") as file1:
        for line in file1.readlines():
            if "eta-kisit" in line:
                return True

    return False


def set_resolvconf_to_localhost():
    subprocess.run(["chattr", "-i", "/etc/resolv.conf"])  # unblock file

    with open(RESOLV_CONF_PATH, "w") as file1:
        file1.write(RESOLV_CONF_CONTENT)

    subprocess.run(["chattr", "+i", "/etc/resolv.conf"])  # block file


def reset_resolvconf_to_default():
    subprocess.run(["chattr", "-i", "/etc/resolv.conf"])  # unblock file
    subprocess.run(["rm", "/etc/resolv.conf"])  # delete file
    subprocess.run(
        ["systemctl", "restart", "NetworkManager.service"]
    )  # generate new resolvconf from network manager


def set_domain_filter_list(domain_list, is_allowlist, dns_servers):
    if is_allowlist:
        for d in ALLOWLIST_DOMAIN_GROUPS.keys():
            if d in domain_list:
                # Concat arrays
                domain_list += ALLOWLIST_DOMAIN_GROUPS[d]
                print(
                    "Domain group added:", d, " depends on ", ALLOWLIST_DOMAIN_GROUPS[d]
                )

        # Append Always allowed domains
        domain_list += ALWAYS_ALLOWED_DOMAINS

        domain_list = list(set(domain_list))
    else:
        # Remove always allowed domains from blocklist
        for d in ALWAYS_ALLOWED_DOMAINS:
            if d in domain_list:
                domain_list.remove(d)

    print("Final domains", domain_list)
    SmartdnsManager.create_smartdns_config(domain_list, is_allowlist, dns_servers)
    BrowserManager.create_browser_config(domain_list, is_allowlist)


def reset_domain_filter_list():
    SmartdnsManager.remove_smartdns_config()
    BrowserManager.remove_browser_config()
