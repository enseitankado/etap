from pathlib import Path
import shutil
import os
import json
from gi.repository import Gio

from managers import FileRestrictionManager
from managers import MalcontentManager
import ETAKisitActivator


CONFIG_DIR = Path("/var/lib/eta/eta-kisit/")
INSTALLED_APPLICATIONS_PATH = os.path.join(CONFIG_DIR, "installed_applications.json")
ALWAYS_ALLOWED_APPLICATIONS = [
    # Restart and Exit buttons
    "tr.org.pardus.eta-exit.desktop",
    "eta-r.desktop",
    # Keyboard
    "eta-keyboard.desktop",
    "eta-keyboard-autostart.desktop",
    # Resolution
    "tr.org.pardus.eta-resolution.desktop",
    # Screenshot
    "org.gnome.Screenshot.desktop",
    # Apps
    "nemo.desktop",  # File Manager
    "eta-poweroff.desktop",  # Power Off
    "tr.org.pardus.pen.desktop",  # Pardus Pen
    "tr.org.pardus.eta-qr-reader.desktop",  # QR
    "tr.org.pardus.eta-screen-cover.desktop",  # Screen Cover
    "tr.org.pardus.eta.count.desktop",  # Counter
    "tr.org.pardus.night-light.desktop",  # Night Light
    "ogretmen-lock.desktop",  # Night Light
    "org.gnome.Evince.desktop",  # PDF
    "org.gnome.Calculator.desktop",  # Calculator
    "org.gnome.FileRoller.desktop",  # Archive Extractor
    "cinnamon-settings-sound.desktop",  # Audio Settings
    # Office
    "libreoffice-base.desktop",
    "libreoffice-calc.desktop",
    "libreoffice-draw.desktop",
    "libreoffice-impress.desktop",
    "libreoffice-math.desktop",
    "libreoffice-startcenter.desktop",
    "libreoffice-writer.desktop",
]
ALWAYS_ALLOWED_EXECUTABLES = [
    "flatpak",
    "bash",
    "sh",
    "env",
    "exo-open",
    "libreoffice",
    "xfce4-panel",
    "xfce4-session-logout",
    "sudo",
    "pkexec",
    "xfwm4",
    "python",
    "python3",
    "libreoffice",
    "cinnamon-session-quit",
    "cinnamon-settings",
    "eta-resolution",
    "system-config-printer",
    "dm-tool",
]
UNPRIVILEGED_USER_APPLICATIONS_DIR = "/home/{}/.local/share/applications".format(
    FileRestrictionManager.UNPRIVILEGED_USER
)


def get_flatpak_applications():
    apps = []

    d = "/var/lib/flatpak/exports/share/applications/"
    if os.path.isdir(d):
        for f in os.listdir(d):
            if ".desktop" in f:
                app = Gio.DesktopAppInfo.new_from_filename(d + f)
                apps.append(app)

    return apps


def get_all_applications(sort_by_id=False):
    apps = Gio.AppInfo.get_all()
    # Filter only visible applications
    apps = filter(lambda a: not a.get_nodisplay(), apps)
    if sort_by_id:
        apps = sorted(apps, key=lambda a: a.get_id())  # Sort alphabetically
    else:
        apps = sorted(apps, key=lambda a: a.get_name())  # Sort alphabetically

    return list(apps)


def _get_executable_name(app):
    executable = app.get_executable()
    cmdline = app.get_commandline()
    if not cmdline:
        print(
            "- Skip - executable and cmdline is corrupted in application:",
            executable,
            cmdline,
        )
        return ""

    # String to Path
    if executable[0] == '"':
        # '"/opt/Youtube Music/youtube-music" %u' -> '/opt/Youtube Music/youtube-music'
        executable = cmdline.split('"')[1]

    # Absolute Path to Executable Name
    if executable[0] == "/":
        # '/opt/Youtube Music/youtube-music' -> 'youtube-music'
        executable = executable.split("/")[-1]

    # Don't restrict Chrom(e|ium) links:
    if "chrom" in executable and "chrom" not in app.get_id():
        return ""

    return executable


def get_executable_path(app, ignore_allowed_list=False):
    executable = _get_executable_name(app)

    # Always Allowed Binary
    if not ignore_allowed_list:
        if executable and executable in ALWAYS_ALLOWED_EXECUTABLES:
            return ""

    # Convert to absolute path
    if executable:
        path = shutil.which(executable)
        if path:
            return path

    return ""


def save_as_json_file(obj, filepath=INSTALLED_APPLICATIONS_PATH):
    try:
        # Then create the file
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(
                obj,
                f,
                ensure_ascii=False,
                indent=4,
                sort_keys=True,
            )
    except PermissionError:
        process = ETAKisitActivator.run_activator(["--fix-permissions"])

        if process.returncode == 0:
            save_as_json_file(filepath)
        else:
            print(
                "Can't change file permissions, are you sure you are root or in floppy group?"
            )


