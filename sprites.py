import pygame
from math import e, log
from random import choice, randrange
from statistics import mean

from settings import *
from helpers.spritesheet_functions import *
from helpers.vector_functions import *
from helpers.interval_trigger import *

vec = pygame.Vector2  # 2D vector - x = vec.x  y = vec.y


class Static_sprite(pygame.sprite.Sprite):
    """Background sprites for visual purposes only (no interaction, collisions. Single image sprites not animated """
    def __init__(self, game, col, row, refkey, image):

        pygame.sprite.Sprite.__init__(self)
        self.game = game
        self.pos = vec(col, row) * TILESIZE  # position in pixels
        self.refkey = refkey  # the sprite dictionary key name
        self.image = image
        self.rect = image.get_rect()
        self.rect.topleft = (self.pos.x, self.pos.y)

        self.refresh_rate = 1  # rate animation changes slide (0.5 - changes twice per second)

    def draw(self):

        self.game.screen.blit(self.image, self.game.camera.apply(self))


class Platform(Static_sprite):
    """Wall sprite; player, mobs can't pass through"""
    antiGrav = 0.5  # constant of acceleration which repels mob sprites away from walls

    def __init__(self, game, col, row, refkey, image):
        """Generates a single platform tile."""
        super().__init__(game, col, row, refkey, image)
        gridref = game.x_coords[int(self.pos.x//GRIDWIDTH)] + game.y_coords[int(self.pos.y//GRIDHEIGHT)]
        self.game.walls[gridref].add(self)


class Pick_up(Static_sprite):

    def __init__(self, game, start_x, start_y, image):
        """Generates a single pick_up tile."""
        super().__init__(game, start_x, start_y, image)

    def apply_pickup(self, player):
        player.game.score += 50


class Mobile_sprite(Static_sprite):
    """Mobile sprites animated and/ or have velocity.  Self.pos is placed at rect.center rather than topleft for rotating sprites"""

    def __init__(self, game, col, row, refkey, image):

        super().__init__(game, col, row, refkey, image)
        self.start_pos = vec(col, row) * TILESIZE  # for keeping mob within rad of starting position
        self.rect.center = self.pos
        self.setup_hitrect()

        self.refkey = refkey  # the sprite dictionary key name
        self.ref_image = image  # for mob image transformation (flip/ rotate)
        self.image = self.ref_image
        self.get_gridref()  # current grid position
        self.radius = 0.75 * ((self.rect.width+self.rect.height)/4)  # for collision detection (collide_circle) between mobile sprites e.g. player and mobs
        self.rect_rtn = 0  # rotate sprite rect and image

        self.actionvar = "idle"  # current sprite action
        self.newaction = "idle"  # new sprite action on e.g. keyboard input- jumping, walking etc

        # handle animations
        self.timer = 0  # used to trigger next frame for animations (can set to -ve value to delay start of an animation)
        self.current_frame_index = 0  # used to check if at end of animation reel i.e. at next game loop animation will start over

    def setup_hitrect(self):
        """ hitrect square centred about self.rect.center. Used for platform collisions. """
        # TODO: hitrect dimensions need to be adjusted for missile sprites, possibly other classes
        self.hitrect = self.rect
        HRlength = 1/2 * (self.rect.width + self.rect.height)
        self.hitrect.width, self.hitrect.height = HRlength, HRlength

    def get_gridref(self):

        grid_col, grid_row = self.rect.center[0] // GRIDWIDTH, self.rect.center[1] // GRIDHEIGHT
        self.gridref = self.game.x_coords[grid_col] + self.game.y_coords[grid_row]

    def assign_sprite_to_grid(self, map_layer):
        """ Remove sprite from previous grids, and reassign sprite to corresponding grids (sprite groups) in game class grid squares dictionary"""

        map_layer[self.gridref].remove(self)  # remove sprite from grid for previous loop
        self.get_gridref()  # get updated grid coordinates
        map_layer[self.gridref].add(self)  # add sprite to new grid

    def adjacent_grids(self):
        """ Return list of current and adjacent grid e.g. if sprite in grid B1 this will return ['A0', 'A1', 'A2', 'B0', 'B1', 'B2', 'C0', 'C1', 'C2'] """

        adjacent_grids = []
        grid_col, grid_row = self.rect.center[0] // GRIDWIDTH, self.rect.center[1] // GRIDHEIGHT
        grids_left = max(grid_col-1, 0)  # return index position for grids to the left
        grids_right = min(grid_col+1, len(self.game.x_coords)-1)
        grids_above = max(grid_row-1, 0)
        grids_below = min(grid_row+1, len(self.game.y_coords)-1)
        for i in range(grids_left, grids_right+1):
            for j in range(grids_above, grids_below+1):
                gridref = self.game.x_coords[i] + self.game.y_coords[j]
                adjacent_grids.append(gridref)

        return adjacent_grids

    def collide_rect(self, rect, platform):

        return rect.colliderect(platform.rect)

    def collide_platforms(self, hitrect, axis):  # [0, 1] for either [x, y] axis
        # TODO Fix player sprite 'judder' when moving along a platform
        self.hitrect[axis] = self.pos[axis] - 1/2*self.hitrect.size[axis]   # update rect with new position
        self.rect.center = self.hitrect.center

        check_grids = self.adjacent_grids()
        totalhits = []  # if colling with wall tiles in multiple grids when between grid boundaries
        for gridref in check_grids:
            grid = self.game.walls[gridref]  # return sprite group from grid_squares dictionary
            hits = pygame.sprite.spritecollide(hitrect, grid, False, self.collide_rect)
            totalhits += hits
        # totalhits = pygame.sprite.spritecollide(hitrect, self.game.walls[self.gridref], False, self.collide_rect)
        if totalhits:

            d = sign(self.vel[axis])  # direction of travel: left = -1, right = 1, up = -1, down = 1

            # overlap between self.hitrect and platform.rect
            overlap = 0.5*d*(self.hitrect.size[axis] + totalhits[0].rect.size[axis]) - (totalhits[0].rect.center[axis] - self.hitrect.center[axis])
            self.pos[axis] -= overlap  # reset position so no longer colliding
            self.hitrect[axis] = self.pos[axis] - 1/2*self.hitrect.size[axis]   # update rect post collision
            self.rect.center = self.hitrect.center
            return True

    def atMapBoundaries(self):
        """ Check if at map boundaries (collision detection not used for platforms at boundary)"""

        self.pos.x = max(min(self.game.map.RHS - 1/2*self.hitrect.width, self.pos.x), self.game.map.LHS + 1/2*self.hitrect.width)
        self.pos.y = max(min(self.game.map.btm - 1/2*self.hitrect.height, self.pos.y), self.game.map.top + 1/2*self.hitrect.height)

    def change_action(self, newaction):
        """ change action from e.g. jumping to falling.  First check current action to see if action has actually changed then return new actionvar"""
        if self.actionvar != newaction:
            self.actionvar = newaction
            self.timer = 0  # set timer at start of animation.  Resets to zero when switching to other animation
            self.current_frame_index = 0  # first animation slide

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
        self.rect.center = self.hitrect.center

    def animate(self, anim_reel):
        """Update current animation frame and transform image"""

        current_frame_index = int((self.timer // self.refresh_rate) % len(anim_reel))  # must be before self.timer updated for check_anim_end to work
        self.timer += self.game.dt
        self.ref_image = anim_reel[current_frame_index]
        self.image = self.ref_image
        self.transform_image()
        # self.image.fill(RED)
        return current_frame_index

    def check_anim_end(self, anim_reel):
        """ check if animation will end & return to 1st frame on next game loop"""

        if int((self.timer // self.refresh_rate) % len(anim_reel)) < self.current_frame_index:
            return True

    def draw(self):

        self.current_frame_index = self.animate(self.current_animation)
        self.game.screen.blit(self.image, self.game.camera.apply(self))


class Player(Mobile_sprite):

    runspeed = 8
    rot_speed = 3  # degrees per second
    health = 100

    def __init__(self, game, col, row, refkey, image):
        super().__init__(game, col, row, refkey, image)

        # self.image.fill(RED)
        self.assign_sprite_to_grid(self.game.players)
        self.vel = vec(0, 0)
        self.direction = vec(1, 0)
        self.actionvar = "player_idle"  # current sprite action
        self.newaction = "player_idle"  # new sprite action on e.g. keyboard input- jumping, walking etc
        self.current_animation = game.player_images[self.actionvar]  # current animation slide (list of images)
        self.refresh_rate = 0.15  # rate animation changes slide (0.5 - changes twice per second)

        self.health = Player.health

    def axial_movement(self):

        """Movement in 8 directions controlled with keys only"""
        keys = pygame.key.get_pressed()
        unit_vel = vec(0, 0)
        verticalKeys = [keys[pygame.K_DOWN], keys[pygame.K_UP]]
        horizontalKeys = [keys[pygame.K_RIGHT], keys[pygame.K_LEFT]]

        self.newaction = "player_idle"
        if sum(verticalKeys) == 1:
            unit_vel += verticalKeys[0] * vec(0, 1)  # up
            unit_vel += verticalKeys[1] * vec(0, -1)  # down
            self.newaction = "player_swimming"

        if sum(horizontalKeys) == 1:
            unit_vel += horizontalKeys[0] * vec(1, 0)  # left
            unit_vel += horizontalKeys[1] * vec(-1, 0)  # right
            self.newaction = "player_swimming"

        self.vel = unit_vel.normalize() * Player.runspeed if unit_vel else vec(0, 0)
        self.direction = vec(unit_vel.x, unit_vel.y) if unit_vel else self.direction
        self.rect_rtn = vec(self.direction.x, self.direction.y).angle_to(vec(1, 0))  # angle sprite in direction of velocity

    def rotational_movement(self):

        keys = pygame.key.get_pressed()
        unit_vel = vec(0, 0)
        self.newaction = "player_swimming"
        if keys[pygame.K_w]:
            unit_vel = vec(0, 1)
            self.newaction = "player_rush"
        elif keys[pygame.K_s]:
            unit_vel = vec(0, -1/2)
            self.newaction = "player_swimming"
        if keys[pygame.K_a]:
            unit_vel = vec(3/4, 0)
            self.newaction = "player_swimming"
        elif keys[pygame.K_d]:
            unit_vel = vec(-3/4, 0)
            self.newaction = "player_swimming"

        scrollH = self.get_mouse(2)
        self.direction = self.direction.rotate(scrollH)
        angle = self.direction.angle_to(vec(0, 1))

        self.vel = (unit_vel*Player.runspeed).rotate(-angle) if unit_vel else vec(0, 0)
        self.rect_rtn = vec(self.direction.x, self.direction.y).angle_to(vec(1, 0))  # rotate sprite

    def get_mouse(self, sensitivity):  #
        """ Set sensitivity range to be betweeen 0.1 - 2 for current setup"""
        pygame.mouse.set_visible(False)
        movement = pygame.mouse.get_rel()  # get the amount of mouse movement (x, y)

        scrollH = 1/10 * movement[0] * sensitivity  # set x axis movement sensitivity
        scrollH = max(min(15, scrollH), -15)  # set to be between 10-20
        return scrollH  # return horizontal mouse movement

    def shoot(self):

        missile_img = self.game.weapons_images['harpoonEast'][0]
        rotated_img = pygame.transform.rotate(missile_img, self.rect_rtn)
        col, row = int(self.pos.x // TILESIZE), int(self.pos.y // TILESIZE)
        missile = Missile(self.game, col, row, 'harpoonEast', rotated_img)
        self.game.all_sprites.add(missile)

    def collide_enemy(self):

        check_grids = self.adjacent_grids()
        for gridref in check_grids:
            grid = self.game.enemies[gridref]
            hits = pygame.sprite.spritecollide(self, grid, False, pygame.sprite.collide_circle)
            for hit in hits:
                self.health -= interval_trigger(self.timer, 0.2, self.game.dt) * hit.mob_damage  # health deducted every 0.2 seconds

    def collide_pick_up(self, pick_ups):

        hits = pygame.sprite.spritecollide(self, pick_ups, False, pygame.sprite.collide_rect_ratio(0.5))
        if hits:
            hits[0].kill()  # delete sprite
            hits[0].apply_pickup(self)

    def death(self):

        if self.health < 0:
            print("Dead")

    def update(self):
        # reset parameters
        self.rot_speed = 0
        # self.vel = vec(0, 0)

        # Check platform collision and update rect
        self.assign_sprite_to_grid(self.game.players)
        self.atMapBoundaries()
        self.collide_platforms(self.hitrect, 0)  # check horizontal collision
        self.collide_platforms(self.hitrect, 1)  # check vertical collision

        # check sprite collisions
        # self.collide_pick_up(self.game.pick_ups)
        self.collide_enemy()

        self.death()

        # Player movement
        self.axial_movement()
        # self.rotational_movement()
        # self.pos += self.vel

        # update player animation reel
        self.change_action(self.newaction)  # change self.actionvar to new action
        self.current_animation = self.game.player_images[self.actionvar]


class Missile(Mobile_sprite):

    runspeed = 25
    # TODO Have child classes of missile richochet walls sporadically if hits at an angle
    def __init__(self, game, col, row, refkey, image):
        super().__init__(game,  col, row, refkey, image)
        self.assign_sprite_to_grid(self.game.weapons)
        self.current_animation = self.game.weapons_images[refkey]
        # self.pos = vec(game.player.rect.centerx, game.player.rect.centery)
        self.rect_rtn = game.player.rect_rtn
        self.vel = game.player.direction.normalize() * Missile.runspeed
        self.vel.x += randrange(-2, 2, 1)  # vary the direction marginally
        self.vel.y += randrange(-2, 2, 1)

    def ricochet(self):

        pass

    def collide_enemy(self):

        check_grids = self.adjacent_grids()
        for gridref in check_grids:
            grid = self.game.enemies[gridref]
            hits = pygame.sprite.spritecollide(self, grid, False, pygame.sprite.collide_rect_ratio(0.7))
            if hits:
                hits[0].hitpoints -= 10
                self.kill()

    def update(self):

        # TODO Fix collision with map boundaries
        self.assign_sprite_to_grid(self.game.weapons)

        # collide walls
        self.atMapBoundaries()
        if self.collide_platforms(self.hitrect, 0) or self.collide_platforms(self.hitrect, 1):
            self.ricochet()
            self.vel = vec(0, 0)
            # self.add(self.game.hold_sprites)
            self.remove(self.game.weapons[self.gridref])

        self.collide_enemy()

        # self.pos += self.vel
        self.rect.center = self.pos


class Bubbles(Mobile_sprite):
    """Shelved"""
    def __init__(self, game, col, row, refkey, image):
        super().__init__(game, col, row, refkey, image)
        self.current_animation = self.game.effects_images[self.refkey]
        self.timer = randrange(-4, 0)
        self.vel = vec(0, 0)

        self.refresh_rate = 0.2

    def update(self):

        # self.pos += self.vel
        self.rect.bottomleft = self.pos

        if self.check_anim_end(self.current_animation):
            respawnpoint = choice(self.game.spawnpoints)
            self.pos.x, self.pos.y = respawnpoint[0]*TILESIZE, respawnpoint[1]*TILESIZE

        if self.timer >= 0:
            self.vel = vec(0, -8)  # velocity vector


class Enemy(Mobile_sprite):

    num_of_mobs = 0

    chase_player_rad = 1 * TILESIZE  # chase player if within radius
    mob_damage = 2  # deducted from player health (damage inflicted)

    def __init__(self, game, col, row, refkey, image):
        super().__init__(game, col, row, refkey, image)
        self.assign_sprite_to_grid(self.game.enemies)
        self.rect_collisionF = pygame.Rect(0, 0, TILESIZE, TILESIZE)  # for testing only
        self.rect_collisionL = pygame.Rect(0, 0, TILESIZE, TILESIZE)  # for testing only
        self.parallel_vec = vec(1, 0)

        self.displacement = vec(0, 0)

        self.hitpoints = 10
        # self.hit_player = False

        self.deathanimation = self.game.effects_images['enemyDeath']
        self.current_animation = self.game.mob_images[self.refkey]
        self.refresh_rate = 0.2

        self.target = vec(0, 0)
        self.target.x = max(min(self.game.map.width - 4 * TILESIZE, self.start_pos.x + choice([-1, 1]) * 2 * TILESIZE), 4 * TILESIZE)
        self.target.y = max(min(self.game.map.height - 4 * TILESIZE, self.start_pos.y + choice([-1, 1]) * 2 * TILESIZE), 4 * TILESIZE)
        self.target_vec = self.pos - self.target

        Enemy.num_of_mobs += 1

    def avoid_walls(self):
        # TODO avoid map boundary walls
        check_grids = self.adjacent_grids()
        hits = []  # list of sprites collided
        for gridref in check_grids:
            grid = self.game.walls[gridref]
            hits += pygame.sprite.spritecollide(self.avoidRect, grid, False, self.collide_rect)  # append collide sprites for each grid
        if hits:

            x_mean = mean(wallsprite.pos.x for wallsprite in hits)  # average x pos for collided wall sprites
            y_mean = mean(wallsprite.pos.y for wallsprite in hits)  # average y pos
            displacement = vec(x_mean, y_mean) - self.pos  # between mob position and wall tile position
            self.displacement = vec(displacement.x, displacement.y)  # testing only
            anti_g = -displacement * (Platform.antiGrav / displacement.length())  # accelleration away from wall- inversly proportional to displacemnt
            self.vel += anti_g

    def get_target_vector(self, target):
        """Find new target vector from mob centre to target centre."""

        # Limit target to within map extents
        self.target.x = max(min(self.game.map.width - (4 * TILESIZE), self.target.x), 4 * TILESIZE)
        self.target.y = max(min(self.game.map.height - (4 * TILESIZE), self.target.y), 4 * TILESIZE)

        new_target_vec = target - vec(self.rect.centerx, self.rect.centery)
        self.target_vec = new_target_vec or self.target_vec  # if new_target_vec is zero return previous target_vec

    def target_error(self):
        """ Intermittently switch target position by a percentage of the target vector for less predictable mob movement.
        Amount target pos varies decreases as mob approaches target"""
        swc = switch_interval(self.timer, self.__class__.switch_freq)  # switch target every second (returns either 0 or -1)
        d = swc or 1  # either 1 or -1
        pdlr_target_vec = vec(d*self.target_vec.y, -d*self.target_vec.x)  # clockwise / anticlockwise perpendicular target vec

        # vary target position by +/- error margin equivalent to 10% of the perpendicular target vector
        x_error = pdlr_target_vec.x * self.__class__.error_margin
        y_error = pdlr_target_vec.y * self.__class__.error_margin

        adjust_target = vec(self.target.x + x_error, self.target.y + y_error)  # target_position adjusted for % error
        return adjust_target

    def idle_swim(self, territory_rad):

        switch_target = False
        if self.target_vec.length() < TILESIZE:
            switch_target = True
        if interval_trigger(self.timer, 4, self.game.dt):
            switch_target = True
        if switch_target:
            self.target.x = randrange(self.start_pos.x - territory_rad, self.start_pos.x + territory_rad)
            self.target.y = randrange(self.start_pos.y - 0.2 * territory_rad, self.start_pos.y + 0.2 * territory_rad)

    def collide_player(self):
        """ Currently shelved"""
        # TODO fix collide_player() to replace collide_emeny(): mob locks onto player and move at combined velocity
        if pygame.sprite.collide_circle(self, self.game.player):
            self.game.player.health -= interval_trigger(self.timer, 0.2, self.game.dt) * self.mob_damage  # health deducted every 0.2 seconds
            if not self.hit_player:  # initial collision with player
                combined_vel = (self.vel - self.game.player.vel) * self.__class__.momentum
                self.vel = combined_vel
                # self.game.player.pos += self.vel  # update player position (in affect player vel == mob vel
                self.game.player.vel = combined_vel
                self.hit_player = True

            elif self.hit_player:  # already collided with player
                self.game.player.vel = self.vel

        else:
            self.hit_player = False

    def death(self):

        if self.hitpoints <= 0:
            self.rect_rtn = 0  # set back to horizontal
            self.remove(self.game.enemies[self.gridref])
            self.add(self.game.hold_sprites)

            # update animation reel to death animation
            self.newaction = 'explode'
            self.current_animation = self.deathanimation
            self.change_action(self.newaction)  # change self.actionvar to new action

    def update(self):

        self.assign_sprite_to_grid(self.game.enemies)
        self.idle_swim(self.__class__.territory_rad)
        if (self.game.player.pos - self.pos).length() < self.chase_player_rad:
            self.target = vec(self.game.player.rect.centerx, self.game.player.rect.centery)
        adjust_target = self.target_error()  # add a % error to the target which switches between +/- error every second
        self.get_target_vector(adjust_target)  # find new target vector
        self.chase_target()
        self.avoid_walls()
        # self.collide_player()
        self.death()
        # self.pos += self.vel

        # collide walls
        self.atMapBoundaries()
        if self.collide_platforms(self.hitrect, 0):  # check horizontal collision
            self.vel.x *= -1 / 2  # bounce off walls
        if self.collide_platforms(self.hitrect, 1):  # check vertical collision
            self.vel.y *= -1 / 2  # bounce off walls

        self.avoidRect.center = self.rect.center


class Daddyfish(Enemy):

    territory_rad = 20 * TILESIZE
    maxspeed = 6
    # momentum = 0.9  # % velocity transferred to player during collision
    error_margin = 0.5  # percentage error for tracking target vec
    switch_freq = 2  # switch to new target every n seconds

    avoidRect_length = 6 * TILESIZE  # rect for detecting platforms/ walls

    def __init__(self, game, col, row, refkey, image):
        super().__init__(game, col, row, refkey, image)
        self.avoidRect = pygame.Rect(0, 0, Daddyfish.avoidRect_length, Daddyfish.avoidRect_length)
        self.avoidRect.center = self.hitrect.center

        self.hitpoints = 100
        self.vel = vec(1, 0)
        self.deathanimation = self.game.effects_images['enemyDeath4x4']
        self.interval = randrange(2000, 3000) / 1000  # time between implementing change in trajectory (seconds) for idle swim

    def chase_target(self):
        """Get acceleration vector directed to target and return new velocity.  Drag coefficient minimises velocity to Daddyfish.maxspeed"""

        self.rect_rtn = vec(self.vel.x, self.vel.y).angle_to(vec(1, 0))  # angle sprite so facing target

        accn = 0.1  # acceleration magnitude
        drag_coeff = accn / Daddyfish.maxspeed  # friction/ drag coefficient

        accn_vec = vec(self.target_vec.normalize() * accn)
        self.vel.x = self.vel.x + accn_vec.x - (drag_coeff * self.vel.x)
        self.vel.y = self.vel.y + accn_vec.y - (drag_coeff * self.vel.y)


class Dartfish(Enemy):

    vel = vec(6, 0)  # initial velocity
    max_speed = 16
    # momentum = 0.1  # % velocity transferred to player during collision
    territory_rad = 15 * TILESIZE
    error_margin = 0.5  # percentage error for tracking target vec
    switch_freq = 2  # switch to new target every n seconds
    avoidRect_length = 8 * TILESIZE  # rect for detecting platforms/ walls

    # turning parameters- trajectory follows log spiral path
    Qrot = 1/100  # geometric progession of turning radius after subtends 360deg e.g. q = 0.1- radius 1/10 of initial radius.  Set to <1 by default for inward spiral
    b = log(Qrot)/(2*pi)  # growth rate of the log spiral trajectory (inward by default)
    k = -1  # control variable equal to +/- 1: determines whether to follow inward or outward spiral trajectory.  Default value of -1: inward spiral
    theta = pi/60  # angle subtended every iteration
    geo_pro = e ** (b * theta)  # geometric increase/ decrease of turning radius from origin for every increment

    def __init__(self, game, col, row, refkey, image):
        super().__init__(game, col, row, refkey, image)

        self.avoidRect = pygame.Rect(0, 0, Dartfish.avoidRect_length, Dartfish.avoidRect_length)
        self.avoidRect.center = self.hitrect.center

        self.vel = Dartfish.vel
        self.deathanimation = self.game.effects_images['enemyDeath2x1']
        self.interval = randrange(1000, 2000)/1000  # time between implementing change in trajectory (seconds) for passive swim

    def spiral_turn(self, direction):
        """ Switch from either log spriral or exp spiral trajectory to close in on target_vec"""

        # find new velocity vector from initial vel and radius vectors to the origin of the spiral path
        prev_rad = get_radius_vector(self.vel, self.theta, self.geo_pro, direction)  # radius from spiral origin to position on previous iteration
        # self.current_rad = vec_trans(prev_rad, prev_rad.length()*(self.geo_pro), self.theta, direction)
        final_rad = vec_trans(prev_rad, prev_rad.length()*(self.geo_pro**2), 2*self.theta, direction)  # radius from origin after self.pos updated with new_vel
        new_vel = prev_rad - final_rad - self.vel  # New vel vector the difference between prior rad, current velocity and the final rad vectors
        self.vel = new_vel

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

    vel = vec(4, 0)  # initial velocity
    max_speed = 12

    def __init__(self, game, col, row, refkey, image):
        super().__init__(game, col, row, refkey, image)

        self.vel = Spinefish.vel
        self.hitpoints = 20
        self.deathanimation = self.game.effects_images['enemyDeath2x1']


