# Project setup

import pygame
import random
from string import ascii_uppercase
from settings import *
from helpers.spritesheet_functions import *
from helpers.transform_images import *
from sprites import *


# HUD functions

def draw_player_health(surf, x, y, pct):

    pct = max(0, pct)
    bar_length = 100
    bar_height = 20
    fill = pct * bar_length
    outline_rect = pygame.Rect(x, y, bar_length, bar_height)
    fill_rect = pygame.Rect(x, y, fill, bar_height)
    if pct > 0.6:
        col = GREEN
    elif pct > 0.3:
        col = YELLOW
    else:
        col = RED
    pygame.draw.rect(surf, col, fill_rect)
    pygame.draw.rect(surf, WHITE, outline_rect, 2)


class Camera:
    # TODO Fix camera 'stutter'
    # TODO Parallax scrolling; objects, map layers move at different rates rel to camera scrolling speed
    def __init__(self, game):

        self.rect = pygame.Rect(0, 0, SCREENWIDTH, SCREENHEIGHT)
        self.game = game

    def update(self, target):
        # update camera offset according to player's new position i.e. camera follows player
        x_offset = -target.rect.centerx + (SCREENWIDTH / 2)  # player moves right, map moves left relative to camera.  Add half screen width to keep player centred on screen
        y_offset = -target.rect.centery + (SCREENHEIGHT / 2)  # player moves up, map moves down ""            ""
        # limit scrolling to map size
        x_offset = min(0, x_offset)  # left map edge
        y_offset = min(0, y_offset)  # top map edge
        x_offset = max(-(self.game.map.width - SCREENWIDTH), x_offset)  # right map edge
        y_offset = max(-(self.game.map.height - SCREENHEIGHT), y_offset)  # bottom map edge

        # # reposition camera rect  (remove/ comment out to 'switch off' camera)
        self.rect.x = int(x_offset)
        self.rect.y = int(y_offset)

    def parallax_scrolling(self):
        """ Entity.rect moves by a fraction of camera offset e.g. 1/2 self.rect.x, 1/2 self.rect.y"""
        pass

    def apply(self, entity):
        # move on screen objects according to camera offset e.g. player moves right, map objects shift left
        return entity.rect.move(self.rect.topleft)


class Map:
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
    """Divide map into grid squares determined by GRIDHEIGHT, GRIDWIDTH.  Mobile sprites transfered to new grid sprite group
     as they travel across the map for collision detection with platforms"""

    def __init__(self, coordinates, x1, y1, x2, y2):

        pygame.sprite.Group.__init__(self)
        self.coordinates = coordinates
        self.x1 = x1  # x top left corner of grid
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2  # y bottom right corner grid


