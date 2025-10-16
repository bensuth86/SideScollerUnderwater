# pickup_config.py
from pathlib import Path

PICKUP_CATGRY = {
    "stamina": (lambda player: setattr(player, 'stamina', player.stamina + 50)),
    "mortarstrike": (lambda player: setattr(player, 'mortarstrike', player.mortarstrike + 1)),
    "machete": (lambda player: setattr(player, 'machete', True)),
    "medikit": (lambda player: setattr(player, 'hitpoints', player.hitpoints + 50)),
    "torpedolauncher": (lambda player: player.weaponstate.update({'torpedo': True})),
    "torpedos": (lambda player: player.ammo.update({key: value + 5 for key, value in player.ammo.items()})),
    "plasmagun": (lambda player: setattr(player, 'plasmagun', True)),
    "plasmaammo": (lambda player: setattr(player, 'plasmaammo', player.plasmaammo + 200)),
    "bubbleorb": (lambda player: setattr(player, 'hitpoints', player.hitpoints + 5)),
    "flashlight": (lambda player: setattr(player, 'flashlight', True)),
    "baitdecoy": (lambda player: setattr(player, 'baitdecoy', player.baitdecoy + 5)),
}

# Pickups to add

# biomask
# doorkey
# respawnpoint
