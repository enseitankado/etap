import subprocess
from Logger import log


def send_notification(title, body="", user=""):
    log(f"send_notification({user}): {title}, {body}")
    if user:
        subprocess.run(
            ["notify-send", "-i", "eta-kisit", "-a", "eta-kisit", title, body],
            user=user,
        )
    else:
        subprocess.run(
            ["notify-send", "-i", "eta-kisit", "-a", "eta-kisit", title, body]
        )
