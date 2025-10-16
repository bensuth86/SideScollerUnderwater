# Project setup

import json
import pygame
import time
from os import path
from pathlib import Path

from .settings import *
from .helpers import resolve_class, resize_images, load_spritesheets, load_json, _map_keyboard_controls, _map_mouse_controls
from .systems import TiledMap, Camera, ObjectPool, Mesh
from .ui.hud import draw_sprite_bar, draw_text, draw_grid
from src import sprites
from .sprites import Pickup, Player, Missile


class Game:

    def __init__(self, screen):

        self.screen = screen
        self.clock = pygame.time.Clock()
        self.elapsed_time = time.time()  # from new game start
        self.dt = 0  # time elapsed for 1 mainloop
        self.running = True  # game running

        # --- Load JSON configuration ---
        self._load_all_configs()

        # --- Core systems ---
        self.camera = Camera(self)

        # --- Load background ---
        bg_path = self.image_path / self.image_config["images"]["background"]
        if not bg_path.exists():
            raise FileNotFoundError(f"Background not found: {bg_path}")
        self.background = pygame.image.load(bg_path).convert_alpha()

        # --- load map from TiledMap ---#
        PlatformClass = resolve_class('src.sprites.Platform')
        map_path = self.maps_path / self.game_config["map_files"]["test"]
        self.map = TiledMap(self, map_path, PlatformClass)
        self.map_img = self.map.generate_map()  # Generate map image and rect
        self.map_rect = self.map_img.get_rect()

        # --- Load sprite images ---
        self._load_images()

        # --- Load sounds ---
        self._load_sounds()

        # --- Load controls ---
        self._load_controls()

        # --- Object pooling ---
        self._init_object_pools()

    def _load_all_configs(self):
        """Load game, image, and sound configuration files."""
        config_dir = Path("config")
        self.game_config = load_json(config_dir / "game_config.json")
        self.image_config = load_json(config_dir / "image_config.json")
        self.sound_config = load_json(config_dir / "sound_config.json")
        self.controls_config = load_json(config_dir / "controls_config.json")

        print("[CONFIG] Game, image, and sound configs loaded")

        # Resolve paths
        base = Path(self.game_config["base"])
        rel_paths = self.game_config["rel_paths"]

        self.image_path = base / rel_paths["images"]
        self.maps_path = base / rel_paths["maps"]
        self.sounds_path = base / rel_paths["sounds"]

    def _load_images(self):

        """Load and cache all sprite images."""

        # Effects
        self.effects_images = load_spritesheets("effects")

        # resize effects for consistent tile scaling
        self.effects_images['enemydeath4x4'] = resize_images(self.effects_images.get('enemydeath'), (4 * self.map.tilesize, 4 * self.map.tilesize))
        self.effects_images['explosion4x4'] = resize_images(self.effects_images.get('explosion'), (4 * self.map.tilesize, 4 * self.map.tilesize))

        # Pickups
        self.pickup_images = load_spritesheets("PickUps")

        # Mobile sprites
        self.mobile_sprite_images = load_spritesheets("mobs", "player", "weapons")

    def _load_sounds(self):
        """Load music and sound effects."""

        # Music
        music_path = self.sounds_path / "music" / self.sound_config["music"]["intro"]
        pygame.mixer.music.load(music_path)

        # Ambient / effects sounds
        self.ambient_sounds = {
            key: [pygame.mixer.Sound(self.sounds_path / "ambient" / snd) for snd in snd_list]
            for key, snd_list in self.sound_config["ambient"].items()
        }
        # Set volumes
        for key, volume in self.sound_config["ambient_volume"].items():
            for snd in self.ambient_sounds[key]:
                snd.set_volume(volume)

    def _load_controls(self):
        """ Map the control keys - load the config file and convert the string names to pygame key constants."""

        keyboard = _map_keyboard_controls(pygame, self.controls_config.get("keyboard", {}))
        mouse = _map_mouse_controls(pygame, self.controls_config.get("mouse", {}))

        self.controls = {"keyboard": keyboard, "mouse": mouse}

    def _init_object_pools(self):
        """Initialize and populate all object pools from configuration."""
        config_path = Path("config/pool_config.json")

        if not config_path.exists():
            raise FileNotFoundError(f"Pool configuration file not found: {config_path}")

        with open(config_path, "r") as f:
            pool_config = json.load(f)

        self.objectpools = {}

        for key, cfg in pool_config.items():
            class_name = cfg["class"]
            size = cfg.get("size", 10)

            # Dynamically resolve class from src.sprites module
            try:
                sprite_class = getattr(sprites, class_name)
            except AttributeError:
                raise ImportError(f"Sprite class '{class_name}' not found in src.sprites")

            # Create the object pool
            pool = ObjectPool(self, sprite_class, refill_threshold=3, max_size=size)
            pool.populate(size)
            self.objectpools[key] = pool

        print(f"[INIT] Object pools initialized from {config_path}")

    def new(self):
        """Start a new game; initialise all variables, load or reload map data, sprites"""
        # init sprite groups
        self.mob_sprites = pygame.sprite.Group()  # TESTING ONLY
        self.hold_sprites = pygame.sprite.Group()  # sprites to be deleted- group for visual effects only
        self.all_sprites = pygame.sprite.Group()  # for drawing only

        # generate static sprites from TiledMap Tile layers
        for key, ttl in self.map.tmxdata.layernames.items():  # ttl - TiledTileLayer
            if ttl.visible:
                if key == 'pickups':
                    for pickup in ttl:
                        pickup_sprite = Pickup(self, pickup.x, pickup.y, pickup.width, pickup.height, pickup.image, pickup.name)
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
        pygame.mixer.music.play(loops=-1)

        while self.playing:
            # self.dt = self.clock.tick(FPS) / 1000  # time elapsed during a single loop (seconds)
            self.clock.tick_busy_loop(FPS)
            # print(self.clock.get_fps())
            self.dt = time.time() - self.elapsed_time  # current time - elapsed time on previous loop
            self.elapsed_time += self.dt  # update elapsed time for current loop

            self.events()
            self.update()
            self.draw()

    def handle_player_input(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_wheel_down, mouse_wheel_up = self.controls["mouse"]["buttons"]["scroll_down"], self.controls["mouse"]["buttons"]["scroll_up"]
            if mouse_wheel_up <= event.button <= mouse_wheel_down:  # mouse wheel scroll
                self.player.choose_weapon_mousewheel(event)

        elif event.type == pygame.KEYDOWN:
            numkeys = list(self.controls["keyboard"]["weapons"].values())
            sys_keys = self.controls["keyboard"]["system"]
            if numkeys[0] <= event.key <= numkeys[-1]:
                weapon_index = int(event.unicode)
                self.player.choose_weapon_numpad(weapon_index)

            elif event.key == sys_keys["toggle_control_mode"]:
                self.player.toggle_controls()

            elif event.key == sys_keys["quit"]:
                pygame.event.set_grab(False)
                self.playing = False

            elif event.key == sys_keys["exit_game"]:
                self.playing = False
                self.running = False

    def events(self):
        pygame.event.set_grab(True)  # lock keyboard and mouse input into pygame app

        for event in pygame.event.get():

            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                self.handle_player_input(event)

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
        # --- 1. Update camera ---
        self.camera.update(self.player)  # change camera rect position according to player position (centred on player rect)
        # for mob in self.mob_sprites:
        #     self.camera.update(mob)

        # --- 2. Update active grids ---
        self.map.get_active_grids()  # grids which are on screen and adjacent to screen boundaries

        # Collect sprites that need to move between grids
        sprites_to_transfer = []  # sprites to be moved to new grid for current update

        # --- 3. Update mobile sprites in active grids ---
        # call sprite update method then update position
        dt_scaled = self.dt * TARGET_FPS
        for map_layer in self.map.mobile_layers:
            layer_grids = self.map.layers[map_layer]  # return dictionary containing grids (sprite groups)

            for grid_ref in self.map.active_gridrefs:  # 'A0', 'A1', 'A2' ...
                grid = layer_grids[grid_ref]
                grid.update()

                for sprite in grid:
                    # Update sprite positions (frame-rate independent)
                    sprite.pos += sprite.vel * dt_scaled

                    # Queue sprite for transfer between grids
                    if sprite.flag_transfer_sprite():
                        sprites_to_transfer.append(sprite)

        # --- 4. Transfer sprites between grids ---
        if sprites_to_transfer:
            self.transfer_sprites(sprites_to_transfer)  # transfer flagged sprites to new grid

        # --- 5. Update hold sprites ---
        sprites_to_return = []

        for sprite in self.hold_sprites:
            sprite.vel *= 0.98  # apply velocity damping
            sprite.pos += sprite.vel
            sprite.hitrect.center = sprite.pos  # must update hitrect rather than rect as rect position overwritten in Mobile_sprite.transform_image()

            # Queue sprite for return to object pool if animation ended
            if sprite.check_anim_end(sprite.current_animation):
                sprites_to_return.append(sprite)
            # Queue sprite for return if off-screen
            elif sprite.gridref not in self.map.active_gridrefs:
                sprites_to_return.append(sprite)

        # --- 6. Return pooled sprites ---
        for sprite in sprites_to_return:
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