def save_all_applications():
    applist = get_all_applications()

    json_object = {}

    for app in applist:
        json_object[app.get_id()] = {
            "name": app.get_name(),
            "bin": app.get_executable(),
            "cmdline": app.get_commandline(),
        }

    save_as_json_file(json_object)


# ==== APPLICATION RESTRICTIONS:


# Flatpak
def restrict_flatpaks(app_id_list, user_id):
    for app in app_id_list:
        print(f"| {app:<50} | {'(Flatpak)':<50} |")
    MalcontentManager.apply_flatpak_blocklist(app_id_list, user_id)


def unrestrict_all_flatpaks(user_id):
    MalcontentManager.clear_flatpak_blocklist(user_id)


# System
def find_local_application(application_id):
    local_desktop_file = UNPRIVILEGED_USER_APPLICATIONS_DIR + "/" + application_id
    if os.path.exists(local_desktop_file):
        return local_desktop_file
    return None


def get_appinfo(application_id):
    # Get DesktopAppInfo from app_id
    try:
        # Check if absolute path:
        if application_id.startswith("/"):
            app = Gio.DesktopAppInfo.new_from_filename(application_id)
        else:
            app = Gio.DesktopAppInfo.new(application_id)

        return app
    except TypeError:
        print("Application not found:", application_id)
        return None


def get_desktop_files(application_id):
    if application_id.startswith("/"):
        # convert full file path to app id
        application_id = application_id.split("/")[-1]

    desktop_file_paths = []
    # TODO: Getting XDG_DATA_DIRS from root is harder than this.
    # Accessing etapadmin's environment variables of Xsession.d is correct way to do this.
    data_dirs = "/usr/share/etap:/var/lib/wine-prefix/.local/share:/usr/share/gnome:/usr/local/share/:/usr/share/"

    # Search for the .desktop file in these directories
    for dir in data_dirs.split(":"):
        applications_dir = os.path.join(dir, "applications")
        if not os.path.isdir(applications_dir):
            continue

        for file in os.listdir(applications_dir):
            if file == application_id:
                file_path = os.path.join(applications_dir, file)
                desktop_file_paths.append(file_path)

    return desktop_file_paths


def restrict_application(application_id):
    desktop_files = get_desktop_files(application_id)
    if not desktop_files:
        print(f"No desktop file found for application:{application_id}")
        return

    # Get DesktopAppInfo from app_id
    app = get_appinfo(application_id)
    if not app:
        print(f"Application not found:{application_id}")
        return

    app_id = app.get_id()

    # Check if .desktop file exists in .local/share/applications/
    local_desktop_file = find_local_application(app_id)
    if local_desktop_file:
        print(f"Also restricted: ~/.local/share/applications:{local_desktop_file}")
        FileRestrictionManager.restrict_desktop_file(local_desktop_file)

    # Restrict desktopfile
    desktop_file_path = app.get_filename()

    if app_id in ALWAYS_ALLOWED_APPLICATIONS:
        return

    # Restrict executable
    executable = get_executable_path(app)

    for file in desktop_files:
        FileRestrictionManager.restrict_desktop_file(file)
        print(f"| {file:<70} | {executable:<40} |")

    if not executable:
        return

    # Restrict executable if not flatpak
    if "/var/lib/flatpak/" in desktop_file_path:
        pass
    else:
        FileRestrictionManager.restrict_bin_file(executable)


def unrestrict_application(application_id):
    desktop_files = get_desktop_files(application_id)
    if not desktop_files:
        print(f"No desktop file found for application:{application_id}")
        return

    # Get DesktopAppInfo from app_id
    app = get_appinfo(application_id)
    if not app:
        print(f"Application not found:{application_id}")
        return

    # Check if .desktop file exists in .local/share/applications/
    local_desktop_file = find_local_application(app.get_id())
    if local_desktop_file:
        print(f"Also unrestricted: ~/.local/share/applications:{local_desktop_file}")
        FileRestrictionManager.unrestrict_local_desktop_file(local_desktop_file)

    # Unrestrict desktop file
    desktop_file_path = app.get_filename()

    # Unrestrict executable
    # ignore_allowed_list: Get even ignored binaries to unrestrict them again
    executable = get_executable_path(app, ignore_allowed_list=True)

    for file in desktop_files:
        FileRestrictionManager.unrestrict_desktop_file(file)
        print(f"| {file:<70} | {executable:<40} |")

    if not executable:
        return

    if "/var/lib/flatpak/" in desktop_file_path:
        pass
    else:
        FileRestrictionManager.unrestrict_bin_file(executable)
