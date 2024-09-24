# Project setup

import pygame
import random
from string import ascii_uppercase
from settings import *
from helpers.spritesheet_functions import *
from helpers.interval_trigger import *
from helpers.transform_images import *
from sprites import *

# mob_spritesheet = SpriteSheet('mobs')
# mob_images = mob_spritesheet.get_sprite_images(MOBS)


class Camera:

    def __init__(self, game):

        self.rect = pygame.Rect(0, 0, SCREENWIDTH, SCREENHEIGHT)
        self.game = game

    def update(self, target):
        # update camera offset according to player's new position
        x_offset = -target.rect.centerx + int(SCREENWIDTH / 2)  # player moves right, map moves left relative to camera.  Add half screen width to keep player centred on screen
        y_offset = -target.rect.centery + int(SCREENHEIGHT / 2)  # player moves up, map moves down ""            ""

        # limit scrolling to map size
        x_offset = min(0, x_offset)  # left map edge
        y_offset = min(0, y_offset)  # top map edge
        x_offset = max(-(self.game.map.width - SCREENWIDTH), x_offset)  # right map edge
        y_offset = max(-(self.game.map.height - SCREENHEIGHT), y_offset)  # bottom map edge

        # # reposition camera rect  (remove/ comment out to 'switch off' camera)
        self.rect.x = x_offset
        self.rect.y = y_offset

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


