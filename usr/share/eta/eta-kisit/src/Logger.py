import os
import datetime
import version

LOG_FILE = "/var/log/eta-kisit.log"


def log(msg):
    try:
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, "w") as f:
                f.write("# ETAKisit Logs: \n")

        with open(LOG_FILE, "a") as f:
            dt = datetime.datetime.now()
            dt = dt.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{dt}](v{version.VERSION}): {msg}\n")
    except PermissionError:
        import ETAKisitActivator

        process = ETAKisitActivator.run_activator(["--fix-permissions"])
        if process.returncode == 0:
            log(msg)
        else:
            print(
                "Can't change file permissions, are you sure you are root or in floppy group?"
            )

    print(msg)
