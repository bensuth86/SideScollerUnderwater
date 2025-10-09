import pygame
import pytest
from src.sprites import Player
from src.settings import TILESIZE

@pytest.fixture
def dummy_game():
    class DummyGame:
        def __init__(self):
            self.screen = pygame.Surface((800, 600))
            self.all_sprites = pygame.sprite.Group()
    return DummyGame()


def test_player_initial_position(dummy_game):
    player = Player(dummy_game, 100, 200)
    assert player.rect.topleft == (100, 200)