class Game:

    screen = pygame.display.set_mode((SCREENWIDTH, SCREENHEIGHT))
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
        self.elapsed_time = 0  # from new game start
        self.dt = 0  # time elapsed for 1 mainloop
        self.running = True  # game running

        # load background textures
        self.background = pygame.image.load(BACKGROUND).convert()
        # self.background = pygame.Surface([width, height]).convert()
        # image.set_colorkey(BLACK)  # set background to be transparent

        # init spritesheets
        self.platform_spritesheet = SpriteSheet('platforms')  # takes file name (not inc file extension)
        self.props_spritesheet = SpriteSheet('props')
        self.effects_spritesheet = SpriteSheet('effects')
        self.player_spritesheet = SpriteSheet('player')
        self.mob_spritesheet = SpriteSheet('mobs')
        self.weapons_spritesheet = SpriteSheet('weapons')

        # get images from spritesheets and store image surf to dictionary - dictionary ordered by category, then nested subcat if applicable
        self.platform_images = self.platform_spritesheet.get_sprite_images(PLATFORMS)
        self.prop_images = self.props_spritesheet.get_sprite_images(PROPS)
        self.effects_images = self.effects_spritesheet.get_sprite_images(EFFECTS)
        self.player_images = self.player_spritesheet.get_sprite_images(PLAYER)
        self.mob_images = self.mob_spritesheet.get_sprite_images(MOBS)
        self.weapons_images = self.weapons_spritesheet.get_sprite_images(WEAPONS)

        # get effects sprites
        self.effects_images['enemyDeath2x1'] = resize_images(self.effects_images.get('enemyDeath'), (2*TILESIZE, 1*TILESIZE))
        self.effects_images['enemyDeath4x4'] = resize_images(self.effects_images.get('enemyDeath'), (4 * TILESIZE, 4 * TILESIZE))

        self.map = Map(path.join(repos, 'map.txt'))  # create map object from Map class, tilemap.py
        self.x_coords, self.y_coords = self.grid_refs()

        self.spawnpoints = []  # locations adjacent platforms for spawning background props, pickups, effects etc

    def grid_refs(self):
        """Return list of x coordinates and y coordinates to be assigned to grid squares"""

        # setup coords (A1, A2, A3 ....)
        AZ = list(ascii_uppercase)  # list alphabet A-Z
        AZZ = AZ + list(ascii_uppercase) + [letter1+letter2 for letter1 in ascii_uppercase for letter2 in ascii_uppercase]  # extended list once map width exceeds 26 grid squares (A-Z + AA - ZZ)

        x_coords = AZZ[:(int(self.map.width/GRIDWIDTH))]  # grid squares along map length [A, B, C, D ...
        y_coords = [str(n) for n in range(int(self.map.height/GRIDHEIGHT))]  # ""            "" map height  [0, 1, 2, 3 ...
        return x_coords, y_coords  # for future grid lookup

    def generate_map_layer(self):

        map_layer = {}
        # generate grid squares
        for i, grid_col in enumerate(self.x_coords):
            for j, grid_row in enumerate(self.y_coords):

                grid_ref = (grid_col+grid_row)  # 'A1'
                x1, y1 = (i * GRIDWIDTH), (j * GRIDHEIGHT)  # top left corner
                x2, y2 = x1+GRIDWIDTH, y1+GRIDHEIGHT  # bottom right corner
                grid = Grid(grid_ref, x1, y1, x2, y2)  # instance of Grid sprite.Group
                map_layer[grid_ref] = grid  # append key:value - 'A1': grid to grid_squares dictionary

        return map_layer

    # def sprite_starting_grid(self, sprite):
    #     """Assign sprite to grid on game init.  Mobile sprites reassigned as they travel across the map, and can be in more than one grid"""
    #
    #     (x, y) = sprite.rect.center
    #     grid_col = self.x_coords[x//GRIDWIDTH]
    #     grid_row = self.y_coords[y//GRIDHEIGHT]
    #     grid_ref = (grid_col + grid_row)
    #     self.grid_squares[grid_ref].add(sprite)

    def read_map_data(self):
        """load map data from map.txt file: create platform, enemy sprites accordingly"""
        # TODO individual map layers for platforms, mobs, items etc, each divided into grid square spritegroups
        for row, tiles in enumerate(self.map.data):
            for col, tile in enumerate(tiles):

                # load platform tiles:  walls, roof, floors ...
                platform_type = PLATFORMKEY.get(tile)
                if platform_type:
                    img = random.choice(self.platform_images[platform_type])  # randomly select platform image

                    # tile sprites around map edges not included in self.walls map layer (no collision detection or interaction with mobile sprites)
                    if row == 0 or row == len(self.map.data)-1:
                        tile = Static_sprite(self, col, row, platform_type, img)
                    elif col == 0 or col == len(self.map.data[row])-1:
                        tile = Static_sprite(self, col, row, platform_type, img)

                    # tunnel entrances also for visuals only
                    elif platform_type == 'tunnelLeft':
                        tile = Static_sprite(self, col, row, platform_type, img)
                    elif platform_type == 'tunnelRight':
                        tile = Static_sprite(self, col, row, platform_type, img)
                    # all other platforms added to self.walls (collision, avoid walls etc)
                    else:
                        tile = Platform(self, col, row, platform_type, img)
                    # create spawnpoints above floor platforms
                    if platform_type == 'floor':
                        self.spawnpoints.append((col, row))

                    self.all_sprites.add(tile)  # for drawing only

                # load enemy sprites
                if tile == 'E':

                    mobkey = random.choice(list(Game.MOBCLASSES.keys()))  # random choice of mob class

                    img = self.mob_images[mobkey][0]
                    mob = Game.MOBCLASSES[mobkey](self, col, row, mobkey, img)
                    # self.sprite_starting_grid(mob)
                    # self.mob_sprites.add(mob)
                    # self.active_sprites.add(mob)
                    self.all_sprites.add(mob)

    def spawn_sprites(self, index, spawnpoint, n, spriteclass, spritekey, imglocation):
        """ spawn secondary sprites/ background images not included within map data at random locations e.g. plants, bubble effects, pickups """

        if index % n == 0:
            img = random.choice(imglocation[spritekey])  # select random image
            col = spawnpoint[0]
            row = spawnpoint[1]
            sprite = spriteclass(self, col, row, spritekey, img)
            sprite.rect.bottomleft = sprite.pos  # sprite placed on top of platform
            self.all_sprites.add(sprite)
            return sprite

    def generate_environment(self):
        # TODO Refactor generate_environment with a generator
        """ call spawn_sprites() to generate background images, background effects e.g. rising bubbles and pickup sprites"""
        """ NEEDS REPLACING WITH A GENERATOR"""
        random.shuffle(self.spawnpoints)
        for i, point in enumerate(self.spawnpoints):

            # static sprites
            sprite = self.spawn_sprites(i, point, 200, Static_sprite, 'monument', self.prop_images)  # for every 200th floor tile spawn a monument
            sprite = self.spawn_sprites(i, point, 50, Static_sprite, 'Statue', self.prop_images)  # for every 50th floor tile spawn a statue
            sprite = self.spawn_sprites(i, point, 3, Static_sprite, 'vegetation', self.prop_images)

            # mobile sprites
            # sprite = self.spawn_sprites(i, point, 256, Bubbles, 'bubbles', self.effects_images)
            # if sprite:
            #     if sprite.refkey == 'bubbles':
            #         self.active_sprites.add(sprite)

    def new(self):
        """Start a new game; initialise all vairables, load or reload map data, sprites"""
        # init sprite groups
        self.mob_sprites = pygame.sprite.Group()  # TESTING ONLY
        self.platform_sprites = pygame.sprite.Group()  # TESTING ONLY
        self.hold_sprites = pygame.sprite.Group()  # sprites to be deleted once they go off screen
        self.active_sprites = pygame.sprite.Group()  # sprites which are updated every loop
        self.all_sprites = pygame.sprite.Group()  # for drawing only

        # map layers (dictionaries) divided into grids (4 X 4 TILES). Grid class inherets pygame.sprite.Group for storing sprites
        self.grid_squares = self.generate_map_layer()  # empty grid TESTING ONLY
        self.players = self.generate_map_layer()
        self.walls = self.generate_map_layer()
        self.pickups = self.generate_map_layer()
        self.weapons = self.generate_map_layer()
        self.enemies = self.generate_map_layer()

        # generate sprites
        self.player = Player(self, 12, 15, 'player', self.player_images['player_idle'][0])  # xpos, ypos, width, height (in TILES i.e. 1 TILE X 2 TILES), image (first frame of North orientation by default)
        # self.active_sprites.add(self.player)
        self.all_sprites.add(self.player)
        self.read_map_data()
        self.generate_environment()

    def run(self):
        """ Main game loop"""
        self.playing = True
        while self.playing:
            self.dt = self.clock.tick(FPS) / 1000  # time elapsed during a single loop (seconds)
            self.dt = max(0.001, (min(0.1, self.dt)))
            self.elapsed_time += self.dt
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
                self.player.shoot()

            if event.type == pygame.KEYDOWN:
                # player actions (movement controls determined by key.get_pressed in Player class)
                if event.key == pygame.K_LCTRL:
                    self.player.shoot()
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
        # self.active_sprites.update()

        # update sprites by grid
        # self.player.update()
        # self.player.pos += self.player.vel
        for map_layer in [self.players, self.pickups, self.weapons, self.enemies]:

            for gridref in map_layer:
                grid = map_layer[gridref]  # return grid (spritegroup)
                grid.update()  # call update function for all sprites in grid
                for sprite in grid:
                    sprite.pos += sprite.vel  # update sprite positions individually

        # update hold_sprites
        for sprite in self.hold_sprites:
            sprite.vel *= 0.95  # velocity halved each loop
            sprite.pos += sprite.vel
            sprite.hitrect.center = sprite.pos  # must update hitrect rather than rect as rect position overwritten in Mobile_sprite.transform_image()
            print(sprite.vel)
            if sprite.check_anim_end(sprite.current_animation):
                sprite.kill()

        self.camera.update(self.player)  # change camera rect position according to player position (centred on player rect)
        # for mob in self.mob_sprites:
        #     self.camera.update(mob)

        # TODO - limit holding group size
        for sprite in self.hold_sprites:
            if sprite.rect.right < (0-self.camera.rect.left) or sprite.rect.left > (2*SCREENWIDTH-self.camera.rect.right):
                sprite.kill()
            if sprite.rect.bottom < (0-self.camera.rect.top) or sprite.rect.top > (2*SCREENHEIGHT-self.camera.rect.bottom):
                sprite.kill()

    def draw_text(self, text, size, colour, x, y):

        font = pygame.font.Font('freesansbold.ttf', size)  # text font
        text_surface = font.render(text, True, colour)
        text_surface.convert()
        text_rect = text_surface.get_rect()
        text_rect.center = (x, y)
        self.screen.blit(text_surface, text_rect)

    def draw_grid(self):  # (rows,columns)
        # Display grid squares for testing #
        font = pygame.font.Font('freesansbold.ttf', 16)
        text = font.render('GeeksForGeeks', True, GREEN, BLUE)

        for grid_ref, sptgrp in self.grid_squares.items():

            x1 = self.x_coords.index(grid_ref[0]) * GRIDWIDTH
            y1 = self.y_coords.index(grid_ref[1]) * GRIDHEIGHT
            x1 = x1 + self.camera.rect.x  # update with camera movement
            y1 = y1 + self.camera.rect.y
            pygame.draw.rect(self.screen, WHITE, [x1, y1, (GRIDWIDTH), (GRIDHEIGHT)], 1)
            text = font.render(grid_ref, True, GREEN, BLUE)
            textRect = text.get_rect()
            textRect.topleft = (x1, y1)
            self.screen.blit(text, textRect)

    def draw(self):
        """Game Loop - draw"""
        pygame.display.set_caption("{:.2f}".format(self.clock.get_fps()))
        self.screen.blit(self.background, (self.camera.rect.x, self.camera.rect.y))  # draw background

        # blit all map sprites, content
        for sprite in self.all_sprites:
            sprite.draw()

        # HUD functions
        draw_player_health(self.screen, 0.5*SCREENWIDTH, 10, self.player.health / Player.health)

        # TESTING ONLY #

        self.draw_grid()

        # current_grids = str(self.player.current_grids)
        # self.draw_text(current_grids, 22, RED, SCREENWIDTH / 2, 15)

        # camera.rect offset
        camera_position = (self.camera.rect.left, self.camera.rect.right)
        camera_position = str(camera_position)
        # self.draw_text(camera_position, 22, RED, SCREENWIDTH/2, SCREENHEIGHT - 15)

        # player data
        pos = str(self.player.pos)
        # self.draw_text(pos, 22, RED, 100, 15)
        velocity = str(self.player.vel)
        # self.draw_text(velocity, 22, RED, SCREENWIDTH - 50, 15)
        # pygame.draw.rect(self.screen, WHITE, self.player.rect, 2)  # player rect
        # pygame.draw.rect(self.screen, RED, self.player.hitrect, 2)  # player hitrect
        # pygame.draw.line(self.screen, RED, (self.player.pos.x, self.player.pos.y), (self.player.pos.x + self.player.direction.x * 100, self.player.pos.y + self.player.direction.y * 100), 1)  # player velocity vector
        # pygame.draw.line(self.screen, GREEN, (self.player.pos.x, self.player.pos.y), (self.player.pos.x + self.player.vel.x * 10, self.player.pos.y + self.player.vel.y * 10), 3)  # player velocity vector

        # mob data
        for mob in self.mob_sprites:
            # pygame.draw.rect(self.screen, RED, mob.rect, 2)
            # pygame.draw.rect(self.screen, WHITE, mob.avoidRect, 2)

            pygame.draw.circle(self.screen, WHITE, (int(mob.rect.centerx), int(mob.rect.centery)), int(mob.radius), 1)  # draw effective radius
            # pygame.draw.circle(self.screen, RED, (int(mob.target.x), int(mob.target.y)), 10, 1)  # draw target position
            # pygame.draw.circle(self.screen, RED, (int(mob.pos.x + mob.target_vec.x), int(mob.pos.y + mob.target_vec.y)), 10, 1)
            # pygame.draw.circle(self.screen, RED, (int(mob.rect.centerx), int(mob.rect.centery)), 10, 1)
            vel = str((round(mob.vel[0], 1), round(mob.vel[1], 1)))
            speed = str(round(mob.vel.length(), 1))
            # target_angle = str(round(mob.target_angle, 0))

            # self.draw_text(vel, 22, RED, SCREENWIDTH - 100, 15)

            # draw vectors
            # pygame.draw.line(self.screen, WHITE, (mob.pos.x, mob.pos.y), (mob.pos.x + mob.target_vec.x, mob.pos.y + mob.target_vec.y), 3)  # target vector
            # pygame.draw.line(self.screen, GREEN, (mob.pos.x, mob.pos.y), (mob.pos.x + mob.displacement.x, mob.pos.y + mob.displacement.y), 3)  # displacement vector
            # pygame.draw.line(self.screen, RED, (mob.pos.x, mob.pos.y), (mob.pos.x + mob.anti_g.x, mob.pos.y + mob.anti_g.y), 3)  # accn away from wall tiles
            # pygame.draw.line(self.screen, GREEN, (mob.pos.x, mob.pos.y), (mob.pos.x + mob.vel.x * 10, mob.pos.y + mob.vel.y *  10), 3)  # velocity vector
            # pygame.draw.line(self.screen, GREEN, (mob.pos.x, mob.pos.y), (mob.pos.x + mob.alt_rad.x, mob.pos.y + mob.alt_rad.y), 3)  # current rad from origin
            # pygame.draw.line(self.screen, YELLOW, (self.player.pos.x, self.player.pos.y), (self.player.pos.x + mob.target_rad.x, self.player.pos.y + mob.target_rad.y), 6)  # target rad from player to origin
            # pygame.draw.line(self.screen, RED, (self.player.pos.x, self.player.pos.y), (self.player.pos.x + mob.actual_rad.x, self.player.pos.y + mob.actual_rad.y), 3)  # final rad after subtending angle delta

            # pygame.draw.line(self.screen, RED, (mob.pos.x, mob.pos.y), (mob.pos.x + mob.vel.x, mob.pos.y + mob.vel.y), 3)  # velocity vector

        # Missiles
        for grid in self.weapons:
            for missile in self.weapons[grid]:
                pygame.draw.rect(self.screen, RED, missile.hitrect, 2)  # player hitrect
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