import pygame
import logging
from math import e, log, pi
from random import choice, randrange, randint
from itertools import chain

from .pickup_config import PICKUP_CATGRY
from .helpers import rect_to_vectors, sign, interval_trigger, switch_interval, vec_intersect, vec_trans, get_radius_vector, get_angleii, turn_direction, clamp
from .visual_effects import SmokeParticle
from loggers import check_valid_grid
vec = pygame.Vector2  # 2D vector - x = vec.x  y = vec.y

logger = logging.getLogger(__name__)


class StaticSprite(pygame.sprite.Sprite):

    """Static, inanimate sprites includes props, platforms, pickups.  Parent class for all sprites. No update method
    Contains position, grid reference, and map-layer registration"""

    def __init__(self, game, x, y, w, h):

        super().__init__()
        self.game = game
        self.pos = vec(x, y)

        self.rect = pygame.Rect(x, y, w, h)
        self.rect.topleft = (self.pos.x, self.pos.y)
        self.hitrect = self.rect.copy()

        self.map_layer = self.__class__.map_layer
        self.draw_layer = 1  # draw_order
        self.priority = True  # used to deprioritize FX when FPS is low

    def get_gridref(self):
        """Return the grid reference (e.g., 'A1') where this sprite currently resides."""
        grid_x = int(self.rect.centerx // self.game.map.gridwidth)
        grid_y = int(self.rect.centery // self.game.map.gridheight)
        gridref = f"{self.game.map.x_coords[grid_x]}{self.game.map.y_coords[grid_y]}"
        check_valid_grid(gridref, self, self.game.map.grid_coords)
        return gridref

    def get_adjacent_grids(self):
        """ Return list of current and adjacent gridrefs e.g. if sprite in grid B1 this will return ['A0', 'A1', 'A2', 'B0', 'B1', 'B2', 'C0', 'C1', 'C2'] """

        grid_x = int(self.rect.centerx // self.game.map.gridwidth)
        grid_y = int(self.rect.centery // self.game.map.gridheight)

        x_min = max(grid_x - 1, 0)
        x_max = min(grid_x + 1, len(self.game.map.x_coords) - 1)
        y_min = max(grid_y - 1, 0)
        y_max = min(grid_y + 1, len(self.game.map.y_coords) - 1)

        self.adjacent_grids = [
            f"{self.game.map.x_coords[i]}{self.game.map.y_coords[j]}"
            for i in range(x_min, x_max + 1)
            for j in range(y_min, y_max + 1)
        ]

        for gridref in self.adjacent_grids:
            check_valid_grid(gridref, self, self.game.map.grid_coords)

    def add_to_map_layer(self):

        self.gridref = self.get_gridref()
        self.game.map.layers[self.map_layer][self.gridref].add(self)  # add sprite to new grid


class Platform(StaticSprite):
    """Wall sprite; player, mobs can't pass through.  Data read from TiledTile Layers within map tmx file.  Individual platform sprites
    have no image- only used for collision detection, anti-g"""

    map_layer = 'platforms'

    def __init__(self, game, x, y, w, h):
        """Generates a single platform tile."""
        super().__init__(game, x, y, w, h)
        self.rect_sides = rect_to_vectors(self.rect)  # store rect sides as list of position vectors for vector intersect
        self.add_to_map_layer()


class Pickup(StaticSprite):
    """Data read from Object Layers within map tmx file:  apply_pickup method calls lamda function corresponding to pickup cat"""

    map_layer = 'pickups'
    _layer = 1

    def __init__(self, game, x, y, w, h, image, pickup_cat):

        super().__init__(game, x, y, w, h)
        self.image = image
        self.pickup_cat = pickup_cat
        self.add_to_map_layer()
        pass

    def apply_pickup(self):

        effect_func = PICKUP_CATGRY.get(self.pickup_cat)
        logger.info(f"[INFO] Player picked up '{self.pickup_cat}'")

        if effect_func:
            effect_func(self.game.player)
            self.kill()  # Remove from all sprite groups
        else:
            logger.warning(f"[WARNING] Unknown pickup category: '{self.pickup_cat}'")

    def draw(self):

        self.game.screen.blit(self.image, self.game.camera.apply(self))


class Mobile_sprite(StaticSprite):
    """Mobile sprites are animated and/ or have velocity.  Data read from Object Layers within map tmx file.
    Self.pos is placed at rect.center rather than topleft for rotating sprites.  Update called each game loop"""
    damage_alpha = [i for i in range(0, 255, 55)]  # setup sequence of alpha channel (transparency) values to iterate through upon receiving damage
    # damage alpha chain from 0 to 255 in steps of 55

    def __init__(self, game, x, y):

        pygame.sprite.Sprite.__init__(self)
        self.game = game

        # Base image and reference (for rotation and flipping)
        ref_key = self.__class__.refkey
        self.ref_image = game.mobile_sprite_images[ref_key][0]
        self.image = self.ref_image.copy()
        self.rect = self.image.get_rect()

        # Position uses center for rotating sprites
        self.pos = vec(x + self.rect.width / 2, y + self.rect.height / 2)
        self.rect.center = self.pos

        # Hitbox setup
        self.HRoffset = 0  # hitrect offset from sprite centre coords
        self.direction = vec(1, 0)  # direction of travel, facing
        self.radius = 0.75 * ((self.rect.width + self.rect.height) / 4)
        self.rect_rtn = 0  # rotation angle in degrees

        self.vel = vec(0, 0)
        self.transfer = False
        self.damaged = False

        # Animation
        self.refresh_rate = 0.2  # seconds per frame
        self.actionvar = "idle"
        self.newaction = "idle"
        self.timer = 0.0
        self.current_frame_index = 0
        self.current_animation = []
        self.setup_hitrect()

    def setup_hitrect(self):
        """ hitrect square centred about self.rect.center. Used for sprite collisions. """

        avg = 0.5 * (self.rect.width + self.rect.height)
        size = int((avg / 2) + 1) * 2  # round up to nearest even int
        self.hitrect = pygame.Rect(0, 0, size, size)
        self.hitrect.center = self.rect.center + (self.direction.normalize() * self.HRoffset)

    def flag_transfer_sprite(self):
        """ If sprite has moved to a new grid flag sprite for update in main game update"""
        new_ref = self.get_gridref()
        if new_ref != getattr(self, "gridref", None):
            self.transfer = True
            self.next_grid = new_ref
            check_valid_grid(new_ref, self, self.game.map.grid_coords)
            return True
        return False

    def collide_sprites(self, test_rect, map_layer):
        """ Return list of collided sprites for current & adj grids within specified maplayer"""

        hits = []
        for grid_ref in self.adjacent_grids:
            for sprite in self.game.map.layers[map_layer][grid_ref]:
                if test_rect.colliderect(sprite.rect):
                    hits.append(sprite)

        return hits

    def continuous_collision_detection(self, axis, map_layer, test_rect, move_by):
        """
        Prevent fast sprites skipping through e.g. walls- by checking if sprites path intersetcs a wall, not just its end position
        Parameters:
            axis (int): 0 for X-axis, 1 for Y-axis
            map_layer (str): The layer to check collisions against.

        Returns:
            tuple or None: The clipped line segment if collision occurs, else None.
        """
        future_rect = test_rect.move(move_by[0], move_by[1])  # hitrect position after next update call
        for grid_ref in self.adjacent_grids:
            for sprite in self.game.map.layers[map_layer][grid_ref]:
                clipped = sprite.rect.clipline(test_rect.center, future_rect.center)
                if clipped:
                    entry = clipped[0][axis]
                    displacement = self.hitrect.center[axis] - entry
                    # Adjust position and hitrect to prevent tunneling
                    self.pos[axis] -= displacement
                    self.hitrect[axis] -= displacement

                    return clipped

    def discrete_collision_detection(self, axis, map_layer):
        """
        Resolve collisions between this sprite and platforms along a given axis.

        Returns:
            list: Collided platform sprites, or an empty list.
        """
        hits = self.collide_sprites(self.hitrect, map_layer)
        if hits:
            # ---return direction of travel +1 or -1 along axis:  left = -1, right = 1, up = -1, down = 1 --- #
            platform = hits[0]
            d = sign(platform.rect.center[axis]-self.hitrect.center[axis])

            # ---get overlap between test_rect and platform.rect along axis ---
            overlap = 0.5*d*(self.hitrect.size[axis] + platform.rect.size[axis]) - (platform.rect.center[axis] - self.hitrect.center[axis])

            # ---adjust position, hitrect so no longer colliding along current axis --- #
            self.pos[axis] -= overlap  # reset position so no longer colliding
            self.hitrect[axis] -= overlap

            return hits

    def change_action(self, anim_reel, newaction):
        """ change action from e.g. jumping to falling.  First check current action to see if action has actually changed then return new actionvar"""
        if self.actionvar != newaction:
            self.actionvar = newaction
            self.timer = 0  # set timer at start of animation.  Resets to zero when switching to other animation
            self.current_frame_index = 0  # first animation slide
            self.current_animation = anim_reel[self.actionvar]

    def rotate_about_centre(self, angle):

        surf = pygame.transform.rotate(self.ref_image, angle)  # rotate image
        # offset = centre + (origin - centre).rotate(-angle)  # rotate image around a pivot point. e.g. centre of screen
        new_rect = surf.get_rect(center=self.pos)  # replace self.pos with offset it rotating about a pivot
        return surf, new_rect

    def transform_image(self):
        """Flip image about y axis if sprite is upside down, then rotate image about rect.center"""

        if self.rect_rtn < - 90 or self.rect_rtn > 90:
            self.ref_image = pygame.transform.flip(self.ref_image, False, True)  # flip image

        self.image, self.rect = self.rotate_about_centre(self.rect_rtn)

    def animate(self, anim_reel):
        """Update current animation frame and transform image"""

        self.current_frame_index = int((self.timer // self.refresh_rate) % len(anim_reel))  # must be before self.timer updated for check_anim_end to work
        self.timer += self.game.dt
        self.ref_image = anim_reel[self.current_frame_index]
        # self.image.fill(RED)

    def check_anim_end(self, anim_reel):
        """ check if animation will end & return to 1st frame on next game loop"""

        if int((self.timer // self.refresh_rate) % len(anim_reel)) < self.current_frame_index:
            return True

    def damage_effect(self):

        if self.damaged:
            try:
                alpha = next(self.damage_alpha)
                self.image.fill((255, 0, 0, alpha), special_flags=pygame.BLEND_RGBA_MULT)
            except StopIteration:
                self.damaged = False
                self.damage_alpha = iter(range(0, 255, 55))  # reset for next hit

    def draw(self):

        self.animate(self.current_animation)
        self.transform_image()
        self.damage_effect()
        offset_x, offset_y = self.game.camera.apply(self)
        self.game.screen.blit(self.image, (int(offset_x), int(offset_y)))


class Missile(Mobile_sprite):
    """ Parent class for harpoons, torpedos ..."""
    _layer = 3

    def __init__(self, game, x, y):

        self.direction = vec(1, 0)
        super().__init__(game, x, y)

        self.current_animation = self.game.mobile_sprite_images[self.__class__.refkey]
        self.HRoffset = self.rect.width * self.__class__.HRoff_pct  # offset from rect.center so hitrect positioned at front of missile
        self.setup_hitrect()

    def setup_hitrect(self):
        """ Define a smaller rectangular hitbox positioned at the missile's front"""
        HRheight = self.rect.height * 0.75
        HRwidth = HRheight
        self.hitrect = pygame.Rect(self.rect.centerx, self.rect.centery, HRwidth, HRheight)
        self.hitrect.center = self.rect.center + (self.direction.normalize()*self.HRoffset)  # offset hitrect from centre

    def activate(self, player):
        """ On player.shoot() borrow missile sprite from pool, set position offset from player, direction and add to weapons map_layer"""
        self.direction = vec(player.direction.x, player.direction.y)
        # set position such that hitrect located at player_rect center
        self.hitrect.center = self.pos
        self.pos = self.pos - (self.HRoffset * self.direction.normalize())
        self.rect_rtn = player.rect_rtn
        self.transform_image()
        self.get_adjacent_grids()

        # ---- Collision test on activation ---------------------------------------
        move_by = self.direction * self.game.map.tilesize

        clipped = False
        # test both CCD passes; clipped if any is True
        if self.continuous_collision_detection(0, 'platforms', self.hitrect, move_by):
            clipped = True

        if self.continuous_collision_detection(1, 'platforms', self.hitrect, move_by):
            clipped = True

        # ---- If safe, push missile out + start flight -----------------------------
        if not clipped:
            self.pos += 2 * self.game.map.tilesize * self.direction
            self.vel = self.direction * self.__class__.runspeed

class Harpoon(Missile):

    map_layer = 'weapons'
    refkey = 'harpoon'
    runspeed = 40
    HRoff_pct = 0.3  # offset from rect.center (as % of rect.width) - so hitrect positioned at front of missile

    def __init__(self, game, x, y):
        super().__init__(game, x, y)

    def handle_platform_collision(self, axis, ):

        if self.continuous_collision_detection(axis, 'platforms', self.hitrect, self.vel):

            self.vel = vec(0, 0)
            self.add(self.game.hold_sprites)
            self.remove(self.game.map.layers[self.map_layer][self.gridref])
            return True

    def collide_enemy(self):

        hits = self.collide_sprites(self.hitrect, 'enemies')
        if hits:
            hits[0].take_damage(10)

            self.game.objectpools[self.refkey].rtrn_object(self)
            choice(self.game.ambient_sounds['mob_hit']).play()

    def collide_mines(self):

        hits = self.collide_sprites(self.hitrect, 'obstacles')  # mine collision 'kill' sprite -return to object pool
        if hits:
            if hits[0].refkey == 'mine':
                self.game.objectpools[self.refkey].rtrn_object(self)

    def update(self):

        self.get_adjacent_grids()

        # collisions
        self.collide_enemy()
        self.collide_mines()


class Torpedo(Missile):

    map_layer = 'weapons'
    refkey = 'torpedo'
    runspeed = 20
    HRoff_pct = 0.2  # offset from rect.center (as % of rect.width) - so hitrect positioned at front of missile

    def __init__(self, game, x, y):

        super().__init__(game, x, y)
        self.affect_rad = 4 * game.map.tilesize  # radius for area of affect.  Countdown timer activated if player within affect_rad
        self.damage_constant = (0.5 * self.affect_rad) ** 3 / 2  # constant for damage to sprites within affect_rad inversely proportional to distance squared
        self.refresh_rate = 0.1  # rate animation changes slide (0.5 - changes twice per second)

        # self.vel = self.direction.normalize() * Torpedo.runspeed

        # Smoke trail control
        self.smoke_timer = 0
        self.smoke_interval = 100  # milliseconds between smoke puffs

    def handle_platform_collision(self, axis):
        """Explode on impact with platforms."""

        if self.continuous_collision_detection(axis, 'platforms', self.hitrect, self.vel):

            self.vel = vec(0, -2)  # explosion rises
            self.explode()

            self.add(self.game.hold_sprites)
            self.remove(self.game.map.layers[self.map_layer][self.gridref])
            return True

    def collide_enemy(self):
        """Direct hit instantly destroys target."""
        # TODO Replace direction collision with proximity to mob triggering explosion
        hits = self.collide_sprites(self.hitrect, "enemies")
        if hits:
            target = hits[0]
            target.vel += self.vel * 3 / 16  # transfer momentum to enemy
            target.hitpoints = 0
            self.vel *= 0.5
            return True

    def collide_mine(self):
        """Trigger mine explosions on contact."""
        for hit in self.collide_sprites(self.hitrect, "obstacles"):
            if hit.refkey == "mine":
                hit.countdown = 0
                hit.active = True
                hit.vel = self.vel * 0.0625  # transfer momentum to the mine
                self.vel *= 0.25
                return True

    def inflict_damage(self, layer_key, v_const):
        """Apply explosion force and damage to nearby sprites"""
        for ref in self.adjacent_grids:
            for sprite in self.game.map.layers[layer_key][ref]:
                # TODO Fix sprite going through walls due to explosion
                # TODO set max vel for sprite as affect of explosion
                displacement = vec(sprite.hitrect.center) - vec(self.hitrect.center)
                damage = self.damage_constant / displacement.length()**2
                sprite.vel = displacement.normalize() * (v_const / displacement.length())  # explosion veloctity in opposite direction to displacement.  Speed proportional to 1/ distance
                sprite.vel += self.direction * -5  # Add velocity constant to increase minimum explosion affect
                sprite.take_damage(damage)

    def explode(self):
        """On explosion, call inflict_damage method on nearby sprites, trigger explosion animation and sound"""
        self.inflict_damage('players', 800)  # inflict damage on sprites within radius
        self.inflict_damage('enemies', 1300)

        self.add(self.game.hold_sprites)
        self.remove(self.game.map.layers['weapons'][self.gridref])

        # update animation reel to explosion animation
        self.change_action(self.game.effects_images, 'explosion')  # change self.actionvar to new action
        choice(self.game.ambient_sounds['torpedo_explode']).play()

    def update(self):

        # self.hitrect.center = self.pos
        self.get_adjacent_grids()

        if any([self.collide_mine(), self.collide_enemy()]):
            self.explode()


class Mine(Mobile_sprite):

    _layer = 3
    map_layer = 'obstacles'
    refkey = 'mine'

    """ damage_constant formula is fixed- DO NOT ALTER.  Only dependent on affect_rad"""
    def __init__(self, game, x, y):

        super().__init__(game, x, y)

        self.affect_rad = 9 * game.map.tilesize  # radius for area of affect.  Countdown timer activated if player within affect_rad
        self.damage_constant = (0.5 * self.affect_rad) ** 3 / 2  # constant for damage to sprites within affect_rad inversely proportional to distance squared

        self.active = False
        self.countdown = 3  # countdown timer seconds

        self.current_animation = self.game.mobile_sprite_images[self.refkey]
        self.refresh_rate = 0.1  # rate animation changes slide (0.5 - changes twice per second)

        self.setup_hitrect()

    def setup_hitrect(self):
        """Configure hitbox centered on the mine sprite."""
        size = int(self.rect.height * 0.6)
        self.hitrect = pygame.Rect(0, 0, size, size)
        self.hitrect.center = self.rect.center

    def handle_platform_collision(self, axis):

        hits = self.collide_sprites(self.hitrect, 'platforms')
        if hits:
            self.explode()

    def activate(self, delay=3.0):
        """Activate the mine with a countdown timer."""
        if not self.active:
            self.active = True
            self.countdown = delay

    def explode(self):
        """Detonate mine — inflict area damage, chain react other mines, and play effects."""
        self.inflict_damage("players", 0)
        self.inflict_damage("enemies", 3000)
        self.chain_react_mines()

        # Remove from map, move to hold group, trigger explosion animation
        self.remove(self.game.map.layers[self.map_layer][self.gridref])
        self.add(self.game.hold_sprites)
        self.change_action(self.game.effects_images, "explosion4x4")

        choice(self.game.ambient_sounds["mine_explode"]).play()

    def inflict_damage(self, layer_key, velocity_constant):
        """Apply explosion damage to sprites within radius in the specified map layer."""
        for ref in self.adjacent_grids:
            for sprite in self.game.map.layers[layer_key][ref]:
                displacement = vec(sprite.rect.center) - vec(self.rect.center)
                distance = displacement.length() or 1  # prevent div by zero

                damage = self.damage_constant / (distance ** 2)
                sprite.vel = displacement.normalize() * (velocity_constant / distance)
                sprite.take_damage(damage)

    def chain_react_mines(self):
        """Trigger nearby mines to begin countdown based on distance."""
        for ref in self.adjacent_grids:
            for sprite in self.game.map.layers[self.map_layer][ref]:
                if sprite is not self and getattr(sprite, "refkey", None) == "mine":
                    displacement = vec(sprite.rect.center) - vec(self.rect.center)
                    distance_tiles = displacement.length() / self.game.map.tilesize
                    sprite.active = False  # override if mine is already active
                    sprite.activate(delay=0.02 * distance_tiles)  # slightly faster reaction chain

    def update(self):
        """Update mine state — activate, countdown, and explode."""
        self.get_adjacent_grids()

        if self.active:
            self.countdown -= self.game.dt
            if self.countdown <= 0:
                self.explode()


class Player(Mobile_sprite):

    _layer = 2
    map_layer = 'players'
    refkey = 'player_idle'

    runspeed = 8
    rot_speed = 3  # degrees per second
    hitpoints = 100
    stamina = 100
    rate_of_fire = 0.4  # rate at which player shoots (seconds)
    weapons = ['harpoon', 'torpedo']

    def __init__(self, game, x, y):

        super().__init__(game, x, y)
        self.startpos = vec(self.pos.x, self.pos.y)  # TESTING ONLY
        self.add_to_map_layer()

        # Core attributes
        self.score = 0
        self.hitpoints = Player.hitpoints
        self.stamina = Player.stamina

        # Control system
        self.control_scheme = {"axial": self.axial_movement,
                               "rotational": self.rotational_movement}
        self.current_scheme = "axial"

        # Weapon system
        self.current_weapon = "harpoon"
        self.weaponstate = {"harpoon": True, "torpedo": True, "plasmagun": False}
        self.ammo = {"harpoon": 200, "torpedo": 500}
        self.last_shot = 0

        # Animation
        self.actionvar = "player_idle"
        self.newaction = "player_idle"
        self.current_animation = game.mobile_sprite_images[self.actionvar]
        self.refresh_rate = 0.15

        # State
        self.dead = False
        self.damaged = False

    def apply_clamps(self):

        self.hitpoints = clamp(self.hitpoints, 0, Player.hitpoints)
        self.stamina = clamp(self.stamina, 0, Player.stamina)

    def toggle_controls(self):
        """Toggle between movement control modes."""
        modes = list(self.control_scheme.keys())
        next_mode = (modes.index(self.current_scheme) + 1) % len(modes)
        self.current_scheme = modes[next_mode]
        logger.info(f"[INFO] Control scheme switched to '{self.current_scheme}'")

    def get_mouse_rotation(self):  #
        """ Handle mouse movement with sensitivity and inversion: sensitivity range set betweeen 0.1 - 2 for current setup"""
        settings = self.game.controls["mouse"]["settings"]
        sensitivity = settings.get("sensitivity", 2.0)
        invert_y = settings.get("invert_y", False)

        pygame.mouse.set_visible(False)
        dx, dy = pygame.mouse.get_rel()  # get the amount of mouse movement (x, y)
        scrollH = clamp(dx / 10 * sensitivity, -15, 15)
        if invert_y:
            dy = -dy
        return scrollH, dy  # return horizontal mouse movement

    def axial_movement(self, keys):

        """Movement in 8 directions controlled with keys only"""
        """8-directional movement (WASD style)."""
        move = self.game.controls["keyboard"]["movement"]
        dash_key = self.game.controls["keyboard"]["actions"]["dash"]

        unit_vel = vec(0, 0)
        vertical = [keys[move["forward"]], keys[move["backward"]]]
        horizontal = [keys[move["left"]], keys[move["right"]]]

        self.newaction = "player_idle"
        if sum(vertical) == 1:
            unit_vel += vertical[0] * vec(0, -1)  # up
            unit_vel += vertical[1] * vec(0, 1)  # down
            self.newaction = "player_swimming"

        if sum(horizontal) == 1:
            unit_vel += horizontal[0] * vec(-1, 0)  # left
            unit_vel += horizontal[1] * vec(1, 0)  # right
            self.newaction = "player_swimming"
        # unit_vel = vec(-1, 1)
        self.vel = unit_vel.normalize() * Player.runspeed if unit_vel else vec(0, 0)
        self.direction = vec(unit_vel.x, unit_vel.y) if unit_vel else self.direction
        self.rect_rtn = vec(self.direction.x, self.direction.y).angle_to(vec(1, 0))  # angle sprite in direction of velocity

        if keys[dash_key]:
            self.dash()
        else:
            self.increment_stamina(1)
            # self.stamina += interval_trigger(self.game.elapsed_time, 0.2, self.game.dt) * 1  # recover stamina

    def rotational_movement(self, keys):

        """Mouse-aimed movement with rotation."""
        move = self.game.controls["keyboard"]["movement"]
        dash_key = self.game.controls["keyboard"]["actions"]["dash"]
        runspeed = 0
        self.vel = vec(0, 0)

        scrollH, _ = self.get_mouse_rotation()
        self.direction = self.direction.rotate(scrollH)

        if keys[move["left"]]:
            runspeed = 0.5 * Player.runspeed
            self.vel += vec(self.direction.y, -self.direction.x)

        elif keys[move["right"]]:
            runspeed = 0.5 * Player.runspeed
            self.vel += vec(-self.direction.y, self.direction.x)

        if keys[move["forward"]]:
            runspeed = Player.runspeed
            self.vel += self.direction

        elif keys[move["backward"]]:
            runspeed = 0.5 * Player.runspeed
            self.vel += -self.direction

        # TODO: Option to invert mouse y axis
        self.newaction = "player_swimming"

        if self.vel:
            self.vel = self.vel.normalize() * runspeed if self.vel else vec(0, 0)
            self.rect_rtn = vec(self.direction.x, self.direction.y).angle_to(vec(1, 0))  # rotate sprite
            self.newaction = "player_swimming"
        else:
            self.newaction = "player_idle"

        self.rect_rtn = vec(self.direction.x, self.direction.y).angle_to(vec(1, 0))  # rotate sprite

        if keys[dash_key]:
            self.dash()
        else:
            self.increment_stamina(1)

    def dash(self):

        if self.stamina > 0:
            self.vel *= 1.5
            # self.stamina -= interval_trigger(self.game.elapsed_time, 0.2, self.game.dt) * 5
            self.increment_stamina(-5)
            self.newaction = 'player_rush'

    def increment_stamina(self, factor = -1):
        """Recover stamina at fixed rate."""
        self.stamina += interval_trigger(self.game.elapsed_time, 0.2, self.game.dt) * factor

    def handle_platform_collision(self, axis):

        self.discrete_collision_detection(axis, 'platforms')

    def choose_weapon_numpad(self, index):

        index = max(0, min(index, len(self.weapons)))

        weaponkey = self.weapons[index-1]
        if self.weaponstate[weaponkey]:  # if player carrying selected weapon key
            self.current_weapon = weaponkey

    def choose_weapon_mousewheel(self, event):

        current_index = self.weapons.index(self.current_weapon)
        if event.button == 4:
            current_index -= 1
        elif event.button == 5:
            current_index += 1

        current_index %= len(self.weapons)  # loop weaponslist
        weaponkey = self.weapons[current_index]
        if self.weaponstate[weaponkey]:  # if player carrying selected weapon
            self.current_weapon = weaponkey

    def shoot(self, keys):
        shoot_key = self.game.controls["keyboard"]["actions"]["shoot"]
        if pygame.mouse.get_pressed()[0] or keys[shoot_key]:
            if self.game.elapsed_time - self.last_shot > Player.rate_of_fire:
                self.last_shot = self.game.elapsed_time * 1

                if self.ammo[self.current_weapon] > 0:
                    #  TODO: vary missile velocity marginally
                    # set start pos such that missile hitrect starts at player rect center
                    start_pos = self.pos - ((self.HRoffset*self.game.map.tilesize) * self.direction.normalize())
                    # start_pos += 92 * self.direction.normalize()
                    # start_pos = self.pos + (2*self.game.map.tilesize - self.HRoffset) * self.direction.normalize()
                    missile = self.game.objectpools[self.current_weapon].borrow_object(start_pos.x, start_pos.y)
                    missile.activate(self)

                    self.ammo[self.current_weapon] -= 1
                    choice(self.game.ambient_sounds[self.current_weapon]).play()
                else:
                    choice(self.game.ambient_sounds['gun_reload']).play()

    def collide_enemy(self):

            hits = self.collide_sprites(self.hitrect, 'enemies')
            for hit in hits:
                self.hitpoints -= interval_trigger(self.game.elapsed_time, 0.2, self.game.dt) * hit.mob_damage  # hitpoints deducted every 0.2 seconds

    def collide_mine(self):

        for ref in self.adjacent_grids:

            for sprite in self.game.map.layers['obstacles'][ref]:
                if sprite.refkey == 'mine':
                    displacement = vec(sprite.rect.center) - vec(self.rect.center)
                    if displacement.length() < sprite.affect_rad:
                        sprite.activate()  # if player within affect_rad activates mine countdown timer

    def collide_pick_up(self):
        # TODO Object pool for pickups
        hits = self.collide_sprites(self.hitrect, 'pickups')
        if hits:
            hits[0].apply_pickup()

    def take_damage(self, points_lost):

        self.hitpoints -= points_lost
        if points_lost > 20:
            self.damaged = True
            self.damage_alpha = chain(self.__class__.damage_alpha * 8)  # cycle through colour gradients twice

    def death(self):

        if self.hitpoints == 0:
            self.dead = True

    def update(self):
        # reset parameters
        self.rot_speed = 0

        self.get_adjacent_grids()  # return list of current and adjacent gridrefs

        # Player controls
        keys = pygame.key.get_pressed()

        if not self.damaged:
            self.control_scheme.get(self.current_scheme)(keys)  # movement control scheme
            self.shoot(keys)

        else:
            self.newaction = "player_hurt"
            if self.continuous_collision_detection(0, 'platforms', self.hitrect, self.vel):
                self.vel.x = 0
            # if no collision detected for hitrect check collision for sprite rect where player is adjacent to the wall
            if self.continuous_collision_detection(1, 'platforms', self.rect, self.vel):
                self.vel.y = 0

        # # Check platform collision and update rect
        # self.collide_platforms(0)  # check horizontal collision
        # self.collide_platforms(1)  # check vertical collision

        # check sprite collisions
        self.collide_pick_up()
        self.collide_mine()
        self.collide_enemy()

        self.apply_clamps()
        self.death()

        self.change_action(self.game.mobile_sprite_images, self.newaction)  # change self.actionvar to new action
        self.current_animation = self.game.mobile_sprite_images[self.actionvar]
        # print(self.pos)


class Enemy(Mobile_sprite):

    _layer = 2
    num_of_mobs = 0
    mob_damage = 2  # deducted from player health (damage inflicted)
    antiGrav = 1.2  # constant of accn which repels mobs away from each other within avoid_rad
    hitpoints = 10
    deathanimation = 'enemydeath'

    def __init__(self, game, x, y):

        super().__init__(game, x, y)
        self.start_pos = vec(x, y)
        self.anti_g = vec(0, 0)
        self.displacement = vec(0, 0)

        self.chase_player_rad = 2 * game.map.gridwidth
        self.rect_collisionF = pygame.Rect(0, 0, game.map.tilesize, game.map.tilesize)
        self.rect_collisionL = pygame.Rect(0, 0, game.map.tilesize, game.map.tilesize)

        self.current_animation = game.mobile_sprite_images[self.refkey]
        self.refresh_rate = 0.2

        # Choose initial random target within safe bounds
        self.target = self._get_random_target()
        self.target_vec = self.pos - self.target

        Enemy.num_of_mobs += 1

    def avoid_walls(self):
        """ Apply repulsion force away from nearby walls"""

        for ref in self.adjacent_grids:
            for ptf in self.game.map.layers['platforms'][ref]:
                displacement = vec(ptf.rect.centerx, ptf.rect.centery) - self.pos  # between mob and centre point of platform tile
                anti_g = -displacement * (self.__class__.mass / displacement.length()**2)  # accelleration away from wall- proportional to current speed, inversly proportional to displacemnt squared
                self.vel += anti_g
                self.anti_g = anti_g  # TESTING only (drawing)

    def avoid_mobs(self):

        """ Prevent clumping by applying repulsion force between enemies"""
        for ref in self.adjacent_grids:
            for mob in self.game.map.layers['enemies'][ref]:  # loop through mobs in current grid
                if mob != self:  # exclude self
                    displacement = mob.pos - self.pos
                    anti_g = -displacement * (Enemy.antiGrav*4 / displacement.length())**2
                    self.vel += anti_g

    def handle_platform_collision(self, axis):
        """Simple elastic bounce response for wall collisions"""
        hits = super().discrete_collision_detection(axis, 'platforms')
        if hits:
            self.vel[axis] *= -1 / 2  # bounce off walls

    def _get_random_target(self):
        """Pick random target within map bounds."""
        gx, gy = self.game.map.gridwidth, self.game.map.gridheight
        tx = clamp(self.pos.x + choice([-1, 1]) * 2 * gx, 4 * gx, self.game.map.width - 4 * gx)
        ty = clamp(self.pos.y + choice([-1, 1]) * 2 * gy, 4 * gy, self.game.map.height - 4 * gy)
        return vec(tx, ty)

    def get_target_vector(self):
        """Compute new vector toward target with random perturbation."""

        adjusted_target = self.target_error()
        new_target_vec = adjusted_target - vec(self.rect.center)
        self.target_vec = new_target_vec or self.target_vec  # if new_target_vec is zero return previous target_vec

    def target_error(self):
        """ Intermittently switch target position by a percentage of the target vector for less predictable mob movement.
        Amount target pos varies decreases as mob approaches target"""
        swc = switch_interval(self.timer, self.__class__.switch_freq)
        direction = swc or 1
        perp_vec = vec(direction * self.target_vec.y, -direction * self.target_vec.x)

        err = randrange(0, self.__class__.error_margin + self.__class__.error_var, 10)
        error_vec = perp_vec * (err / 100)
        return self.target + error_vec

    def idle_swim(self, territory_rad):
        """ Swim towards random points (targets) on screen when not chasing player, other mobs etc"""
        switch_target = (
            self.vel.length_squared() < 1
            or interval_trigger(self.timer, 4, self.game.dt)
        )

        if switch_target:

            targetx = randrange(int(self.start_pos.x - territory_rad), int(self.start_pos.x + territory_rad))
            targety = randrange(int(self.start_pos.y - 0.25 * territory_rad), int(self.start_pos.y + 0.25 * territory_rad))

            # Limit target to within map extents
            targetx = clamp(targetx, self.game.map.gridwidth, self.game.map.width - self.game.map.gridwidth)
            targety = clamp(targety, self.game.map.gridheight, self.game.map.height - self.game.map.gridheight)

            new_target = vec(targetx, targety)
            if not self.check_intersect(new_target):
                self.target = new_target

    def chase_player(self):
        """Switch target to player if within chase radius and unobstructed."""
        player_vec = self.game.player.pos - self.pos
        if player_vec.length_squared() < self.chase_player_rad ** 2:
            target = vec(self.game.player.rect.center)
            if not self.check_intersect(target):
                self.target = target

    def check_intersect(self, target):
        """ Check if platform is between current position and target vect"""
        for ref in self.adjacent_grids:
            for ptf in self.game.map.layers['platforms'][ref]:
                for side in ptf.rect_sides:
                    if vec_intersect(self.pos, target, side[0], side[1]):
                        self.start_pos = vec(self.pos.x, self.pos.y)  # reset start position
                        return True
        return False

    def take_damage(self, points_lost):

        self.hitpoints -= points_lost
        self.damaged = True  # for damage effect visualisation
        self.damage_alpha = chain(self.__class__.damage_alpha * 2)  # cycle through colour gradients twice

    def death(self):

        if self.hitpoints <= 0:
            choice(self.game.ambient_sounds['mob_death']).play()
            self.rect_rtn = 0  # set back to horizontal
            self.remove(self.game.map.layers['enemies'][self.gridref])
            self.add(self.game.hold_sprites)
            self.change_action(self.game.effects_images, self.__class__.deathanimation)  # change self.actionvar to new action

    def update(self):

        self.get_adjacent_grids()
        self.idle_swim(self.__class__.territory_rad)

        self.get_target_vector()  # find new target vector
        self.chase_target()
        self.chase_player()
        self.avoid_walls()
        self.avoid_mobs()
        self.death()


class Daddyfish(Enemy):

    map_layer = 'enemies'
    refkey = 'daddyfish'
    hitpoints = 100
    territory_rad = 1472  # 4 * map.gridwidth
    maxspeed = 8
    mass = 4

    error_margin = 5  # average percentage error for tracking target vec  (25%
    error_var = 2  # variance in percentage error ( 25 +/- 5% )
    switch_freq = 2  # switch to new target every n seconds

    avoidRect_length = 276  # 6 * TILESIZE  # rect for detecting platforms/ walls

    deathanimation = 'enemydeath4x4'

    def __init__(self, game, x, y):

        super().__init__(game, x, y)

        # self.hitpoints = Daddyfish.hitpoints
        self.vel = vec(1, 0)
        self.interval = randrange(2000, 3000) / 1000  # time between implementing change in trajectory (seconds) for idle swim

    def chase_target(self):
        """Get acceleration vector directed to target.  Drag coefficient minimises velocity to Daddyfish.maxspeed"""

        self.rect_rtn = self.vel.angle_to(vec(1, 0))
        accn = 0.3
        drag = accn / self.__class__.maxspeed
        acc_vec = self.target_vec.normalize() * accn
        self.vel += acc_vec - drag * self.vel


class Dartfish(Enemy):

    map_layer = 'enemies'
    refkey = 'dartfish'
    hitpoints = 10
    vel = vec(6, 0)  # initial velocity
    max_speed = 14
    mass = 6
    territory_rad = 690  # 15 * TILESIZE
    error_margin = 25  # average percentage error for tracking target vec  (25%
    error_var = 30  # variance in percentage error ( 25 +/- 30% )
    switch_freq = 0.2  # recalc target_error every n seconds (don't confuse with change target idle_swim fnc)

    avoidRect_length = 368  # 8 * TILESIZE  # rect for detecting platforms/ walls

    # Spiral trajectory parameters- follows log spiral path
    Qrot = 1/100  # geometric progession of turning radius after subtends 360deg e.g. q = 0.1- radius 1/10 of initial radius.  Set to <1 by default for inward spiral
    b = log(Qrot)/(2*pi)  # growth rate of the log spiral trajectory (inward by default)
    theta = pi/60  # angle subtended every iteration
    geo_pro = e ** (b * theta)  # geometric increase/ decrease of turning radius from origin for every increment

    def __init__(self, game, x, y):

        super().__init__(game, x, y)
        self.hitpoints = Dartfish.hitpoints
        self.vel = Dartfish.vel
        self.interval = randrange(1000, 2000)/1000  # time between implementing change in trajectory (seconds) for passive swim

    def spiral_turn(self, direction):
        """ Switch from either log spriral or exp spiral trajectory to close in on target_vec"""

        # find new velocity vector from initial vel and radius vectors to the origin of the spiral path
        prev_rad = get_radius_vector(self.vel, self.theta, self.geo_pro, direction)  # radius from spiral origin to position on previous iteration
        # self.current_rad = vec_trans(prev_rad, prev_rad.length()*(self.geo_pro), self.theta, direction)
        final_rad = vec_trans(prev_rad, prev_rad.length()*(self.geo_pro**2), 2*self.theta, direction)  # radius from origin after self.pos updated with new_vel
        self.vel = prev_rad - final_rad - self.vel  # New vel vector the difference between prior rad, current velocity and the final rad vectors

        return final_rad

    def change_trajectory(self, direction):
        """ Will switch geometric progression from inward to outward spiral path, so mob will intersect target at current target.pos
            Uses control variable c: if c=1 will continue inward spiral by default, if c=-1 will switch to outward spiral path """
        alt_rad = get_radius_vector(self.vel, self.theta, 1/self.geo_pro, direction)  # radius vector from origin for outward spiral if currently following inward spiral path, and vice versa
        target_rad = alt_rad - self.target_vec    # radius vector between target and origin of alternate spiral trajectory
        delta = get_angleii(alt_rad, target_rad, direction)
        dif = (alt_rad.length()*((1/self.geo_pro)**(delta/self.theta))) - target_rad.length()  # if difference = 0 for current mob position then mob will intersect player by changing trajectory from inward to outward spiral (vice versa)

        c = sign(dif)  # returns either +- 1  # control variable determines whether to follow inward or outward spiral path
        # TODO minimum speed - switch to outward path
        c = 1 if self.vel.length() > (Dartfish.max_speed + (0.2*c*Dartfish.max_speed)) else c  # if vel exceeds max limit force inward path

        self.geo_pro = Dartfish.geo_pro ** c

    def chase_target(self):

        self.rect_rtn = vec(self.vel.x, self.vel.y).angle_to(vec(1, 0))  # angle sprite in direction of velocity
        direction = turn_direction(self.vel, self.target_vec)
        self.spiral_turn(direction)
        self.change_trajectory(direction)


class Spinefish(Dartfish):

    map_layer = 'enemies'
    refkey = 'spinefish'
    hitpoints = 20
    vel = vec(4, 0)  # initial velocity
    max_speed = 12

    def __init__(self, game, x, y):

        super().__init__(game, x, y)

        self.vel = Spinefish.vel
        self.hitpoints = 20
