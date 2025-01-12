def direction_vector(self):
    direction = vec(0, 0)
    if self.vel.x != 0:
        direction.x = self.vel.x / fabs(self.vel.x)
    if self.vel.y != 0:
        direction.y = self.vel.y / fabs(self.vel.y)

def increment_angle(self, target_angle):
    """Not using this function"""
    if not target_angle - 5 < self.current_angle < target_angle + 5:  # if current angle not within +/- 5 degrees of target_angle
        self.current_angle += 1 * (target_angle - self.current_angle) / fabs(target_angle - self.current_angle)  # increment/ decrement angle
        if self.current_angle * target_angle <= 0:  # reset current angle if rotated through 360 degrees to prevent mob rotating 360 to face player
            self.current_angle = target_angle

        self.rot_image(self.current_angle)

def chase_player_old(self):

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