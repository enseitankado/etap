import os
import json
import ETAKisitActivator
from pathlib import Path
import copy

CONFIG_DIR = Path("/var/lib/eta/eta-kisit/")
PROFILES_PATH = os.path.join(CONFIG_DIR, "profiles.json")
APPLIED_PROFILE_PATH = os.path.join(CONFIG_DIR, "applied_profile.lock.json")

ADMIN_USERNAME = "etapadmin"

_DEFAULT_PROFILES = {
    "profile_list": {
        "Varsayılan Ayar": {
            "activate_on_startup": False,  # Apply automatically on user login
            "application": {
                "allowlist": [],
                "denylist": [],
                "restriction_type": "none",
            },
            "website": {
                "allowlist": [],
                "denylist": [],
                "restriction_type": "none",
            },
            "created_by": "",  # indicates user name that created this profil
            # "is_default": true # only managed from liderahenk, users can't change this profile.
        },
    },
    "current_profile": "Varsayılan Ayar",
    "always_restricted_applications": ["tr.org.pardus.eta-help.desktop"],
}


class Profile(object):
    def __init__(self, json_object):
        self.__dict__ = json_object  # deserialize json object to the profile struct

    # Getters
    def get_application_allowlist(self):
        return self.application["allowlist"]

    def get_application_denylist(self):
        return self.application["denylist"]

    def get_website_allowlist(self):
        return self.website["allowlist"]

    def get_website_denylist(self):
        return self.website["denylist"]

    def get_application_restriction_type(self):
        return self.application["restriction_type"]

    def get_website_restriction_type(self):
        return self.website["restriction_type"]

    def get_is_application_list_allowlist(self):
        return self.application["restriction_type"] == "allowlist"

    def get_is_website_list_allowlist(self):
        return self.website["restriction_type"] == "allowlist"

    def get_activate_on_startup(self):
        return self.activate_on_startup

    def get_created_by(self):
        return self.created_by if hasattr(self, "created_by") else ""

    # default means = not changeable profile
    def get_is_default(self):
        return hasattr(self, "is_default") and self.is_default

    # Setters
    def set_application_allowlist(self, value):
        if isinstance(value, list):
            self.application["allowlist"] = value

    def set_application_denylist(self, value):
        if isinstance(value, list):
            self.application["denylist"] = value

    def set_website_allowlist(self, value):
        if isinstance(value, list):
            self.website["allowlist"] = value

    def set_website_denylist(self, value):
        if isinstance(value, list):
            self.website["denylist"] = value

    def set_application_restriction_type(self, value):
        if isinstance(value, str):
            self.application["restriction_type"] = value

    def set_website_restriction_type(self, value):
        if isinstance(value, str):
            self.website["restriction_type"] = value

    def set_is_application_list_allowlist(self, value):
        if isinstance(value, bool):
            self.set_application_restriction_type("allowlist" if value else "denylist")

    def set_is_website_list_allowlist(self, value):
        if isinstance(value, bool):
            self.set_website_restriction_type("allowlist" if value else "denylist")

    def set_activate_on_startup(self, value):
        if isinstance(value, bool):
            self.activate_on_startup = value

    def set_created_by(self, value):
        if isinstance(value, str):
            self.created_by = value

    # JSON
    def as_json(self):
        return json.dumps(
            self.__dict__,
            default=lambda o: o.__dict__,
            ensure_ascii=False,
            indent=4,
            sort_keys=True,
        )

    # Insert
    def insert_application_allowlist(self, app_id):
        if app_id in self.application["allowlist"]:
            return False

        self.application["allowlist"].append(app_id)
        return True

    def insert_application_denylist(self, app_id):
        if app_id in self.application["denylist"]:
            return False

        self.application["denylist"].append(app_id)
        return True

    def insert_website_allowlist(self, website_domain):
        if website_domain in self.website["allowlist"]:
            return False

        self.website["allowlist"].append(website_domain)
        return True

    def insert_website_denylist(self, website_domain):
        if website_domain in self.website["denylist"]:
            return False

        self.website["denylist"].append(website_domain)
        return True

    # Remove
    def remove_application_allowlist(self, app_id):
        if app_id not in self.application["allowlist"]:
            return False

        self.application["allowlist"].remove(app_id)
        return True

    def remove_application_denylist(self, app_id):
        if app_id not in self.application["denylist"]:
            return False

        self.application["denylist"].remove(app_id)
        return True

    def remove_website_allowlist(self, website_domain):
        if website_domain not in self.website["allowlist"]:
            return False

        self.website["allowlist"].remove(website_domain)
        return True

    def remove_website_denylist(self, website_domain):
        if website_domain not in self.website["denylist"]:
            return False

        self.website["denylist"].remove(website_domain)
        return True


