import pygame
from math import e, log, pi
from random import choice, randrange
from itertools import chain

from .config import PICKUP_CATGRY
from .helpers import rect_to_vectors, sign, interval_trigger, switch_interval, vec_intersect, vec_trans, get_radius_vector, get_angleii, turn_direction

vec = pygame.Vector2  # 2D vector - x = vec.x  y = vec.y


class Static_sprite(pygame.sprite.Sprite):

    """Static, inanimate sprites includes props, platforms, pickups.  Parent class for all sprites. No update method"""
    def __init__(self, game, x, y, w, h):

        pygame.sprite.Sprite.__init__(self)
        self.game = game
        self.pos = vec(x, y)
        self.rect = pygame.Rect(x, y, w, h)
        # self.hitrect = pygame.Rect(x, y, w, h)
        self.rect.topleft = (self.pos.x, self.pos.y)
        self.hitrect = self.rect.copy()
        self.map_layer = self.__class__.map_layer

    def get_gridref(self):

        grid_col, grid_row = self.rect.center[0] // self.game.map.gridwidth, self.rect.center[1] // self.game.map.gridheight
        gridref = self.game.map.x_coords[grid_col] + self.game.map.y_coords[grid_row]

        return gridref

    def get_adjacent_grids(self):
        """ Return list of current and adjacent gridrefs e.g. if sprite in grid B1 this will return ['A0', 'A1', 'A2', 'B0', 'B1', 'B2', 'C0', 'C1', 'C2'] """

        self.adjacent_grids = []
        grid_col, grid_row = self.rect.center[0] // self.game.map.gridwidth, self.rect.center[1] // self.game.map.gridheight
        grids_left = max(grid_col-1, 0)  # return index position for grids to the left
        grids_right = min(grid_col+1, len(self.game.map.x_coords)-1)
        grids_above = max(grid_row-1, 0)
        grids_below = min(grid_row+1, len(self.game.map.y_coords)-1)
        for i in range(grids_left, grids_right+1):
            for j in range(grids_above, grids_below+1):
                gridref = self.game.map.x_coords[i] + self.game.map.y_coords[j]
                self.adjacent_grids.append(gridref)

    def add_to_map_layer(self):

        self.gridref = self.get_gridref()
        self.game.map.layers[self.map_layer][self.gridref].add(self)  # add sprite to new grid


class Platform(Static_sprite):
    """Wall sprite; player, mobs can't pass through.  Data read from TiledTile Layers within map tmx file.  Individual platform sprites
    have no image- only used for collision detection, anti-g"""

    map_layer = 'platforms'

    def __init__(self, game, x, y, w, h):
        """Generates a single platform tile."""
        super().__init__(game, x, y, w, h)
        self.rect_sides = rect_to_vectors(self.rect)  # store rect sides as list of position vectors for vector intersect
        self.add_to_map_layer()


class Pick_up(Static_sprite):
    """Data read from Object Layers within map tmx file:  apply_pickup method calls lamda function corresponding to pickup cat"""

    map_layer = 'pickups'

    def __init__(self, game, x, y, w, h, image, pickup_cat):

        super().__init__(game, x, y, w, h)
        self.image = image
        self.pickup_cat = pickup_cat
        self.add_to_map_layer()

    def apply_pickup(self):

        update_inst = PICKUP_CATGRY[self.pickup_cat]  # apply lambda function for pickup_cat
        update_inst(self.game.player)
        self.game.player.score += 50

    def draw(self):

        self.game.screen.blit(self.image, self.game.camera.apply(self))


