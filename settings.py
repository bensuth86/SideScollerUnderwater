from os import path
from helpers.read_spritedata import *

# define colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
PURPLE = (184, 61, 184)
DEEPBLUE = (8, 37, 64)
YELLOW = (255, 255, 0)

repos = r"C:\Users\ben_s\Documents\Python_Scripts\PROJECTS\SideScrollerUnderwater"  # working directory

# game options/settings
TITLE = "Animate player"

# all screen dimensions, grids tiles multiples of 4
# TILESIZE = 46  # length, width in pixels
SCREENWIDTH = 1472  # screen width in tiles (must be divisible by 2)
SCREENHEIGHT = 736  # screen height in tiles
# GRIDWIDTH, GRIDHEIGHT = 5*TILESIZE, 5*TILESIZE  # map divided into grids 4 X 4 TILES

FPS = 60  # frames per second
TARGET_FPS = 60  # targer frame rate- used for frame rate independence


# Background
BACKGROUND = path.join(repos, "Images", "UnderwaterBackground.png")

# Map keys
# PLATFORMKEY = {'8': 'roof',
#                '2': 'floor',
#                '4': 'wallRight',
#                '6': 'wallLeft',
#                '7': 'topRightCorner',
#                '9': 'topLeftCorner',
#                '1': 'bottomLeftCorner',
#                '3': 'bottomRightCorner',
#                '5': 'tunnelLeft',
#                '0': 'tunnelRight'
#                }
