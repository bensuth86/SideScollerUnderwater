import colorsys
from pygame import Vector2 as vec, draw

from src.systems.map_manager import Grid


class Mesh:
    """ For testing: setup nodes at map tile corners stored as dictionaries.  For each node calculate anti_g vector (effect of platforms)
    and store corresponding r, g, b variable ranging from blue to red hue for drawing to screen.
    """

    def __init__(self, game):

        self.game = game
        self.nodes = []  # mesh nodes colour coded for drawing to screen
        for x in range(0, self.game.map.width, self.game.map.tilesize):
            for y in range(0, self.game.map.height, self.game.map.tilesize):
                node = self.generate_node(x, y)
                self.nodes.append(node)

    def generate_node(self, x, y):
        """ Dictionary to store x, y, position, anti_g vector and corresponding colour"""
        adjacent_grids = self.get_adjacent_grids(x, y)

        # calculate anti_g vector
        anti_g_vector = vec(0, 0)
        for ref in adjacent_grids:
            for ptf in self.game.map.layers['platforms'][ref]:
                displacement = vec(ptf.rect.centerx, ptf.rect.centery) - vec(x, y)  # between mob and centre point of platform tile
                anti_g = -displacement * (6 / displacement.length() ** 2)  # accelleration away from wall- inversly proportional to displacemnt squared
                anti_g_vector += anti_g

        rgb = self.get_colour(anti_g_vector.length(), 0, 1)

        node = {'x_coord': x,
                'y_coord': y,
                'anti_g': anti_g_vector,
                'colour': rgb}

        return node

    def get_adjacent_grids(self, x, y):

        adjacent_grids = []
        grid_col, grid_row = x // self.game.map.gridwidth, y // self.game.map.gridheight

        grids_left = max(grid_col - 1, 0)  # return index position for grids to the left
        grids_right = min(grid_col + 1, len(self.game.map.x_coords) - 1)
        grids_above = max(grid_row - 1, 0)
        grids_below = min(grid_row + 1, len(self.game.map.y_coords) - 1)
        for i in range(grids_left, grids_right + 1):
            for j in range(grids_above, grids_below + 1):
                gridref = self.game.map.x_coords[i] + self.game.map.y_coords[j]
                adjacent_grids.append(gridref)

        return adjacent_grids

    def get_colour(self, var, v_min, v_max):
        """
        Maps a value `v` in [v_min, v_max] to a rainbow color:
        Blue → Green → Yellow → Red (hue 2/3 → 0).

        Returns:
            (R, G, B): Tuple of ints (0–255)
        """
        # Clamp and normalize to 0–1
        v = max(min(var, v_max), v_min)
        t = (v - v_min) / (v_max - v_min)

        # Hue: 0.66 (blue) → 0.0 (red)
        h = (1 - t) * 0.66  # linear interpolation: blue → red
        s = 1.0  # full saturation
        brightness = 1.0  # full brightness

        r, g, b = colorsys.hsv_to_rgb(h, s, brightness)
        return (int(r * 255), int(g * 255), int(b * 255))

    def draw(self):

        for node in self.nodes:
            x1 = node['x_coord'] - self.game.camera.pos.x  # update with camera movement
            y1 = node['y_coord'] - self.game.camera.pos.y

            draw.circle(self.game.screen, node['colour'], (x1, y1), 2)
