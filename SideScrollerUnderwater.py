# Project setup

import pygame
import pytmx
import random
from string import ascii_uppercase
import time
# from settings import *
# from helpers.spritesheet_functions import *
from helpers.transform_images import *
from sprites import *


# HUD functions

def draw_sprite_bar(surf, x, y, pct, c1, c2, c3):

    pct = max(0, pct)
    bar_length, bar_height = 100, 20
    # bar_height = 20
    fill = pct * bar_length
    outline_rect = pygame.Rect(x, y, bar_length, bar_height)
    fill_rect = pygame.Rect(x, y, fill, bar_height)
    if pct > 0.6:
        col = c1
    elif pct > 0.3:
        col = c2
    else:
        col = c3
    pygame.draw.rect(surf, col, fill_rect)
    pygame.draw.rect(surf, WHITE, outline_rect, 2)


class Camera:
    # TODO Fix camera lag for smooth motion
    # TODO Parallax scrolling; objects, map layers move at different rates rel to camera scrolling speed
    def __init__(self, game):

        self.camera_rect = pygame.Rect(0, 0, SCREENWIDTH, SCREENHEIGHT)
        self.pos = pygame.Vector2(0, 0)  # float-based camera position
        self.game = game

    def update(self, target, lerp_factor=0.1):

        # update camera offset according to player's new position i.e. camera follows player
        x_offset = target.pos.x - (SCREENWIDTH / 2)
        y_offset = target.pos.y - (SCREENHEIGHT / 2)

        # limit scrolling to map size
        x_offset = max(0, x_offset)  # left map edge
        y_offset = max(0, y_offset)  # top map edge
        x_offset = min(self.game.map.width - SCREENWIDTH, x_offset)  # right map edge
        y_offset = min(self.game.map.height - SCREENHEIGHT, y_offset)  # bottom map edge

        # LERP current camera position toward target position (adjust between 0.05 - 0.2 for best results
        self.pos.x += (x_offset - self.pos.x ) * lerp_factor
        self.pos.y += (y_offset - self.pos.y ) * lerp_factor

    def parallax_scrolling(self, surface, background_image):
        """ Entity.rect moves by a fraction of camera offset e.g. 1/2 self.rect.x, 1/2 self.rect.y"""
        # Drawing background layer at 50% scroll speed
        bg_offset = self.camera.pos * 0.5
        surface.blit(background_image, (-bg_offset.x, -bg_offset.y))

    def apply(self, sprite):

        # move on screen objects according to camera offset e.g. player moves right, map objects shift left
        offset_x = sprite.rect.x - self.pos.x
        offset_y = sprite.rect.y - self.pos.y
        return offset_x, offset_y
        # return sprite.rect.move(self.pos)

    def apply_rect(self, rect):
        """ Apply to rect rather than sprite"""
        # return rect.move(self.camera_rect.topleft)
        offset_x = rect.x - self.pos.x
        offset_y = rect.y - self.pos.y
        return offset_x, offset_y


class TextMap:
    """Shelved """
    """ Read map data from .txt file; platform tiles, mobs"""
    def __init__(self, filename):
        self.data = []
        with open(filename, 'rt') as f:
            for line in f:
                line = line.replace("\t", '')  # remove tab scape characters
                self.data.append(line.strip())  # .strip prevents invisible new line characters being read from text file

        self.width = len(self.data[0]) * TILESIZE  # pixel width of the map
        self.height = len(self.data) * TILESIZE
        self.LHS, self.RHS = TILESIZE, self.width - TILESIZE
        self.top, self.btm = TILESIZE, self.height - TILESIZE


class Grid(pygame.sprite.Group):
    """Divide map layers into grid squares determined by map.gridwidth, map.gridheight.  Mobile sprites transfered to new grid sprite group
     as they travel across the map for collision detection"""

    def __init__(self, coordinates, x1, y1, x2, y2):

        pygame.sprite.Group.__init__(self)
        self.coordinates = coordinates
        self.x1 = x1  # x top left corner of grid
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2  # y bottom right corner grid


