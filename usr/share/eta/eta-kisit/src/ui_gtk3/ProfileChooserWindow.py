from ui_gtk3 import PActionRow
from ui_gtk3.Dialogs import InputDialog
from managers.ProfileManager import ProfileManager, ADMIN_USERNAME
from managers import LinuxUserManager
from ui_gtk3 import Dialogs
import random
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio, GLib, GObject  # noqa


class ProfileItem(GObject.GObject):
    text = GObject.Property(type=str)
    is_editable = GObject.Property(type=bool, default=False)

    def __init__(self, text, is_editable=False):
        GObject.GObject.__init__(self)
        self.text = text
        self.is_editable = is_editable


class ProfileChooserWindow(Gtk.Window):
    def __init__(
        self, profile_manager: ProfileManager, parent_window, cmb_current_profile
    ):
        super().__init__(
            transient_for=parent_window,
            modal=True,
            window_position=Gtk.WindowPosition.CENTER_ON_PARENT,
        )

        self.profile_manager = profile_manager
        self.cmb_current_profile = cmb_current_profile
        self.logged_username = LinuxUserManager.get_logged_username()

        self.setup_window()

        self.setup_ui()

        self.selected_profile = self.profile_manager.get_current_profile_name()

    # == SETUP ==
    def setup_window(self):
        self.set_default_size(400, 400)
        self.set_title("Ayar Listesi")
        self.connect("delete-event", self.on_window_delete)

    def setup_ui(self):
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=7,
            margin=14,
        )

        # New Profile button
        hbox1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        btn_new = Gtk.Button.new_from_stock(Gtk.STOCK_ADD)
        btn_new.set_halign(Gtk.Align.END)
        btn_new.set_always_show_image(True)
        btn_new.connect("clicked", self.on_btn_new_clicked)
        hbox1.add(btn_new)

        box.add(hbox1)

        # Profiles ListBox
        self.listmodel_profiles = Gio.ListStore.new(ProfileItem)
        self.listbox_profiles = Gtk.ListBox()
        self.listbox_profiles.bind_model(
            self.listmodel_profiles, self.create_profile_row
        )

        scrolledwindow = Gtk.ScrolledWindow(
            max_content_width=386, min_content_height=240, vexpand=True
        )
        frame = Gtk.Frame()
        frame.add(scrolledwindow)
        scrolledwindow.add(self.listbox_profiles)
        box.add(frame)

        # Ok button
        btn_okay = Gtk.Button(label="Tamam")
        btn_okay.connect("clicked", self.on_btn_okay_clicked)
        btn_okay.get_style_context().add_class("suggested-action")
        box.add(btn_okay)

        # Finish
        self.add(box)

        self.fill_profiles_group()

    # == FUNCTIONS ==
    def create_profile_row(self, item: ProfileItem):
        if item.is_editable:
            return PActionRow.new(
                title=item.text,
                on_deleted=self.on_btn_delete_row_clicked,
                on_edited=self.on_profile_name_changed,
                on_duplicated=self.on_profile_duplicate_clicked,
            )
        else:
            return PActionRow.new(
                title=item.text,
                on_duplicated=self.on_profile_duplicate_clicked,
            )

    def fill_profiles_group(self):
        profile_list = self.profile_manager.get_profile_list().items()

        # First add default profiles
        for profile_name, profile in profile_list:
            if profile.get_is_default():
                self.listmodel_profiles.append(ProfileItem(profile_name, False))

        # Then add normal profiles
        for profile_name, profile in profile_list:
            if not profile.get_is_default():
                is_editable = (
                    self.logged_username == ADMIN_USERNAME
                    or profile_name == self.logged_username
                    or profile.get_created_by() == self.logged_username
                )

                self.listmodel_profiles.append(ProfileItem(profile_name, is_editable))

    # == CALLBACKS ==
    def on_window_delete(self, win, event):
        # Reset all editables to titles
        rows = self.listbox_profiles.get_children()
        for row in rows:
            if hasattr(row, "entry"):
                if row.title != row.entry.get_text():
                    row.entry.set_text(row.title)

        # Don't delete window on close, just hide.
        self.hide()
        return True

    def on_btn_new_clicked(self, btn):
        input_dialog = InputDialog(
            self, "İsim giriniz", "", self.on_new_profile_entered, None, "Yeni Ayar"
        )
        input_dialog.show_all()

    def on_new_profile_entered(self, text):
        new_profile_name = text

        if self.profile_manager.has_profile_name(new_profile_name):
            Dialogs.info(
                "Hata: '{}' ismi zaten mevcut!".format(new_profile_name),
                Gtk.MessageType.ERROR,
            )

        else:
            # New profile created
            self.profile_manager.insert_default_profile(
                new_profile_name, self.logged_username
            )

            # Update profiles in Gtk.ComboBoxText
            self.cmb_current_profile.append_text(new_profile_name)

            # Add Row
            self.listmodel_profiles.append(ProfileItem(new_profile_name, True))

            self.show_all()

            # Dialogs.info("Yeni ayar oluşturuldu: '{}'".format(new_profile_name))

    def on_btn_delete_row_clicked(
        self, btn, action_row, user_data, _parent_listmodel, _is_model_allowlist
    ):
        # Checks
        if len(self.profile_manager.get_profile_list()) == 1:
            Dialogs.info("En az bir ayar olmak zorundadır.")
            return False

        profile_name = action_row.title
        current_profile = self.profile_manager.get_current_profile_name()

        if profile_name == current_profile:
            Dialogs.info("Etkin ayar silinemez.")
            return False

        # Ask user, are you sure?
        result = Dialogs.ok_cancel("'{}' silinecektir.".format(profile_name))
        if result != Gtk.ResponseType.OK:
            return False

        # Remove from ListModel
        for i, item in enumerate(self.listmodel_profiles):
            if item.text == profile_name:
                self.listmodel_profiles.remove(i)
                break

        # Remove from Gtk.ComboBoxText
        for i, row in enumerate(self.cmb_current_profile.get_model()):
            if row[0] == profile_name:
                if self.cmb_current_profile.get_active() == i:
                    self.cmb_current_profile.set_active(0)

                self.cmb_current_profile.remove(i)
                break

        # Remove from profiles.json
        self.profile_manager.remove_profile(profile_name)

        self.show_all()

    def on_profile_name_changed(self, entry, row, user_data):
        new_text = entry.get_text()

        if new_text == "":
            Dialogs.info("Ayar ismi boş olamaz!")
            return False

        old_text = row.title

        if self.profile_manager.has_profile_name(new_text):
            Dialogs.info(
                "Hata: '{}' zaten mevcut!".format(new_text),
                Gtk.MessageType.ERROR,
            )

            return False

        # Update profiles.json
        self.profile_manager.update_profile_name(old_text, new_text)

        # Update Gtk.ComboBoxText
        for modelrow in self.cmb_current_profile.get_model():
            if modelrow[0] == old_text:
                modelrow[0] = new_text
                break

        row.title = new_text

        # If current profile's name changed
        if self.selected_profile == old_text:
            self.selected_profile = new_text
            self.profile_manager.set_current_profile(self.selected_profile)

        # Dialogs.info("Ayar ismi değiştirildi: '{}'".format(new_text))

    def on_profile_duplicate_clicked(self, btn, action_row, user_data):
        profile_name = action_row.title
        new_profile_name = "{}(1)".format(profile_name)

        # Generate random names until find an unused one
        while self.profile_manager.has_profile_name(new_profile_name):
            random_number = random.getrandbits(24)
            new_profile_name = "{}({})".format(profile_name, random_number)

        # New profile create
        self.profile_manager.duplicate_profile(
            profile_name, new_profile_name, self.logged_username
        )

        # Update profiles in Gtk.ComboBoxText
        self.cmb_current_profile.append_text(new_profile_name)

        # Add Row
        self.listmodel_profiles.append(ProfileItem(new_profile_name, True))

        self.show_all()

        # Dialogs.info("Yeni ayar oluşturuldu: '{}'".format(new_profile_name))

    def on_btn_okay_clicked(self, btn):
        # Activate all editable
        rows = self.listbox_profiles.get_children()
        for row in rows:
            if hasattr(row, "entry"):
                if row.title != row.entry.get_text():
                    print("degismis:", row.title, row.entry.get_text())
                    row.entry.activate()

        self.close()
