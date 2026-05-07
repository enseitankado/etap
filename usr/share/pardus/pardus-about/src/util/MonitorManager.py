import os
from . import edid


def read_edid(path) -> edid.Edid:
    with open(path, "rb") as f:
        content = f.read()
        monitor_info = edid.Edid(content)
        return monitor_info

    return None


monitors = []


def scan_monitors():
    global monitors
    if monitors:
        return monitors

    # DRM altındaki tüm edid dosyalarını ara
    drm_paths = "/sys/class/drm"
    for drm_path in os.listdir(drm_paths):
        try:
            edid_path = os.path.join(drm_paths, drm_path, "edid")

            if not os.path.isfile(edid_path):
                continue

            edid_info = read_edid(edid_path)

            if edid_info:
                summary_dict = {
                    "name": edid_info.name,
                    "vendor": edid_info.manufacturer,
                    "model_id": edid_info.model_id,
                    "resolution": f"{edid_info.resolution_width}x{edid_info.resolution_height}",
                }

                monitors.append(summary_dict)

        except PermissionError:
            print(
                f"Permission denied: {drm_path}.",
            )
        except ValueError:
            pass
        except Exception as e:
            print(f"Error reading {drm_path}: {e}")

    return monitors
