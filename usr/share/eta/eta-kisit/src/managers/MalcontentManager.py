import platform
import gi

gi.require_version("Malcontent", "0")
from gi.repository import Malcontent, Gio  # noqa


dbus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
if dbus is None:
    print("DBus SYSTEM connection error!")
    exit()

manager = Malcontent.Manager.new(dbus)


def _build_app_filter(list_app_id):
    builder = Malcontent.AppFilterBuilder.new()
    arch = platform.machine()

    # Generate AppFilter from application id list
    for a in list_app_id:
        builder.blocklist_flatpak_ref("app/{}/{}/stable".format(a, arch))

    builder.set_allow_user_installation(True)
    builder.set_allow_system_installation(True)

    new_app_filter = builder.end()

    return new_app_filter


def clear_flatpak_blocklist(user_id):
    new_app_filter = _build_app_filter([])

    manager.set_app_filter(
        int(user_id), new_app_filter, Malcontent.ManagerSetValueFlags.NONE, None
    )


def apply_flatpak_blocklist(list_app_id, user_id):
    new_app_filter = _build_app_filter(list_app_id)

    manager.set_app_filter(
        int(user_id), new_app_filter, Malcontent.ManagerSetValueFlags.NONE, None
    )
