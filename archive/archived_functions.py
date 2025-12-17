def get_gridsi(self, rect):
    """ Return grid or multiple grids if between boundaries to check for collisions"""

    def lookupgrid(pos):
        x, y = int(pos[0]), int(pos[1])
        x = min((self.game.map.width - 2 * TILESIZE), x)  # limit possible x pos to within map width (2340)
        y = min((self.game.map.height - 2 * TILESIZE), y)  # 900
        grid_col = (x - TILESIZE) // GRIDWIDTH
        grid_row = (y - TILESIZE) // GRIDHEIGHT
        return self.game.grid_squares[grid_row][grid_col]

    grids = map(lookupgrid, (rect.topleft,
                             rect.topright,
                             rect.bottomleft,
                             rect.bottomright))
    grids = list(set(grids))  # return grids minus duplicates

    return grids

def lookup_grids(self):
    """Returns list of grid references sprite rect overlaps (assignment to main grid_squares dictionary handled seperately"""
    # return index position of grids overlapping rect
    grid_cols = list(range((self.rect.topleft[0])//GRIDWIDTH, (((self.rect.topright[0])//GRIDWIDTH) + 1)))
    grid_rows = list(range((self.rect.topleft[1])//GRIDHEIGHT, ((self.rect.bottomleft[1])//GRIDHEIGHT) + 1))
    grids = []

    # find corresponding grid reference and append to list
    for i in grid_cols:
        i = max(min(len(self.game.x_coords)-1, i), 0)  # limit to total columns in map.width
        col = self.game.x_coords[i]  # 'A'
        for j in grid_rows:
            j = max(min(len(self.game.y_coords) - 1, j), 0)  # limit to total rows in map.height
            row = self.game.y_coords[j]  # '1'
            grid_ref = col + row    # 'A1'
            grids.append(grid_ref)

    # print([[grid_ref] for grid_ref in grids])
    return grids


def increment_angle(self, target_angle):
    """Not using this function"""
    if not target_angle - 5 < self.current_angle < target_angle + 5:  # if current angle not within +/- 5 degrees of target_angle
        self.current_angle += 1 * (target_angle - self.current_angle) / fabs(target_angle - self.current_angle)  # increment/ decrement angle
        if self.current_angle * target_angle <= 0:  # reset current angle if rotated through 360 degrees to prevent mob rotating 360 to face player
            self.current_angle = target_angle

        self.rot_image(self.current_angle)

# Daddyfish #

def chase_target(self):
    # self.angle = vec(self.target_vec.x, self.target_vec.y).angle_to(vec(1, 0))  # angle sprite so facing target
    self.angle = vec(self.vel.x, self.vel.y).angle_to(vec(1, 0))  # angle sprite in direction of velocity

    target_direction = vec(0, 0)  # e.g. (1, 0) travelling to right of screen (no y component)
    target_direction.x = sign(self.target_vec.x)  # return -1, 1  for left, right respect. ...
    target_direction.y = sign(self.target_vec.y)  # return -1, 1  for up, down respect. ...

    target_vel = self.target_vec.normalize() * Daddyfish.maxspeed  # velocity vector towards player position with magnitude equal to runspeed
    print(target_vel)
    # accelerate towards player

    self.vel.x = sqrt(self.maxspeed * fabs(target_vel.x))
    self.vel.x *= target_direction.x
    self.vel.y = sqrt(self.maxspeed * fabs(target_vel.y))
    self.vel.y *= target_direction.y


# Dartfish #

def switch_direction(self):
    """ Change direction intermittently to follow a less predictable path"""
    # self.interval = randrange(3, 6)  # time between implementing change in trajectory (seconds)
    trigger = ((self.timer % self.interval) + self.game.dt) // self.interval  # returns 1 at the end of every interval, else returns 0

    self.interval += trigger * (randrange(-100, 100)) / 1000
    switch = (self.timer // self.interval) % 2  # return either 0 or 1
    direction = 1 + (switch * -2)  # returns either 1 or -1

    self.geo_pro = Dartfish.geo_pro ** direction
    if switch == 1:
        print(direction)

    return direction


def flip_images(frame, flip):  # (list of images, (bool x, bool y))

    def apply(image):
        image = transform.flip(image, flip[0], flip[1])
        return image

    newframe = map(apply, frame)
    newframe = list(newframe)
    return list(newframe)


def rotate_images(frame, rotation):  # angle

    def apply(image):
        image = transform.rotate(image, rotation)
        return image

    newframe = map(apply, frame)
    newframe = list(newframe)
    return list(newframe)


def readSpriteData(filename):

    sprites = {}

    with open(filename, 'r') as f:
        headings = f.readline().strip('\n').split('|')  # read first line of file
        for line in f:
            listDetails = line.strip('\n').split('|')
            sprites[listDetails[0]] = {headings[1]: int(listDetails[1])}
            sprites[listDetails[0]].update({headings[2]: int(listDetails[2])})

    return sprites


def continuous_collision_detection(self, map_layer):
    """ Prevent fast sprites skipping through e.g. walls- by checking if sprites path intersetcs a wall, not just its end position"""
    test_rect = self.rect.move(self.vel.x, self.vel.y)
    for grid_ref in self.adjacent_grids:
        grid = self.game.map.layers[map_layer][grid_ref]
        for sprite in grid:
            if self.rect.clipline(test_rect.center, self.rect.center):
                return True


def _get_random_target(self):
    """Pick random target within map bounds."""
    gx, gy = self.game.map.gridwidth, self.game.map.gridheight
    tx = clamp(self.pos.x + choice([-1, 1]) * 2 * gx, 4 * gx, self.game.map.width - 4 * gx)
    ty = clamp(self.pos.y + choice([-1, 1]) * 2 * gy, 4 * gy, self.game.map.height - 4 * gy)
    return vec(tx, ty)


def avoid_walls(self):
    """ SHELVED; Apply repulsion force away from nearby walls"""

    for ref in self.adjacent_grids:
        for ptf in self.game.map.layers['platforms'][ref]:
            displacement = vec(ptf.rect.centerx, ptf.rect.centery) - self.pos  # between mob and centre point of platform tile
            anti_g = -displacement * (self.__class__.mass / displacement.length()**2)  # accelleration away from wall- proportional to current speed, inversly proportional to displacemnt squared
            self.vel += anti_g
            self.anti_g = anti_g  # TESTING only (drawing)


def target_error(self):
    """ Intermittently switch target position by a percentage of the target vector for less predictable mob movement.
    Amount target pos varies decreases as mob approaches target"""
    swc = switch_interval(self.timer, self.__class__.switch_freq)
    direction = swc or 1
    perp_vec = vec(direction * self.target_vec.y, -direction * self.target_vec.x)

    err = randrange(0, self.__class__.error_margin + self.__class__.error_var, 10)
    error_vec = perp_vec * (err / 100)
    error_vec = vec(0, 0)  # comment out to apply target_error
    return self.target + error_vec


def change_trajectoryi(self):
    """ Will switch geometric progression from inward to outward spiral path, so mob will intersect target at current target.pos
        Uses control variable c: if c=1 will continue inward spiral by default, if c=-1 will switch to outward spiral path """
    alt_rad = get_radius_vector(self.vel, self.theta, 1/self.geo_pro, self.rot_direction)  # radius vector from origin for outward spiral if currently following inward spiral path, and vice versa
    target_rad = alt_rad - self.target_vec    # radius vector between target and origin of alternate spiral trajectory
    delta = get_angleii(alt_rad, target_rad, self.rot_direction)
    dif = (alt_rad.length()*((1/self.geo_pro)**(delta/self.theta))) - target_rad.length()  # if difference = 0 for current mob position then mob will intersect player by changing trajectory from inward to outward spiral (vice versa)
    self.dif = dif  # TESTING
    c = sign(dif)  # returns either +- 1  # control variable determines whether to follow inward or outward spiral path

    # TODO minimum speed - switch to outward path
    c = 1 if self.vel.length() > (Dartfish.max_speed + (0.2*c*Dartfish.max_speed)) else c  # if vel exceeds max limit force inward path

    self.geo_pro = Dartfish.geo_pro ** c
