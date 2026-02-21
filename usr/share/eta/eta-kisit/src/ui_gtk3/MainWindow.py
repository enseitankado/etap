from ui_gtk3.PreferencesWindow import PreferencesWindow
from ui_gtk3.ProfileChooserWindow import ProfileChooserWindow
from ui_gtk3 import Dialogs

from managers import ProfileManager
from managers import LinuxUserManager
from managers import NotificationManager

import ETAKisitActivator
import version

import os
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Gio  # noqa

CWD = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "{}/../../data".format(CWD)


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)

        # Setup Variables
        self.setup_variables()

        # Setup Window
        self.setup_window()

        # Setup CSS
        self.setup_css()

        # Setup Headerbar
        self.setup_headerbar()

        # Setup UI
        self.setup_ui()

        # Setup Dialogs
        self.setup_dialogs()

        # Setup File Monitor
        self.setup_file_monitor()

    def show_ui(self):
        self.show_all()

        # BAD WORKAROUND: setting visible child overrided to first child after "show_all()" -.-"
        profile_name = (
            self.profile_manager.get_current_profile_name()
            if ETAKisitActivator.is_service_active()
            else self.cmb_current_profile.get_active_text()
        )
        profile = self.profile_manager.get_profile(profile_name)

        profile_owner = profile.created_by if profile.created_by else profile_name
        current_user = LinuxUserManager.get_logged_username()
        if profile_owner == current_user:
            self.stack_startup_checkbox.set_visible_child_name("checkbox")
        else:
            self.stack_startup_checkbox.set_visible_child_name("empty")

    # === Setups ===
    def setup_variables(self):
        self.logged_username = LinuxUserManager.get_logged_username()
        self.profile_manager = ProfileManager.get_default()

        # Create user's profile if not exists
        if self.logged_username is not None and self.logged_username != "":
            try:
                self.profile_manager.get_profile(self.logged_username)
            except KeyError:
                print("Couldnt find username: '{}'".format(self.logged_username))
                print("Creating new profile.")
                self.profile_manager.insert_default_profile(self.logged_username)

        # self.profile_manager.set_current_profile(self.logged_username)

    def setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path("{}/style_gtk3.css".format(DATA_DIR))

        style = self.get_style_context()
        style.add_provider_for_screen(
            Gdk.Screen.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

    def setup_window(self):
        self.set_default_size(400, 600)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_icon_name("eta-kisit")

        self.connect("destroy", lambda x: self.get_application().quit())

    def setup_headerbar(self):
        self.set_title("ETA Sınırlı Erişim")

    def setup_main_page(self):
        # Main Page
        mainbox = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            margin=13,
            spacing=7,
        )
        btn_about_dialog = Gtk.Button(halign="start")
        btn_about_dialog.add(Gtk.Image(icon_name="help-about-symbolic"))
        btn_about_dialog.connect("clicked", self.on_btn_about_dialog_clicked)
        mainbox.add(btn_about_dialog)

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=7,
            vexpand=True,
            valign=Gtk.Align.CENTER,
            halign=Gtk.Align.FILL,
        )

        # Logo
        self.img_logo = Gtk.Image.new_from_file("{}/img/eta-kisit.svg".format(DATA_DIR))
        self.img_logo.set_name(
            "floating_logo" if ETAKisitActivator.is_service_active() else "logo"
        )  # css #logo id
        box.add(self.img_logo)

        box.add(Gtk.Separator(orientation="vertical"))

        # Profile Selection Box
        box_profiles = Gtk.Box(halign=Gtk.Align.FILL, spacing=7)

        # Open Profiles List Window
        self.btn_open_profile_chooser = Gtk.Button(
            child=Gtk.Image(icon_name="list-add-symbolic")
        )
        self.btn_open_profile_chooser.connect(
            "clicked", self.on_btn_open_profile_chooser_clicked
        )

        # Current Profile Selection Combobox
        self.cmb_current_profile = Gtk.ComboBoxText(hexpand=True)
        self.setup_profiles_combobox(self.cmb_current_profile)

        profile = (
            self.profile_manager.get_current_profile()
            if ETAKisitActivator.is_service_active()
            else self.profile_manager.get_profile(
                self.cmb_current_profile.get_active_text()
            )
        )

        box_profiles.add(self.btn_open_profile_chooser)
        box_profiles.add(self.cmb_current_profile)
        box.add(box_profiles)

        # Profile Preferences
        btn_show_preferences = Gtk.Button(
            label="Ayar Tercihleri", hexpand=True, halign="fill"
        )
        btn_show_preferences.connect("clicked", self.on_btn_show_preferences_clicked)

        box.add(btn_show_preferences)

        box.add(Gtk.Separator(orientation="vertical"))

        # Applied profile label
        self.lbl_activated_profile = Gtk.Label("")
        box.add(self.lbl_activated_profile)

        # Status Headers
        box_status_headers = Gtk.Box(orientation="horizontal", homogeneous=True)
        self.lbl_application_filter_header = Gtk.Label(label="Uygulama Filtresi")
        self.lbl_website_filter_header = Gtk.Label(label="İnternet Filtresi")
        box_status_headers.add(self.lbl_application_filter_header)
        box_status_headers.add(self.lbl_website_filter_header)
        box.add(box_status_headers)

        # Status
        frame_status = Gtk.Frame()
        frame_box = Gtk.Box(orientation="horizontal", margin=7, spacing=7)

        # Application Status
        self.box_application_status = Gtk.Box(orientation="vertical", hexpand=True)

        application_restriction_type = profile.get_application_restriction_type()
        self.radio_application_allowlist = Gtk.RadioButton(
            label="İzinliler Listesi",
        )
        self.radio_application_none = Gtk.RadioButton(
            group=self.radio_application_allowlist,
            label="Kapalı",
        )
        self.radio_application_denylist = Gtk.RadioButton(
            group=self.radio_application_allowlist,
            label="Kısıtlılar Listesi",
        )
        self.radio_application_allowlist.set_active(
            application_restriction_type == "allowlist"
        )
        self.radio_application_none.set_active(application_restriction_type == "none")
        self.radio_application_denylist.set_active(
            application_restriction_type == "denylist"
        )

        self.radio_application_allowlist.connect(
            "toggled",
            self.on_restriction_type_changed,
            True,
            "allowlist",
        )
        self.radio_application_none.connect(
            "toggled",
            self.on_restriction_type_changed,
            True,
            "none",
        )
        self.radio_application_denylist.connect(
            "toggled",
            self.on_restriction_type_changed,
            True,
            "denylist",
        )

        self.box_application_status.add(self.radio_application_allowlist)
        self.box_application_status.add(self.radio_application_none)
        self.box_application_status.add(self.radio_application_denylist)

        # Website status
        self.box_website_status = Gtk.Box(orientation="vertical", hexpand=True)
        website_restriction_type = profile.get_website_restriction_type()
        self.radio_website_allowlist = Gtk.RadioButton(
            label="İzinliler Listesi",
        )
        self.radio_website_none = Gtk.RadioButton(
            group=self.radio_website_allowlist,
            label="Kapalı",
        )
        self.radio_website_denylist = Gtk.RadioButton(
            group=self.radio_website_allowlist,
            label="Kısıtlılar Listesi",
        )
        self.radio_website_allowlist.set_active(website_restriction_type == "allowlist")
        self.radio_website_none.set_active(website_restriction_type == "none")
        self.radio_website_denylist.set_active(website_restriction_type == "denylist")

        self.radio_website_allowlist.connect(
            "toggled",
            self.on_restriction_type_changed,
            False,
            "allowlist",
        )
        self.radio_website_none.connect(
            "toggled",
            self.on_restriction_type_changed,
            False,
            "none",
        )
        self.radio_website_denylist.connect(
            "toggled",
            self.on_restriction_type_changed,
            False,
            "denylist",
        )

        self.box_website_status.add(self.radio_website_allowlist)
        self.box_website_status.add(self.radio_website_none)
        self.box_website_status.add(self.radio_website_denylist)

        frame_box.add(self.box_application_status)
        frame_box.add(Gtk.Separator(orientation="vertical"))
        frame_box.add(self.box_website_status)
        frame_status.add(frame_box)
        box.add(frame_status)

        # Activate on startup checkbox
        self.stack_startup_checkbox = Gtk.Stack()

        self.btn_activate_on_startup = Gtk.CheckButton(
            active=profile.get_activate_on_startup(),
            label="Hesabıma girdiğimde otomatik etkinleştir",
            tooltip_text="Örneğin 'ogretmen123' kullanıcısı oturum açtığında 'ogretmen123' ismindeki ayar otomatik etkinleştirilir.",
        )
        self.btn_activate_on_startup.connect(
            "toggled", self.on_btn_activate_on_startup_toggled
        )

        self.stack_startup_checkbox.add_named(Gtk.Box(), "empty")
        self.stack_startup_checkbox.add_named(self.btn_activate_on_startup, "checkbox")
        box.add(self.stack_startup_checkbox)

        # Service Activate Button
        self.btn_service_activate = Gtk.Button(
            halign="center", label="Etkinleştir", margin_bottom=21
        )
        self.btn_service_activate.get_style_context().add_class("suggested-action")
        self.btn_service_activate.connect(
            "clicked", self.on_btn_service_activate_clicked
        )
        box.add(self.btn_service_activate)

        # Copyright
        mainbox.add(box)
        mainbox.add(
            Gtk.Label(
                label="© TÜBİTAK BİLGEM",
                valign="end",
                margin_bottom=7,
            )
        )
        self.add(mainbox)

    def setup_dialogs(self):
        profile = self.profile_manager.get_profile(
            self.cmb_current_profile.get_active_text()
        )
        self.win_preferences = PreferencesWindow(profile, self.profile_manager, self)
        self.win_profiles = ProfileChooserWindow(
            self.profile_manager, self, self.cmb_current_profile
        )

        self.about_dialog = Gtk.AboutDialog(
            program_name="ETA Sınırlı Erişim",
            version=version.VERSION,
            website="https://pardus.org.tr",
            copyright="© 2025 Pardus",
            comments="Uygulama ve İnternet Sitelerine erişimi kısıtlayın.",
            logo_icon_name="eta-kisit",
            authors=["Pardus Geliştiricileri <gelistirici@pardus.org.tr>"],
        )

    def setup_file_monitor(self):
        # Monitor Applied profile file
        f = Gio.File.new_for_path(ProfileManager.APPLIED_PROFILE_PATH)
        self.applied_profile_monitor = f.monitor_file(Gio.FileMonitorFlags.NONE, None)
        self.applied_profile_monitor.connect(
            "changed", self.on_applied_profile_file_changed
        )

    def setup_profiles_combobox(self, combobox):
        combobox.set_size_request(240, 42)

        current_profile_index = 0
        i = 0

        # Append default profiles managed by the system
        for profile_name in self.profile_manager.get_profile_list():
            if self.profile_manager.get_profile(profile_name).get_is_default():
                combobox.append_text(profile_name)

                if profile_name == self.profile_manager.get_current_profile_name():
                    current_profile_index = i

                i += 1

        # Add non default profiles
        for profile_name in self.profile_manager.get_profile_list():
            if not self.profile_manager.get_profile(profile_name).get_is_default():
                combobox.append_text(profile_name)

                if profile_name == self.profile_manager.get_current_profile_name():
                    current_profile_index = i

                i += 1

        combobox.set_active(current_profile_index)
        combobox.connect("changed", self.on_combobox_profile_changed)

    def setup_ui(self):
        self.setup_main_page()

        self.set_widget_styles()

    # === FUNCTIONS ===
    def start_service(self):
        if ETAKisitActivator.is_service_active():
            return

        if self.is_no_restriction_selected():
            Dialogs.info(
                "Şu anda iki filtre de Kapalı durumda. Lütfen en az bir liste seçiniz ve tekrar deneyiniz."
            )
            return

        # Activate
        process = ETAKisitActivator.run_activator(["--restrict"])

        if process.returncode != 0:
            print(process.stderr.decode())
            Dialogs.info(
                "Bir hata oluştu:\n{}".format(process.stderr.decode()),
                Gtk.MessageType.ERROR,
            )
        else:
            NotificationManager.send_notification("Sınırlı Erişim Etkin")

        print(process.stdout.decode())

        self.set_widget_styles()

    def stop_service(self):
        if not ETAKisitActivator.is_service_active():
            return

        # Deactivate
        process = ETAKisitActivator.run_activator(["--unrestrict"])

        if process.returncode != 0:
            Dialogs.info(
                "Bir hata oluştu:\n{}".format(process.stderr.decode()),
                Gtk.MessageType.ERROR,
            )
        else:
            NotificationManager.send_notification("Sınırlı Erişim Devre Dışı")

        print(process.stdout.decode())

        self.set_widget_styles()

    def is_no_restriction_selected(self):
        profile_name = self.cmb_current_profile.get_active_text()
        profile = self.profile_manager.get_profile(profile_name)

        if (
            profile.get_application_restriction_type() == "none"
            and profile.get_website_restriction_type() == "none"
        ):
            return True
        return False

    def set_widget_styles(self):
        if ETAKisitActivator.is_service_active():
            # can't change profile if one is active
            self.cmb_current_profile.set_sensitive(False)
            self.btn_open_profile_chooser.set_sensitive(False)

            profile_name = self.profile_manager.get_current_profile_name()
            profile = self.profile_manager.get_current_profile()

            self.lbl_activated_profile.set_markup(
                "Etkin Ayar: <b>{}</b>".format(profile_name)
            )
            self.btn_service_activate.set_label("Devre Dışı Bırak")
            self.img_logo.set_name("floating_logo")

            # Status Box
            if profile.get_application_restriction_type() != "none":
                self.lbl_application_filter_header.set_name("success")
                self.lbl_application_filter_header.set_label("Uygulama Filtresi Etkin")

            if profile.get_website_restriction_type() != "none":
                self.lbl_website_filter_header.set_name("success")
                self.lbl_website_filter_header.set_label("İnternet Filtresi Etkin")

            self.box_application_status.set_sensitive(False)
            self.box_website_status.set_sensitive(False)
            self.btn_activate_on_startup.set_sensitive(False)
        else:
            self.cmb_current_profile.set_sensitive(True)
            self.btn_open_profile_chooser.set_sensitive(True)

            self.lbl_activated_profile.set_label("")
            self.btn_service_activate.set_label("Etkinleştir")
            self.img_logo.set_name("logo")

            # Status Box
            self.lbl_application_filter_header.set_name("")
            self.lbl_application_filter_header.set_label("Uygulama Filtresi")

            self.lbl_website_filter_header.set_name("")
            self.lbl_website_filter_header.set_label("İnternet Filtresi")

            self.box_application_status.set_sensitive(True)
            self.box_website_status.set_sensitive(True)
            self.btn_activate_on_startup.set_sensitive(True)

    # === CALLBACKS ===
    # == Main Window
    def on_destroy(self, btn):
        self.window.get_application().quit()

    def on_btn_open_profile_chooser_clicked(self, btn):
        self.win_profiles.show_all()

    def on_btn_show_preferences_clicked(self, btn):
        profile_name = self.cmb_current_profile.get_active_text()

        self.win_preferences.show_ui(
            profile_name, ETAKisitActivator.is_service_active()
        )

    def on_btn_service_activate_clicked(self, btn):
        if ETAKisitActivator.is_service_active():
            result = Dialogs.ok_cancel(
                "Kapat?",
                "Etkinleştirdiğiniz filtreler kaldırılacak ve öğrenciler tahtayı filtresiz olarak kullanacaklar. Emin misiniz?",
            )

            if result == Gtk.ResponseType.OK:
                # Refresh UI
                self.on_combobox_profile_changed(self.cmb_current_profile)
                self.stop_service()
        else:
            if self.is_no_restriction_selected():
                Dialogs.info(
                    "Şu anda iki filtre de Kapalı durumda. Lütfen en az bir liste seçiniz ve tekrar deneyiniz."
                )
                return

            result = Dialogs.ok_cancel(
                "Etkinleştir?",
                "Etkinleştirdiğiniz filtreler devreye alınacak ve öğrencileriniz tahtayı izin verdiğiniz ölçüde kullanabilecekler. Emin misiniz?",
            )

            if result == Gtk.ResponseType.OK:
                self.on_combobox_profile_changed(self.cmb_current_profile)
                self.profile_manager.set_current_profile(
                    self.cmb_current_profile.get_active_text()
                )
                self.start_service()

                result = Dialogs.with_custom_buttons(
                    "Sınırlı Erişim oturumuna geç?",
                    'Başarıyla aktifleştirildi. Sınırlı Erişim oturumuna geçmek için "Şimdi" butonuna, geçişi daha sonra oturum seçme ekranından yapmak için ise "Daha Sonra" butonuna tıklayınız.',
                    [
                        ("Daha Sonra", Gtk.ResponseType.CANCEL),
                        ("Şimdi", Gtk.ResponseType.OK),
                    ],
                )

                if result == Gtk.ResponseType.OK:
                    LinuxUserManager.switch_user_session("ogrenci")

    def on_combobox_profile_changed(self, combobox):
        selected_profile_name = combobox.get_active_text()

        # Change Filter Selection of radio buttons
        profile = self.profile_manager.get_profile(selected_profile_name)

        application_restriction_type = profile.get_application_restriction_type()
        website_restriction_type = profile.get_website_restriction_type()

        # Update Activate on startup checkbutton
        profile_owner = (
            profile.created_by if profile.created_by else selected_profile_name
        )
        current_user = LinuxUserManager.get_logged_username()
        # print("on_combobox_profile_changed, profile_owner:", profile_owner, "current:", current_user)
        if profile_owner == current_user:
            self.stack_startup_checkbox.set_visible_child_name("checkbox")
        else:
            self.stack_startup_checkbox.set_visible_child_name("empty")

        self.btn_activate_on_startup.set_active(profile.get_activate_on_startup())

        if application_restriction_type == "allowlist":
            self.radio_application_allowlist.set_active(True)
        elif application_restriction_type == "denylist":
            self.radio_application_denylist.set_active(True)
        else:
            self.radio_application_none.set_active(True)

        if website_restriction_type == "allowlist":
            self.radio_website_allowlist.set_active(True)
        elif website_restriction_type == "denylist":
            self.radio_website_denylist.set_active(True)
        else:
            self.radio_website_none.set_active(True)

        # Fill Preferences Window
        self.win_preferences.fill_lists_from_profile(profile)

    def on_restriction_type_changed(self, btn, is_application, restriction_type):
        if btn.get_active():
            profile_name = self.cmb_current_profile.get_active_text()
            profile = self.profile_manager.get_profile(profile_name)
            if is_application:
                profile.set_application_restriction_type(restriction_type)
            else:
                profile.set_website_restriction_type(restriction_type)

            self.profile_manager.save_as_json_file()

    def on_btn_activate_on_startup_toggled(self, btn):
        profile_name = self.cmb_current_profile.get_active_text()
        profile = self.profile_manager.get_profile(profile_name)

        profile.set_activate_on_startup(btn.get_active())

        self.profile_manager.save_as_json_file()

    def on_applied_profile_file_changed(self, _monitor, file, _other_file, event):
        if event in [
            Gio.FileMonitorEvent.CHANGES_DONE_HINT,
            Gio.FileMonitorEvent.DELETED,
        ]:
            self.profile_manager.load_profiles()
            self.set_widget_styles()

    def on_btn_about_dialog_clicked(self, btn):
        self.about_dialog.run()
        self.about_dialog.hide()
