import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib

HOSTNAME_BUS_NAME = "org.freedesktop.hostname1"
HOSTNAME_OBJECT_PATH = "/org/freedesktop/hostname1"

DBUS_PROXY = Gio.DBusProxy.new_for_bus_sync(
    Gio.BusType.SYSTEM,
    Gio.DBusProxyFlags.NONE,
    None,
    HOSTNAME_BUS_NAME,
    HOSTNAME_OBJECT_PATH,
    HOSTNAME_BUS_NAME,
    None,
)


def get_hostname():
    variant = DBUS_PROXY.call_sync(
        method_name="org.freedesktop.DBus.Properties.Get",
        parameters=GLib.Variant.new_tuple(
            GLib.Variant.new_string(HOSTNAME_BUS_NAME),
            GLib.Variant.new_string("Hostname"),
        ),
        flags=Gio.DBusCallFlags.NONE,
        timeout_msec=-1,
        cancellable=None,
    )

    return variant.get_child_value(0).get_variant().get_string()


def set_hostname(hostname):
    if not hostname:
        return False

    hostname_var = GLib.Variant.new_string(hostname)

    try:
        # SetPrettyHostname
        print("Setting PrettyHostname...")
        DBUS_PROXY.call_sync(
            method_name="SetPrettyHostname",
            parameters=GLib.Variant.new_tuple(
                hostname_var,
                GLib.Variant.new_boolean(False),
            ),
            flags=Gio.DBusCallFlags.NONE,
            timeout_msec=-1,
            cancellable=None,
        )
        print("PrettyHostname is set:", hostname)

        # SetStaticHostname
        print("Setting PrettyHostname...")
        DBUS_PROXY.call_sync(
            method_name="SetStaticHostname",
            parameters=GLib.Variant.new_tuple(
                hostname_var,
                GLib.Variant.new_boolean(False),
            ),
            flags=Gio.DBusCallFlags.NONE,
            timeout_msec=-1,
            cancellable=None,
        )
        print("StaticHostname is set:", hostname)

    except GLib.Error as e:
        print("Error:", e)
        return False

    return True
