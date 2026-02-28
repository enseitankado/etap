from ui_gtk3 import PActionRow
from managers.ProfileManager import ProfileManager, Profile, ADMIN_USERNAME
from managers import LinuxUserManager

from ui_gtk3.Dialogs import InputDialog
from ui_gtk3.ApplicationChooserWindow import ApplicationChooserWindow
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, GLib, GObject  # noqa

WEBSITE_REGEX = r"^([\w-]+)\.(\w[\w.-]*[a-zA-Z])$"  # domain control regex


class StringItem(GObject.GObject):
    text = GObject.property(type=str)

    def __init__(self, text):
        GObject.GObject.__init__(self)
        self.text = text


class PreferencesWindow(Gtk.Window):
    def __init__(
        self, profile: Profile, profile_manager: ProfileManager, parent_window
    ):
        super().__init__(
            transient_for=parent_window,
            modal=True,
            window_position=Gtk.WindowPosition.CENTER_ON_PARENT,
        )

        self.profile = profile
        self.profile_manager = profile_manager

        self.logged_username = LinuxUserManager.get_logged_username()

        self.setup_window()

        self.setup_ui()

        self.setup_dialogs()

    def show_ui(self, profile_name, is_service_activated):
        profile = self.profile_manager.get_profile(profile_name)
        self.profile = profile

        is_profile_default = profile.get_is_default()

        # Fill lists
        self.fill_lists_from_profile(profile)

        self.show_all()

        # Visible Child set:
        if profile.get_application_restriction_type() == "allowlist":
            self.stack_application_list.set_visible_child_name("allowlist")
            self.radio_application_allow.set_active(True)
        elif profile.get_application_restriction_type() == "denylist":
            self.stack_application_list.set_visible_child_name("denylist")
            self.radio_application_deny.set_active(True)

        if profile.get_website_restriction_type() == "allowlist":
            self.stack_website_list.set_visible_child_name("allowlist")
            self.radio_website_allow.set_active(True)
        elif profile.get_website_restriction_type() == "denylist":
            self.stack_website_list.set_visible_child_name("denylist")
            self.radio_website_deny.set_active(True)

        # If service enabled, disable sensitivity
        is_editable = (
            profile_name == self.logged_username
            or ADMIN_USERNAME == self.logged_username
            or profile.get_created_by() == self.logged_username
        )
        is_sensitive = (
            not is_service_activated and not is_profile_default
        ) and is_editable
        self.stack.set_sensitive(is_sensitive)

        if is_service_activated:
            self.lbl_information_message.set_markup(
                "<b>Ayar etkin iken ayar tercihleri değiştirilemez.</b>"
            )
        elif is_profile_default:
            self.lbl_information_message.set_markup(
                "<b>Bu ayar kuruluşunuz tarafından uzaktan yönetilmektedir ve tercihleri değiştirilemez.</b>"
            )
        elif not is_editable:
            self.lbl_information_message.set_markup(
                "<b>Diğer kullanıcıların ayarları değiştirilemez.</b>"
            )
        else:
            self.lbl_information_message.set_text("")

    # Setups
    def setup_window(self):
        self.set_default_size(800, 600)
        self.set_title("Ayar Tercihleri")
        self.connect("delete-event", self.on_window_delete)

    def setup_dialogs(self):
        self.win_app_chooser = ApplicationChooserWindow(self)

    def setup_applications_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)

        profile = self.profile
        application_restriction_type = profile.get_application_restriction_type()

        # Filter Choice
        box_radio = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Allow / Deny toggle button
        self.radio_application_allow = Gtk.RadioButton(
            label="İzinliler Listesi",
        )
        self.radio_application_deny = Gtk.RadioButton(
            group=self.radio_application_allow,
            label="Kısıtlılar Listesi",
        )
        self.radio_application_allow.set_active(
            application_restriction_type == "allowlist"
        )
        self.radio_application_deny.set_active(
            application_restriction_type == "denylist"
        )

        # Allowlist Denylist stack
        self.stack_application_list = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT,
        )

        self.radio_application_allow.connect(
            "toggled",
            self.on_allow_deny_list_changed,
            True,
            True,
            self.stack_application_list,
        )
        self.radio_application_deny.connect(
            "toggled",
            self.on_allow_deny_list_changed,
            False,
            True,
            self.stack_application_list,
        )

        box_radio.add(self.radio_application_allow)
        box_radio.add(self.radio_application_deny)
        box.add(box_radio)

        box.add(Gtk.Separator())

        # Allowlist
        box_allowlist = Gtk.Box(
            orientation="vertical", hexpand=True, vexpand=True, spacing=7
        )

        box_allowlist.add(Gtk.Label(label="İzin Verilecek Uygulamalar Listesi"))

        # Add new Application to Allowlist button
        self.btn_add_application_allowlist = Gtk.Button()
        self.btn_add_application_allowlist.add(Gtk.Image(icon_name="list-add-symbolic"))
        self.btn_add_application_allowlist.get_style_context().add_class(
            "suggested-action"
        )
        self.btn_add_application_allowlist.connect(
            "clicked", self.on_btn_add_application_allowlist_clicked
        )

        box_allowlist.add(self.btn_add_application_allowlist)

        # Allowlist Application ListBox
        self.listbox_applications_allowlist = Gtk.ListBox()
        scrolledwindow = Gtk.ScrolledWindow(min_content_height=400)
        frame = Gtk.Frame()
        frame.add(self.listbox_applications_allowlist)
        scrolledwindow.add(frame)
        box_allowlist.add(scrolledwindow)

        # Denylist
        box_denylist = Gtk.Box(
            orientation="vertical", hexpand=True, vexpand=True, spacing=7
        )

        box_denylist.add(Gtk.Label(label="Kısıtlanacak Uygulamalar Listesi"))

        # Add new Application to Denylist button
        self.btn_add_application_denylist = Gtk.Button()
        self.btn_add_application_denylist.add(Gtk.Image(icon_name="list-add-symbolic"))
        self.btn_add_application_denylist.get_style_context().add_class(
            "suggested-action"
        )
        self.btn_add_application_denylist.connect(
            "clicked", self.on_btn_add_application_denylist_clicked
        )

        box_denylist.add(self.btn_add_application_denylist)

        # Denylist Application ListBox
        self.listbox_applications_denylist = Gtk.ListBox()
        scrolledwindow = Gtk.ScrolledWindow(min_content_height=400)
        frame = Gtk.Frame()
        frame.add(self.listbox_applications_denylist)
        scrolledwindow.add(frame)
        box_denylist.add(scrolledwindow)

        # Add Allowlist Denylist Stack
        self.stack_application_list.add_titled(
            box_allowlist, "allowlist", "İzin Verilenler"
        )
        self.stack_application_list.add_titled(box_denylist, "denylist", "Kısıtlılar")
        box.add(self.stack_application_list)

        self.page_applications = box

    def setup_websites_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)

        profile = self.profile
        website_restriction_type = profile.get_website_restriction_type()

        # Allow / Deny toggle button
        box_radio = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.radio_website_allow = Gtk.RadioButton(label="İzinliler Listesi")
        self.radio_website_deny = Gtk.RadioButton(
            group=self.radio_website_allow, label="Kısıtlılar Listesi"
        )
        self.radio_website_allow.set_active(website_restriction_type == "allowlist")
        self.radio_website_deny.set_active(website_restriction_type == "denylist")

        # Allowlist Denylist stack
        self.stack_website_list = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT
        )

        self.radio_website_allow.connect(
            "toggled",
            self.on_allow_deny_list_changed,
            True,
            False,
            self.stack_website_list,
        )
        self.radio_website_deny.connect(
            "toggled",
            self.on_allow_deny_list_changed,
            False,
            False,
            self.stack_website_list,
        )

        box_radio.add(self.radio_website_allow)
        box_radio.add(self.radio_website_deny)
        box.add(box_radio)

        box.add(Gtk.Separator())

        # Allowlist
        box_allowlist = Gtk.Box(
            orientation="vertical", hexpand=True, vexpand=True, spacing=7
        )

        box_allowlist.add(Gtk.Label(label="İzin Verilecek İnternet Siteleri Listesi"))

        # Add new Website to Allowlist button
        self.btn_add_website_allowlist = Gtk.Button()
        self.btn_add_website_allowlist.add(Gtk.Image(icon_name="list-add-symbolic"))
        self.btn_add_website_allowlist.get_style_context().add_class("suggested-action")
        self.btn_add_website_allowlist.connect(
            "clicked", self.on_btn_add_website_allowlist_clicked
        )

        box_allowlist.add(self.btn_add_website_allowlist)

        # Allowlist Website ListBox
        self.listbox_websites_allowlist = Gtk.ListBox()
        scrolledwindow = Gtk.ScrolledWindow(min_content_height=400)
        frame = Gtk.Frame()
        frame.add(self.listbox_websites_allowlist)
        scrolledwindow.add(frame)
        box_allowlist.add(scrolledwindow)

        # Denylist
        box_denylist = Gtk.Box(
            orientation="vertical", hexpand=True, vexpand=True, spacing=7
        )

        box_denylist.add(Gtk.Label(label="Kısıtlanacak İnternet Siteleri Listesi"))

        # Add new Website to Denylist button
        self.btn_add_website_denylist = Gtk.Button()
        self.btn_add_website_denylist.add(Gtk.Image(icon_name="list-add-symbolic"))
        self.btn_add_website_denylist.get_style_context().add_class("suggested-action")
        self.btn_add_website_denylist.connect(
            "clicked", self.on_btn_add_website_denylist_clicked
        )

        box_denylist.add(self.btn_add_website_denylist)

        # Denylist Website ListBox
        self.listbox_websites_denylist = Gtk.ListBox()
        scrolledwindow = Gtk.ScrolledWindow(min_content_height=400)
        frame = Gtk.Frame()
        frame.add(self.listbox_websites_denylist)
        scrolledwindow.add(frame)
        box_denylist.add(scrolledwindow)

        # Add Allowlist Denylist Stack
        self.stack_website_list.add_titled(
            box_allowlist, "allowlist", "İzin Verilenler"
        )
        self.stack_website_list.add_titled(box_denylist, "denylist", "Kısıtlılar")
        box.add(self.stack_website_list)

        self.page_websites = box

    def setup_ui(self):
        self.stack = Gtk.Stack(
            vexpand=True, transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT
        )

        # Applications
        self.setup_applications_page()

        # Websites
        self.setup_websites_page()

        # Add Pages
        self.stack.add_titled(
            self.page_applications, "page_applications", "Uygulamalar"
        )
        self.stack.add_titled(self.page_websites, "page_websites", "İnternet Siteleri")

        # Fill groups
        self.fill_lists_from_profile(self.profile)

        stack_switcher = Gtk.StackSwitcher(stack=self.stack, halign="center")
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=7,
            margin=27,
            margin_top=7,
        )
        box.add(stack_switcher)
        box.add(self.stack)
        self.lbl_information_message = Gtk.Label(label="")
        box.add(self.lbl_information_message)

        btn_okay = Gtk.Button(label="Tamam")
        btn_okay.connect("clicked", self.on_btn_okay_clicked)
        btn_okay.get_style_context().add_class("suggested-action")
        box.add(btn_okay)

        self.add(box)

    # Functions
    def fill_applications_listbox(self, allowlist, denylist, is_profile_default=False):
        self.listmodel_applications_allowlist = Gio.ListStore()
        self.listmodel_applications_denylist = Gio.ListStore()

        for i in allowlist:
            self.listmodel_applications_allowlist.append(StringItem(i))

        for i in denylist:
            self.listmodel_applications_denylist.append(StringItem(i))

        def create_row(item, listmodel, is_model_allowlist):
            try:
                if item.text.startswith("/"):
                    app_info = Gio.DesktopAppInfo.new_from_filename(item.text)
                else:
                    app_info = Gio.DesktopAppInfo.new(item.text)

                return PActionRow.new(
                    title=app_info.get_name(),
                    subtitle=app_info.get_id(),
                    gicon=app_info.get_icon(),
                    on_deleted=None
                    if is_profile_default
                    else self.on_btn_delete_row_clicked,
                    user_data=app_info,
                    parent_listmodel=listmodel,
                    is_model_allowlist=is_model_allowlist,
                )
            except TypeError:
                return PActionRow.new(
                    title=item.text,
                    subtitle="APPLICATION NOT FOUND",
                    on_deleted=self.on_btn_delete_row_clicked,
                    parent_listmodel=listmodel,
                    is_model_allowlist=is_model_allowlist,
                )

        self.listbox_applications_allowlist.bind_model(
            self.listmodel_applications_allowlist,
            create_row,
            self.listmodel_applications_allowlist,
            True,
        )
        self.listbox_applications_denylist.bind_model(
            self.listmodel_applications_denylist,
            create_row,
            self.listmodel_applications_denylist,
            False,
        )

    def fill_websites_listbox(self, allowlist, denylist, is_profile_default=False):
        self.listmodel_websites_allowlist = Gio.ListStore()
        self.listmodel_websites_denylist = Gio.ListStore()

        for i in allowlist:
            self.listmodel_websites_allowlist.append(StringItem(i))

        for i in denylist:
            self.listmodel_websites_denylist.append(StringItem(i))

        def create_row(item, listmodel, is_model_allowlist):
            return PActionRow.new(
                title=item.text,
                on_deleted=None
                if is_profile_default
                else self.on_btn_delete_row_clicked,
                parent_listmodel=listmodel,
                is_model_allowlist=is_model_allowlist,
            )

        self.listbox_websites_allowlist.bind_model(
            self.listmodel_websites_allowlist,
            create_row,
            self.listmodel_websites_allowlist,
            True,
        )
        self.listbox_websites_denylist.bind_model(
            self.listmodel_websites_denylist,
            create_row,
            self.listmodel_websites_denylist,
            False,
        )

    def fill_lists_from_profile(self, profile: Profile):
        is_profile_default = profile.get_is_default()

        # Set button values
        self.radio_application_allow.set_active(
            profile.get_is_application_list_allowlist()
        )
        self.radio_website_allow.set_active(profile.get_is_website_list_allowlist())

        # Fill Applications
        self.fill_applications_listbox(
            profile.get_application_allowlist(),
            profile.get_application_denylist(),
            is_profile_default,
        )

        # Fill Websites
        self.fill_websites_listbox(
            profile.get_website_allowlist(),
            profile.get_website_denylist(),
            is_profile_default,
        )

    # == CALLBACKS ==
    def on_window_delete(self, win, event):
        # Don't delete window on close, just hide.
        self.hide()
        return True

    # New Items
    def on_btn_add_application_allowlist_clicked(self, btn):
        self.win_app_chooser.show_ui(self.on_application_selected_in_dialog_allowlist)

    def on_btn_add_application_denylist_clicked(self, btn):
        self.win_app_chooser.show_ui(self.on_application_selected_in_dialog_denylist)

    def on_btn_add_website_allowlist_clicked(self, btn):
        input_dialog = InputDialog(
            self,
            "",
            """Lütfen başına www, https vb. yazmadan bir alan adı giriniz (örneğin: google.com)

Alt alan adları geçersizdir (örneğin eba.gov.tr/trt-ebatv)""",
            self.on_new_website_entered_allowlist,
            WEBSITE_REGEX,
            "Ekle",
        )
        input_dialog.show_all()

    def on_btn_add_website_denylist_clicked(self, btn):
        input_dialog = InputDialog(
            self,
            "",
            """Lütfen başına www, https vb. yazmadan bir alan adı giriniz (örneğin: google.com)

Alt alan adları geçersizdir (örneğin eba.gov.tr/trt-ebatv)""",
            self.on_new_website_entered_denylist,
            WEBSITE_REGEX,
            "Ekle",
        )
        input_dialog.show_all()

    def on_btn_delete_row_clicked(
        self, btn, action_row, user_data, parent_listmodel, is_model_allowlist
    ):
        profile = self.profile

        is_app_instance = isinstance(user_data, Gio.DesktopAppInfo)
        is_app = isinstance(user_data, Gio.DesktopAppInfo)

        # Removed applications is not Gio.DesktopAppInfo but ends with .desktop at title
        if ".desktop" in action_row.title:
            is_app = True

        # Get filename and app_id
        if is_app:
            if is_app_instance:
                filename = user_data.get_filename()
                app_id = user_data.get_id()
            else:
                filename = action_row.title
                app_id = ""

        # Remove from profiles.json
        if is_app:
            if is_model_allowlist:
                profile.remove_application_allowlist(filename)
                profile.remove_application_allowlist(app_id)
            else:
                profile.remove_application_denylist(filename)
                profile.remove_application_denylist(app_id)
        else:
            if is_model_allowlist:
                profile.remove_website_allowlist(action_row.title)
            else:
                profile.remove_website_denylist(action_row.title)

        # then remove from listbox
        if is_app:
            for i, item in enumerate(parent_listmodel):
                if item.text == filename or item.text == app_id:
                    parent_listmodel.remove(i)
                    break
        else:
            for i, item in enumerate(parent_listmodel):
                if item.text == action_row.title:
                    parent_listmodel.remove(i)
                    break

        self.profile_manager.save_as_json_file()

    def on_application_selected_in_dialog_allowlist(self, app):
        if not isinstance(app, Gio.DesktopAppInfo):
            return

        profile = self.profile
        print(app.get_filename(), app.get_id())

        if profile.insert_application_allowlist(app.get_id()):
            self.listmodel_applications_allowlist.append(StringItem(app.get_id()))
            self.listbox_applications_allowlist.show_all()

        self.profile_manager.save_as_json_file()

    def on_application_selected_in_dialog_denylist(self, app):
        if not isinstance(app, Gio.DesktopAppInfo):
            return

        profile = self.profile
        print(app.get_filename(), app.get_id())

        if profile.insert_application_denylist(app.get_id()):
            self.listmodel_applications_denylist.append(StringItem(app.get_id()))
            self.listbox_applications_denylist.show_all()

        self.profile_manager.save_as_json_file()

    def on_new_website_entered_allowlist(self, domain):
        profile = self.profile

        if profile.insert_website_allowlist(domain):
            self.listmodel_websites_allowlist.append(StringItem(domain))
            self.listbox_websites_allowlist.show_all()

        self.profile_manager.save_as_json_file()

    def on_new_website_entered_denylist(self, domain):
        profile = self.profile

        if profile.insert_website_denylist(domain):
            self.listmodel_websites_denylist.append(StringItem(domain))
            self.listbox_websites_denylist.show_all()

        self.profile_manager.save_as_json_file()

    # Allow / Deny List choice
    def on_allow_deny_list_changed(self, btn, is_allowlist_btn, is_application, stack):
        if btn.get_active():
            stack.set_visible_child_name(
                "allowlist" if is_allowlist_btn else "denylist"
            )

    def on_btn_okay_clicked(self, btn):
        self.close()
