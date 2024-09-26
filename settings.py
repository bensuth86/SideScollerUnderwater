from os import path
from helpers.read_spritedata import *

# define colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)

repos = r"C:\Users\ben_s\Documents\Python_Scripts\PROJECTS\SideScrollerUnderwater"  # working directory

# game options/settings
TITLE = "Animate player"
TILESIZE = 36  # length, width in pixels
GRIDWIDTH, GRIDHEIGHT = 4*TILESIZE, 4*TILESIZE  # map divided into grids 4 X 4 TILES
SCREENWIDTH = 40 * TILESIZE  # screen width in tiles (must be divisible by 4)
SCREENHEIGHT = 20 * TILESIZE  # screen height in tiles (must be divisible by 4)
FPS = 60

# Background
BACKGROUND = path.join(repos, "Images", "UnderwaterBackground.png")

# Map keys
PLATFORMKEY = {'8': 'roof',
               '2': 'floor',
               '4': 'wallRight',
               '6': 'wallLeft',
               '7': 'topRightCorner',
               '9': 'topLeftCorner',
               '1': 'bottomLeftCorner',
               '3': 'bottomRightCorner',
               '0': 'tunnelRight',
               '5': 'tunnelLeft'
               }

# read sprite data from text files and store to dictionary

PLATFORMS = readSpriteData(path.join(repos, 'spritedata', 'platformsdata.txt'))
PROPS = readSpriteData(path.join(repos, 'spritedata', 'propsdata.txt'))
PLAYER = readSpriteData(path.join(repos, 'spritedata', 'playerdata.txt'))
MOBS = readSpriteData(path.join(repos, 'spritedata', 'mobsdata.txt'))
EFFECTS = readSpriteData(path.join(repos, 'spritedata', 'effectsdata.txt'))
WEAPONS = readSpriteData(path.join(repos, 'spritedata', 'weaponsdata.txt'))

# sprite orientations  [K_RIGHT, K_LEFT , K_DOWN, K_UP]
ORIENTATIONS = {
                    'East': [1, 0, 0, 0],
                    'West': [0, 1, 0, 0],
                    'South': [0, 0, 1, 0],
                    'North': [0, 0, 0, 1],
                    'NorthEast': [1, 0, 0, 1],
                    'SouthEast': [1, 0, 1, 0],
                    'NorthWest': [0, 1, 0, 1],
                    'SouthWest': [0, 1, 1, 0]
                }
