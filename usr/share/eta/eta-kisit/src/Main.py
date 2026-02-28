#!/usr/bin/python3
from time import sleep
import gi
import sys
import argparse
from managers import FileRestrictionManager
from managers import NotificationManager
from managers import ProfileManager
import ETAKisitActivator

# Privileged run check
if not FileRestrictionManager.check_user_privileged():
    sys.stderr.write("You are not privileged to run this script.\n")
    sys.exit(1)

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio  # noqa
from ui_gtk3.MainWindow import MainWindow  # noqa
from Logger import log  # noqa


class Main(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="tr.org.pardus.eta-kisit",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )

        self.window = None

    def do_activate(self):
        if self.window is None:
            self.window = MainWindow(self)

        self.window.show_ui()


# Argument Parsing
parser = argparse.ArgumentParser(description="Application & Domain restricting app.")

parser.add_argument(
    "--reload", action="store_true", help="Apply new profiles.json to the system."
)
parser.add_argument(
    "--user-login",
    action="store",
    help="Specify a user logged in. This disables network restrictions if user is a privileged user.",
)
parser.add_argument(
    "--user-logout",
    action="store",
    help="Specify a user logged out. This re-enables network restrictions if user is a unprivileged user.",
)
parser.add_argument(
    "--generate-applist",
    action="store_true",
    help='Write installed applications in "/var/lib/eta/eta-kisit/installed_applications.json"',
)
args = parser.parse_args()


def on_restricted_user_login():
    # Always restrict apps:
    ETAKisitActivator.run_activator(["--always-restricted-apps"])

    if ETAKisitActivator.is_service_active():
        ETAKisitActivator.run_activator(["--enable-websites-restriction"])

        sleep(5)
        NotificationManager.send_notification(
            "Sınırlı Erişim Etkin.", "", user="ogrenci"
        )


def on_normal_user_login():
    # Disable website restrictions for normal user
    ETAKisitActivator.run_activator(["--disable-websites-restriction"])


def activate_profile(profile_name):
    profile_manager = ProfileManager.get_default()

    # Deactive
    print("Reverting previous settings...")
    ETAKisitActivator.run_activator(["--unrestrict"])

    profile_manager.set_current_profile(profile_name)

    print("Applying new settings...")
    ETAKisitActivator.run_activator(["--restrict"])


def activate_on_startup(username):
    profile_manager = ProfileManager.get_default()

    # Create profile if not exists
    try:
        profile = profile_manager.get_profile(username)
    except KeyError:
        # No profile found, create a new one
        if username is not None:
            log(f"Profile not found, creating new one:'{username}'")
            profile_manager.insert_default_profile(username)
            log(f"Profile created for the user:'{username}'")

    # Apply profile when user logged in:
    if profile.get_activate_on_startup():
        activate_profile(username)
        log(f"Profile '{username}' activated on startup.")

        # Wait for user log in session
        sleep(5)
        NotificationManager.send_notification(
            "Sınırlı Erişim Etkinleştirildi",
            f"{username} profili hesabınıza giriş yaptığınızda otomatik aktifleştirildi.",
            user=username,
        )

        exit(0)

    # If there are other profiles created by the same user, check them also
    for p in profile_manager.get_profile_list().keys():
        profile_owner = profile.created_by if profile.created_by else username

        if username == profile_owner and profile.get_activate_on_startup():
            activate_profile(p)
            log(f"Profile '{p}' owned by '{username}' activated on startup.")
            sleep(5)
            NotificationManager.send_notification(
                "Sınırlı Erişim Etkinleştirildi",
                f"{p} profili hesabınıza giriş yaptığınızda otomatik aktifleştirildi.",
                user=username,
            )

            exit(0)


if args.reload:
    # Deactive
    print("Reverting previous settings...")
    ETAKisitActivator.run_activator(["--unrestrict"])

    print("Applying new settings...")
    ETAKisitActivator.run_activator(["--restrict"])

    print("Done.")
elif args.user_login:
    username = args.user_login

    log(f"--user-login {username}")

    # Enable website restriction and exit if ogrenci
    if username == "ogrenci":
        on_restricted_user_login()
    else:
        on_normal_user_login()
        activate_on_startup(username)


elif args.user_logout:
    username = args.user_logout

    log(f"--user-logout {username}")

    if ETAKisitActivator.is_service_active() and username == "ogrenci":
        ETAKisitActivator.run_activator(["--disable-websites-restriction"])

elif args.generate_applist:
    from managers import ApplicationManager

    ApplicationManager.save_all_applications()
    print(
        "Applications saved to {}".format(
            ApplicationManager.INSTALLED_APPLICATIONS_PATH
        )
    )
else:
    # Start GUI
    app = Main()
    app.run(sys.argv)