class Mobile_sprite(Static_sprite):
    """Mobile sprites are animated and/ or have velocity.  Data read from Object Layers within map tmx file.
    Self.pos is placed at rect.center rather than topleft for rotating sprites.  Update called each game loop"""
    damage_alpha = [i for i in range(0, 255, 55)]  # setup sequence of alpha channel (transparency) values to iterate through upon receiving damage
    # damage alpha chain from 0 to 255 in steps of 55

    def __init__(self, game, x, y):

        pygame.sprite.Sprite.__init__(self)
        self.game = game
        # self.image_dict = image_dict
        self.ref_image = game.mobile_sprite_images[self.__class__.refkey][0]  # reference original image for image transformation (flip/ rotate)
        self.image = game.mobile_sprite_images[self.__class__.refkey][0]
        self.rect = self.image.get_rect()
        self.pos = vec(x + self.rect.width / 2, y + self.rect.height / 2)
        self.rect.center = self.pos
        # self.refkey = refkey  # key name for sprite map layer, image dictionary
        self.HRoffset = 0  # hitrect offset from sprite rect centre
        self.radius = 0.75 * ((self.rect.width + self.rect.height) / 4)  # for collision detection (collide_circle) between mobile sprites e.g. player and mobs
        self.rect_rtn = 0  # rotate sprite rect and image
        self.direction = vec(1, 0)

        self.setup_hitrect()
        self.transfer = False

        self.vel = vec(0, 0)  # initialise velocity vector

        # handle animations
        self.refresh_rate = 0.2  # rate animation changes slide (0.5 - changes twice per second)
        self.actionvar = "idle"  # current sprite action
        self.newaction = "idle"  # new sprite action on e.g. keyboard input- jumping, walking etc

        self.timer = 0  # used to trigger next frame for animations (can set to -ve value to delay start of an animation)
        self.current_frame_index = 0  # used to check if at end of animation reel i.e. at next game loop animation will start over

        self.damaged = False  # # For damage effect visual only

    def setup_hitrect(self):
        """ hitrect square centred about self.rect.center. Used for sprite collisions. """

        HRwidth = 1/2 * (self.rect.width + self.rect.height)  # MUST be divisible by 2 (without remainder) for collisions to work properly
        HRwidth = int((HRwidth/2)+1) * 2  # if not divisible by 2 round up 1/2 HRlength length to nearest integer
        HRheight = HRwidth
        self.hitrect = pygame.Rect(self.rect.centerx, self.rect.centery, HRwidth, HRheight)
        self.hitrect.center = self.rect.center + self.direction.normalize() * self.HRoffset

    def flag_transfer_sprite(self):
        """ If sprite has moved to a new grid flag sprite for update in main game update"""
        gridref = self.get_gridref()
        if gridref != self.gridref:
            self.transfer = True
            self.next_grid = gridref
            return True

    def collide_rect(self, sprite1, sprite2):
        """ hitrect collision between 2 sprites"""
        return sprite1.hitrect.colliderect(sprite2.hitrect)

    def collide_sprites(self, map_layer):
        """ Return list of collided sprites for current & adj grids within specified maplayer"""
        totalhits = []  # for colliding with sprites in multiple grids when between grid boundaries
        for ref in self.adjacent_grids:

            grid = self.game.map.layers[map_layer][ref]  # return sprite group from grid_squares dictionary
            hits = pygame.sprite.spritecollide(self, grid, False, self.collide_rect)
            totalhits += hits

        return totalhits

    def collide_platforms(self, axis):  # [0, 1] for either [x, y] axis

        self.hitrect[axis] = self.pos[axis] - 1/2*self.hitrect.size[axis]  # update rect with new position
        totalhits = self.collide_sprites('platforms')

        if totalhits:

            d = sign(totalhits[0].rect.center[axis]-self.hitrect.center[axis])  # direction of travel: left = -1, right = 1, up = -1, down = 1
            # overlap between self.hitrect and platform.rect
            overlap = 0.5*d*(self.hitrect.size[axis] + totalhits[0].rect.size[axis]) - (totalhits[0].rect.center[axis] - self.hitrect.center[axis])
            self.pos[axis] -= overlap  # reset position so no longer colliding
            self.hitrect[axis] = self.pos[axis] - 1/2*self.hitrect.size[axis]
            return True

    def atMapBoundaries(self):
        """SHELVED"""
        """ Check if at map boundaries (collision detection not used for platforms at boundary)"""

        self.pos.x = max(min(self.game.map.RHS - 1/2*self.hitrect.width, self.pos.x), self.game.map.LHS + 1/2*self.hitrect.width)
        self.pos.y = max(min(self.game.map.btm - 1/2*self.hitrect.height, self.pos.y), self.game.map.top + 1/2*self.hitrect.height)

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
        self.rect.center = self.hitrect.center - (self.direction.normalize() * self.HRoffset)

    def damage_effect(self):

        if self.damaged:

            try:
                #  fill sprite image with increasing alpha channel values.  In addition apply special flag to blend the image
                self.image.fill((255, 0, 0, next(self.damage_alpha)), special_flags = pygame.BLEND_RGBA_MULT)

            except:  # exception raised once reach end of the damage_alpha chain
                self.damaged = False

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

    def draw(self):

        self.animate(self.current_animation)
        self.transform_image()
        self.damage_effect()
        offset_x, offset_y = self.game.camera.apply(self)
        self.game.screen.blit(self.image, (int(offset_x), int(offset_y)))


