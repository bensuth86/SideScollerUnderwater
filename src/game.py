# Project setup

import pygame
import time
from os import path

from .settings import *
from .config import IMAGE_PATH, MAPS_PATH, MUSIC_PATH, AMBIENT_PATH, WEAPONSND_PATH, MOBILE_SPRITE_CLASSES
from .helpers import resolve_class, resize_images, load_spritesheets
from .systems import TiledMap, Camera, ObjectPool, Mesh
from .ui.hud import draw_sprite_bar, draw_text, draw_grid
from .sprites import Pick_up, Player, Missile


class Game:

    def __init__(self, screen):

        self.screen = screen
        self.camera = Camera(self)

        self.clock = pygame.time.Clock()
        self.elapsed_time = time.time()  # from new game start
        self.dt = 0  # time elapsed for 1 mainloop
        self.running = True  # game running

        # load background textures
        self.background = pygame.image.load(path.join(IMAGE_PATH, BACKGROUND)).convert_alpha()

        # load map from TiledMap #
        PlatformClass = resolve_class('src.sprites.Platform')
        map_dir = path.join(MAPS_PATH, 'test.tmx')
        self.map = TiledMap(self, map_dir, PlatformClass)

        # comment explaining next 2 lines
        self.map_img = self.map.generate_map()
        # self.map_img.set_colorkey(BLACK)  # set background to be transparent
        self.map_rect = self.map_img.get_rect()

        # get images from spritesheets and cache image surf to dictionary - dictionary ordered by category, then nested subcat if applicable
        self.effects_images = load_spritesheets('effects')
        self.effects_images['enemydeath4x4'] = resize_images(self.effects_images.get('enemydeath'), (4 * self.map.tilesize, 4 * self.map.tilesize))
        self.effects_images['explosion4x4'] = resize_images(self.effects_images.get('explosion'), (4 * self.map.tilesize, 4 * self.map.tilesize))

        self.pickup_images = load_spritesheets('PickUps')

        mobile_spritesheets = ['mobs', 'player', 'weapons']
        self.mobile_sprite_images = load_spritesheets(*mobile_spritesheets)

        # load sounds
        pygame.mixer.music.load(path.join(MUSIC_PATH, MUSIC['Intro_music']))

        self.effects_sounds = {key: [pygame.mixer.Sound(path.join(AMBIENT_PATH, snd)) for snd in AMBIENT_SOUNDS[key]] for key in AMBIENT_SOUNDS}
        [snd.set_volume(0.3) for snd in self.effects_sounds['torpedo_explode']]
        [snd.set_volume(1) for snd in self.effects_sounds['mine_explode']]
        [snd.set_volume(0.1) for snd in self.effects_sounds['mob_hit']]

        self.weapon_shoot_sounds = {key: [pygame.mixer.Sound(path.join(WEAPONSND_PATH, snd)) for snd in WEAPON_SHOOT_SOUNDS[key]] for key in WEAPON_SHOOT_SOUNDS}
        [snd.set_volume(0.3) for snd in self.weapon_shoot_sounds['harpoon']]
        [snd.set_volume(0.2) for snd in self.weapon_shoot_sounds['torpedo']]

        self.objectpools = {}

    def new(self):
        """Start a new game; initialise all variables, load or reload map data, sprites"""
        # init sprite groups
        self.mob_sprites = pygame.sprite.Group()
        self.hold_sprites = pygame.sprite.Group()  # sprites to be deleted- group for visual effects only
        self.all_sprites = pygame.sprite.Group()  # for drawing only

        # Object pools
        for key in MOBILE_SPRITE_CLASSES.keys():
            SpriteClass = resolve_class(MOBILE_SPRITE_CLASSES[key])
            self.objectpools[key] = ObjectPool(self, SpriteClass, 20)

        # generate static sprites from TiledMap Tile layers
        for key, ttl in self.map.tmxdata.layernames.items():  # ttl - TiledTileLayer
            if ttl.visible:
                if key == 'pickups':
                    for pickup in ttl:
                        pickup_sprite = Pick_up(self, pickup.x, pickup.y, pickup.width, pickup.height, pickup.image, pickup.name)
                        self.all_sprites.add(pickup_sprite)

        # generate mobile sprites from TiledMap object layers
        for key, tog in self.map.tmxdata.layernames.items():  # ttl - TiledObjectGroup
            if tog.visible:
                if key == 'players':
                    for player in tog:
                        self.player = Player(self, player.x, player.y)  # xpos, ypos, width, height
                        self.all_sprites.add(self.player)

                if key == 'obstacles':
                    for obstacle in tog:
                        if obstacle.name == 'Mine':
                            x, y = obstacle.x + obstacle.width / 2, obstacle.y + obstacle.height / 2
                            self.objectpools['mine'].borrow_object(x, y)

        # generate enemies from TiledMap object layers
        for i, enemy in enumerate(self.map.tmxdata.layernames['enemies']):
            if enemy.name == 'Enemy':  # if mob child class is not specified
                if i + 1 % 3 == 0:  # every 3rd mob generated
                    mobkey = 'spinefish'
                elif i + 1 % 20 == 0:  # every 10th mob generated
                    mobkey = 'daddyfish'
                else:
                    mobkey = 'dartfish'
            else:  # mob child class is determined
                mobkey = enemy.name
            x, y = enemy.x + enemy.width / 2, enemy.y + enemy.height / 2
            mob = self.objectpools[mobkey].borrow_object(x, y)

            self.mob_sprites.add(mob)  # TESTING ONLY

        self.mesh = Mesh(self)  # load Mesh TESTING ONLY

    def run(self):

        # """ Main game loop"""
        self.playing = True
        # pygame.mixer.music.play(loops=-1)

        while self.playing:
            # self.dt = self.clock.tick(FPS) / 1000  # time elapsed during a single loop (seconds)
            self.clock.tick_busy_loop(FPS)
            # print(self.clock.get_fps())
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

    def transfer_sprites(self, sprites_to_transfer):
        """ Transfer flagged sprites to new grid within their map layer"""
        if sprites_to_transfer:
            for sprite in sprites_to_transfer:
                self.map.layers[sprite.map_layer][sprite.gridref].remove(sprite)
                self.map.layers[sprite.map_layer][sprite.next_grid].add(sprite)
                sprite.gridref = sprite.next_grid
                # return missile sprites not in active sprites list to Objectpool
                if sprite.gridref not in self.map.active_gridrefs:
                    if isinstance(sprite, Missile):  # if missile sprite
                        self.objectpools[sprite.refkey].rtrn_object(sprite)

    def update(self):
        """Game Loop - Update"""
        self.camera.update(self.player)  # change camera rect position according to player position (centred on player rect)
        # for mob in self.mob_sprites:
        #     self.camera.update(mob)

        # update sprites by grid
        self.map.get_active_grids()  # grids which are on screen and adjacent to screen boundaries
        sprites_to_transfer = []  # sprites to be moved to new grid for current update

        # call mobile sprite update fnc then update new rect position
        for map_layer in self.map.mobile_layers:
            grids = self.map.layers[map_layer]  # return dictionary containing grids (sprite groups)
            for ref in self.map.active_gridrefs:  # 'A0', 'A1', 'A2' ...
                grids[ref].update()
                # post sprite update call for current grid, update sprite positions and transfer sprites to new grid where applicable
                for sprite in grids[ref]:
                    sprite.pos += sprite.vel * self.dt * TARGET_FPS  # update position independent of frame rate

                    # reference sprites to be transferred to new grid
                    if sprite.flag_transfer_sprite():
                        sprites_to_transfer.append(sprite)

        self.transfer_sprites(sprites_to_transfer)  # transfer flagged sprites to new grid

        # update hold_sprites
        for sprite in self.hold_sprites:
            sprite.vel *= 0.98  # velocity reduced each loop
            sprite.pos += sprite.vel
            sprite.hitrect.center = sprite.pos  # must update hitrect rather than rect as rect position overwritten in Mobile_sprite.transform_image()

            # return sprites to object pools after 1 animation cycle
            if sprite.check_anim_end(sprite.current_animation):
                self.objectpools[sprite.refkey].rtrn_object(sprite)

        # return sprites to pools if they're off screen
        for sprite in self.hold_sprites:
            if sprite.gridref not in self.map.active_gridrefs:
                self.objectpools[sprite.refkey].rtrn_object(sprite)

    def draw(self):
        """Game Loop - draw"""
        pygame.display.set_caption("{:.2f}".format(self.clock.get_fps()))
        # self.screen.blit(self.background, (self.camera.camera_rect.x, self.camera.camera_rect.y))  # draw background
        self.screen.fill(DEEPBLUE)
        offset_x, offset_y = self.camera.apply_rect(self.map_rect)
        self.screen.blit(self.map_img, (int(offset_x), int(offset_y)))

        # blit all map sprites, content
        for sprite in self.all_sprites:
            sprite.draw()

        # HUD functions
        draw_sprite_bar(self.screen, 0.2 * SCREENWIDTH, 10, self.player.hitpoints / Player.hitpoints, GREEN, YELLOW, RED)
        draw_sprite_bar(self.screen, 0.8 * SCREENWIDTH, 10, self.player.stamina / Player.stamina, RED, BLUE, PURPLE)
        draw_text(self, self.player.current_weapon, 20, RED, 0.4 * SCREENWIDTH, 15)  # current weapon

        draw_text(self, str(self.player.ammo[self.player.current_weapon]), 20, RED, 0.6 * SCREENWIDTH, 15)
        for grid in self.map.layers['obstacles'].values():
            for sprite in grid:
                if sprite.refkey == 'mine':
                    if sprite.active:
                        draw_text(self, str(int(sprite.countdown + 1)), 50, RED, sprite.rect.centerx - self.camera.pos.x, sprite.rect.centery - self.camera.pos.y)

        # TESTING ONLY #

        draw_grid(self)
        # self.mesh.draw()

        # current_grids = str(self.player.current_grids)
        # self.draw_text(current_grids, 22, RED, SCREENWIDTH / 2, 15)

        # camera.rect offset

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

        pygame.draw.rect(self.screen, WHITE, self.player.rect, 2)  # player rect
        pygame.draw.rect(self.screen, RED, self.player.hitrect, 2)  # player hitrect
        # pygame.draw.line(self.screen, RED, (self.player.pos.x, self.player.pos.y), (self.player.pos.x + self.player.direction.x * 100, self.player.pos.y + self.player.direction.y * 100), 1)  # player velocity vector
        # pygame.draw.line(self.screen, GREEN, (self.player.pos.x, self.player.pos.y), (self.player.pos.x + self.player.vel.x * 10, self.player.pos.y + self.player.vel.y * 10), 3)  # player velocity vector

        for grid in self.map.layers['weapons'].values():
            for sprite in grid:
                # pygame.draw.rect(self.screen, WHITE, sprite.rect, 2)  # missile rect
                pygame.draw.rect(self.screen, RED, sprite.hitrect, 2)  # missile hitrect
                pass

        # mob data
        for mob in self.mob_sprites:
            x_pos = mob.pos.x - self.camera.pos.x
            y_pos = mob.pos.y - self.camera.pos.y

            # draw_sprite_bar(self.screen, x_pos - 50, y_pos - 50, mob.hitpoints / mob.__class__.hitpoints, GREEN, YELLOW, RED)
            # pygame.draw.rect(self.screen, WHITE, mob.rect, 2)
            # pygame.draw.rect(self.screen, RED, mob.hitrect, 2)

            anti_g = str((round(mob.anti_g.x, 3), round(mob.anti_g.y, 3)))
            anti_g_size = str((round(mob.anti_g.length(), 3)))
            # self.draw_text(anti_g_size, 22, RED, SCREENWIDTH / 2, SCREENHEIGHT - 15)

            # pygame.draw.circle(self.screen, WHITE, (int(mob.rect.centerx), int(mob.rect.centery)), int(mob.radius), 1)  # draw effective radius
            pygame.draw.circle(self.screen, RED, (int(mob.target.x - self.camera.pos.x), int(mob.target.y - self.camera.pos.y)), 10, 1)
            # pygame.draw.circle(self.screen, RED, (int(x_pos), int(y_pos)), 10, 1)
            vel = str((round(mob.vel[0], 1), round(mob.vel[1], 1)))
            speed = str(round(mob.vel.length(), 1))
            # self.draw_text(speed, 22, GREEN, SCREENWIDTH / 2, SCREENHEIGHT - 35)

            # target_angle = str(round(mob.target_angle, 0))

            # draw vectors

            # pygame.draw.line(self.screen, WHITE, (x_pos, y_pos), (x_pos + mob.target_vec.x, y_pos + mob.target_vec.y), 3)  # target vector
            # pygame.draw.line(self.screen, RED, (x_pos, y_pos), (x_pos + mob.anti_g.x*10000, y_pos + mob.anti_g.y*10000), 3)  # accn away from wall tiles
            # pygame.draw.line(self.screen, GREEN, (x_pos, y_pos), (x_pos + (mob.vel.x*5), y_pos + (mob.vel.y*5)), 3)  # velocity vector
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
        draw_text(self, "GAME OVER", 48, RED, SCREENWIDTH / 2, SCREENHEIGHT / 4)
        pygame.display.flip()
