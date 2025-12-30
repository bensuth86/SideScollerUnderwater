import pytmx
import pygame

from string import ascii_uppercase
from random import choice

from ..helpers import clamp
from ..settings import SCREENWIDTH, SCREENHEIGHT
from loggers import check_valid_grid


class Grid(pygame.sprite.Group):
    """Divide map layers into grid squares determined by map.gridwidth, map.gridheight.  Mobile sprites transfered to new grid sprite group
     as they travel across the map for collision detection"""

    def __init__(self, coordinates, x1, y1, x2, y2):
        super().__init__()
        self.coordinates = coordinates
        self.x1 = x1  # x top left corner of grid
        self.y1 = y1
        self.x2 = x2  # y bottom right corner grid
        self.y2 = y2


class TiledMap:

    def __init__(self, game, map_path: str, PlatformClass):

        self.game = game
        self.Platform = PlatformClass

        self.tmxdata = pytmx.load_pygame(map_path, pixelalpha=True)
        self.tilesize = self.tmxdata.tilewidth
        self.width = self.tmxdata.width * self.tilesize
        self.height = self.tmxdata.height * self.tilesize

        self.LHS, self.RHS = self.tilesize, self.width - self.tilesize
        self.top, self.bottom = self.tilesize, self.height - self.tilesize

        self.gridwidth = 8 * self.tilesize
        self.gridheight = 8 * self.tilesize

        # Grid coordinate references (A1, A2, ..., Z9, AA1, etc.)

        self.x_coords, self.y_coords = self._generate_grid_refs()

        # Map layers divided into grid cells
        self.layers = self._generate_map_layers()

        self.grid_coords = list(self.layers["empty"].keys())  # list of grid coordinate references for current map

        # Layers that contain moving entities
        self.stationary_layers = ["pickups"]  # sprites always within assigned grid
        self.mobile_layers = {"players", "obstacles", "weapons", "enemies"}  # sprites can move from grid to grid

        self.active_gridrefs = []

        # For generating spawn points
        self.platform_tiles = set()  # store platform tile coords (tile-based)
        self.spawn_radius = 3  # min Manhattan distance from any platform
        self.valid_spawn_tiles = []  # will store precomputed valid spawn tiles

    def _generate_grid_refs(self):
        """Generate grid coordinate labels for map columns and rows."""

        max_cols = int(self.width / self.gridwidth)
        max_rows = int(self.height / self.gridheight)

        # Extended alphabet (A-Z, AA-ZZ)
        letters = list(ascii_uppercase)
        extended_letters = letters + [a + b for a in letters for b in letters]
        x_coords = extended_letters[:max_cols]  # grid cols along map length [A, B, C, D ...
        y_coords = [str(i) for i in range(max_rows)]  # grid rows along map height [0, 1, 2, 3 ...

        return x_coords, y_coords

    def _generate_map_layers(self):
        """ Create layer dictionaries divided into grid cells. Grid class inherets pygame.sprite.Group for storing sprites """
        layer_names = ["empty", "platforms", "obstacles", "pickups", "players", "weapons", "enemies"]
        map_layers = {name: {} for name in layer_names}

        for layer_obj in map_layers.values():
            # generate grid squares
            for i, col_label in enumerate(self.x_coords):
                for j, row_label in enumerate(self.y_coords):
                    grid_ref = f"{col_label}{row_label}"  # 'A1'
                    x1, y1 = (i * self.gridwidth), (j * self.gridheight)  # top left corner
                    x2, y2 = x1 + self.gridwidth, y1 + self.gridheight  # bottom right corner
                    grid = Grid(grid_ref, x1, y1, x2, y2)  # instance of Grid sprite.Group
                    layer_obj[grid_ref] = grid  # append key:value - 'A1': grid to grid_squares dictionary

        return map_layers

    def get_active_grids(self):
        """ Return list of gridrefs currently on screen and adjacent to screen boundaries - for calling grid.update"""
        cam_x, cam_y = self.game.camera.pos.x, self.game.camera.pos.y

        x_min = clamp(cam_x - self.gridwidth, 0, self.width)
        x_max = clamp(cam_x + SCREENWIDTH + 2 * self.gridwidth, 0, self.width)
        y_min = clamp(cam_y - self.gridheight, 0, self.height)
        y_max = clamp(cam_y + SCREENHEIGHT + 2 * self.gridheight, 0, self.height)

        left_col, right_col = int(x_min // self.gridwidth), int(x_max // self.gridwidth)
        top_row, bottom_row = int(y_min // self.gridheight), int(y_max // self.gridheight)

        active_cols = self.x_coords[left_col:right_col]
        active_rows = self.y_coords[top_row:bottom_row]

        self.active_gridrefs = [f"{col}{row}" for col in active_cols for row in active_rows]

        # --- Debug ---
        for gridref in self.active_gridrefs:
            check_valid_grid(gridref, None, self.grid_coords)

        return self.active_gridrefs

    def compute_valid_spawn_tiles(self):
        """
        Identify all tile coordinates that are >= N tiles away from any platform tile.
        Distance is measured in Manhattan distance.
        """

        max_cols = self.tmxdata.width
        max_rows = self.tmxdata.height
        radius = self.spawn_radius

        valid = []

        for col in range(max_cols):
            for row in range(max_rows):

                # Skip if this is a platform tile
                if (col, row) in self.platform_tiles:
                    continue

                # Check distance from all platform tiles
                too_close = False
                for px, py in self.platform_tiles:
                    dist = abs(px - col) + abs(py - row)  # Manhattan distance

                    if dist < radius:
                        too_close = True
                        break

                if not too_close:
                    valid.append((col, row))

        self.valid_spawn_tiles = valid
        print(f"[SPAWNS] Found {len(valid)} valid spawn tiles.")

    def get_random_spawn_point(self):
        """
        Returns a random spawn position in pixel coordinates at centre of the tile.
        Must be called AFTER compute_valid_spawn_tiles().
        """

        if not self.valid_spawn_tiles:
            raise RuntimeError("Valid spawn tiles have not been computed yet!")

        col, row = choice(self.valid_spawn_tiles)

        # Convert tile coords → world pixel coords
        x = col * self.tilesize + self.tilesize // 2
        y = row * self.tilesize + self.tilesize // 2

        return x, y

    def read_tiled_data(self, surface):
        """ Generate platform tiles and single map surf image for drawing """
        # ti = self.tmxdata.get_tile_image_by_gid  # shorthand function call
        for layer in self.tmxdata.visible_layers:  # check visible map layers (generator) in Tiled
            if isinstance(layer, pytmx.TiledTileLayer):  # Tile Layer
                for col, row, gid, in layer:
                    tile_image = self.tmxdata.get_tile_image_by_gid(gid)
                    if tile_image:
                        tile_width, tile_height = self.tmxdata.tilewidth, self.tmxdata.tileheight
                        x, y = col * tile_width, row * tile_height  # position in pixels
                        surface.blit(tile_image, (x, y))  # blit tile onto map surf image
                        if layer.name == 'Platforms':
                            # generate platform tile sprites and store to platforms map layer
                            self.Platform(self.game, x, y, tile_width, tile_height)
                            # Store tile-grid coordinate, not pixel coordinates
                            self.platform_tiles.add((col, row))
        self.compute_valid_spawn_tiles()

    def generate_map(self):

        temp_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)  # create surface to draw map onto
        self.read_tiled_data(temp_surface)
        return temp_surface