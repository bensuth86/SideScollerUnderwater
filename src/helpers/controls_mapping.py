def _map_keyboard_controls(pygame, keyboard_cfg):
    """Convert K_* strings into pygame key constants."""
    mapped = {}
    for category, mapping in keyboard_cfg.items():
        mapped[category] = {
            action: getattr(pygame, keyname)
            for action, keyname in mapping.items()
        }
    return mapped


def _map_mouse_controls(pygame, mouse_cfg):
    """Convert mouse button names into button IDs."""
    button_map = {
        "MOUSE_LEFT": 0,
        "MOUSE_MIDDLE": 1,
        "MOUSE_RIGHT": 2,
        "MOUSE_WHEEL_UP": 4,
        "MOUSE_WHEEL_DOWN": 5
    }

    mapped_buttons = {}
    for action, name in mouse_cfg.get("buttons", {}).items():
        mapped_buttons[action] = button_map.get(name, None)

    return {
        "buttons": mapped_buttons,
        "settings": mouse_cfg.get("settings", {})
    }