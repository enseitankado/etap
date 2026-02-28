import copy
import json
import os
from pathlib import Path


CHROME_POLICY_PATH = Path("/etc/opt/chrome/policies/managed/policies.json")
BRAVE_POLICY_PATH = Path("/etc/brave/policies/managed/policies.json")
CHROMIUM_POLICY_PATH = Path("/etc/chromium/policies/managed/policies.json")
CHROMIUM2_POLICY_PATH = Path("/etc/chromium-browser/policies/managed/policies.json")
FIREFOX_POLICY_PATH = Path("/usr/share/firefox-esr/distribution/policies.json")

CHROME_POLICY_JSON = {
    "URLBlocklist": [],  # e.g. "google.com", "*" to block everything, "youtube.com"
    "URLAllowlist": [],
    "DnsOverHttpsMode": "off",
    # "ClearBrowsingDataOnExitList": ["hosted_app_data", "cached_images_and_files"],
}

# These keys will be appended/removed in the json.
FIREFOX_POLICY_JSON = {
    # This is disabled because it doesn't work properly.
    "WebsiteFilter": {
        # https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Match_patterns
        "Block": [],  # eg "<all_urls>"
        "Exceptions": [],  # eg "*://*.youtube.com/*", "*://*.pardus.org.tr/*"
    },
    "DNSOverHTTPS": {"Enabled": False, "Locked": True},
    "SanitizeOnShutdown": {
        "Cache": True,
        "Cookies": True,
        "History": True,
        "Sessions": True,
        "SiteSettings": True,
        "Locked": True,
    },
}


def _generate_chromium_policy(domain_list, is_allowlist):
    chromium_policy_object = copy.deepcopy(CHROME_POLICY_JSON)

    if is_allowlist:
        # Block everything except allowlist
        chromium_policy_object["URLBlocklist"] = ["*"]
        chromium_policy_object["URLAllowlist"] = domain_list
    else:
        chromium_policy_object["URLAllowlist"] = []
        chromium_policy_object["URLBlocklist"] = domain_list

    return chromium_policy_object


def _generate_firefox_policy(domain_list, is_allowlist):
    obj = copy.deepcopy(FIREFOX_POLICY_JSON)

    # Firefox browser policy doesn't work properly:
    if is_allowlist:
        # Block everything except allowlist
        # convert e.g. "google.com" -> "*://*.google.com/*"
        new_domain_list = []
        for d in domain_list:
            new_domain_list.append("http://*.{}/*".format(d))
            new_domain_list.append("https://*.{}/*".format(d))

        obj["WebsiteFilter"]["Block"] = ["<all_urls>"]
        obj["WebsiteFilter"]["Exceptions"] = new_domain_list
    else:
        # convert e.g. "google.com" -> "*://*.google.com/*"
        new_domain_list = []
        for d in domain_list:
            new_domain_list.append("http://*.{}/*".format(d))
            new_domain_list.append("https://*.{}/*".format(d))

        obj["WebsiteFilter"]["Block"] = new_domain_list
        del obj["WebsiteFilter"]["Exceptions"]

    return obj


def _update_firefox_browser_policy(browser_config_path: Path, obj, is_remove_keys):
    if not browser_config_path.exists():
        empty_policy = {"policies": {}}
        print("policies.json not found, creating a new one.", empty_policy)
        _save_browser_policy(browser_config_path, empty_policy)

    with open(browser_config_path, "r+") as f:
        try:
            content = json.load(f)
            if "policies" not in content:
                content["policies"] = {}
        except json.decoder.JSONDecodeError:
            content = {"policies": {}}

        # object loaded, add policies:
        if is_remove_keys:
            for key in obj.keys():
                if key in content["policies"].keys():
                    del content["policies"][key]
        else:
            for key in obj.keys():
                content["policies"][key] = obj[key]

        # Write new policies:
        f.seek(0)
        json.dump(
            content,
            f,
            ensure_ascii=False,
            indent=4,
            sort_keys=True,
        )
        f.truncate()

        print("Browser Policy Updated: {}".format(browser_config_path))


def _save_browser_policy(browser_config_path: Path, policy_json_object):
    if not browser_config_path.exists():
        browser_config_path.parent.mkdir(parents=True, exist_ok=True)
        browser_config_path.touch()

    with open(browser_config_path, "w") as file1:
        json_text = json.dumps(
            policy_json_object,
            ensure_ascii=False,
            indent=4,
            sort_keys=True,
        )

        json_text += "\n"
        file1.write(json_text)

    print("Browser Policy Saved:{}".format(browser_config_path))


def create_browser_config(domain_list, is_allowlist):
    chromium_policy = _generate_chromium_policy(domain_list, is_allowlist)
    firefox_policy = _generate_firefox_policy(domain_list, is_allowlist)

    # Save for all browsers
    _save_browser_policy(CHROME_POLICY_PATH, chromium_policy)
    _save_browser_policy(BRAVE_POLICY_PATH, chromium_policy)
    _save_browser_policy(CHROMIUM_POLICY_PATH, chromium_policy)
    _save_browser_policy(CHROMIUM2_POLICY_PATH, chromium_policy)

    _update_firefox_browser_policy(FIREFOX_POLICY_PATH, firefox_policy, False)


def remove_browser_config():
    _remove_file_if_exists(CHROME_POLICY_PATH)
    _remove_file_if_exists(BRAVE_POLICY_PATH)
    _remove_file_if_exists(CHROMIUM_POLICY_PATH)
    _remove_file_if_exists(CHROMIUM2_POLICY_PATH)

    _update_firefox_browser_policy(FIREFOX_POLICY_PATH, FIREFOX_POLICY_JSON, True)


def _remove_file_if_exists(path):
    if os.path.exists(path):
        os.remove(path)
        print("Removed: {}".format(path))
