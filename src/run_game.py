# run_game.py

import pygame
from .settings import TITLE, SCREENWIDTH, SCREENHEIGHT
from .game import Game
from .logger import logger


def run():

    # initialize game window
    pygame.init()
    pygame.mixer.init()
    pygame.display.set_caption(TITLE)
    screen = pygame.display.set_mode((SCREENWIDTH, SCREENHEIGHT), flags=pygame.SCALED, vsync=1)
    game = Game(screen)
    game.show_start_screen()
    while game.running:
        game.new()
        game.run()
        game.show_go_screen()

    pygame.quit()

