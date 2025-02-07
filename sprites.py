import pygame
from math import fabs, floor
from math import sqrt, e, log
from random import choice, randrange
from settings import *
from helpers.spritesheet_functions import *
from helpers.vector_functions import *
from helpers.interval_trigger import *

vec = pygame.Vector2  # 2D vector - x = vec.x  y = vec.y


class Static_sprite(pygame.sprite.Sprite):
    """PLatform, item, prop sprites. Single image sprites not animated """
    def __init__(self, game, col, row, refkey, image):

        pygame.sprite.Sprite.__init__(self)
        self.game = game
        self.pos = vec(col, row) * TILESIZE  # position in pixels
        self.refkey = refkey  # the sprite dictionary key name
        self.image = image
        # self.rect = pygame.Rect(0, 0, width, height)
        self.rect = image.get_rect()
        self.rect.topleft = self.pos

        self.refresh_rate = 1  # rate at which animation frame changes (=1 than changes every second

    def draw(self):

        self.game.screen.blit(self.image, self.game.camera.apply(self))


class Platform(Static_sprite):

    def __init__(self, start_x, start_y, image):
        "Generates a single platform tile."
        super().__init__(start_x, start_y, image)


class Pick_up(Static_sprite):

    def __init__(self, start_x, start_y, image):
        "Generates a single pick_up tile."
        super().__init__(start_x, start_y, image)

    def apply_pickup(self, player):
        player.game.score += 50