class Missile(Mobile_sprite):

    def __init__(self, game, x, y):

        self.direction = vec(1, 0)
        super().__init__(game, x, y)
        self.current_animation = self.game.mobile_sprite_images[self.__class__.refkey]
        self.HRoffset = 0.5*self.rect.width # offset from rect.center

    def setup_hitrect(self):

        HRheight = self.rect.height * 0.75
        HRwidth = HRheight
        self.hitrect = pygame.Rect(self.rect.centerx, self.rect.centery, HRwidth, HRheight)
        self.HRoffset = 0.5*self.rect.width  # offset from rect.center so hitrect positioned at front of missile
        self.rect.center = self.hitrect.center - self.direction.normalize()*self.HRoffset
        pass

    def activate(self, player):
        """ On player.shoot() borrow missile sprite from pool, set position offset from player, direction and add to weapons map_layer"""
        self.direction = vec(player.direction.x, player.direction.y)
        self.rect_rtn = player.rect_rtn
        self.vel = self.direction.normalize() * Harpoon.runspeed


class Harpoon(Missile):

    map_layer = 'weapons'
    refkey = 'harpoon'
    runspeed = 25

    def __init__(self, game, x, y):
        super().__init__(game, x, y)

    def collide_walls(self):

        if self.collide_sprites('platforms'):
            self.vel = vec(0, 0)
            self.add(self.game.hold_sprites)
            self.remove(self.game.map.layers[self.map_layer][self.gridref])

    def collide_enemy(self):

        hits = self.collide_sprites('enemies')
        if hits:
            hits[0].take_damage(10)

            self.game.objectpools[self.refkey].rtrn_object(self)
            choice(self.game.effects_sounds['mob_hit']).play()

    def collide_mines(self):

        hits = self.collide_sprites('obstacles')  # mine collision kill sprite
        if hits:
            if hits[0].refkey == 'mine':
                self.game.objectpools[self.refkey].rtrn_object(self)

    def update(self):

        self.hitrect.center = self.pos

        self.get_adjacent_grids()

        # collisions
        self.collide_walls()
        self.collide_enemy()
        self.collide_mines()


class Torpedo(Missile):

    map_layer = 'weapons'
    refkey = 'torpedo'
    runspeed = 20

    def __init__(self, game, x, y):

        super().__init__(game, x, y)
        self.affect_rad = 4 * game.map.tilesize  # radius for area of affect.  Countdown timer activated if player within affect_rad
        self.damage_constant = (0.5 * self.affect_rad) ** 3 / 2  # constant for damage to sprites within affect_rad inversely proportional to distance squared
        self.refresh_rate = 0.1  # rate animation changes slide (0.5 - changes twice per second)

        self.vel = self.direction.normalize() * Torpedo.runspeed

    def collide_walls(self):

        if self.collide_sprites('platforms'):
            self.pos.x += sign(self.vel.x) * 70  # move explosion closer to the platform
            self.pos.y += sign(self.vel.y) * 70  # ditto

            self.vel = vec(0, -2)  # explosion rises
            return True

    def collide_enemy(self):

        for ref in self.adjacent_grids:
            grid = self.game.map.layers['enemies'][ref]
            hits = pygame.sprite.spritecollide(self, grid, False, pygame.sprite.collide_rect_ratio(0.7))
        hits = self.collide_sprites('enemies')
        if hits:
            hits[0].vel += self.vel * 3/16  # add partial vel vector to mob on collision
            hits[0].hitpoints = 0  # instant death for head on collision
            self.vel *= 2/4
            return True

    def collide_mine(self):

        hits = self.collide_sprites('obstacles')
        for hit in hits:
            if hit.refkey == 'mine':
                # set mine to explode on current iteration i.e. immediately
                hit.countdown = 0
                hit.active = True
                hit.vel = self.vel * 1 / 16  # transfer momentum to mine
                self.vel *= 1 / 4  # vel reduced as a result
                return True

    def explode(self):

        self.inflict_damage('players', 800)  # inflict damage on sprites within radius
        self.inflict_damage('enemies', 1300)

        self.remove(self.game.map.layers['weapons'][self.gridref])
        self.add(self.game.hold_sprites)

        # update animation reel to explosion animation
        self.change_action(self.game.effects_images, 'explosion')  # change self.actionvar to new action
        choice(self.game.effects_sounds['torpedo_explode']).play()

    def inflict_damage(self, maplayerkey, v_const):

        for ref in self.adjacent_grids:
            for sprite in self.game.map.layers[maplayerkey][ref]:
                # TODO Fix sprite going through walls due to explosion
                # TODO set max vel for sprite as affect of explosion
                displacement = vec(sprite.hitrect.center) - vec(self.hitrect.center)
                damage = self.damage_constant / displacement.length()**2
                sprite.vel = displacement.normalize() * (v_const / displacement.length())  # explosion veloctity in opposite direction to displacement.  Speed proportional to 1/ distance
                sprite.vel += self.direction * -5  # Add velocity constant to increase minimum explosion affect
                sprite.take_damage(damage)

    def smoke_trail(self):

        pass

    def update(self):

        self.hitrect.center = self.pos
        self.get_adjacent_grids()
        if any([self.collide_walls(), self.collide_mine(), self.collide_enemy()]):
            self.explode()


