import subprocess


def get_disabled_snap_applications():
    apps = []

    try:
        p = subprocess.run(
            ["snap", "list", "--color=never", "--unicode=never"], capture_output=True
        )

        if p.returncode != 0:
            return []

        for line in p.stdout.decode().splitlines():
            columns = line.strip().split(" ")
            columns = list(filter(lambda x: x, columns))

            if columns[-1] == "disabled":
                apps.append(columns[0])
    except FileNotFoundError as e:
        pass

    return apps


def restrict_snap(app_id):
    try:
        subprocess.run(["snap", "disable", app_id], capture_output=True)
    except FileNotFoundError:
        pass


def unrestrict_snap(app_id):
    try:
        subprocess.run(["snap", "enable", app_id], capture_output=True)
    except FileNotFoundError:
        pass