class Grid(pygame.sprite.Group):
    """Divide map into grid squares determined by GRIDHEIGHT, GRIDWIDTH.  Mobile sprites transfered to new grid sprite group
     as they travel across the map for collision detection"""

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
        # self.playerswim_images = self.player_spritesheet.get_sprite_images("player_swim", PLAYERMOBSDIM)

        # duplicate and transform images then append to dictionary
        # for key, value in self.mob_images.items():
        #     mobsInverted = flip_images(value, (False, True))  # upside down mobs
        #     self.mob_images[key] = (value, mobsInverted)  # tuple for holding (Upfacing, Downfacing)  images

        # get effects sprites
        self.effects_images['enemyDeath2x1'] = resize_images(self.effects_images.get('enemyDeath'), (2*TILESIZE, 1*TILESIZE))
        self.effects_images['enemyDeath4x4'] = resize_images(self.effects_images.get('enemyDeath'), (4 * TILESIZE, 4 * TILESIZE))

        # harpoon image rotated through 45 deg increments and stored to dictionary
        self.weapons_images['harpoonNorthEast'] = rotate_images(self.weapons_images.get('harpoonEast'), 45)
        self.weapons_images['harpoonNorth'] = rotate_images(self.weapons_images.get('harpoonEast'), 90)
        self.weapons_images['harpoonNorthWest'] = rotate_images(self.weapons_images.get('harpoonEast'), 135)
        self.weapons_images['harpoonWest'] = rotate_images(self.weapons_images.get('harpoonEast'), 180)
        self.weapons_images['harpoonSouthWest'] = rotate_images(self.weapons_images.get('harpoonEast'), 225)
        self.weapons_images['harpoonSouth'] = rotate_images(self.weapons_images.get('harpoonEast'), 270)
        self.weapons_images['harpoonSouthEast'] = rotate_images(self.weapons_images.get('harpoonEast'), 315)

        self.map = Map(path.join(repos, 'map.txt'))  # create map object from Map class, tilemap.py
        self.grid_squares = []  # game map divided into grids (4 X 4 TILES). Grid class inherets pygame.sprite.Group for storing sprites
        self.grid_setup()

        self.spawnpoints = []  # locations adjacent platforms for spawning background props, pickups, effects etc

    def grid_setup(self):

        # setup coords (A1, A2, A3 ....)
        AZ = list(ascii_uppercase)  # list alphabet A-Z
        AZZ = AZ + list(ascii_uppercase) + [letter1+letter2 for letter1 in ascii_uppercase for letter2 in ascii_uppercase]  # extended list once map width exceeds 26 grid squares (A-Z + AA - ZZ)

        x_grids = int((self.map.width - 2*TILESIZE)/(GRIDWIDTH))  # total count of grid squares along map length
        y_grids = int((self.map.height - 2*TILESIZE)/(GRIDHEIGHT))  # total ""            "" map height

        # generate grid squares
        for j in range(y_grids):
            x_coord = AZZ[j]  # 'A'
            grid_row = []
            for i in range(x_grids):
                y_coord = str(i+1)  # '1'
                grid_ref = (x_coord+y_coord)  # 'A1'
                x1, y1 = TILESIZE + (i*GRIDWIDTH), TILESIZE + (j*GRIDHEIGHT)  # top left corner
                x2, y2 = x1+(GRIDWIDTH), y1+(GRIDHEIGHT)  # bottom right corner
                grid = Grid(grid_ref, x1, y1, x2, y2)
                grid_row.append(grid)
            self.grid_squares.append(grid_row)  # each row nested list within main list

    def assign_sprite_to_grid(self, sprite):
        """ static sprites; platforms, pickups etc assigned on game init.  Mobile sprites reassigned as they travel across the map"""

        (x_coord, y_coord) = sprite.rect.center
        grid_col = (x_coord-TILESIZE)//(GRIDWIDTH)
        grid_row = (y_coord-TILESIZE)//(GRIDHEIGHT)
        self.grid_squares[grid_row][grid_col].add(sprite)

    def read_map_data(self):
        """load map data from map.txt file: create platform, player, enemy sprites accordingly"""

        for row, tiles in enumerate(self.map.data):
            for col, tile in enumerate(tiles):

                # load platform tiles:  walls, roof, floors ...
                platform_type = PLATFORMKEY.get(tile)
                if platform_type:
                    img = random.choice(self.platform_images[platform_type])  # randomly select platform image
                    ptf = Static_sprite(self, col, row, platform_type, img)

                    if row in range(1, len(self.map.data)-1) and col in range(1, len(self.map.data[0])-1):  # exclude map boundary sprites
                        if platform_type != 'tunnelLeft' and platform_type != 'tunnelRight':  # exclude tunnel entrance
                            self.assign_sprite_to_grid(ptf)

                    self.platform_sprites.add(ptf)
                    self.all_sprites.add(ptf)
                    if platform_type == 'floor':
                        self.spawnpoints.append((col, row))  # create spawnpoints adjacent to platform

                # load enemy sprites
                # mob_type = MOBSKEY.get(tile)
                if tile == 'E':
                    mobkey = random.choice(list(Game.MOBCLASSES.keys()))  # random choice of mob class
                    img = self.mob_images[mobkey][0]
                    mob = Game.MOBCLASSES[mobkey](self, col, row, mobkey, img)
                    self.mob_sprites.add(mob)
                    self.all_sprites.add(mob)

    def spawn_sprites(self, index, spawnpoint, n, spriteclass, spritekey, imglocation):
        """ spawn secondary sprites/ background images not included within map data at random locations e.g. plants, bubble effects, pickups """

        if index % n == 0:
            img = random.choice(imglocation[spritekey])  # select random image
            col = spawnpoint[0]
            row = spawnpoint[1]
            sprite = spriteclass(self, col, row, spritekey, img)
            sprite.rect.bottomleft = sprite.pos  # ensure sprite placed above spawnpoint
            self.all_sprites.add(sprite)

    def generate_environment(self):
        """ call spawn_sprites() to generate background images, background effects e.g. rising bubbles and pickup sprites"""

        random.shuffle(self.spawnpoints)
        for i, point in enumerate(self.spawnpoints):

            # self.spawn_sprites(i, point, 200, Static_sprite, 'monument', self.prop_images)  # at every 200th floor tile spawn a monument
            # self.spawn_sprites(i, point, 50, Static_sprite, 'Statue', self.prop_images)  # at every 50th floor tile spawn a statue
            self.spawn_sprites(i, point, 3, Static_sprite, 'vegetation', self.prop_images)
            # self.spawn_sprites(i, point, 256, Bubbles, 'bubbles', self.effects_images)


    def new(self):
        """Start a new game; load or reload map data, sprites"""
        # init sprite groups
        self.platform_sprites = pygame.sprite.Group()
        self.mob_sprites = pygame.sprite.Group()
        self.hold_sprites = pygame.sprite.Group()  # sprites not to be drawn (move sprites between hold and all_sprites if desired)
        self.all_sprites = pygame.sprite.Group()

        # generate sprites
        self.player = Player(self, 6, 16, 'player', self.player_images['player_idle']['North'][0])  # xpos, ypos, width, height (in TILES i.e. 1 TILE X 2 TILES), image (first frame of North orientation by default)
        self.all_sprites.add(self.player)
        self.read_map_data()
        self.generate_environment()

    def run(self):
        """ Main game loop"""
        self.playing = True
        while self.playing:
            self.dt = self.clock.tick(FPS) / 1000  # time elapsed during a single loop (seconds)
            self.elapsed_time += self.dt
            self.events()
            self.update()
            self.draw()

    def events(self):

        for event in pygame.event.get():
            # check for closing pygame window
            if event.type == pygame.QUIT:
                if self.playing:  # if in game
                    self.playing = False  # exit game
                self.running = False  # close pygame application

            if event.type == pygame.KEYDOWN:
                # player actions (movement controls determined by key.get_pressed in Player class)
                if event.key == pygame.K_LCTRL:
                    self.player.shoot()

                if event.key == pygame.K_q:
                    self.playing = False  # exit game

    def update(self):
        """Game Loop - Update"""
        self.player.update()
        self.all_sprites.update()
        self.camera.update(self.player)  # change camera rect position according to player position (centred on player rect)
        # for sprite in self.mob_sprites:
        #     self.camera.update(sprite)

    def draw_text(self, text, size, colour, x, y):

        font = pygame.font.Font('freesansbold.ttf', size)  # text font
        text_surface = font.render(text, True, colour)
        text_rect = text_surface.get_rect()
        text_rect.center = (x, y)
        self.screen.blit(text_surface, text_rect)

    def draw_grid(self):  # (rows,columns)
        # Display grid squares for testing #
        font = pygame.font.Font('freesansbold.ttf', 16)
        text = font.render('GeeksForGeeks', True, GREEN, BLUE)

        for row in self.grid_squares:
            for grid in row:
                x1 = grid.x1
                y1 = grid.y1
                x1 = x1 + self.camera.rect.x  # update with camera movement
                y1 = y1 + self.camera.rect.y
                pygame.draw.rect(self.screen, WHITE, [x1, y1, (GRIDWIDTH), (GRIDHEIGHT)], 1)
                text = font.render(grid.coordinates, True, GREEN, BLUE)
                textRect = text.get_rect()
                textRect.topleft = (x1, y1)
                self.screen.blit(text, textRect)

    def draw(self):
        """Game Loop - draw"""
        pygame.display.set_caption("{:.2f}".format(self.clock.get_fps()))
        self.screen.blit(self.background, (0, 0))  # draw background

        for sprite in self.all_sprites:
            sprite.draw()

        # Testing only #
        self.draw_grid()

        # current_grids = str(self.player.current_grids)
        # self.draw_text(current_grids, 22, RED, SCREENWIDTH / 2, 15)

        camera_position = str(self.camera.rect)
        self.draw_text(camera_position, 22, RED, SCREENWIDTH/2, SCREENHEIGHT- 15)

        vel = str(self.player.vel)
        self.draw_text(vel, 22, RED, SCREENWIDTH - 100, 15)
        # self.draw_text(self.player.direction, 22, RED, SCREENWIDTH - 50, 15)
        velocity = str(self.player.vel)
        # self.draw_text(velocity, 22, RED, SCREENWIDTH - 50, 15)
        for mob in self.mob_sprites:
            vel = (round(mob.vel[0], 3), round(mob.vel[1], 3))
            speed = mob.vel.length()
            vel = str(vel)
            speed = str(round(speed))

            # self.draw_text(speed, 22, RED, SCREENWIDTH - 100, 15)
            # angle = str(round(mob.angle, 1))
            # target_angle = str(round(mob.target_angle, 1))
            # self.draw_text(angle, 22, RED, 30, 30)
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