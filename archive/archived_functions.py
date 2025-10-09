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