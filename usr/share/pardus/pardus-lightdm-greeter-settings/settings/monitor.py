# General
_("Display")
self.settings["monitor"].set_data("mirror", {
    "label": _("Mirror monitors"),
    "value": config.get("mirror", "true", "screen"),
})
monitors = util.list_monitors()
self.settings["monitor"].set_data("default-monitor-name", {
    "label": _("Default monitor"),
    "options": monitors,
    "value": config.get("default-monitor-name", monitors[0] if len(monitors) > 0 else "", "screen")
})

settings = self.settings


def mirror_state_event(widget, state):
    global settings
    settings["monitor"].widgets["default-monitor-name"].set_sensitive(
        not state)


state = config.get("mirror", "true", "screen").lower() == "true"
settings["monitor"].widgets["default-monitor-name"].set_sensitive(not state)
self.settings["monitor"].widgets["mirror"].state_event = mirror_state_event
