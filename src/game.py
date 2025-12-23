# Project setup

import json
import pygame
import time
import numpy as np
import logging
from pathlib import Path

from .settings import *
from .helpers import resolve_class, resize_images, load_spritesheets, load_json, _map_keyboard_controls, _map_mouse_controls
from .systems import TiledMap, Camera, ObjectPool
from .ui.hud import draw_sprite_bar, draw_text, draw_grid, draw_ray
from src import sprites
from .sprites import Pickup, Player, Missile
from loggers import performance_FPS_monitoring, check_sprite_size, check_extreme_vel, left_map_bounds

logger = logging.getLogger(__name__)


class Game:

    def __init__(self, screen):

        self.screen = screen
        self.clock = pygame.time.Clock()
        self.elapsed_time = time.perf_counter()  # from new game start
        self.dt = 0  # time elapsed for 1 mainloop
        self.running = True  # game running
        self.lock_controls = True
        self.debug = False

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

        # --- Load mesh ---
        self._load_mesh()

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
        self.mesh_config = load_json(config_dir / "mesh_config.json")
        self.sound_config = load_json(config_dir / "sound_config.json")
        self.controls_config = load_json(config_dir / "controls_config.json")


        logger.info("[CONFIG] Game, image, and sound configs loaded")

        # Resolve paths
        base = Path(self.game_config["base"])
        rel_paths = self.game_config["rel_paths"]

        self.image_path = base / rel_paths["images"]
        self.mesh_path = base / rel_paths["mesh"]
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

        logger.info("[INFO] effects, pickups, mobs, player, weapons images loaded")

        # --- Debug ---

        check_sprite_size(self.effects_images, self.map.tilesize)
        check_sprite_size(self.pickup_images, self.map.tilesize)
        check_sprite_size(self.mobile_sprite_images, self.map.tilesize)

    def _load_mesh(self):
        """     Load all .npy mesh files defined in self.mesh_config into NumPy arrays.

    Expected mesh_config structure:
        {
            "anti_g": {
                "level1": "level1_anti_g.npy",
                "level2": "level2_anti_g.npy"
            },
            "waterflow": {
                "level1": "level1_waterflow.npy"
            }
        }
    Returns:
        dict(level_name -> mesh_array)
"""
        self.mesh_arrays = {}  # load n

        for mesh_type, level_dict in self.mesh_config.items():
            self.mesh_arrays.update({mesh_type: {}})
            for level_name, mesh_file in level_dict.items():

                file_path = self.mesh_path / mesh_file
                # Check file exists
                if not file_path.exists():
                    logger.warning(f"[WARNING] Mesh file not found: {file_path}")
                    self.mesh_arrays[mesh_type][level_name] = None
                    continue
                # Attempt to load the file
                try:
                    array = np.load(file_path)
                    self.mesh_arrays[mesh_type][level_name] = array
                    logger.info(f"[OK] Loaded mesh: {file_path}")
                except Exception as e:
                    logger.error(f"[ERROR] Failed to load mesh file: {file_path}")
                    logger.error(f"        Reason: {e}")
                    self.mesh_arrays[level_name] = None

    def _load_sounds(self):
        """Load music and sound effects."""

        # Music
        music_path = self.sounds_path / "music" / self.sound_config["music"]["intro"]
        pygame.mixer.music.load(music_path)
        pygame.mixer.music.set_volume(self.sound_config["music_volume"])

        # Ambient / effects sounds
        self.ambient_sounds = {
            key: [pygame.mixer.Sound(self.sounds_path / "ambient" / snd) for snd in snd_list]
            for key, snd_list in self.sound_config["ambient"].items()
        }
        # Set volumes
        for key, volume in self.sound_config["ambient_volume"].items():
            for snd in self.ambient_sounds[key]:
                snd.set_volume(volume)

        logger.info("[INFO] music, ambient sounds loaded")

    def _load_controls(self):
        """ Map the control keys - load the config file and convert the string names to pygame key constants."""

        keyboard = _map_keyboard_controls(pygame, self.controls_config.get("keyboard", {}))
        mouse = _map_mouse_controls(pygame, self.controls_config.get("mouse", {}))

        self.controls = {"keyboard": keyboard, "mouse": mouse}

        logger.info("loaded player controls")

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
                logger.info(f"[INFO] {sprite_class} object_pool initialised")
            except AttributeError:
                raise ImportError(f"Sprite class '{class_name}' not found in src.sprites")

            # Create the object pool
            pool = ObjectPool(self, sprite_class, refill_threshold=3, max_size=size)
            pool.populate(size)
            self.objectpools[key] = pool

        logger.info(f"[INIT] Object pools initialized from {config_path}")

    def new(self):
        """Start a new game; initialise all variables, load or reload map data, sprites"""
        # init sprite groups
        self.mob_sprites = pygame.sprite.Group()  # TESTING ONLY
        self.hold_sprites = pygame.sprite.Group()  # sprites to be deleted- group for visual effects only
        self.active_sprites = pygame.sprite.LayeredUpdates()  # for drawing only
        self.fx_sprites = pygame.sprite.Group()

        tmxdata = self.map.tmxdata

        # --- Generate static sprites (e.g. pickups) ---
        # generate static sprites from TiledMap Tile layers
        pickups_layer = tmxdata.layernames.get("pickups")
        if pickups_layer.visible:
            for tile in pickups_layer:
                pickup_sprite = Pickup(self, tile.x, tile.y, tile.width, tile.height, tile.image, tile.name)
                # self.active_sprites.add(pickup_sprite)

        # generate mobile sprites from TiledMap object layers

        for key, tog in self.map.tmxdata.layernames.items():  # ttl - TiledObjectGroup
            if tog.visible:
                if key == 'players':
                    for player in tog:
                        self.player = Player(self, player.x, player.y)  # xpos, ypos, width, height
                        # self.all_sprites.add(self.player)

                if key == 'obstacles':
                    for obstacle in tog:
                        if obstacle.name == 'Mine':
                            mine = self.objectpools['mine'].borrow_object()
                            x, y = obstacle.x + obstacle.width / 2, obstacle.y + obstacle.height / 2
                            mine.activate(x, y)

        # --- Generate enemies ---
        # generate enemies from TiledMap object layers
        enemies_layer = tmxdata.layernames.get("enemies")
        for i, enemy in enumerate(enemies_layer, start=1):
            if enemy.name != 'Enemy':  # if mob child class specified i.e. not generic Enemy definition
                mobkey = enemy.name
            elif i % 3 == 0:  # every 3rd mob generated
                mobkey = 'spinefish'
            elif i % 20 == 0:  # every 10th mob generated
                mobkey = 'daddyfish'
            else:
                mobkey = 'dartfish'

            mob = self.objectpools[mobkey].borrow_object()
            x, y = enemy.x + enemy.width / 2, enemy.y + enemy.height / 2
            mob.activate(x, y)

            self.mob_sprites.add(mob)  # TESTING ONLY

    def run(self):

        # """ Main game loop"""
        self.playing = True
        pygame.mixer.music.play(loops=-1)

        while self.playing:

            self.clock.tick_busy_loop(FPS)

            self.dt = time.perf_counter() - self.elapsed_time  # current time - elapsed time on previous loop
            self.elapsed_time += self.dt  # update elapsed time for current loop
            # ---------------------------------------------
            # ✓ Store actual FPS this frame
            # ---------------------------------------------
            self.fps = self.clock.get_fps()

            self.events()
            self.update()
            self.draw()

    def handle_player_input(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_buttons = self.controls["mouse"]["buttons"]
            scroll_up = mouse_buttons["scroll_up"]
            scroll_down = mouse_buttons["scroll_down"]

            if scroll_up <= event.button <= scroll_down:  # mouse wheel scroll
                self.player.choose_weapon_mousewheel(event)

        elif event.type == pygame.KEYDOWN:
            keyboard = self.controls["keyboard"]
            weapon_keys = list(keyboard["weapons"].values())

            sys_keys = keyboard["system"]
            if weapon_keys[0] <= event.key <= weapon_keys[-1]:
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
        if self.lock_controls:
            pygame.event.set_grab(True)  # lock keyboard and mouse input into pygame app

        for event in pygame.event.get():

            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                self.handle_player_input(event)

            if event.type == pygame.QUIT:
                self.playing = False
                self.running = False

    def transfer_sprites(self, sprites_to_transfer):
        """ Transfer flagged sprites to new grid within their map layer and handle pool returns"""
        if not sprites_to_transfer:
            return

        for sprite in sprites_to_transfer:
            # Move sprite between grids (spritegroups)
            self.map.layers[sprite.map_layer][sprite.gridref].remove(sprite)
            self.map.layers[sprite.map_layer][sprite.next_grid].add(sprite)
            sprite.gridref = sprite.next_grid

            # return missile sprites not in active sprites list to Objectpool
            if sprite.next_grid not in self.map.active_gridrefs:

                if isinstance(sprite, Missile):
                    self.objectpools[sprite.refkey].rtrn_object(sprite)

    def update_active_grids(self):
        """ For mobile map layers, call sprite update() for active grids (spritegroups).  Then update individual sprite positions
        Finally transfer marked sprites to new grids"""

        dt_scaled = self.dt * TARGET_FPS

        sprites_to_transfer = []

        # --- Call update for active grids ---
        for grid_ref in self.map.active_gridrefs:
            for layer in self.map.mobile_layers:
                grid = self.map.layers[layer][grid_ref]
                grid.update()

                # --- Update individual sprite positions then check for platform collision
                for sprite in grid:
                    self.active_sprites.add(sprite)
                    velocity = sprite.vel * dt_scaled  # adjust velocity so frame_rate independent
                    sprite.pos += velocity  # Update sprite positions (frame-rate independent)

                    sprite.hitrect.centerx = sprite.pos.x + (sprite.direction.x * sprite.HRoffset)
                    sprite.handle_platform_collision(0)  # detect along x axis

                    sprite.hitrect.centery = sprite.pos.y + (sprite.direction.y * sprite.HRoffset)
                    sprite.handle_platform_collision(1)  # detect along y axis

                    if sprite.flag_transfer_sprite():
                        sprites_to_transfer.append(sprite)

                    # --- Debug ---
                    check_extreme_vel(sprite)
                    left_map_bounds(sprite, self.map)

        # --- 4. Transfer sprites between grids ---
        if sprites_to_transfer:
            self.transfer_sprites(sprites_to_transfer)  # transfer flagged sprites to new grid

    def update_holdsprites(self):

        sprites_to_return = []

        for sprite in self.hold_sprites:
            sprite.vel *= 0.98  # apply velocity damping
            sprite.pos += sprite.vel

            # Queue sprite for return to object pool if animation ended
            if sprite.check_anim_end(sprite.current_animation):
                sprites_to_return.append(sprite)
            # Queue sprite for return if off-screen
            elif sprite.gridref not in self.map.active_gridrefs:
                sprites_to_return.append(sprite)

            # ---  Return pooled sprites ---
        for sprite in sprites_to_return:
            self.objectpools[sprite.refkey].rtrn_object(sprite)

    def update(self):
        """Game Loop - Update"""

        self.active_sprites.empty()

        # --- 2. Update list of active grids ---
        self.map.get_active_grids()  # grids which are on screen and adjacent to screen boundaries

        # --- 3. Update stationary sprites in active grids ---
        for grid_ref in self.map.active_gridrefs:
            for layer in self.map.stationary_layers:
                sprgroup = self.map.layers[layer][grid_ref]
                self.active_sprites.add(*sprgroup.sprites())

        # --- 4. Update mobile sprites in active grids ---
        self.update_active_grids()

        # --- 5. Update hold sprites ---
        self.update_holdsprites()

        # --- 1. Update camera ---
        self.camera.update(self.player)  # change camera rect position according to player position (centred on player rect)
        # for mob in self.mob_sprites:
        #     self.camera.update(mob)

    def draw(self):
        """Render one full game frame: map, sprites, HUD, and optional debug layers."""
        # TODO- apply adaptive rendering for draw():

        # ---------------------------------------------
        #   Display Setup
        # ---------------------------------------------
        pygame.display.set_caption(f"{self.fps:.2f}")
        self.screen.fill(DEEPBLUE)

        # ---------------------------------------------
        #   Adaptive Rendering Thresholds
        # ---------------------------------------------
        low_fps = self.fps < 30
        critical_only = self.fps < 20  # e.g. skip particle FX when very low FPS

        # ---------------------------------------------
        #   Draw Background Map
        # ---------------------------------------------
        offset_x, offset_y = self.camera.apply_rect(self.map_rect)
        self.screen.blit(self.map_img, (int(offset_x), int(offset_y)))

        # ---------------------------------------------
        #   Draw Game Sprites
        # ---------------------------------------------
        for sprite in self.active_sprites:
            # Skip non-critical FX under low FPS
            if critical_only and getattr(sprite, "priority", "") == "fx":
                continue
            sprite.draw()

        if not critical_only:
            for sprite in self.fx_sprites:
                sprite.draw()
            for sprite in self.hold_sprites:
                sprite.draw()

        # ---------------------------------------------
        #   HUD (health, stamina, weapon, ammo) ---
        # ---------------------------------------------
        # --- player hitpoints ---
        draw_sprite_bar(self.screen, 0.2 * SCREENWIDTH, 10, self.player.hitpoints / Player.hitpoints, GREEN, YELLOW, RED)
        # --- player stamina ---
        draw_sprite_bar(self.screen, 0.8 * SCREENWIDTH, 10, self.player.stamina / Player.stamina, RED, BLUE, PURPLE)
        # --- player aim --- #
        draw_ray(self)
        # --- current weapon select --
        draw_text(self, self.player.current_weapon, 20, RED, 0.4 * SCREENWIDTH, 15)
        # --- ammo ---
        draw_text(self, str(self.player.ammo[self.player.current_weapon]), 20, RED, 0.6 * SCREENWIDTH, 15)
        # --- Mine countdown numbers ---
        for grid in self.map.layers['obstacles'].values():
            for sprite in grid:
                if sprite.refkey == 'mine' and sprite.active:
                    draw_text(self, str(int(sprite.countdown + 1)), 50, RED,
                    sprite.rect.centerx - self.camera.pos.x,
                    sprite.rect.centery - self.camera.pos.y)

        # ---------------------------------------------
        #   Debug / Performance Monitoring
        # ---------------------------------------------
        performance_FPS_monitoring(self.fps)

        # ---------------------------------------------
        #   Testing + Debug (Heavy Overlays)
        # ---------------------------------------------
        if self.debug:  # optional flag for dev builds
            self.draw_test_overlays()

        pygame.display.flip()  # *after* drawing everything, flip the display

    def draw_test_overlays(self):
        """Draw all debug/test overlays.
        Call only when self.debug == True to keep performance stable."""

        # --- Grid overlay ---
        draw_grid(self)

        # --- Player rectangles ---
        rect = pygame.Rect(
            self.player.rect.x - self.camera.pos.x, self.player.rect.y - self.camera.pos.y, self.player.rect.width,self.player.rect.height,
        )
        hitrect = pygame.Rect(
            self.player.hitrect.x - self.camera.pos.x, self.player.hitrect.y - self.camera.pos.y, self.player.hitrect.width, self.player.hitrect.height,
        )

        pygame.draw.rect(self.screen, WHITE, rect, 2)
        pygame.draw.rect(self.screen, RED, hitrect, 2)

        # Player start position
        # pygame.draw.circle(
        #     self.screen, WHITE,
        #     (int(self.player.spawn_pos.x - self.camera.pos.x),
        #      int(self.player.spawn_pos.y - self.camera.pos.y)),
        #     10, 1
        # )
        # Player current position
        pygame.draw.circle(
            self.screen, RED,
            (int(self.player.pos.x - self.camera.pos.x),
             int(self.player.pos.y - self.camera.pos.y)),
            10, 1
        )

        # --- Enemies debug ---
        for mob in self.mob_sprites:
            x = mob.pos.x - self.camera.pos.x
            y = mob.pos.y - self.camera.pos.y

            # dif = str(int(mob.dif))
            # draw_text(self, dif, 20, RED, SCREENWIDTH - 25, 15)

            # --- target position --- #
            pygame.draw.circle(
                self.screen, RED,
                (int(mob.target.x - self.camera.pos.x),
                 int(mob.target.y - self.camera.pos.y)),
                10, 1
            )

            # --- mob vectors --- #
            pygame.draw.line(self.screen, WHITE, (x, y), (x + mob.target_vec.x, y + mob.target_vec.y), 3)  # target vector
            pygame.draw.line(self.screen, RED, (x, y), (x + mob.vel.x, y + mob.vel.y), 3)  # mob vel

            # --- mob rectangles ---
            rect = pygame.Rect(
                mob.rect.x - self.camera.pos.x, mob.rect.y - self.camera.pos.y, mob.rect.width, mob.rect.height,
            )
            hitrect = pygame.Rect(
                mob.hitrect.x - self.camera.pos.x, mob.hitrect.y - self.camera.pos.y, mob.hitrect.width, mob.hitrect.height,
            )

            # pygame.draw.rect(self.screen, WHITE, rect, 2)
            pygame.draw.rect(self.screen, RED, hitrect, 2)

            # pygame.draw.circle(self.screen, WHITE, (int(mob.rect.centerx), int(mob.rect.centery)), int(mob.radius), 1)

        # --- Weapon hitboxes ---
        for grid in self.map.layers['weapons'].values():
            for sprite in grid:
                pass
                # pygame.draw.rect(self.screen, WHITE, sprite.rect, 2)
                # pygame.draw.rect(self.screen, RED, sprite.hitrect, 2)

        # --- Spawn tiles ---
        # for col, row in self.map.valid_spawn_tiles:
        #     px, py = col * self.map.tilesize, row * self.map.tilesize
        #     pygame.draw.rect(self.screen, RED,
        #                      (px - self.camera.pos.x, py - self.camera.pos.y,
        #                       self.map.tilesize, self.map.tilesize),
        #                      1)

        # --- Camera Position Example ---
        # cam = f"Camera: {round(self.camera.pos.x,1)}, {round(self.camera.pos.y,1)}"
        # draw_text(self, cam, 22, RED, SCREENWIDTH/2, SCREENHEIGHT - 15)

    def show_start_screen(self):
        # game splash/start screen
        pass

    def show_go_screen(self):
        # game over/continue
        self.screen.fill(BLACK)
        draw_text(self, "GAME OVER", 48, RED, SCREENWIDTH / 2, SCREENHEIGHT / 4)
        pygame.display.flip()
