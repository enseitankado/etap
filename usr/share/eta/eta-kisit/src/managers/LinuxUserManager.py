import subprocess
import os
import pwd


def get_logged_username():
    return pwd.getpwuid(os.getuid()).pw_name


def get_user_id(username):
    return pwd.getpwnam(username).pw_uid


def _get_users():
    list_users = pwd.getpwall()

    return list(filter(lambda x: "bash" in x.pw_shell, list_users))


def get_active_session_username():
    users = _get_users()

    for u in users:
        process = subprocess.run(
            ["loginctl", "show-user", u.pw_name, "-p", "State"], capture_output=True
        )

        if process.returncode == 0:
            if "=active" in process.stdout.decode():
                return u.pw_name

    print("Couldnt find active session username from loginctl.")

    return None


def switch_user_session(username):
    _ = subprocess.run(["dm-tool", "switch-to-user", "ogrenci"])