class TiledMap:

    def __init__(self, filename, game):

        tm = pytmx.load_pygame(filename, pixelalpha=True)
        self.tmxdata = tm
        self.tilesize = tm.tilewidth  # or tileheight
        self.width = tm.width * tm.tilewidth
        self.height = tm.height * tm.tileheight

        self.LHS, self.RHS = self.tilesize, self.width - self.tilesize
        self.top, self.btm = self.tilesize, self.height - self.tilesize

        self.gridwidth = 8 * self.tilesize  # map divided into grids 5 X 5 TILES
        self.gridheight = 8 * self.tilesize

        # grid square coordinates (A1, A2, A3 ... )
        self.setup_grid_refs()

        # map layers (dictionaries) divided into grids (4 X 4 TILES). Grid class inherets pygame.sprite.Group for storing sprites
        self.layers = self.generate_map_layers()
        self.mobile_layers = ['players', 'weapons', 'enemies']  # map layers holding mobile sprites

        self.game = game

    def setup_grid_refs(self):
        """Return list of x coordinates and y coordinates to be assigned to grid squares"""

        # setup coords (A1, A2, A3 ....)
        AZ = list(ascii_uppercase)  # list alphabet A-Z
        AZZ = AZ + list(ascii_uppercase) + [letter1+letter2 for letter1 in ascii_uppercase for letter2 in ascii_uppercase]  # extended list once map width exceeds 26 grid squares (A-Z + AA - ZZ)

        self.x_coords = AZZ[:(int(self.width/self.gridwidth))]  # grid squares along map length [A, B, C, D ...
        self.y_coords = [str(n) for n in range(int(self.height/self.gridheight))]  # ""            "" map height  [0, 1, 2, 3 ...

    def generate_map_layers(self):
        """ Map layers for Platforms, players, mobs etc.  Each layer divided into grids (4 X 4 TILES). Grid class inherets pygame.sprite.Group for storing sprites """

        map_layers = {'empty': {},  # TESTING ONLY
                      'platforms': {},
                      'pickups': {},
                      'players': {},
                      'weapons': {},
                      'enemies': {}
                      }

        for value in map_layers.values():
            # generate grid squares
            for i, grid_col in enumerate(self.x_coords):
                for j, grid_row in enumerate(self.y_coords):

                    grid_ref = (grid_col+grid_row)  # 'A1'
                    x1, y1 = (i * self.gridwidth), (j * self.gridheight)  # top left corner
                    x2, y2 = x1+self.gridwidth, y1+self.gridheight  # bottom right corner
                    grid = Grid(grid_ref, x1, y1, x2, y2)  # instance of Grid sprite.Group
                    value[grid_ref] = grid  # append key:value - 'A1': grid to grid_squares dictionary

        return map_layers

    def read_tiled_data(self, surface):
        """ Generate platform tiles and single map surf image for drawing """
        ti = self.tmxdata.get_tile_image_by_gid
        for layer in self.tmxdata.visible_layers:  # check visible map layers (dictionary) in Tiled
            if isinstance(layer, pytmx.TiledTileLayer):  # Tile Layer, Object Layer or Image Layer
                for col, row, gid, in layer:
                    tile_image = ti(gid)
                    if tile_image:
                        x, y = col * self.tmxdata.tilewidth, row * self.tmxdata.tileheight  # position in pixels
                        surface.blit(tile_image, (x, y))  # blit tile onto map surf image
                        if layer.name == 'Platforms':
                            # generate platform tile sprites and store to platforms map layer
                            Platform(self.game, x, y, tile_image, 'platforms')

    def generate_map(self):

        temp_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)  # create surface to draw map onto
        self.read_tiled_data(temp_surface)
        return temp_surface


