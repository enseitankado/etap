import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa


def new(
    title,
    subtitle="",
    icon_name="",
    gicon=None,
    on_activated=None,
    on_deleted=None,
    on_edited=None,
    on_duplicated=None,
    user_data=None,
    is_activatable=None,
    parent_listmodel=None,
    is_model_allowlist=None,
):
    row = Gtk.ListBoxRow(
        activatable=True if on_activated or is_activatable else False,
        selectable=False,
    )
    row.user_data = user_data
    row.title = title
    box = Gtk.Box(spacing=0)

    if icon_name:
        box.add(Gtk.Image(icon_name=icon_name, pixel_size=32))
    elif gicon:
        box.add(Gtk.Image(gicon=gicon, pixel_size=32))

    if on_edited:
        box.get_style_context().add_class("linked")

        row.entry = Gtk.Entry(hexpand=True)
        row.entry.set_input_purpose(Gtk.InputPurpose.ALPHA)
        row.entry.set_icon_from_icon_name(
            Gtk.EntryIconPosition.SECONDARY, "document-edit-symbolic"
        )
        row.entry.set_icon_activatable(Gtk.EntryIconPosition.SECONDARY, False)
        row.entry.connect("activate", on_edited, row, user_data)
        row.entry.set_text(title)

        box.add(row.entry)
    else:
        if subtitle:
            label_box = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=3,
                hexpand=True,
                halign="start",
                margin_left=7,
                margin_top=4,
                margin_bottom=3,
            )
            label_box.add(Gtk.Label(label=title, use_markup=False, halign="start"))
            label_subtitle = Gtk.Label(label=subtitle, use_markup=False, halign="start")
            label_subtitle.get_style_context().add_class("dim-label")
            label_box.add(label_subtitle)

            box.add(label_box)
        else:
            box.add(
                Gtk.Label(label=title, use_markup=False, hexpand=True, halign="start")
            )

    if on_activated:
        row.connect("activate", on_activated, user_data)

    if on_duplicated:
        btn_duplicate = Gtk.Button(halign="end")
        btn_duplicate.add(Gtk.Image(icon_name="edit-copy-symbolic"))
        btn_duplicate.connect("clicked", on_duplicated, row, user_data)

        box.add(btn_duplicate)

    if on_deleted:
        btn_delete = Gtk.Button(halign="end")
        btn_delete.add(Gtk.Image(icon_name="user-trash-symbolic"))
        btn_delete.get_style_context().add_class("destructive-action")
        btn_delete.connect(
            "clicked", on_deleted, row, user_data, parent_listmodel, is_model_allowlist
        )

        box.add(btn_delete)

        row.hide_delete_button = lambda: btn_delete.hide()
        row.show_delete_button = lambda: btn_delete.show()

    row.add(box)

    return row