class Mobile_sprite(Static_sprite):
    """Mobile sprites animated and/ or have velocity"""
    def __init__(self, game, col, row, refkey, image):

        super().__init__(game, col, row, refkey, image)
        self.refkey = refkey  # the sprite dictionary key name
        self.ref_image = image  # for mob image transformation (flip/ rotate)
        self.image = self.ref_image
        self.angle = 0  # angle subtended from vector (1, 0) i.e. anticlockwise from the x-axis
        # self.vel = vec(0, 0)  # unit vector to be multiplied by runspeed

        self.current_grids = self.get_grids()  # grids for which sprite overlaps

        self.actionvar = "idle"  # current sprite action
        self.newaction = "idle"  # new sprite action on e.g. keyboard input- jumping, walking etc

        # handle animations
        self.timer = 0  # used to trigger next frame for animations (can set to -ve value to delay start of an animation
        self.current_frame_index = 0  # used to check if at end of animation reel i.e. at next game loop animation will start over

    def get_unit_vel(self, directionKeys):
        """ return unit vector for velocity"""
        self.vel += directionKeys[0] * vec(1, 0)   # up
        self.vel += directionKeys[1] * vec(-1, 0)  # down
        self.vel += directionKeys[2] * vec(0, 1)   # left
        self.vel += directionKeys[3] * vec(0, -1)  # right

        if self.vel != vec(0, 0):
            self.vel = self.vel.normalize()  # return unit vector with magnitude == 1 ( vec[1, 1] would have magnitude sqrt(2) without this step)
            return True

    def get_grids(self):
        """ Return grid or multiple grids if between boundaries to check for collisions"""

        def lookupgrid(pos):
            x, y = int(pos[0]), int(pos[1])
            x = min((self.game.map.width-2*TILESIZE), x)  # limit possible x pos to within map width (2340)
            y = min((self.game.map.height-2*TILESIZE), y) # 900
            grid_col = (x-TILESIZE)//GRIDWIDTH
            grid_row = (y-TILESIZE)//GRIDHEIGHT
            return self.game.grid_squares[grid_row][grid_col]

        grids = map(lookupgrid, (self.rect.topleft,
                                 self.rect.topright,
                                 self.rect.bottomleft,
                                 self.rect.bottomright))
        grids = list(set(grids))  # return grids minus duplicates

        return grids

    def collide_platforms(self, axis):  # [0, 1] for either [x, y] axis

        self.rect[axis] = self.pos[axis]  # update rect with new position
        self.current_grids = self.get_grids()  # must be before spritecollide
        totalhits = []  # if colling with sprites in multiple grids when between grid boundaries
        for grid in self.current_grids:
            hits = pygame.sprite.spritecollide(self, grid, False)
            totalhits += hits

        if totalhits:

            d = int(self.vel[axis] / fabs(self.vel[axis]))  # direction of travel: left = -1, right = 1, up = -1, down = 1
            # overlap between self.rect and platform.rect
            overlap = 0.5*d*(self.rect.size[axis] + totalhits[0].rect.size[axis]) - (totalhits[0].rect.center[axis] - self.rect.center[axis])
            self.pos[axis] -= overlap  # reset position so no longer colliding
            self.rect[axis] = self.pos[axis]  # update rect position

    def atMapBoundaries(self):
        """ Check if at map boundaries (collision detection not used for platforms at boundary)"""

        if self.rect.left <= 0.8*TILESIZE or self.rect.right >= self.game.map.width - 0.8*TILESIZE:
            self.pos.x += (self.vel.x * -1)
            return True

        if self.rect.top <= 0.8*TILESIZE or self.rect.bottom >= self.game.map.height - 0.8*TILESIZE:
            self.pos.y += (self.vel.y * -1)
            return True

    def change_action(self, newaction):
        """ change action from e.g. jumping to falling.  First check current action to see if action has actually changed then return new actionvar"""
        if self.actionvar != newaction:
            self.actionvar = newaction
            self.timer = 0  # set timer at start of animation.  Resets to zero when switching to other animation
            self.current_frame_index = 0  # first animation slide

    def transform_image(self):
        """Flip image about y axis if sprite is upside down, then rotate image about rect.center"""

        if (self.angle < -90 or self.angle > 90):
            self.image = pygame.transform.flip(self.image, False, True)
        self.image = pygame.transform.rotate(self.image, self.angle)

    def animate(self, anim_reel):
        """Update current animation frame and transform image"""

        current_frame_index = int((self.timer // self.refresh_rate) % len(anim_reel))  # must be before self.timer updated for check_anim_end to work
        self.timer += self.game.dt
        self.image = anim_reel[current_frame_index]
        self.transform_image()

        return current_frame_index

    def check_anim_end(self, anim_reel):
        """ check if animation will return to 1st frame on next game loop"""

        if int((self.timer // self.refresh_rate) % len(anim_reel)) < self.current_frame_index:
            return True

    def draw(self):

        self.current_frame_index = self.animate(self.current_animation)
        self.game.screen.blit(self.image, self.game.camera.apply(self))


class Player(Mobile_sprite):

    runspeed = 8

    def __init__(self, game, col, row, refkey, image):
        super().__init__(game, col, row, refkey, image)

        # self.image.fill(RED)
        self.direction = 'North'
        self.directionKeys = [0, 0, 0, 0]  # see get_direction()
        self.dead = False
        self.vel = vec(0, 0)

        self.current_grids = self.get_grids()  # grids for which player sprite overlaps
        self.actionvar = "player_idle"  # current sprite action
        self.newaction = "player_idle"  # new sprite action on e.g. keyboard input- jumping, walking etc
        self.current_animation = game.player_images[self.actionvar]  # current animation slide (list of images)
        self.refresh_rate = 0.25

    def get_direction(self):
        """compare directionKeys to ORIENTATIONS and return accordingly"""
        keys = pygame.key.get_pressed()
        self.directionKeys = [keys[pygame.K_RIGHT], keys[pygame.K_LEFT], keys[pygame.K_DOWN], keys[pygame.K_UP]]  # e.g. [1, 0, 0, 1] will return NorthEast from ORIENTATIONS
        for key, value in ORIENTATIONS.items():
            if self.directionKeys == value:
                self.direction = key

    def shoot(self):

        harpoonimg = 'harpoon' + self.direction  # image keyref according to direction being fired e.g. 'harpoonWest'
        missile_img = self.game.weapons_images[harpoonimg][0]
        missile = Missile(self.game, 0, 0, harpoonimg, missile_img)
        self.game.active_sprites.add(missile)
        self.game.all_sprites.add(missile)

    def collide_enemy(self):

        hits = pygame.sprite.spritecollide(self, self.game.mob_sprites, False, pygame.sprite.collide_rect_ratio(0.7))

        if hits:
            # hits[0].hitpoints = 0
            print("Collide")

    def collide_pick_up(self, pick_ups):

        hits = pygame.sprite.spritecollide(self, pick_ups, False, pygame.sprite.collide_rect_ratio(0.5))
        if hits:
            hits[0].kill()  # delete sprite
            hits[0].apply_pickup(self)

    def update(self):

        # Check platform collision
        self.collide_platforms(0)  # check horizontal collision
        self.collide_platforms(1)  # check vertical collision

        self.atMapBoundaries()

        # check sprite collisions
        self.collide_enemy()
        # self.collide_pick_up(self.game.pick_ups)

        self.vel = vec(0, 0)
        self.newaction = "player_idle"

        # Player movement
        self.get_direction()
        if self.get_unit_vel(self.directionKeys):
            self.newaction = "player_swim"
            self.vel *= Player.runspeed

        self.pos += self.vel

        # update player animation reel
        self.change_action(self.newaction)  # change self.actionvar to new action
        self.current_animation = self.game.player_images[self.actionvar][self.direction]


class Missile(Mobile_sprite):

    runspeed = 25

    def __init__(self, game, col, row, refkey, image):
        super().__init__(game,  col, row, refkey, image)
        self.current_animation = self.game.weapons_images[refkey]
        self.pos = vec(game.player.rect.centerx, game.player.rect.centery)
        self.vel = vec(0, 0)
        self.direction = game.player.direction
        self.get_unit_vel(ORIENTATIONS[self.direction])
        self.vel *= Missile.runspeed
        self.vel.x += randrange(-2, 2, 1)  # vary the direction marginally
        self.vel.y += randrange(-2, 2, 1)

    def collide_enemy(self):

        hits = pygame.sprite.spritecollide(self, self.game.mob_sprites, False, pygame.sprite.collide_rect_ratio(0.7))
        if hits:
            hits[0].hitpoints -= 10
            self.kill()

    def update(self):

        self.pos += self.vel
        self.rect.center = self.pos
        self.current_grids = self.get_grids()  # update grid position

        self.collide_enemy()

        # check platform collision
        for grid in self.current_grids:
            if pygame.sprite.spritecollideany(self, grid, pygame.sprite.collide_rect_ratio(0.8)):
                self.vel = vec(0, 0)
                self.add(self.game.hold_sprites)
                self.remove(self.game.active_sprites)  # not longer updated, drawn only

        if self.atMapBoundaries():
            self.vel = vec(0, 0)
            self.add(self.game.hold_sprites)
            self.remove(self.game.active_sprites)


class Bubbles(Mobile_sprite):

    def __init__(self, game, col, row, refkey, image):
        super().__init__(game, col, row, refkey, image)
        self.current_animation = self.game.effects_images[self.refkey]
        self.timer = randrange(-4, 0)
        self.vel = vec(0, 0)

        self.refresh_rate = 0.2

    def update(self):

        self.pos += self.vel
        self.rect.bottomleft = self.pos

        if self.check_anim_end(self.current_animation):
            respawnpoint = choice(self.game.spawnpoints)
            self.pos.x, self.pos.y = respawnpoint[0]*TILESIZE, respawnpoint[1]*TILESIZE

        if self.timer >= 0:
            self.vel = vec(0, -8)  # velocity vector


class Enemy(Mobile_sprite):

    num_of_mobs = 0
    chase_player_rad = 1000 * TILESIZE  # chase player if within radius
    attack_player_rad = 5 * TILESIZE  # attack player ""          ""

    def __init__(self, game, col, row, refkey, image):
        super().__init__(game, col, row, refkey, image)

        self.start_pos = vec(col, row) * TILESIZE  # for keeping mob within rad of starting position
        self.hitpoints = 10
        self.deathanimation = self.game.effects_images['enemyDeath']
        self.current_animation = self.game.mob_images[self.refkey]
        self.refresh_rate = 0.2
        self.target_vec = vec(0, 0)

        Enemy.num_of_mobs += 1

    def get_target_vector(self, target):
        """Find new target vector from mob centre to target centre.  Add varying % error to x, y components for more 'natural' path finding"""
        x_targ = target[0]
        y_targ = target[1]
        self.target_vec = vec(x_targ, y_targ)- vec(self.rect.centerx, self.rect.centery)  # find new target vector
        self.target_vec = vec(target[0], target[1]) - vec(self.rect.centerx, self.rect.centery)  # find new target vector

    def attack_player(self):
        """Currently shelved"""
        if self.target_vec.length() < self.attack_player_rad:
            self.vel = self.vel.normalize()*8


class Daddyfish(Enemy):

    def __init__(self, game, col, row, refkey, image):
        super().__init__(game, col, row, refkey, image)

        self.hitpoints = 100
        self.runspeed = 1
        self.vel = vec(self.runspeed, 0)
        self.deathanimation = self.game.effects_images['enemyDeath4x4']

    def chase_player(self):

        if self.target_vec.length() < self.chase_player_rad:

            self.angle = vec(self.target_vec.x, self.target_vec.y).angle_to(vec(1, 0))  # angle sprite so facing target

            target_direction = vec(0, 0)  # e.g. (1, 0) travelling to right of screen (no y component)
            if self.target_vec.x != 0:
                target_direction.x = self.target_vec.x / fabs(self.target_vec.x)  # return -1, 1  for left, right respect. ...
            if self.target_vec.y != 0:
                target_direction.y = self.target_vec.y / fabs(self.target_vec.y)  # return -1, 1  for up, down respect. ...

            target_vel = self.target_vec.normalize() * self.runspeed  # velocity vector towards player position with magnitude equal to runspeed

            # accelerate towards player
            self.vel.x = sqrt(self.runspeed * fabs(target_vel.x))
            self.vel.x *= target_direction.x
            self.vel.y = sqrt(self.runspeed * fabs(target_vel.y))
            self.vel.y *= target_direction.y

    def update(self):

        self.get_target_vector(self.game.player.rect.center)  # find new target vector
        self.chase_player()

        if self.hitpoints <= 0:
            self.remove(self.game.mob_sprites)
            self.remove(self.game.active_sprites)
            self.add(self.game.hold_sprites)

            # update animation reel to death animation
            self.newaction = 'explode'
            self.current_animation = self.deathanimation
            self.change_action(self.newaction)  # change self.actionvar to new action

        self.pos += self.vel
        self.rect.topleft = self.pos


class Dartfish(Enemy):

    vel = vec(4, 0)  # initial velocity
    max_speed = 16
    territory_rad = 5 * TILESIZE

    # turning parameters- trajectory follows log spiral path
    Qrot = 1/100  # geometric progession of turning radius after subtends 360deg e.g. q = 0.1- radius 1/10 of initial radius.  Set to <1 by default for inward spiral
    b = log(Qrot)/(2*pi)  # growth rate of the log spiral trajectory (inward by default)
    k = -1  # control variable equal to +/- 1: determines whether to follow inward or outward spiral trajectory.  Default value of -1: inward spiral
    theta = pi/60  # angle subtended every iteration
    geo_pro = e ** (b * theta)  # geometric increase/ decrease of turning radius from origin for every increment

    def __init__(self, game, col, row, refkey, image):
        super().__init__(game, col, row, refkey, image)

        self.vel = Dartfish.vel
        self.deathanimation = self.game.effects_images['enemyDeath2x1']
        self.interval = randrange(3000, 4000)/1000  # time between implementing change in trajectory (seconds)
        self.target = vec(0, 0)
        self.target.x = self.start_pos.x - (randrange(0 - Dartfish.territory_rad, Dartfish.territory_rad))
        self.target.y = self.start_pos.y - (randrange(0 - 0.5*Dartfish.territory_rad, 0.5*Dartfish.territory_rad))
        self.delta = 2*pi

    def spiral_turn(self, direction):
        """ Switch from either log spriral or exp spiral trajectory to close in on target_vec"""

        self.angle = vec(self.vel.x, self.vel.y).angle_to(vec(1, 0))  # angle sprite in direction of velocity

        # find new velocity vector from initial vel and radius vectors to the origin of the spiral path
        prev_rad = get_radius_vector(self.vel, self.theta, self.geo_pro, direction)  # radius from spiral origin to position on previous iteration
        # self.current_rad = vec_trans(prev_rad, prev_rad.length()*(self.geo_pro), self.theta, direction)
        final_rad = vec_trans(prev_rad, prev_rad.length()*(self.geo_pro**2), 2*self.theta, direction)  # radius from origin after self.pos updated with new_vel
        new_vel = prev_rad - final_rad - self.vel  # New vel vector the difference between prior rad, current velocity and the final rad vectors
        self.vel = new_vel

        return final_rad

    def change_trajectory(self, direction):
        """ Will switch geometric progression from inward to outward spiral path, so mob will intersect target at current target.pos
            Uses control variable d: if d=1 will continue inward spiral by default, if d=-1 will switch to outward spiral path """
        alt_rad = get_radius_vector(self.vel, self.theta, 1/self.geo_pro, direction)  # radius vector from origin for outward spiral if currently following inward spiral path, and vice versa
        target_rad = alt_rad - self.target_vec    # radius vector between target and origin of alternate spiral trajectory
        delta = get_angleii(alt_rad, target_rad, direction)
        dif = (alt_rad.length()*((1/self.geo_pro)**(delta/self.theta))) - target_rad.length()  # if difference = 0 for current mob position then mob will intersect player by changing trajectory from inward to outward spiral (vice versa)

        c = sign(dif)  # returns either +- 1  # control variable determines whether to follow inward or outward spiral path
        c = 1 if self.vel.length() > Dartfish.max_speed else c  # if vel exceeds max limit force inward path
        self.geo_pro = Dartfish.geo_pro ** c

    def chase_target(self):

        direction = turn_direction(self.pos, self.vel, self.target_vec)
        self.spiral_turn(direction)
        self.change_trajectory(direction)

    def update(self):

        if self.target_vec.length() < self.chase_player_rad:

            self.get_target_vector(self.game.player.rect.center)  # find new target vector
            self.target_vec += 5*self.vel  # adjust target according to players current vel
            self.chase_target()

        if self.hitpoints <= 0:
            self.remove(self.game.mob_sprites)
            self.remove(self.game.active_sprites)
            self.add(self.game.hold_sprites)

            # update animation reel to death animation
            self.newaction = 'explode'
            self.current_animation = self.deathanimation
            self.change_action(self.newaction)  # change self.actionvar to new action

        # self.limit_velocity()  # limit velocity magnitude
        self.pos += self.vel
        self.rect.topleft = self.pos


class Spinefish(Dartfish):

    vel = vec(4, 0)  # initial velocity
    max_speed = 12

    def __init__(self, game, col, row, refkey, image):
        super().__init__(game, col, row, refkey, image)

        self.vel = Spinefish.vel
        self.hitpoints = 20
        self.deathanimation = self.game.effects_images['enemyDeath2x1']


