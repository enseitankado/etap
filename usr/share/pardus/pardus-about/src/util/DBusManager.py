import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib

SYSTEM_BUS = Gio.bus_get_sync(Gio.BusType.SYSTEM)

def read_property(bus_name, object_path, param):
    return SYSTEM_BUS.call_sync(
        bus_name,
        object_path,
        interface_name="org.freedesktop.DBus.Properties",
        method_name="Get",
        parameters=GLib.Variant.new_tuple(
            GLib.Variant.new_string(bus_name), GLib.Variant.new_string(param)
        ),
        reply_type=None,
        flags=Gio.DBusCallFlags.NONE,
        timeout_msec=-1,
        cancellable=None,
    )


def read_string_in_tuple(bus_name, object_path, param, index):
    result = read_property(bus_name, object_path, param)

    return result.get_child_value(index).get_variant().get_string()