class Mine(Mobile_sprite):

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

        HRheight = self.rect.height * 0.6
        HRwidth = HRheight
        self.hitrect = pygame.Rect(self.rect.centerx, self.rect.centery, HRwidth, HRheight)
        self.hitrect.center = self.rect.center

    def explode(self):

        self.inflict_damage('players', 0)  # inflict damage on sprites within radius
        self.inflict_damage('enemies', 3000)

        # detonate other mines within adjacent grids
        for ref in self.adjacent_grids:
            for sprite in self.game.map.layers['obstacles'][ref]:
                if sprite != self:
                    if sprite.refkey == 'mine':
                        # blow up mines in adjacent grids
                        displacement = vec(sprite.rect.center) - vec(self.rect.center)  # distance between 2 mines
                        sprite.countdown = 1/50 * (displacement.length() // self.game.map.tilesize)  # countdown reset in proportion to distance
                        sprite.active = True

        self.remove(self.game.map.layers['obstacles'][self.gridref])
        self.add(self.game.hold_sprites)

        # update animation reel to explosion animation
        self.change_action(self.game.effects_images, 'explosion4x4')  # change self.actionvar to new action

        choice(self.game.effects_sounds['mine_explode']).play()

    def inflict_damage(self, maplayerkey, v_const):

        for ref in self.adjacent_grids:
            for sprite in self.game.map.layers[maplayerkey][ref]:
                displacement = vec(sprite.rect.center) - vec(self.rect.center)
                damage = self.damage_constant / displacement.length()**2
                sprite.vel = displacement.normalize()*v_const / displacement.length()  # explosion veloctity in opposite direction to displacement.  Speed proportional to 1/ distance
                sprite.take_damage(damage)

    def update(self):

        self.get_adjacent_grids()

        if self.active:
            self.countdown -= self.game.dt
            if self.countdown < 0:
                self.explode()


class Player(Mobile_sprite):

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
        self.add_to_map_layer()
        self.score = 0
        self.hitpoints = Player.hitpoints
        self.stamina = Player.stamina

        # self.d = [key for index, key in enumerate(self.weapons)]  # ordered list of weapon keys
        self.torpedos = 0
        # self.image.fill(RED)
        self.vel = vec(0, 0)
        self.direction = vec(1, 0)
        self.actionvar = "player_idle"  # current sprite action
        self.newaction = "player_idle"  # new sprite action on e.g. keyboard input- jumping, walking etc
        self.current_animation = game.mobile_sprite_images[self.actionvar]  # current animation slide (list of images)
        self.refresh_rate = 0.15  # rate animation changes slide (0.5 - changes twice per second)

        self.last_shot = 0  # get self.timer at instant player shoots to control fire_rate
        self.dead = False
        self.current_weapon = 'harpoon'  # Default weaponclass key
        self.weaponstate = {'harpoon': True,
                            'torpedo': True,
                            'plasmagun': False}

        self.ammo = {'harpoon': 200,
                     'torpedo': 500}

    def apply_clamps(self):

        self.hitpoints = max(0, min(self.hitpoints, Player.hitpoints))
        self.stamina = max(0, min(self.stamina, Player.stamina))

    def get_mouse(self, sensitivity):  #
        """ Set sensitivity range to be betweeen 0.1 - 2 for current setup"""
        pygame.mouse.set_visible(False)
        movement = pygame.mouse.get_rel()  # get the amount of mouse movement (x, y)

        scrollH = 1 / 10 * movement[0] * sensitivity  # set x axis movement sensitivity
        scrollH = max(min(15, scrollH), -15)  # set to be between 10-20
        return scrollH  # return horizontal mouse movement

    def axial_movement(self, keys):

        """Movement in 8 directions controlled with keys only"""

        unit_vel = vec(0, 0)
        verticalKeys = [keys[pygame.K_s], keys[pygame.K_w]]
        horizontalKeys = [keys[pygame.K_d], keys[pygame.K_a]]

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

    def rotational_movement(self, keys):

        unit_vel = vec(0, 0)
        self.newaction = "player_swimming"
        if keys[pygame.K_w]:
            unit_vel = vec(0, 1)
            self.newaction = "player_rush"
        elif keys[pygame.K_s]:
            unit_vel = vec(0, -1 / 2)
            self.newaction = "player_swimming"
        if keys[pygame.K_a]:
            unit_vel = vec(3 / 4, 0)
            self.newaction = "player_swimming"
        elif keys[pygame.K_d]:
            unit_vel = vec(-3 / 4, 0)
            self.newaction = "player_swimming"

        scrollH = self.get_mouse(2)
        self.direction = self.direction.rotate(scrollH)
        angle = self.direction.angle_to(vec(0, 1))

        self.vel = (unit_vel * Player.runspeed).rotate(-angle) if unit_vel else vec(0, 0)
        self.rect_rtn = vec(self.direction.x, self.direction.y).angle_to(vec(1, 0))  # rotate sprite

    def dash(self, keys):

        if keys[pygame.K_SPACE] and self.vel:
            if self.stamina > 0:
                self.vel *= 1.5
                self.stamina -= interval_trigger(self.game.elapsed_time, 0.2, self.game.dt) * 5
                self.newaction = 'player_rush'
        else:
            self.stamina += interval_trigger(self.game.elapsed_time, 0.2, self.game.dt) * 1  # recover stamina

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

        if pygame.mouse.get_pressed()[0] or keys[pygame.K_LCTRL]:
            if self.game.elapsed_time - self.last_shot > Player.rate_of_fire:
                self.last_shot = self.game.elapsed_time * 1

                if self.ammo[self.current_weapon] > 0:
                    #  TODO: vary missile velocity marginally
                    start_pos = self.pos + 10 * self.direction.normalize()  # start position offset from player.rect by 10 pixels
                    missile = self.game.objectpools[self.current_weapon].borrow_object(start_pos.x, start_pos.y)
                    missile.activate(self)

                    self.ammo[self.current_weapon] -= 1
                    choice(self.game.weapon_shoot_sounds[self.current_weapon]).play()
                else:
                    choice(self.game.weapon_shoot_sounds['gun_reload']).play()

    def collide_enemy(self):

            hits = self.collide_sprites('enemies')
            for hit in hits:
                self.hitpoints -= interval_trigger(self.game.elapsed_time, 0.2, self.game.dt) * hit.mob_damage  # hitpoints deducted every 0.2 seconds

    def collide_mine(self):

        for ref in self.adjacent_grids:

            for sprite in self.game.map.layers['obstacles'][ref]:
                if sprite.refkey == 'mine':
                    displacement = vec(sprite.rect.center) - vec(self.rect.center)
                    if displacement.length() < sprite.affect_rad:
                        sprite.active = True  # if player within affect_rad activates mine countdown timer

    def collide_pick_up(self):
        # TODO Object pool for pickups
        hits = self.collide_sprites('pickups')
        if hits:
            hits[0].apply_pickup()
            hits[0].kill()  # delete sprite

    def take_damage(self, points_lost):

        self.hitpoints -= points_lost
        if points_lost > 20:
            self.damaged = True
            self.damage_alpha = chain(self.__class__.damage_alpha * 8)  # cycle through colour gradients twice

    def damage_effect(self):

        if self.damaged:
            try:
                self.image.fill((255, 0, 0, next(self.damage_alpha)), special_flags = pygame.BLEND_RGBA_MULT)
            except:
                self.damaged = False

    def death(self):

        if self.hitpoints == 0:
            self.dead = True

    def update(self):
        # reset parameters
        self.rot_speed = 0

        # Check platform collision and update rect
        self.get_adjacent_grids()  # return list of current and adjacent gridrefs

        # Player controls
        keys = pygame.key.get_pressed()

        if not self.damaged:
            self.axial_movement(keys)
            # self.rotational_movement(keys)
            self.dash(keys)
            self.shoot(keys)

        else:
            self.newaction = "player_hurt"

        self.collide_platforms(0)  # check horizontal collision
        self.collide_platforms(1)  # check vertical collision

        # check sprite collisions
        self.collide_pick_up()
        self.collide_mine()
        self.collide_enemy()

        self.apply_clamps()
        self.death()

        self.change_action(self.game.mobile_sprite_images, self.newaction)  # change self.actionvar to new action
        self.current_animation = self.game.mobile_sprite_images[self.actionvar]
        # check if sprite will move to new grid on next update


class Enemy(Mobile_sprite):

    num_of_mobs = 0
    mob_damage = 2  # deducted from player health (damage inflicted)
    antiGrav = 1.2  # constant of accn which repels mobs away from each other within avoid_rad
    hitpoints = 10

    deathanimation = 'enemydeath'

    def __init__(self, game, x, y):

        super().__init__(game, x, y)
        self.start_pos = vec(x, y)
        self.anti_g = vec(0, 0)  # TESTING only
        self.chase_player_rad = 2 * self.game.map.gridwidth  # chase player if within radius
        self.rect_collisionF = pygame.Rect(0, 0, self.game.map.tilesize, self.game.map.tilesize)  # for testing only
        self.rect_collisionL = pygame.Rect(0, 0, self.game.map.tilesize, self.game.map.tilesize)  # for testing only

        self.displacement = vec(0, 0)

        self.current_animation = self.game.mobile_sprite_images[self.refkey]
        self.refresh_rate = 0.2

        self.target = vec(0, 0)
        self.target.x = max(min(self.game.map.width - 4 * self.game.map.tilesize, self.pos.x + choice([-1, 1]) * 2 * self.game.map.tilesize), 4 * self.game.map.tilesize)
        self.target.y = max(min(self.game.map.height - 4 * self.game.map.tilesize, self.pos.y + choice([-1, 1]) * 2 * self.game.map.tilesize), 4 * self.game.map.tilesize)
        self.target_vec = self.pos - self.target

        Enemy.num_of_mobs += 1

    def avoid_walls(self):

        """ Avoid wall collisions with platforms in current and adjacent grids"""

        for ref in self.adjacent_grids:
            for ptf in self.game.map.layers['platforms'][ref]:
                displacement = vec(ptf.rect.centerx, ptf.rect.centery) - self.pos  # between mob and centre point of platform tile
                anti_g = -displacement * (self.__class__.mass / displacement.length()**2)  # accelleration away from wall- proportional to current speed, inversly proportional to displacemnt squared
                self.vel += anti_g
                self.anti_g = anti_g  # TESTING only (drawing)

    def avoid_mobs(self):

        """ Avoid bunching together when chasing player by avoiding other mobs in current grid"""
        for ref in self.adjacent_grids:
            for mob in self.game.map.layers['enemies'][ref]:  # loop through mobs in current grid
                if mob != self:  # exclude self
                    displacement = mob.pos - self.pos
                    anti_g = -displacement * (Enemy.antiGrav*4 / displacement.length())**2
                    self.vel += anti_g

    def collide_walls(self):

        if self.collide_platforms(0):  # check horizontal collision
            self.vel.x *= -1 / 2  # bounce off walls
        if self.collide_platforms(1):  # check vertical collision
            self.vel.y *= -1 / 2  # bounce off walls

    def get_target_vector(self):
        """Find new target vector from mob centre to target centre + error."""

        adjust_target = self.target_error()
        new_target_vec = adjust_target - vec(self.rect.centerx, self.rect.centery)
        self.target_vec = new_target_vec or self.target_vec  # if new_target_vec is zero return previous target_vec

    def target_error(self):
        """ Intermittently switch target position by a percentage of the target vector for less predictable mob movement.
        Amount target pos varies decreases as mob approaches target"""
        swc = switch_interval(self.timer, self.__class__.switch_freq)  # switch target every second (returns either 0 or -1)
        d = swc or 1  # either 1 or -1
        pdlr_target_vec = vec(d*self.target_vec.y, -d*self.target_vec.x)  # clockwise / anticlockwise perpendicular target vec

        # vary target position by +/- error margin equivalent to % of perpendicular target vector
        error_margin = randrange(0, self.__class__.error_margin + self.__class__.error_var, 10)  # vary error margin between +/- error_var
        x_error = pdlr_target_vec.x * error_margin / 100
        y_error = pdlr_target_vec.y * error_margin / 100

        adjust_target = vec(self.target.x + x_error, self.target.y + y_error)  # target_position adjusted for % error

        return adjust_target

    def idle_swim(self, territory_rad):
        """ Swim towards random points (targets) on screen when not chasing player, other mobs etc"""
        switch_target = False
        if self.vel.length_squared() < 1:
            switch_target = True

        if interval_trigger(self.timer, 4, self.game.dt):  # trigger target switch every 4 seconds
            switch_target = True

        if switch_target:

            targetx = randrange(int(self.start_pos.x - territory_rad), int(self.start_pos.x + territory_rad))
            targety = randrange(int(self.start_pos.y - 0.25 * territory_rad), int(self.start_pos.y + 0.25 * territory_rad))

            # Limit target to within map extents
            targetx = max(min(self.game.map.width - self.game.map.gridwidth, targetx), self.game.map.gridwidth)
            targety = max(min(self.game.map.height - self.game.map.gridheight, targety), self.game.map.gridheight)

            target = vec(targetx, targety)
            if not self.check_intersect(target):
                self.target = target

    def chase_player(self):
        """ Switch target to player centre if platform not between mob and player"""
        if (self.game.player.pos - self.pos).length_squared() < self.chase_player_rad ** 2:
            target = vec(self.game.player.rect.centerx, self.game.player.rect.centery)
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
            choice(self.game.effects_sounds['mob_death']).play()
            self.rect_rtn = 0  # set back to horizontal
            self.remove(self.game.map.layers['enemies'][self.gridref])
            self.add(self.game.hold_sprites)

            # update animation reel to death animation
            self.change_action(self.game.effects_images, self.__class__.deathanimation)  # change self.actionvar to new action

    def update(self):

        self.get_adjacent_grids()
        self.idle_swim(self.__class__.territory_rad)
        self.chase_player()
        self.get_target_vector()  # find new target vector
        self.chase_target()
        self.avoid_walls()
        self.avoid_mobs()
        self.collide_walls()

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

        self.hitpoints = Daddyfish.hitpoints
        self.vel = vec(1, 0)
        self.interval = randrange(2000, 3000) / 1000  # time between implementing change in trajectory (seconds) for idle swim

    def chase_target(self):
        """Get acceleration vector directed to target.  Drag coefficient minimises velocity to Daddyfish.maxspeed"""

        self.rect_rtn = vec(self.vel.x, self.vel.y).angle_to(vec(1, 0))  # angle sprite so facing target

        accn = 0.3  # acceleration magnitude
        drag_coeff = accn / Daddyfish.maxspeed  # friction/ drag coefficient

        accn_vec = vec(self.target_vec.normalize() * accn)
        self.vel.x = self.vel.x + accn_vec.x - (drag_coeff * self.vel.x)
        self.vel.y = self.vel.y + accn_vec.y - (drag_coeff * self.vel.y)


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

    # turning parameters- trajectory follows log spiral path
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

    map_layer = 'enemies'
    refkey = 'spinefish'
    hitpoints = 20
    vel = vec(4, 0)  # initial velocity
    max_speed = 12

    def __init__(self, game, x, y):

        super().__init__(game, x, y)

        self.vel = Spinefish.vel
        self.hitpoints = 20
