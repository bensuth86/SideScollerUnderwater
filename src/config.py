# config.py
from pathlib import Path

# Resolve paths relative to project root dir
BASE_DIR = Path.cwd()
IMAGE_PATH = (BASE_DIR / 'assets' / 'Images').resolve()
MAPS_PATH = (BASE_DIR / 'assets' / 'maps').resolve()

SOUNDS_PATH = (BASE_DIR / 'assets' / 'sounds').resolve()
MUSIC_PATH = (BASE_DIR / 'assets' / 'sounds' / 'music').resolve()
AMBIENT_PATH = (BASE_DIR / 'assets' / 'sounds' / 'ambient').resolve()
WEAPONSND_PATH = (BASE_DIR / 'assets' / 'sounds' / 'weaponsnd').resolve()

# SPRITE CONFIG

MOBILE_SPRITE_CLASSES = {
    # 'player': 'src.sprites.Player',
    'harpoon': 'src.sprites.Harpoon',
    'torpedo': 'src.sprites.Torpedo',
    'daddyfish': 'src.sprites.Daddyfish',
    'dartfish': 'src.sprites.Dartfish',
    'spinefish': 'src.sprites.Spinefish',
    'mine': 'src.sprites.Mine'
}


# PICKUP CONFIG

PICKUP_CATGRY = {
    "stamina": (lambda player: setattr(player, 'stamina', player.stamina + 50)),
    "mortarstrike": (lambda player: player.mortarstrike + 1),
    # "biomask": (),
    # "digiclock": (),
    "machete": (lambda player: player.machete is True),
    "medikit": (lambda player: setattr(player, 'hitpoints', player.hitpoints + 50)),
    "torpedolauncher": (lambda player: player.weaponstate.update({'torpedo': True})),
    "torpedos": (lambda player: player.ammo.update({key: value + 5 for key, value in player.ammo.items()})),
    "plasmagun": (lambda player: player.plasmagun is True),
    "plasmaammo": (lambda player: player.plasmaammo + 200),
    # "doorkey": (),
    "bubbleorb": (lambda player: setattr(player, 'hitpoints', player.hitpoints + 5)),
    "flashlight": (lambda player: player.flashlight is True),
    # "respawnpoint": (lambda player: player.respawm is vec(46, 46)),
    "baitdecoy": (lambda player: player.baitdecoy + 5)
}
