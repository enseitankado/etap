#!/usr/bin/python3

import sys
import os
import argparse
import subprocess
import shutil

from managers import FileRestrictionManager
from managers import ProfileManager
from managers import NetworkFilterManager
from managers import ApplicationManager
from managers import SmartdnsManager

from Logger import log

CWD = os.path.dirname(os.path.abspath(__file__))


def is_service_active():
    return os.path.exists(ProfileManager.APPLIED_PROFILE_PATH)


def run_activator(params):
    process = subprocess.run(
        ["pkexec", CWD + "/" + os.path.basename(__file__)] + params, capture_output=True
    )

    log("Activator run with params: {}".format(params))

    return process


def fix_permissions(path):
    os.chown(
        path,
        0,
        FileRestrictionManager.PRIVILEGED_GROUP_ID,
    )
    os.chmod(path, 0o775)


class ETAKisitActivator:
    def __init__(self, args):
        self.args = args
        print("args:", args)

        # Privileged run check
        if not FileRestrictionManager.check_user_privileged():
            sys.stderr.write("You are not privileged to run this script.\n")
            sys.exit(1)

    def run(self):
        print("== ETAKisitActivator STARTED ==")

        if self.args.fix_permissions:
            # config dir
            fix_permissions(ProfileManager.CONFIG_DIR)

            # profiles.json
            fix_permissions(ProfileManager.PROFILES_PATH)

            # applied_profile.lock_json
            if os.path.exists(ProfileManager.APPLIED_PROFILE_PATH):
                fix_permissions(ProfileManager.APPLIED_PROFILE_PATH)

            # installed_applications.json
            if os.path.exists(ApplicationManager.INSTALLED_APPLICATIONS_PATH):
                fix_permissions(ApplicationManager.INSTALLED_APPLICATIONS_PATH)

            print(
                "Permissions for profiles.json, applied_profiles.lock.json, config directory is fixed."
            )
            exit(0)
        elif self.args.always_restricted_apps:
            app_list = ProfileManager.get_default().get_always_restricted_applications()
            self.always_restrict_apps(app_list)

            exit(0)

        is_restrict = True if self.args.restrict else False
        is_unrestrict = True if self.args.unrestrict else False
        is_enable_websites = True if self.args.enable_websites_restriction else False
        is_disable_websites = True if self.args.disable_websites_restriction else False

        # Read Profiles
        self.profile = None
        self.applied_profile = None

        self.read_profile()
        self.read_applied_profile()

        # Clear browser cache by closing
        self.close_browsers_in_ogrenci()

        # Websites
        if (
            self.applied_profile
            and self.applied_profile.get_website_restriction_type() != "none"
        ):
            if is_enable_websites and is_service_active():
                self.set_network_filter(True, self.applied_profile)
            elif is_disable_websites or is_unrestrict:
                self.set_network_filter(False, self.applied_profile)

        # Applications
        if is_restrict and self.profile:
            self.set_application_filter(True, self.profile)
        elif is_unrestrict and self.applied_profile:
            self.set_application_filter(False, self.applied_profile)

        # Save/Remove json file
        if is_restrict and self.profile:
            self.save_applied_profile()
        elif is_unrestrict:
            self.remove_applied_profile()

        # Always restrict some apps:
        app_list = ProfileManager.get_default().get_always_restricted_applications()
        self.always_restrict_apps(app_list)

        print("== ETAKisitActivator FINISHED ==")

    def read_profile(self):
        self.profile = ProfileManager.get_default().get_current_profile()

    def read_applied_profile(self):
        if is_service_active():
            self.applied_profile = ProfileManager.Profile(
                ProfileManager.get_default().load_json(
                    ProfileManager.APPLIED_PROFILE_PATH
                )
            )

    def save_applied_profile(self):
        profile_manager = ProfileManager.get_default()
        current_profile = profile_manager.get_current_profile()

        try:
            profile_manager.save_as_json_file(
                ProfileManager.APPLIED_PROFILE_PATH, current_profile
            )
        except PermissionError:
            log(
                "PermissionError, cant create file:'{}'".format(
                    ProfileManager.APPLIED_PROFILE_PATH
                )
            )

    def remove_applied_profile(self):
        if os.path.isfile(ProfileManager.APPLIED_PROFILE_PATH):
            os.remove(ProfileManager.APPLIED_PROFILE_PATH)

    def always_restrict_apps(self, app_list):
        # log("=== Restricting Always Restricted Apps: {}".format(app_list))
        for app_id in app_list:
            ApplicationManager.restrict_application(app_id)

    def set_application_filter(self, is_activate, profile):
        if is_activate:
            print("=== Restricting Applications:")
            print(f"| {'App':<70} | {'Binary':<40} |")
            print(f"| {'-' * 70} | {'-' * 40} |")
            restriction_type = profile.get_application_restriction_type()

            if restriction_type == "allowlist":
                all_applications = ApplicationManager.get_all_applications(
                    sort_by_id=True
                )

                for app in all_applications:
                    desktop_file_path = app.get_filename()
                    app_id = app.get_id()

                    if (
                        app_id not in profile.get_application_allowlist()
                        and desktop_file_path not in profile.get_application_allowlist()
                    ):
                        ApplicationManager.restrict_application(app.get_id())

                # Flatpaks:
                blocked_app_ids = []
                for app in ApplicationManager.get_flatpak_applications():
                    desktop_file_path = app.get_filename()
                    app_id = app.get_id()

                    if desktop_file_path not in profile.get_application_allowlist():
                        new_id = app.get_id()[:-8]  # remove .desktop suffix
                        blocked_app_ids.append(new_id)

                ApplicationManager.restrict_flatpaks(
                    blocked_app_ids, FileRestrictionManager.UNPRIVILEGED_USER_ID
                )
            elif restriction_type == "denylist":
                for app_id in profile.get_application_denylist():
                    ApplicationManager.restrict_application(app_id)

                # Flatpaks:
                blocked_app_ids = []
                for app in ApplicationManager.get_flatpak_applications():
                    desktop_file_path = app.get_filename()
                    app_id = app.get_id()

                    if desktop_file_path in profile.get_application_denylist():
                        new_id = app.get_id()[:-8]  # remove .desktop suffix
                        blocked_app_ids.append(new_id)

                ApplicationManager.restrict_flatpaks(
                    blocked_app_ids, FileRestrictionManager.UNPRIVILEGED_USER_ID
                )

        else:
            print("=== Unrestricting Applications:")
            print(f"| {'App':<70} | {'Binary':<40} |")
            print(f"| {'-' * 70} | {'-' * 40} |")
            restriction_type = profile.get_application_restriction_type()

            if restriction_type == "allowlist":
                all_applications = ApplicationManager.get_all_applications(
                    sort_by_id=True
                )
                for app in all_applications:
                    # Remove All app restrictions
                    ApplicationManager.unrestrict_application(app.get_id())
            elif restriction_type == "denylist":
                for app_id in profile.get_application_denylist():
                    ApplicationManager.unrestrict_application(app_id)

            # Flatpaks:
            ApplicationManager.unrestrict_all_flatpaks(
                FileRestrictionManager.UNPRIVILEGED_USER_ID
            )

    def set_network_filter(self, is_activate, profile):
        if is_activate:
            if (
                NetworkFilterManager.is_resolvconf_generated_by_eta_kisit()
                and SmartdnsManager.is_smartdns_conf_generated_by_eta_kisit()
            ):
                # Service already on, don't do anything

                return

            # Static DNS Servers:
            base_dns_servers = ["195.175.37.137", "195.175.37.138"]

            log(f"base_dns_servers:{base_dns_servers}")

            restriction_type = profile.get_website_restriction_type()

            if restriction_type == "none":
                return

            # browser + domain configs
            if restriction_type == "allowlist":
                website_list = profile.get_website_allowlist()

                NetworkFilterManager.set_domain_filter_list(
                    website_list, True, base_dns_servers
                )
            elif restriction_type == "denylist":
                website_list = profile.get_website_denylist()
                if len(website_list) == 0:
                    return

                NetworkFilterManager.set_domain_filter_list(
                    website_list, False, base_dns_servers
                )

            # resolvconf
            NetworkFilterManager.set_resolvconf_to_localhost()

            # smartdns-rs
            SmartdnsManager.enable_smartdns_service()
            SmartdnsManager.restart_smartdns_service()
        else:
            restriction_type = profile.get_website_restriction_type()

            if restriction_type == "none":
                return

            # resolvconf
            NetworkFilterManager.reset_resolvconf_to_default()

            # smartdns-rs
            SmartdnsManager.stop_smartdns_service()
            SmartdnsManager.disable_smartdns_service()

            # browser + domain configs
            NetworkFilterManager.reset_domain_filter_list()

    def close_browsers_in_ogrenci(self):
        subprocess.run(["pkill", "-KILL", "chrome", "-u", "ogrenci"])
        subprocess.run(["pkill", "-KILL", "chromium", "-u", "ogrenci"])
        subprocess.run(["pkill", "-KILL", "firefox-esr", "-u", "ogrenci"])
        subprocess.run(["pkill", "-KILL", "firefox", "-u", "ogrenci"])
        subprocess.run(["pkill", "-KILL", "brave", "-u", "ogrenci"])

        # Remove firefox cache
        cache_path = (
            f"/home/{FileRestrictionManager.UNPRIVILEGED_USER}/.cache/mozilla/firefox"
        )
        if os.path.exists(cache_path) and os.path.isdir(cache_path):
            shutil.rmtree(cache_path)


if __name__ == "__main__":
    # Argument Parsing
    parser = argparse.ArgumentParser(
        description="Application & Domain restricting activator."
    )

    # Restrict Arguments
    parser.add_argument(
        "--restrict",
        action="store_true",
        help="Restrict applications and websites in current profile.",
    )
    parser.add_argument(
        "--enable-websites-restriction",
        action="store_true",
        help="Enable website restriction in applied profile.",
    )

    # Update permissions of Always Restricted Apps
    parser.add_argument(
        "--always-restricted-apps",
        action="store_true",
        help="Restrict apps in the 'always_restricted_applications' list in profiles.json .",
    )

    # Unrestrict Arguments
    parser.add_argument(
        "--unrestrict",
        action="store_true",
        help="Unrestrict applications and websites in applied profile",
    )
    parser.add_argument(
        "--disable-websites-restriction",
        action="store_true",
        help="Enable website restriction in applied profile.",
    )

    # File Permission Fix
    parser.add_argument(
        "--fix-permissions",
        action="store_true",
        help="Fix permissions of stored json files.",
    )
    args = parser.parse_args()

    activator = ETAKisitActivator(args)
    activator.run()
