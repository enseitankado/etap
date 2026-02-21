#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 23 23:47:01 2024

@author: fatih
"""

import os
import subprocess
import sys
import time
from pathlib import Path
from lxml import etree

import dbus
import gi

gi.require_version("GLib", "2.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

try:
    gi.require_version('AppIndicator3', '0.1')
    from gi.repository import AppIndicator3 as appindicator
except:
    # fall back to Ayatana
    gi.require_version('AyatanaAppIndicator3', '0.1')
    from gi.repository import AyatanaAppIndicator3 as appindicator


class MainWindow(object):
    def __init__(self, application):
        self.application = application

        if "autostart-mode" in self.application.args.keys():
            time.sleep(1)

        self.current_res = ""
        self.hidpi_text = "4K - %200"
        self.fullhd_text = "Full HD - %100"
        self.hidpi_found = False
        self.fullhd_found = False
        self.hidpi_res = None
        self.fullhd_res = None

        self.current_desktop = self.get_current_desktop()
        if "gnome" in self.current_desktop:
            self.monitors_xml = "{}/.config/monitors.xml".format(Path.home())
        elif "cinnamon" in self.current_desktop:
            self.monitors_xml = "{}/.config/cinnamon-monitors.xml".format(Path.home())

        self.init_bus()
        self.resolutions = self.get_monitor_resolutions()
        if "nogui" not in self.application.args.keys():
            self.init_indicator()
            self.set_indicator()
            self.control_args()
        else:
            print("in no gui")
            self.control_args()
            sys.exit(0)

    def get_current_desktop(self):
        if "XDG_CURRENT_DESKTOP" in os.environ:
            return os.environ["XDG_CURRENT_DESKTOP"].lower()
        elif "DESKTOP_SESSION" in os.environ:
            return os.environ["DESKTOP_SESSION"].lower()
        elif "SESSION" in os.environ:
            return os.environ["SESSION"].lower()
        else:
            return ""

    def control_args(self):
        if "set" in self.application.args.keys():
            try:
                value = int(self.application.args["set"])
            except Exception as e:
                print("{}".format(e))
                print("invalid arg. 0 for 4K %200, 1 for FullHD %100")
                return

            if value == 0:
                # 4K %200
                if self.hidpi_found and self.hidpi_res is not None:
                    self.set_monitor_resolution(self.hidpi_res)
                else:
                    print("4K not supported")

            elif value == 1:
                # FullHD %100
                if self.fullhd_found and self.fullhd_res is not None:
                    self.set_monitor_resolution(self.fullhd_res)
                else:
                    print("FullHD not supported")
            else:
                print("value {} not supported yet.".format(value))

    def init_bus(self):
        self.bus = dbus.SessionBus()
        if "gnome" in self.current_desktop:
            self.display_config_name = "org.gnome.Mutter.DisplayConfig"
            self.display_config_path = "/org/gnome/Mutter/DisplayConfig"
        elif "cinnamon" in self.current_desktop:
            self.display_config_name = "org.cinnamon.Muffin.DisplayConfig"
            self.display_config_path = "/org/cinnamon/Muffin/DisplayConfig"
        else:
            print("unsupported desktop: {}".format(self.current_desktop))
            sys.exit(0)
        print("DE: {}".format(self.current_desktop))

    def get_monitor_resolutions(self):
        display_config_proxy = self.bus.get_object(self.display_config_name, self.display_config_path)
        display_config_interface = dbus.Interface(display_config_proxy, dbus_interface=self.display_config_name)
        serial, physical_monitors, logical_monitors, properties = display_config_interface.GetCurrentState()
        availables = []
        for x, y, scale, transform, primary, linked_monitors_info, props in logical_monitors:
            for linked_monitor_connector, linked_monitor_vendor, linked_monitor_product, linked_monitor_serial in linked_monitors_info:
                for monitor_info, monitor_modes, monitor_properties in physical_monitors:
                    monitor_connector, monitor_vendor, monitor_product, monitor_serial = monitor_info
                    if linked_monitor_connector == monitor_connector:
                        for mode_id, mode_width, mode_height, mode_refresh, mode_preferred_scale, mode_supported_scales, mode_properties in monitor_modes:
                            availables.append(mode_id)
                            print("available: {}".format(mode_id))
                            if mode_properties.get("is-current", False):
                                print("current: " + mode_id)
                                self.current_res = mode_id

        self.hidpi_found = False
        self.fullhd_found = False
        for res in availables:
            if "3840x2160" in res and not self.hidpi_found:
                self.hidpi_found = True
                self.hidpi_res = res
                print("hidpi_found: {}".format(res))
            if "1920x1080" in res and not self.fullhd_found:
                self.fullhd_found = True
                self.fullhd_res = res
                print("fullhd_found: {}".format(res))

        return availables

    def init_indicator(self):
        self.indicator = appindicator.Indicator.new(
            "eta-resolution", "preferences-desktop-display-symbolic",
            appindicator.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
        self.indicator.set_title("ETA Çözünürlük")

        self.menu = Gtk.Menu()

        self.item_quit = Gtk.MenuItem()
        self.item_quit.set_label("Çıkış")
        self.item_quit.connect('activate', self.on_menu_quit_app)

        if self.hidpi_found:
            menuitem = Gtk.MenuItem()
            menuitem.set_label("{}".format(self.hidpi_text))
            menuitem.set_name("{}".format(self.hidpi_res))
            menuitem.connect("activate", self.on_menu_action)
            self.menu.append(menuitem)
        if self.fullhd_found:
            menuitem = Gtk.MenuItem()
            menuitem.set_label("{}".format(self.fullhd_text))
            menuitem.set_name("{}".format(self.fullhd_res))
            menuitem.connect("activate", self.on_menu_action)
            self.menu.append(menuitem)

        self.menu.append(self.item_quit)
        self.menu.show_all()
        self.indicator.set_menu(self.menu)

    def set_indicator(self):
        hidpi = False
        fullhd = False
        if "3840x2160" in self.current_res:
            hidpi = True
        elif "1920x1080" in self.current_res:
            fullhd = True

        try:
            for row in self.menu:
                if "3840x2160" in row.get_name():
                    if hidpi:
                        row.set_label("* {}".format(self.hidpi_text))
                    else:
                        row.set_label("{}".format(self.hidpi_text))
                if "1920x1080" in row.get_name():
                    if fullhd:
                        row.set_label("* {}".format(self.fullhd_text))
                    else:
                        row.set_label("{}".format(self.fullhd_text))
        except AttributeError as e:
            print("{}".format(e))

    def on_menu_action(self, widget):
        self.set_monitor_resolution(widget.get_name())

    def set_monitor_resolution(self, new_mode):
        if "3840x2160" in new_mode:
            new_scale = 2
        elif "1920x1080" in new_mode:
            new_scale = 1
        else:
            print("invalid mode")
            return

        m_connector = ""
        m_vendor = ""
        m_product = ""
        m_serial = ""

        display_config_proxy = self.bus.get_object(self.display_config_name, self.display_config_path)
        display_config_interface = dbus.Interface(display_config_proxy, dbus_interface=self.display_config_name)
        serial, physical_monitors, logical_monitors, properties = display_config_interface.GetCurrentState()
        updated_logical_monitors = []
        for x, y, scale, transform, primary, linked_monitors_info, props in logical_monitors:
            physical_monitors_config = []
            for linked_monitor_connector, linked_monitor_vendor, linked_monitor_product, linked_monitor_serial in linked_monitors_info:
                for monitor_info, monitor_modes, monitor_properties in physical_monitors:
                    monitor_connector, monitor_vendor, monitor_product, monitor_serial = monitor_info
                    if linked_monitor_connector == monitor_connector:
                        m_connector, m_vendor, m_product, m_serial = monitor_info
                        for mode_id, mode_width, mode_height, mode_refresh, mode_preferred_scale, mode_supported_scales, mode_properties in monitor_modes:
                            if mode_properties.get("is-current", False):
                                physical_monitors_config.append(dbus.Struct([monitor_connector, new_mode, {}]))
                                if scale not in mode_supported_scales:
                                    print("Error: " + monitor_properties.get(
                                        "display-name") + " doesn't support that scaling value! (" + str(
                                        new_scale) + ")")
                                else:
                                    print("{}: new mode:{} - scale:{}".format(monitor_properties.get("display-name"),
                                                                              new_mode, new_scale))
            updated_logical_monitor_struct = dbus.Struct(
                [dbus.Int32(x), dbus.Int32(y), dbus.Double(new_scale), dbus.UInt32(transform), dbus.Boolean(primary),
                 physical_monitors_config])
            updated_logical_monitors.append(updated_logical_monitor_struct)
        properties_to_apply = {"layout_mode": properties.get("layout-mode")}
        method = 1
        display_config_interface.ApplyMonitorsConfig(dbus.UInt32(serial), dbus.UInt32(method), updated_logical_monitors,
                                                     properties_to_apply)


        # write changes to monitors xml too

        hertz = "{}".format(new_mode.split("@")[1])
        width = "{}".format(new_mode.split("@")[0].split("x")[0])
        height = "{}".format(new_mode.split("@")[0].split("x")[1])

        if os.path.exists(self.monitors_xml):
            parser = etree.XMLParser(remove_blank_text=True)
            tree = etree.parse(self.monitors_xml, parser)
            root = tree.getroot()
        else:
            print("{} file not exists so creating.".format(self.monitors_xml))
            root = etree.Element('monitors', version='2')
            tree = etree.ElementTree(root)

        found = False
        for configuration in root.findall('configuration'):
            for monitor in configuration.findall('.//monitor'):
                connector = monitor.find('.//connector')
                vendor = monitor.find('.//vendor')
                product = monitor.find('.//product')
                serial = monitor.find('.//serial')
                if connector is not None and vendor is not None and product is not None and serial is not None:
                    if connector.text == m_connector and vendor.text == m_vendor and product.text == m_product and serial.text == m_serial:
                        scale_element = configuration.find('.//scale')
                        width_element = monitor.find('.//mode/width')
                        height_element = monitor.find('.//mode/height')
                        rate_element = monitor.find('.//mode/rate')

                        scale_element.text = "{}".format(new_scale)
                        width_element.text = "{}".format(width)
                        height_element.text = "{}".format(height)
                        rate_element.text = "{}".format(hertz)

                        found = True
                        break

        if not found:
            new_configuration = etree.Element('configuration')
            new_logical_monitor = etree.SubElement(new_configuration, 'logicalmonitor')

            etree.SubElement(new_logical_monitor, 'x').text = '0'
            etree.SubElement(new_logical_monitor, 'y').text = '0'
            etree.SubElement(new_logical_monitor, 'scale').text = "{}".format(new_scale)
            etree.SubElement(new_logical_monitor, 'primary').text = "yes"

            new_monitor = etree.SubElement(new_logical_monitor, 'monitor')
            new_monitor_spec = etree.SubElement(new_monitor, 'monitorspec')
            etree.SubElement(new_monitor_spec, 'connector').text = "{}".format(m_connector)
            etree.SubElement(new_monitor_spec, 'vendor').text = "{}".format(m_vendor)
            etree.SubElement(new_monitor_spec, 'product').text = "{}".format(m_product)
            etree.SubElement(new_monitor_spec, 'serial').text = "{}".format(m_serial)

            new_mode = etree.SubElement(new_monitor, 'mode')
            etree.SubElement(new_mode, 'width').text = "{}".format(width)
            etree.SubElement(new_mode, 'height').text = "{}".format(height)
            etree.SubElement(new_mode, 'rate').text = "{}".format(hertz)

            root.append(new_configuration)

        tree.write(self.monitors_xml, pretty_print=True, xml_declaration=False, encoding='utf-8')


        # if os.path.isfile("/ortak-alan/wine/user.reg"):
        #     # wine scale
        #     if new_scale == 1:
        #         subprocess.run("env WINEPREFIX=/ortak-alan/wine wine reg add \"HKEY_CURRENT_USER\Control Panel\Desktop\" /v LogPixels /t REG_DWORD /d 0x60 /f", shell=True)
        #     elif new_scale == 2:
        #         subprocess.run("env WINEPREFIX=/ortak-alan/wine wine reg add \"HKEY_CURRENT_USER\Control Panel\Desktop\" /v LogPixels /t REG_DWORD /d 0xc0 /f", shell=True)
        #     # kill all wine apps
        #     subprocess.run("env WINEPREFIX=/ortak-alan/wine wineserver -k", shell=True)

        # Reload start menu to get correct dimensions
        if "cinnamon" in self.current_desktop:
            try:
                subprocess.run("dbus-send --session --dest=org.Cinnamon.LookingGlass --type=method_call"
                               " /org/Cinnamon/LookingGlass org.Cinnamon.LookingGlass.ReloadExtension"
                               " string:'menu@cinnamon.org' string:'APPLET'", shell=True)
            except Exception as e:
                print("{}".format(e))

            # try:
            #     subprocess.run("dbus-send --type=method_call --dest=org.Cinnamon"
            #                    " /org/Cinnamon org.Cinnamon.Eval string:'global.real_restart()'", shell=True)
            # except Exception as e:
            #     print("{}".format(e))

            try:
                subprocess.run("nemo-desktop -q", shell=True)
                subprocess.run("nohup nemo-desktop > /dev/null 2>&1 &", shell=True)
            except Exception as e:
                print("{}".format(e))

        # try:
        #     # refresh gnome-shell
        #     time.sleep(5)
        #     subprocess.run(["busctl", "--user", "call", "org.gnome.Shell", "/org/gnome/Shell", "org.gnome.Shell",
        #                     "Eval", "s", "Meta.restart('Yenileniyor…')"])
        #     time.sleep(5)
        #     # switch off/on user extensions
        #     time.sleep(1)
        #     subprocess.run(["gsettings", "set", "org.gnome.shell", "disable-user-extensions", "true"])
        #     subprocess.run(["gsettings", "set", "org.gnome.shell", "disable-user-extensions", "false"])
        # except Exception as e:
        #     print("{}".format(e))

        self.get_monitor_resolutions()
        if "nogui" not in self.application.args.keys():
            GLib.idle_add(self.indicator.set_status, appindicator.IndicatorStatus.PASSIVE)
            GLib.idle_add(self.set_indicator)
            GLib.idle_add(self.indicator.set_status, appindicator.IndicatorStatus.ACTIVE)

    def on_menu_quit_app(self, *args):
        Gtk.main_quit()