class Game:

    PICKUP_CATGRY = {"stamina": (lambda player: setattr(player, 'stamina', player.stamina + 50)),
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
                     "flashlight": (lambda player: player.flashlight is True),
                     "respawnpoint": (lambda player: player.respawm is vec(46, 46)),
                     "baitdecoy": (lambda player: player.baitdecoy + 5)
                    }

    MOBCLASSES = {
        'dartfish': Dartfish,
        'spinefish': Spinefish,
        'daddyfish': Daddyfish
    }

    def __init__(self):
        # initialize game window, etc
        pygame.init()
        pygame.mixer.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((SCREENWIDTH, SCREENHEIGHT))
        self.camera = Camera(self)

        self.clock = pygame.time.Clock()
        self.elapsed_time = time.time()  # from new game start
        self.dt = 0  # time elapsed for 1 mainloop
        self.running = True  # game running

        # load background textures
        self.background = pygame.image.load(BACKGROUND).convert_alpha()

        # load map from TiledMap
        self.map = TiledMap(path.join(repos, 'maps', 'test.tmx'), self)

        # comment explaining next 2 lines
        self.map_img = self.map.generate_map()
        # self.map_img.set_colorkey(BLACK)  # set background to be transparent
        self.map_rect = self.map_img.get_rect()

        # init spritesheets
        self.effects_spritesheet = SpriteSheet('effects')
        self.pickups_spritesheet = SpriteSheet('PickUps')
        self.player_spritesheet = SpriteSheet('player')
        self.mob_spritesheet = SpriteSheet('mobs')
        self.weapons_spritesheet = SpriteSheet('weapons')

        # get images from spritesheets and store image surf to dictionary - dictionary ordered by category, then nested subcat if applicable
        self.effects_images = self.effects_spritesheet.get_sprite_images()
        self.effects_images['enemydeath4x4'] = resize_images(self.effects_images.get('enemydeath'), (4 * self.map.tilesize, 4 * self.map.tilesize))
        self.effects_images['explosion4x4'] = resize_images(self.effects_images.get('explosion'), (4 * self.map.tilesize, 4 * self.map.tilesize))

        self.pickup_images = self.pickups_spritesheet.get_sprite_images()
        self.player_images = self.player_spritesheet.get_sprite_images()
        self.mob_images = self.mob_spritesheet.get_sprite_images()
        self.weapons_images = self.weapons_spritesheet.get_sprite_images()

        self.spawnpoints = []  # locations adjacent platforms for spawning background props, pickups, effects etc

    def new(self):
        """Start a new game; initialise all variables, load or reload map data, sprites"""
        # init sprite groups
        self.mob_sprites = pygame.sprite.Group()
        self.hold_sprites = pygame.sprite.Group()  # sprites to be deleted- group for visual effects only
        self.all_sprites = pygame.sprite.Group()  # for drawing only

        # generate mobile sprites from TiledMap object layers
        for pickup in self.map.tmxdata.layernames['pickups']:

            pickup = Pick_up(self, pickup.x, pickup.y, pickup.image, 'pickups', pickup.name)
            self.all_sprites.add(pickup)

        for tile_object in self.map.tmxdata.objects:

            if tile_object.name == 'Player':
                self.player = Player(self, tile_object.x, tile_object.y,  'players', self.player_images, 'player_idle')  # xpos, ypos, width, height (in TILES i.e. 1 TILE X 2 TILES), image (first frame of North orientation by default)
                self.all_sprites.add(self.player)
            if tile_object.name == 'Enemy':
                mobkey = random.choice(list(Game.MOBCLASSES.keys()))  # random choice of mob class
                # TODO distributed random selection e.g. every 1 in 10 mobs select Daddyfish, 1 in 3 select Dartfish etc
                # img = self.mob_images[mobkey][0]
                mob = Game.MOBCLASSES[mobkey](self, tile_object.x, tile_object.y, 'enemies', self.mob_images, mobkey)
                self.all_sprites.add(mob)
                self.mob_sprites.add(mob)  # TESTING ONLY
            if tile_object.name == 'Mine':
                mine = Mine(self, tile_object.x, tile_object.y, 'weapons', self.weapons_images, 'mine')
                self.all_sprites.add(mine)

    def run(self):
        """ Main game loop"""
        self.playing = True
        while self.playing:
            # self.dt = self.clock.tick(FPS) / 1000  # time elapsed during a single loop (seconds)
            self.clock.tick(FPS)
            self.dt = time.time() - self.elapsed_time  # current time - elapsed time on previous loop
            self.elapsed_time += self.dt  # update elapsed time for current loop

            self.events()
            self.update()
            self.draw()

    def events(self):

        for event in pygame.event.get():
            # check for closing pygame window
            # pygame.event.set_grab(True)  # lock keyboard and mouse input into pygame app
            if event.type == pygame.QUIT:
                if self.playing:  # if in game
                    self.playing = False  # exit game
                self.running = False  # close pygame application
            if event.type == pygame.MOUSEBUTTONDOWN:
                if 4 <= event.button <= 5:  # middle mouse scroll
                    self.player.choose_weapon_mousewheel(event)

            if event.type == pygame.KEYDOWN:
                if pygame.K_1 <= event.key <= pygame.K_9:
                    weapon_index = int(event.unicode)
                    self.player.choose_weapon_numpad(weapon_index)
                if event.key == pygame.K_q:
                    # exit game
                    pygame.event.set_grab(False)  # lock keyboard and mouse input into pygame app
                    self.playing = False
                if event.key == pygame.K_ESCAPE:
                    # close pygame
                    self.playing = False
                    self.running = False

    def update(self):
        """Game Loop - Update"""
        self.camera.update(self.player)  # change camera rect position according to player position (centred on player rect)
        # for mob in self.mob_sprites:
        #     self.camera.update(mob)
        # update sprites by grid
        # TODO only update grids currently on screen plus grids adjacent to to screen edges

        for map_layer in self.map.mobile_layers:
            grids = self.map.layers[map_layer]
            for grid in grids.values():
                grid.update()  # call update function for mobile sprites within current grid
                for sprite in grid.spritedict:
                    sprite.pos += sprite.vel * self.dt * TARGET_FPS  # update position independent of frame rate

        # update hold_sprites
        for sprite in self.hold_sprites:
            sprite.vel *= 0.98  # velocity reduced each loop
            sprite.pos += sprite.vel
            sprite.hitrect.center = sprite.pos  # must update hitrect rather than rect as rect position overwritten in Mobile_sprite.transform_image()

            if sprite.check_anim_end(sprite.current_animation):
                sprite.kill()

        # TODO - limit holding group size
        # Kill sprites in hold_sprites group if they're off screen
        for sprite in self.hold_sprites:

            if self.player.pos.x - sprite.rect.right > SCREENWIDTH * 5/8 or sprite.rect.left - self.player.pos.x > SCREENWIDTH * 5/8:
                sprite.kill()

            if self.player.pos.y - sprite.rect.bottom > SCREENHEIGHT * 5/8 or sprite.rect.top - self.player.pos.y > SCREENHEIGHT * 5/8:
                sprite.kill()

    def draw_text(self, text, size, colour, x, y):

        font = pygame.font.Font('freesansbold.ttf', size)  # text font
        text_surface = font.render(text, True, colour)
        # text_surface.convert()
        text_rect = text_surface.get_rect()
        text_rect.center = (x, y)
        self.screen.blit(text_surface, text_rect)

    def draw_grid(self):  # (rows,columns)
        # Display grid squares for testing #
        font = pygame.font.Font('freesansbold.ttf', 16)
        text = font.render('GeeksForGeeks', True, GREEN, BLUE)

        # for grid_ref, sptgrp in self.grid_squares.items():
        for grid in self.map.layers['empty'].values():
            x1 = grid.x1
            y1 = grid.y1
            x1 = x1 + self.camera.pos.x  # update with camera movement
            y1 = y1 + self.camera.pos.y
            pygame.draw.rect(self.screen, WHITE, [x1, y1, self.map.gridwidth, self.map.gridheight], 1)
            text = font.render(grid.coordinates, True, GREEN, BLUE)
            textRect = text.get_rect()
            textRect.topleft = (x1, y1)
            self.screen.blit(text, textRect)

    def draw(self):
        """Game Loop - draw"""
        pygame.display.set_caption("{:.2f}".format(self.clock.get_fps()))
        # self.screen.blit(self.background, (self.camera.camera_rect.x, self.camera.camera_rect.y))  # draw background
        self.screen.fill(DEEPBLUE)
        offset_x, offset_y = self.camera.apply_rect(self.map_rect)
        # self.screen.blit(self.map_img, (int(offset_x), int(offset_y)))
        # blit all map sprites, content
        for sprite in self.all_sprites:

            sprite.draw()

        # HUD functions
        draw_sprite_bar(self.screen, 0.2*SCREENWIDTH, 10, self.player.hitpoints / Player.hitpoints, GREEN, YELLOW, RED)
        draw_sprite_bar(self.screen, 0.8*SCREENWIDTH, 10, self.player.stamina / Player.stamina, RED, BLUE, PURPLE)
        self.draw_text(self.player.current_weapon, 20, RED, 0.4*SCREENWIDTH, 15)  # current weapon
        self.draw_text(str(self.player.ammo[self.player.current_weapon]), 20, RED, 0.6*SCREENWIDTH, 15)
        for grid in self.map.layers['weapons'].values():
            for sprite in grid:
                if sprite.refkey == 'mine':
                    if sprite.active:
                        self.draw_text(str(int(sprite.countdown+1)), 50, RED, sprite.rect.centerx - self.camera.pos.x, sprite.rect.centery - self.camera.pos.y)

        pygame.display.flip()  # *after* drawing everything, flip the display
        # TESTING ONLY #

        # self.draw_grid()

        # current_grids = str(self.player.current_grids)
        # self.draw_text(current_grids, 22, RED, SCREENWIDTH / 2, 15)

        # camera.rect offset
        # camera_position = (self.camera.pos.x, self.camera.pos.y)
        camera_position = str((round(self.camera.pos.x, 1), round(self.camera.pos.y, 1)))
        # self.draw_text(camera_position, 22, RED, SCREENWIDTH/2, SCREENHEIGHT - 15)

        # player data
        player_x = self.player.pos.x + self.camera.pos.x
        player_y = self.player.pos.y + self.camera.pos.y

        pos = str(self.player.pos)
        # self.draw_text(pos, 22, RED, 100, 15)
        velocity = str(self.player.vel)
        # self.draw_text(velocity, 22, RED, SCREENWIDTH - 50, 15)

        # draw player rect

        # pygame.draw.rect(self.screen, WHITE, self.player.rect, 2)  # player rect
        # pygame.draw.rect(self.screen, RED, self.player.hitrect, 2)  # player hitrect
        # pygame.draw.line(self.screen, RED, (self.player.pos.x, self.player.pos.y), (self.player.pos.x + self.player.direction.x * 100, self.player.pos.y + self.player.direction.y * 100), 1)  # player velocity vector
        # pygame.draw.line(self.screen, GREEN, (self.player.pos.x, self.player.pos.y), (self.player.pos.x + self.player.vel.x * 10, self.player.pos.y + self.player.vel.y * 10), 3)  # player velocity vector

        for grid in self.map.layers['weapons'].values():
            for sprite in grid:
                # pygame.draw.rect(self.screen, WHITE, sprite.rect, 2)  # missile rect
                pygame.draw.rect(self.screen, RED, sprite.hitrect, 2)  # missile hitrect
                pass

        # mob data
        for mob in self.mob_sprites:
            x_pos = mob.pos.x + self.camera.pos.x
            y_pos = mob.pos.y + self.camera.pos.y

            draw_sprite_bar(self.screen, mob.pos.x - 50 + self.camera.pos.x, mob.pos.y - 50 + self.camera.pos.y, mob.hitpoints / mob.__class__.hitpoints, GREEN, YELLOW, RED)
            # pygame.draw.rect(self.screen, RED, mob.rect, 2)
            # pygame.draw.rect(self.screen, WHITE, mob.avoidRect, 2)

            # pygame.draw.circle(self.screen, WHITE, (int(mob.rect.centerx), int(mob.rect.centery)), int(mob.radius), 1)  # draw effective radius
            # pygame.draw.circle(self.screen, RED, (int(mob.target.x+self.camera.camera_rect.x), int(mob.target.y+self.camera.camera_rect.y)), 10, 1)  # draw target position
            # pygame.draw.circle(self.screen, RED, (int(mob.pos.x + mob.target_vec.x), int(mob.pos.y + mob.target_vec.y)), 10, 1)
            # pygame.draw.circle(self.screen, RED, (int(x_pos), int(y_pos)), 10, 1)
            vel = str((round(mob.vel[0], 1), round(mob.vel[1], 1)))
            speed = str(round(mob.vel.length(), 1))
            # target_angle = str(round(mob.target_angle, 0))

            # self.draw_text(vel, 22, RED, SCREENWIDTH - 100, 15)

            # draw vectors
            # pygame.draw.line(self.screen, WHITE, (mob.pos.x, mob.pos.y), (mob.pos.x + mob.target_vec.x, mob.pos.y + mob.target_vec.y), 3)  # target vector
            # pygame.draw.line(self.screen, GREEN, (mob.pos.x, mob.pos.y), (mob.pos.x + mob.displacement.x, mob.pos.y + mob.displacement.y), 3)  # displacement vector
            # pygame.draw.line(self.screen, WHITE, (x_pos, y_pos), (x_pos + mob.anti_g.x, y_pos + mob.anti_g.y), 3)  # accn away from wall tiles
            # pygame.draw.line(self.screen, GREEN, (x_pos, y_pos), (x_pos + mob.vel.x * 10, y_pos + mob.vel.y *  10), 3)  # velocity vector
            # pygame.draw.line(self.screen, GREEN, (mob.pos.x, mob.pos.y), (mob.pos.x + mob.alt_rad.x, mob.pos.y + mob.alt_rad.y), 3)  # current rad from origin
            # pygame.draw.line(self.screen, YELLOW, (self.player.pos.x, self.player.pos.y), (self.player.pos.x + mob.target_rad.x, self.player.pos.y + mob.target_rad.y), 6)  # target rad from player to origin
            # pygame.draw.line(self.screen, RED, (self.player.pos.x, self.player.pos.y), (self.player.pos.x + mob.actual_rad.x, self.player.pos.y + mob.actual_rad.y), 3)  # final rad after subtending angle delta

            # pygame.draw.line(self.screen, RED, (mob.pos.x, mob.pos.y), (mob.pos.x + mob.vel.x, mob.pos.y + mob.vel.y), 3)  # velocity vector

        # for grid in self.map.layers['weapons'].values():
        #     for sprite in grid:
        #         if sprite.refkey == 'mine':
        #             self.draw_text(sprite.gridref, 25, WHITE, sprite.pos.x + self.camera.camera_rect.x, sprite.pos.y + self.camera.camera_rect.y)
        #             pygame.draw.circle(self.screen, RED, (int(sprite.pos.x + self.camera.camera_rect.x), int(sprite.pos.y + self.camera.camera_rect.y)), sprite.affect_rad, 1)  # draw target position
        pygame.display.flip()  # *after* drawing everything, flip the display

    def show_start_screen(self):
        # game splash/start screen
        pass

    def show_go_screen(self):
        # game over/continue
        self.screen.fill(BLACK)
        self.draw_text("GAME OVER", 48, RED, SCREENWIDTH / 2, SCREENHEIGHT / 4)
        pygame.display.flip()


game = Game()
game.show_start_screen()
while game.running:
    game.new()
    game.run()
    game.show_go_screen()

pygame.quit()