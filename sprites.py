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

        self.refresh_rate = 1  # rate animation changes slide (0.5 - changes twice per second)

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
        self.rect.center = self.pos
        self.hitrect = self.rect
        self.start_pos = vec(col, row) * TILESIZE  # for keeping mob within rad of starting position
        self.refkey = refkey  # the sprite dictionary key name

        self.ref_image = image  # for mob image transformation (flip/ rotate)
        self.image = self.ref_image
        self.angle = 0  # angle subtended from vector (1, 0) i.e. anticlockwise from the x-axis
        self.current_grids = self.get_grids(self.hitrect)  # grids which sprite overlaps
        self.actionvar = "idle"  # current sprite action
        self.newaction = "idle"  # new sprite action on e.g. keyboard input- jumping, walking etc

        # handle animations
        self.timer = 0  # used to trigger next frame for animations (can set to -ve value to delay start of an animation)
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

    def get_grids(self, rect):

        # return index position of grids overlapping rect
        grid_cols = list(range((rect.topleft[0])//GRIDWIDTH, (((rect.topright[0])//GRIDWIDTH) + 1)))
        grid_rows = list(range((rect.topleft[1])//GRIDHEIGHT, ((rect.bottomleft[1])//GRIDHEIGHT) + 1))
        grids = []

        for row in grid_rows:
            row = max(min(len(self.game.grid_squares) - 1, row), 0)  # limit col within grid_squares width
            for col in grid_cols:
                col = max(min(len(self.game.grid_squares[0]) - 1, col), 0)  # limit row within grid_squares height
                grid = self.game.grid_squares[row][col]  # lookup grid sprite.Group
                grids.append(grid)
        # print([[grid.coordinates] for grid in grids])
        return grids

    def collide_rect(self, rect, platform):

        return rect.colliderect(platform.rect)

    def collide_platforms(self, hitrect, axis):  # [0, 1] for either [x, y] axis

        self.hitrect[axis] = self.pos[axis] - 1/2*self.hitrect.size[axis]   # update rect with new position
        self.rect.center = self.hitrect.center
        self.current_grids = self.get_grids(self.hitrect)  # must be before spritecollide
        totalhits = []  # if colling with sprites in multiple grids when between grid boundaries
        for grid in self.current_grids:
            hits = pygame.sprite.spritecollide(hitrect, grid, False, self.collide_rect)
            totalhits += hits

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
        new_rect = surf.get_rect(center = self.pos)  # replace self.pos with offset it rotating about a pivot
        return surf, new_rect

    def transform_image(self):
        """Flip image about y axis if sprite is upside down, then rotate image about rect.center"""

        if self.angle < -90 or self.angle > 90:
            self.ref_image = pygame.transform.flip(self.ref_image, False, True)  # flip image

        self.image, self.rect = self.rotate_about_centre(self.angle)

    def animate(self, anim_reel):
        """Update current animation frame and transform image"""

        current_frame_index = int((self.timer // self.refresh_rate) % len(anim_reel))  # must be before self.timer updated for check_anim_end to work
        self.timer += self.game.dt
        self.ref_image = anim_reel[current_frame_index]
        self.image = self.ref_image
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
    health = 100

    def __init__(self, game, col, row, refkey, image):
        super().__init__(game, col, row, refkey, image)

        # self.image.fill(RED)
        self.direction = 'North'
        self.directionKeys = [0, 0, 0, 0]  # see get_direction()
        self.vel = vec(0, 0)

        self.actionvar = "player_idle"  # current sprite action
        self.newaction = "player_idle"  # new sprite action on e.g. keyboard input- jumping, walking etc
        self.current_animation = game.player_images[self.actionvar]  # current animation slide (list of images)
        self.refresh_rate = 0.25  # rate animation changes slide (0.5 - changes twice per second)

        self.health = Player.health

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

        for hit in hits:
            self.health -= interval_trigger(self.timer, 0.2, self.game.dt) * hit.mob_damage  # health deducted every 0.2 seconds

            # TODO mob locks onto player and move at combined velocity
            combined_vel = hit.vel + self.vel  # inactive feature
            mobvel = 0.01 * combined_vel  # replace mobvel with hit.vel
            playervel = 0.01 * combined_vel  # replace playervel with self.vel

    def collide_pick_up(self, pick_ups):

        hits = pygame.sprite.spritecollide(self, pick_ups, False, pygame.sprite.collide_rect_ratio(0.5))
        if hits:
            hits[0].kill()  # delete sprite
            hits[0].apply_pickup(self)

    def death(self):

        if self.health < 0:
            print("Dead")

    def update(self):

        # check sprite collisions
        # self.collide_enemy()
        # self.collide_pick_up(self.game.pick_ups)

        # self.vel = vec(0, 0)
        self.newaction = "player_idle"

        # check sprite collisions

        self.collide_enemy()
        # self.collide_pick_up(self.game.pick_ups)

        # Player movement
        self.get_direction()
        if self.get_unit_vel(self.directionKeys):
            self.newaction = "player_swim"
            self.vel *= Player.runspeed

        self.death()
        self.pos += self.vel

        # Check platform collision

        self.atMapBoundaries()
        self.collide_platforms(self.hitrect, 0)  # check horizontal collision
        self.collide_platforms(self.hitrect, 1)  # check vertical collision

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

        # TODO Fix collision with map boundaries

        self.current_grids = self.get_grids(self.rect)  # update grid position
        collide = False
        for grid in self.current_grids:
            if pygame.sprite.spritecollideany(self, grid, pygame.sprite.collide_rect_ratio(0.8)):
                collide = True

        if collide:
            self.vel = vec(0, 0)
            self.add(self.game.hold_sprites)
            self.remove(self.game.active_sprites)

        self.collide_enemy()

        self.pos += self.vel
        self.rect.center = self.pos


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

    chase_player_rad = 5 * TILESIZE  # chase player if within radius
    avoidRect_length = 6 * TILESIZE  # rect for detecting platforms/ walls
    mob_damage = 1  # deducted from player health (damage inflicted)

    def __init__(self, game, col, row, refkey, image):
        super().__init__(game, col, row, refkey, image)

        self.avoidRectH = pygame.Rect(self.hitrect.centerx, self.hitrect.centery, Enemy.avoidRect_length, self.hitrect.height)  # avoidRect for horizontal collisions
        self.avoidRectV = pygame.Rect(self.hitrect.centerx, self.hitrect.centery, self.hitrect.width, Enemy.avoidRect_length)  # avoidRect for vertical collisions
        self.avoidRectH.midleft = self.hitrect.center
        self.avoidRectV.midtop = self.hitrect.center

        self.hitpoints = 10
        self.deathanimation = self.game.effects_images['enemyDeath']
        self.current_animation = self.game.mob_images[self.refkey]
        self.refresh_rate = 0.2

        self.target = vec(0, 0)
        self.target.x = max(min(self.game.map.width - 4 * TILESIZE, self.start_pos.x + choice([-1, 1]) * 2 * TILESIZE), 4 * TILESIZE)
        self.target.y = max(min(self.game.map.height - 4 * TILESIZE, self.start_pos.y + choice([-1, 1]) * 2 * TILESIZE), 4 * TILESIZE)
        self.target_vec = self.pos - self.target

        Enemy.num_of_mobs += 1

    def avoid_walls(self, avoidRect, axis):
        """ Use self.avoidRect to detect upcoming walls and turn to avoid collision"""
        current_grids = self.get_grids(avoidRect)  # grids overlapping avoidRect

        for grid in current_grids:
            hits = pygame.sprite.spritecollide(avoidRect, grid, False, self.collide_rect)
            if hits:
                wallvec = hits[0].pos - self.pos  # vector from mob to wall
                # d = sign(vec(1, 0).dot(self.target_vec))  # if vel in same direction as target_vec (dot product > 0), switch target to be behind player (reflect coords about player pos line of symetry)
                d = sign(wallvec.dot(self.target_vec))  # if vel in same direction as target_vec (dot product > 0), switch target to be behind player (reflect coords about player pos line of symetry)
                self.target[axis] = self.pos[axis] - d*(self.target[axis] - self.pos[axis])

        return avoidRect

    def get_target_vector(self, target):
        """Find new target vector from mob centre to target centre."""

        new_target_vec = target - vec(self.rect.centerx, self.rect.centery)
        self.target_vec = new_target_vec or self.target_vec  # if new_target_vec is zero return previous target_vec

    def switch_target(self):
        """ Intermittently switch target position by a precentage of the target vector for less predictable mob movement.
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

        if self.target_vec.length() < TILESIZE:
            self.target.x = randrange(self.start_pos.x - territory_rad, self.start_pos.x + territory_rad)
            self.target.y = randrange(self.start_pos.y - 0.5 * territory_rad, self.start_pos.y + 0.5 * territory_rad)

    def limit_target_vec(self):
        """  Limit target to within map extents"""

        self.target.x = max(min(self.game.map.width - (4 * TILESIZE), self.target.x), 4 * TILESIZE)
        self.target.y = max(min(self.game.map.height - (4 * TILESIZE), self.target.y), 4 * TILESIZE)

    def death(self):

        if self.hitpoints <= 0:
            self.angle = 0
            self.remove(self.game.mob_sprites)
            self.remove(self.game.active_sprites)
            self.add(self.game.hold_sprites)

            # update animation reel to death animation
            self.newaction = 'explode'
            self.current_animation = self.deathanimation
            self.change_action(self.newaction)  # change self.actionvar to new action

    def update(self, *args):

        self.idle_swim(self.__class__.territory_rad)
        if (self.game.player.pos - self.pos).length() < self.chase_player_rad:
            self.target = vec(self.game.player.rect.centerx, self.game.player.rect.centery)
        self.avoidRectH = self.avoid_walls(self.avoidRectH, 0)
        self.avoidRectV = self.avoid_walls(self.avoidRectV, 1)
        adjust_target = self.switch_target()  # add a % error to the target which switches between +/- error every second
        self.limit_target_vec()  # limit target_vec to within map boundaries
        self.get_target_vector(adjust_target)  # find new target vector
        self.chase_target()
        self.death()
        self.pos += self.vel

        self.avoidRectH.midleft = self.hitrect.center
        self.avoidRectH.width *= sign(self.vel.x)
        self.avoidRectH.normalize()  # avoid negative values for width, height- illegal for rect.collide

        self.avoidRectV.midtop = self.hitrect.center
        self.avoidRectV.height *= sign(self.vel.y)
        self.avoidRectV.normalize()

        # Check platform collision
        self.atMapBoundaries()
        self.collide_platforms(self.hitrect, 0)  # check horizontal collision
        self.collide_platforms(self.hitrect, 1)  # check vertical collision


class Daddyfish(Enemy):

    territory_rad = 10 * TILESIZE
    maxspeed = 6
    error_margin = 0.5  # percentage error for tracking target vec
    switch_freq = 2  # switch to new target every n seconds

    def __init__(self, game, col, row, refkey, image):
        super().__init__(game, col, row, refkey, image)

        self.hitpoints = 100
        self.vel = vec(1, 0)
        self.deathanimation = self.game.effects_images['enemyDeath4x4']
        self.interval = randrange(2000, 3000) / 1000  # time between implementing change in trajectory (seconds) for idle swim

    def chase_target(self):
        """Get acceleration vector directed to target and return new velocity.  Drag coefficient minimises velocity to Daddyfish.maxspeed"""

        self.angle = vec(self.vel.x, self.vel.y).angle_to(vec(1, 0))  # angle sprite so facing target

        accn = 0.1  # acceleration magnitude
        drag_coeff = accn / Daddyfish.maxspeed  # friction/ drag coefficient

        accn_vec = vec(self.target_vec.normalize() * accn)
        self.vel.x = self.vel.x + accn_vec.x - (drag_coeff * self.vel.x)
        self.vel.y = self.vel.y + accn_vec.y - (drag_coeff * self.vel.y)


class Dartfish(Enemy):

    vel = vec(6, 0)  # initial velocity
    max_speed = 16
    territory_rad = 8 * TILESIZE
    error_margin = 0.5  # percentage error for tracking target vec
    switch_freq = 2  # switch to new target every n seconds

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
        self.interval = randrange(1000, 2000)/1000  # time between implementing change in trajectory (seconds) for passive swim
        self.delta = 2*pi

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
            Uses control variable d: if d=1 will continue inward spiral by default, if d=-1 will switch to outward spiral path """
        alt_rad = get_radius_vector(self.vel, self.theta, 1/self.geo_pro, direction)  # radius vector from origin for outward spiral if currently following inward spiral path, and vice versa
        target_rad = alt_rad - self.target_vec    # radius vector between target and origin of alternate spiral trajectory
        delta = get_angleii(alt_rad, target_rad, direction)
        dif = (alt_rad.length()*((1/self.geo_pro)**(delta/self.theta))) - target_rad.length()  # if difference = 0 for current mob position then mob will intersect player by changing trajectory from inward to outward spiral (vice versa)

        c = sign(dif)  # returns either +- 1  # control variable determines whether to follow inward or outward spiral path
        # TODO minimum speed - switch to outward path
        c = 1 if self.vel.length() > (Dartfish.max_speed + (0.2*c*Dartfish.max_speed)) else c  # if vel exceeds max limit force inward path

        self.geo_pro = Dartfish.geo_pro ** c

    def chase_target(self,):

        self.angle = vec(self.vel.x, self.vel.y).angle_to(vec(1, 0))  # angle sprite in direction of velocity
        direction = turn_direction(self.pos, self.vel, self.target_vec)
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


