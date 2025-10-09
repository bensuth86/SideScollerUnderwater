import pytmx
import pygame
from string import ascii_uppercase

from ..settings import SCREENWIDTH, SCREENHEIGHT


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

    def __init__(self, game, map_dir, PlatformClass):

        tm = pytmx.load_pygame(map_dir, pixelalpha=True)
        self.tmxdata = tm
        self.tilesize = tm.tilewidth  # or tileheight
        self.width = tm.width * tm.tilewidth
        self.height = tm.height * tm.tileheight

        self.LHS, self.RHS = self.tilesize, self.width - self.tilesize
        self.top, self.btm = self.tilesize, self.height - self.tilesize

        self.gridwidth = 8 * self.tilesize  # must be divisible by map width
        self.gridheight = 8 * self.tilesize  # ditto map height

        # grid square coordinates (A1, A2, A3 ... )
        self.setup_grid_refs()

        # map layers (dictionaries) divided into grids (4 X 4 TILES). Grid class inherets pygame.sprite.Group for storing sprites
        self.layers = self.generate_map_layers()
        self.mobile_layers = ['players', 'obstacles', 'weapons', 'enemies']  # map layers holding mobile sprites

        self.game = game
        self.Platform = PlatformClass

    def setup_grid_refs(self):
        """Return list of x coordinates and y coordinates to be assigned to grid squares"""

        # setup coords (A1, A2, A3 ....)
        AZ = list(ascii_uppercase)  # list alphabet A-Z
        AZZ = AZ + list(ascii_uppercase) + [letter1 + letter2 for letter1 in ascii_uppercase for letter2 in ascii_uppercase]  # extended list once map width exceeds 26 grid squares (A-Z + AA - ZZ)

        self.x_coords = AZZ[:(int(self.width / self.gridwidth))]  # grid squares along map length [A, B, C, D ...
        self.y_coords = [str(n) for n in range(int(self.height / self.gridheight))]  # ""            "" map height  [0, 1, 2, 3 ...

    def generate_map_layers(self):
        """ Map layers for Platforms, players, mobs etc.  Each layer divided into grids (4 X 4 TILES). Grid class inherets pygame.sprite.Group for storing sprites """

        map_layers = {'empty': {},  # TESTING ONLY
                      'platforms': {},
                      'obstacles': {},
                      'pickups': {},
                      'players': {},
                      'weapons': {},
                      'enemies': {}
                      }

        for value in map_layers.values():
            # generate grid squares
            for i, grid_col in enumerate(self.x_coords):
                for j, grid_row in enumerate(self.y_coords):
                    grid_ref = (grid_col + grid_row)  # 'A1'
                    x1, y1 = (i * self.gridwidth), (j * self.gridheight)  # top left corner
                    x2, y2 = x1 + self.gridwidth, y1 + self.gridheight  # bottom right corner
                    grid = Grid(grid_ref, x1, y1, x2, y2)  # instance of Grid sprite.Group
                    value[grid_ref] = grid  # append key:value - 'A1': grid to grid_squares dictionary

        return map_layers

    def get_active_grids(self):
        """ Return list of gridrefs currently on screen and adjacent to screen boundaries - for calling grid.update"""
        x_bound = [self.game.camera.pos.x - self.gridwidth, self.game.camera.pos.x + SCREENWIDTH + 2 * self.gridwidth]  # (left boundary, right boundary)
        x_bound[0], x_bound[1] = max(x_bound[0], 0), min(x_bound[1], self.width)  # clamp to within map boundaries
        y_bound = [self.game.camera.pos.y - self.gridheight, self.game.camera.pos.y + SCREENHEIGHT + 2 * self.gridheight]  # (top boundary, bottom boundary)
        y_bound[0], y_bound[1] = max(y_bound[0], 0), min(y_bound[1], self.height)  # clamp to within map boundaries

        left_col, right_col = int(x_bound[0] // self.gridwidth), int(x_bound[1] // self.gridwidth)
        top_row, bottom_row = int(y_bound[0] // self.gridheight), int(y_bound[1] // self.gridheight)
        active_cols = self.x_coords[left_col: right_col]
        active_rows = self.y_coords[top_row: bottom_row]
        self.active_gridrefs = [f"{col}{row}" for col in active_cols for row in active_rows]

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

    def generate_map(self):

        temp_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)  # create surface to draw map onto
        self.read_tiled_data(temp_surface)
        return temp_surface
