import pygame
from math import fabs, floor
from math import sqrt as sqrt
from random import choice, randrange
from settings import *
from helpers.spritesheet_functions import *

vec = pygame.Vector2  # 2D vector - x = vec.x  y = vec.y


class Static_sprite(pygame.sprite.Sprite):
    """Don't have velocity though may be animated"""
    def __init__(self, game, col, row, refkey, image):

        pygame.sprite.Sprite.__init__(self)
        self.game = game
        self.pos = vec(col, row) * TILESIZE  # position in pixels
        self.refkey = refkey  # the sprite dictionary key name
        self.image = image
        # self.rect = pygame.Rect(0, 0, width, height)
        self.rect = image.get_rect()
        self.rect.topleft = self.pos

    def animate(self, time_period, anim_reel):

        # frames = anim_reel  # list of sprite animations
        current_frame_index = int((self.timer // time_period) % len(anim_reel))
        self.image = anim_reel[current_frame_index]
        return current_frame_index

    def check_anim_end(self, time_period, anim_reel):
        """ check if animation will return to 1st frame on next game loop"""
        if int((self.timer // time_period) % len(anim_reel)) < self.current_frame_index:
            return True

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
    """Mobile sprites defined as having velocity"""
    def __init__(self, game, col, row, refkey, image):

        super().__init__(game, col, row, refkey, image)
        self.refkey = refkey  # the sprite dictionary key name
        self.ref_image = image  # for mob image transformation (flip/ rotate)
        self.image = self.ref_image
        self.angle = 0  # angle subtended from vector (1, 0) i.e. anticlockwise from the x-axis
        # self.rect = image.get_rect()
        # self.rect.center = self.pos
        self.vel = vec(0, 0)  # unit vector to be multiplied by runspeed

        self.current_grids = self.get_grids()  # grids for which sprite overlaps

        self.actionvar = "idle"  # current sprite action
        self.newaction = "idle"  # new sprite action on e.g. keyboard input- jumping, walking etc

        # handle animations
        self.timer = 0  # used to trigger next frame for animations (can set to -ve value to delay start of an animation
        self.current_frame_index = 0  # used to check if at end of animation reel i.e. at next game loop animation will start over

    def get_grids(self):
        """ Return grid or multiple grids if between boundaries to check for collisions"""

        def lookupgrid(pos):
            x, y = int(pos[0]), int(pos[1])
            x = min((self.game.map.width-2*TILESIZE), x)  # limit possible x pos to within map width (2340)
            y = min((self.game.map.height-2*TILESIZE), y) # 900
            grid_col = (x-TILESIZE)//GRIDWIDTH
            grid_row = (y-TILESIZE)//GRIDHEIGHT
            return self.game.grid_squares[grid_row][grid_col]

        grids = map(lookupgrid, ((self.rect.topleft),
                                 (self.rect.topright),
                                 (self.rect.bottomleft),
                                 (self.rect.bottomright)))
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

    def checkMapBoundaries(self):
        """ Check if at map boundaries (collision detection not used for platforms at boundary)"""

        # if self.pos.x <= TILESIZE or self.pos.x >= self.game.map.width - TILESIZE - self.rect.width - self.vel.x:
        #     self.pos.x += (self.vel.x * -1)
        # if self.pos.y <= TILESIZE or self.pos.y >= self.game.map.height - TILESIZE - self.rect.height - self.vel.y:
        #     self.pos.y += (self.vel.y * -1)

        if self.rect.left <= TILESIZE or self.rect.right >= self.game.map.width - TILESIZE:
            self.pos.x += (self.vel.x * -1)
        if self.rect.top <= TILESIZE or self.rect.bottom >= self.game.map.height - TILESIZE:
            self.pos.y += (self.vel.y * -1)

    def change_action(self, newaction):
        """ change action from e.g. jumping to falling.  First check current action to see if action has actually changed then return new actionvar"""

        if self.actionvar != newaction:

            self.actionvar = newaction
            self.timer = 0  # set timer at start of animation.  Resets to zero when switching to other animation
            self.current_frame_index = 0  # first animation slide


class Player(Mobile_sprite):

    runspeed = 4

    def __init__(self, game, col, row, refkey, image):
        super().__init__(game, col, row, refkey, image)

        # self.image.fill(RED)
        self.direction = 'North'
        self.dead = False

        self.current_grids = self.get_grids()  # grids for which player sprite overlaps
        self.actionvar = "player_idle"  # current sprite action
        self.newaction = "player_idle"  # new sprite action on e.g. keyboard input- jumping, walking etc
        self.current_animation = game.player_images[self.actionvar]  # current animation slide (list of images)

    def get_keys(self):

        keys = pygame.key.get_pressed()
        directionKeys = [keys[pygame.K_RIGHT], keys[pygame.K_LEFT], keys[pygame.K_DOWN], keys[pygame.K_UP]]  # e.g. [1, 0, 0, 1] will return NorthEast from ORIENTATIONS
        return directionKeys

    def get_direction(self, directionKeys):
        """compare directionKeys to ORIENTATIONS and return accordingly"""
        for key, value in ORIENTATIONS.items():
            if directionKeys == value:
                self.direction = key

    def find_unitvelocity(self, directionKeys):
        """ return unit vector for velocity"""
        self.vel += directionKeys[0] * vec(1, 0)   # up
        self.vel += directionKeys[1] * vec(-1, 0)  # down
        self.vel += directionKeys[2] * vec(0, 1)   # left
        self.vel += directionKeys[3] * vec(0, -1)  # right

        if self.vel != vec(0, 0):
            self.newaction = "player_swim"
            self.vel = self.vel.normalize()  # return unit vector -magnitude == 1 ( vec(1, 1) would have magnitude sqrt(2) without this step)

    def shoot(self):

        harpoonimg = 'harpoon' + self.direction  # image keyref according to direction being fired e.g. 'harpoonWest'
        missile_img = self.game.weapons_images[harpoonimg][0]
        self.missile = Missile(self.game, 0, 0, 'harpoon', missile_img)
        self.game.all_sprites.add(self.missile)

    def collide_enemy(self):

        hits = pygame.sprite.spritecollide(self, self.game.mob_sprites, False, pygame.sprite.collide_rect_ratio(0.7))  # check hits to the right

        if hits:
            hits[0].dead = True  # currently mob is killed if it collides with player
            hits[0].remove(self.game.mob_sprites)  # remove from sprite group
            hits[0].newaction = 'enemyDeath'  # mob sprite not deleted until after its death animation

    def collide_pick_up(self, pick_ups):

        hits = pygame.sprite.spritecollide(self, pick_ups, False, pygame.sprite.collide_rect_ratio(0.5))
        if hits:
            hits[0].kill()  # delete sprite
            hits[0].apply_pickup(self)

    def update(self):

        self.vel = vec(0, 0)
        self.newaction = "player_idle"

        # Player movement
        directionKeys = self.get_keys()
        self.get_direction(directionKeys)
        self.find_unitvelocity(directionKeys)
        self.vel *= Player.runspeed
        self.pos += self.vel

        # Check platform collision
        self.collide_platforms(0)  # check horizontal collision
        self.collide_platforms(1)  # check vertical collision

        # check sprite collisions
        self.collide_enemy()
        # self.collide_pick_up(self.game.pick_ups)

        # player animation
        self.change_action(self.newaction)  # change self.actionvar to new action
        self.current_animation = self.game.player_images[self.actionvar]
        self.current_frame_index = self.animate(0.5, self.current_animation[self.direction])
        self.timer += self.game.dt

        self.checkMapBoundaries()  # at map boundary?


class Missile(Mobile_sprite):

    runspeed = 25

    def __init__(self, game, col, row, refkey, image):
        super().__init__(game,  col, row, refkey, image)
        self.pos = vec(game.player.rect.centerx, game.player.rect.centery)
        self.direction = game.player.direction
        self.find_unitvelocity()
        self.vel *= Missile.runspeed

    def find_unitvelocity(self):

        self.vel += ORIENTATIONS[self.direction][0] * vec(1, 0)
        self.vel += ORIENTATIONS[self.direction][1] * vec(-1, 0)
        self.vel += ORIENTATIONS[self.direction][2] * vec(0, 1)
        self.vel += ORIENTATIONS[self.direction][3] * vec(0, -1)

        self.vel = self.vel.normalize()  # return unit vector -magnitude == 1

    def collide_enemy(self):

        hits = pygame.sprite.spritecollide(self, self.game.mob_sprites, False, pygame.sprite.collide_rect_ratio(0.7))
        if hits:
            hits[0].hitpoints -= 10
            self.kill()

    def update(self):

        self.pos += self.vel
        self.rect.center = self.pos

        self.collide_enemy()

        # delete missile once it goes off the map (not the screen)
        if self.pos.x < 0 or self.pos.x > self.game.map.width:
            self.kill()
        if self.pos.y < 0 or self.pos.y > self.game.map.height:
            self.kill()


class Bubbles(Mobile_sprite):

    def __init__(self, game, col, row, refkey, image):
        super().__init__(game, col, row, refkey, image)
        self.current_animation = self.game.effects_images[self.refkey]
        self.timer = randrange(-4, 0)

    def update(self):

        self.pos += self.vel
        self.rect.bottomleft = self.pos

        if self.check_anim_end(0.2, self.current_animation):
            respawnpoint = choice(self.game.spawnpoints)
            self.pos.x, self.pos.y = respawnpoint[0]*TILESIZE, respawnpoint[1]*TILESIZE

        if self.timer >= 0:
            self.vel = vec(0, -8)  # velocity vector
            self.current_frame_index = self.animate(0.2, self.current_animation)

        self.timer += self.game.dt


class Enemy(Mobile_sprite):

    num_of_mobs = 0
    runspeed = 1
    chase_player_rad = 20 * TILESIZE  # chase player if within radius
    attack_player_rad = 5 * TILESIZE  # attack player ""          ""

    def __init__(self, game, col, row, refkey, image):
        super().__init__(game, col, row, refkey, image)

        self.vel = vec(1, 0)
        self.target_vec = self.vel  # displacement vector between player and enemy
        self.hitpoints = 10
        self.upside_down = False
        self.deathanimation = self.game.effects_images['enemyDeath']
        self.current_animation = self.game.mob_images[self.refkey]

        Enemy.num_of_mobs += 1

    def get_target_vector(self, target):
        """Find new target vector from mob centre to target centre"""
        self.target_vec = vec(target.rect.centerx, target.rect.centery) - vec(self.rect.centerx, self.rect.centery)  # find new target vector

    def transform_image(self):
        """Flip image about y axis if sprite is upside down, then rotate image about rect.center"""

        if (self.angle < -90 or self.angle > 90):
            self.ref_image = pygame.transform.flip(self.ref_image, False, True)
        self.image = pygame.transform.rotate(self.ref_image, self.angle)
        # self.rect = self.image.get_rect(center=self.rect.center)

    def chase_player(self):

        if self.attack_player_rad < self.target_vec.length() < self.chase_player_rad:
            # self.turn_around()
            self.angle = vec(self.target_vec.x, self.target_vec.y).angle_to(vec(1, 0))  # angle sprite so facing target

            target_direction = vec(0, 0)  # e.g. (1, 0) travelling to right of screen (no y component)
            if self.target_vec.x != 0:
                target_direction.x = self.target_vec.x / fabs(self.target_vec.x)   # return -1, 1  for left, right respect. ...
            if self.target_vec.y != 0:
                target_direction.y = self.target_vec.y / fabs(self.target_vec.y)   # return -1, 1  for up, down respect. ...

            target_vel = self.target_vec.normalize() * self.runspeed  # velocity vector towards player position with magnitude equal to runspeed

            # accelerate towards player
            self.vel.x = sqrt(self.runspeed * fabs(target_vel.x))
            self.vel.x *= target_direction.x
            self.vel.y = sqrt(self.runspeed * fabs(target_vel.y))
            self.vel.y *= target_direction.y

    def attack_player(self):

        if self.target_vec.length() < self.attack_player_rad:
            self.vel = self.vel.normalize()*8

    def turn_around(self):
        """INCOMPLETE"""
        """ After attacking player or if player enter chase radius turn to pursue player"""
        target_vel = self.target_vec.normalize() * self.runspeed  # velocity vector towards player position with magnitude equal to runspeed
        self.target_angle = vec(target_vel).angle_to(self.vel)  # angle sprite so facing target
        dot_product = self.vel.dot(target_vel)
        if dot_product < 0:  # angle between mob velocity and target velocity > 90 deg
            turn_rate = 0.5
            perpendicular = vec(-self.vel.y, self.vel.x)
            turn_accn = perpendicular.normalize()*turn_rate
            self.vel += turn_accn

        target_direction = vec(0, 0)  # e.g. (1, 0) travelling to right of screen (no y component)
        # if self.target_vel.x != 0:
        #     target_direction.x = self.target_vel.x / fabs(self.target_vel.x)
        # if self.target_vel.y != 0:
        #     target_direction.y = self.target_vel.y / fabs(self.target_vel.y)

    def update(self):

        self.current_frame_index = self.animate(0.2, self.current_animation)
        self.timer += self.game.dt
        self.ref_image = self.current_animation[self.current_frame_index]  # current animation frame before any transformation (rotation, flip etc)

        if self.hitpoints > 0:
            self.get_target_vector(self.game.player)  # find new target vector

            self.chase_player()
            self.attack_player()
            self.transform_image()  # must be after self.animate in order to transform current image

        # if self.target_vec.x * self.vel.x < 0 or self.target_vec.y * self.vel.y < 0:  # if moving away from player
        else:
            self.dead = True
            self.newaction = 'explode'
            self.current_animation = self.deathanimation
            self.change_action(self.newaction)  # change self.actionvar to new action
            if self.check_anim_end(0.2, self.current_animation):
                self.kill()

        self.rect.topleft = self.pos
        self.pos += self.vel


class Dartfish(Enemy):

    runspeed = 4
    # runspeed = 1

    def __init__(self, game, col, row, refkey, image):
        super().__init__(game, col, row, refkey, image)

        self.deathanimation = self.game.effects_images['enemyDeath2x1']


class Spinefish(Enemy):

    runspeed = 2
    # runspeed = 1

    def __init__(self, game, col, row, refkey, image):
        super().__init__(game, col, row, refkey, image)

        self.hitpoints = 20
        self.deathanimation = self.game.effects_images['enemyDeath2x1']


class Daddyfish(Enemy):

    def __init__(self, game, col, row, refkey, image):
        super().__init__(game, col, row, refkey, image)

        self.hitpoints = 100
        self.deathanimation = self.game.effects_images['enemyDeath4x4']