class ProfileManager:
    def __init__(self):
        self.load_profiles()

    # Getters
    def get_profile_list(self):
        return self.profile_list

    def get_profile(self, name) -> Profile:
        return self.profile_list[name]

    def get_current_profile(self) -> Profile:
        return self.get_profile(self.current_profile)

    def get_current_profile_name(self):
        return self.current_profile

    def has_profile_name(self, profile_name):
        return profile_name in self.profile_list

    def get_always_restricted_applications(self):
        if not hasattr(self, "always_restricted_applications"):
            self.set_always_restricted_applications(
                _DEFAULT_PROFILES["always_restricted_applications"]
            )

        return self.always_restricted_applications

    # Setters
    def set_profile_dict(self, value):
        if isinstance(value, dict):
            self.profile_list = value

            self.save_as_json_file()

    def set_current_profile(self, value):
        if isinstance(value, str):
            self.current_profile = value

            self.save_as_json_file()

    def set_always_restricted_applications(self, value):
        if isinstance(value, list):
            self.always_restricted_applications = value

            self.save_as_json_file()

    # Insert
    def insert_default_profile(self, profile_name, created_by=""):
        profile = Profile(
            copy.deepcopy(_DEFAULT_PROFILES["profile_list"]["Varsayılan Ayar"])
        )

        profile.set_created_by(created_by)

        profile.__dict__.pop(
            "is_default", None
        )  # remove is_default if exists, is_default means immutable profile managed by liderahenk

        self.profile_list[profile_name] = profile
        self.save_as_json_file()

    def duplicate_profile(
        self, duplicated_profile_name, new_profile_name, created_by=""
    ):
        profile = Profile(
            copy.deepcopy(self.get_profile(duplicated_profile_name).__dict__)
        )

        profile.set_created_by(created_by)

        profile.__dict__.pop(
            "is_default", None
        )  # remove is_default if exists, is_default means immutable profile managed by liderahenk

        self.profile_list[new_profile_name] = profile
        self.save_as_json_file()

    # Remove
    def remove_profile(self, profile_name):
        if profile_name not in self.profile_list:
            return

        del self.profile_list[profile_name]

        self.save_as_json_file()

    # Update
    def update_profile_name(self, old_name, new_name):
        if old_name not in self.profile_list:
            return

        self.profile_list[new_name] = self.profile_list[old_name]

        del self.profile_list[old_name]

        if old_name == self.current_profile:
            self.current_profile = new_name

        self.save_as_json_file()

    # JSON
    def as_json(self):
        return json.dumps(
            self.__dict__,
            default=lambda o: o.__dict__,
            ensure_ascii=False,
            indent=4,
            sort_keys=True,
        )

    def save_as_json_file(self, filepath=PROFILES_PATH, json_object=None):
        if json_object is None:
            json_object = self.__dict__

        # Create the profiles.json if not exists
        try:
            # Write json data
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(
                    json_object,
                    f,
                    default=lambda o: o.__dict__,
                    ensure_ascii=False,
                    indent=4,
                    sort_keys=True,
                )
        except PermissionError:
            process = ETAKisitActivator.run_activator(["--fix-permissions"])

            if process.returncode == 0:
                self.save_as_json_file(filepath, json_object)
            else:
                print(
                    "Can't change file permissions, are you sure you are root or in floppy group?"
                )

    def load_profiles(self):
        print("Loading profiles from {}".format(PROFILES_PATH))
        self.__dict__ = self.load_json()

        for key in self.profile_list:
            self.profile_list[key] = Profile(self.profile_list[key])

    def load_json(self, filepath=PROFILES_PATH):
        # Read the profiles.json
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print("File not found: ", filepath)
            print("Returning default profiles.")

            return copy.deepcopy(_DEFAULT_PROFILES)
        except PermissionError:
            process = ETAKisitActivator.run_activator(["--fix-permissions"])

            if process.returncode == 0:
                return self.load_json(filepath)
            else:
                print("ERROR! Couldn't fix the permissions with '--fix-permissions'!")
                print("ERROR! Still can't access path:", filepath)
                exit(1)
        except json.JSONDecodeError:
            print(
                "{} is not valid json file. Moving file to backup: profiles.json.backup. Using default profiles.json".format(
                    filepath
                )
            )
            # Backup current one
            os.rename(filepath, "{}.backup".format(filepath))

            return copy.deepcopy(_DEFAULT_PROFILES)


profile_manager = None


def get_default() -> ProfileManager:
    global profile_manager

    if profile_manager is None:
        profile_manager = ProfileManager()

    return profile_manager
