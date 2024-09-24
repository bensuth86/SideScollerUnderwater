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