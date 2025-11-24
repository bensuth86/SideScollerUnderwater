from pygame import Rect, Vector2

from ..settings import SCREENWIDTH, SCREENHEIGHT
from loggers import camera_lerp, detectNan_infinite_drift

import logging


class Camera:

    # TODO Parallax scrolling; objects, map layers move at different rates rel to camera scrolling speed
    def __init__(self, game):
        self.camera_rect = Rect(0, 0, SCREENWIDTH, SCREENHEIGHT)
        self.pos = Vector2(0, 0)  # float-based camera position top left of screen and map
        self.game = game

    def update(self, target, lerp_factor=0.1):  # lerp of 0.1 preferref

        # update camera offset according to player's new position i.e. camera follows player
        x_offset = target.rect.centerx - (SCREENWIDTH / 2)
        y_offset = target.rect.centery - (SCREENHEIGHT / 2)

        # limit scrolling to map size
        x_offset = max(0, x_offset)  # left map edge
        y_offset = max(0, y_offset)  # top map edge
        x_offset = min(self.game.map.width - SCREENWIDTH, x_offset)  # right map edge
        y_offset = min(self.game.map.height - SCREENHEIGHT, y_offset)  # bottom map edge

        # LERP current camera position toward target position (adjust between 0.05 - 0.2 for best results, 1 for no lerp- instantaneous snapping)
        old_pos = self.pos.copy()  # For debug only
        self.pos.x += (x_offset - self.pos.x) * lerp_factor
        self.pos.y += (y_offset - self.pos.y) * lerp_factor

        # --- Debug ---
        camera_lerp(lerp_factor)  # expected lerp 0 < f < 1
        detectNan_infinite_drift(self.pos, old_pos)

    def parallax_scrolling(self, surface, background_image):
        """ Entity.rect moves by a fraction of camera offset e.g. 1/2 self.rect.x, 1/2 self.rect.y"""
        # Drawing background layer at 50% scroll speed
        bg_offset = self.pos * 0.5
        surface.blit(background_image, (-bg_offset.x, -bg_offset.y))

    def apply(self, sprite):
        # move on screen objects according to camera offset e.g. player moves right, map objects shift left
        offset_x = sprite.rect.x - self.pos.x
        offset_y = sprite.rect.y - self.pos.y
        return offset_x, offset_y

    def apply_rect(self, rect):
        """ Apply to rect rather than sprite"""
        # return rect.move(self.camera_rect.topleft)
        offset_x = rect.x - self.pos.x
        offset_y = rect.y - self.pos.y
        return offset_x, offset_y

    def in_view(self, buffer, rect):
        """ CURRENTLY REDUNDANT """
        """Return True if the rect is within the visible camera area"""

        cam_left, cam_top = self.pos.x - buffer, self.pos.y - buffer
        cam_right, cam_bottom = cam_left + SCREENWIDTH + 2 * buffer, cam_top + SCREENHEIGHT + 2 * buffer

        # Check if rect overlaps the camera view area
        return not (
            rect.right < cam_left or
            rect.left > cam_right or
            rect.bottom < cam_top or
            rect.top > cam_bottom
        )
