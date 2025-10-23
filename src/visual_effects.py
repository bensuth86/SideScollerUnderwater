import pygame
from random import randint

vec = pygame.Vector2


class SmokeParticle(pygame.sprite.Sprite):
    """Red smoke particle that expands and fades out visibly."""
    def __init__(self, game, pos, size=18, lifetime=1000):
        super().__init__(game.fx_sprites)
        self.game = game
        self.pos = vec(pos)
        self.lifetime = lifetime  # milliseconds
        self.timer = 0

    def update(self):
        """Update position, fade alpha, and grow particle size over lifetime."""
        pass

    def draw(self):

        self.game.screen.blit(self.image, self.game.camera.apply(self))
