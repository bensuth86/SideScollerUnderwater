from pygame.math import Vector2 as vec
from math import sin, cos, acos, sqrt

#  Vector function for turning


def turn_direction(vel, target):
    """ From current velocity and target vectors, choose turning direction- anticlockwise: return -1, clockwise: return 1
        Direction used in vec_trans function to determine rotation matrix and therefore velocity direction"""
    x_product = vel.cross(target)  # cross product of velocity and target vector
    direction = x_product / abs(x_product)

    return direction


def vec_trans(vector_in, const, angle, direction):
    """ Rotate input vector by angle (rot matrix) and resize by constant variable"""
    vector_out = vec(0, 0)  # starting radius from origin
    vector_out.x = (vector_in.x * cos(angle) - (direction * vector_in.y * sin(angle)))
    vector_out.y = (direction * vector_in.x * sin(angle) + (vector_in.y * cos(angle)))
    vector_out = vector_out.normalize()  # unit vector
    return vector_out * const


def get_angle(vec1, vec2):
    """theta is a constant angle which is subtended every game loop. Determines the geometric progression of the spiral trajectory"""
    theta = acos(vec1.dot(vec2) / (vec1.length() * vec2.length()))  # angle subtended for every increment (constant angle)
    return theta


def get_radius_vector(vel, theta, geo_pro, direction):
    """Radius from spiral origin to position on previous iteration"""
    rad0_mag = sqrt((vel.length()**2)/((1+geo_pro**2) - (2*geo_pro*cos(theta))))
    beta = acos((vel.length() ** 2 + rad0_mag ** 2 - (geo_pro * rad0_mag) ** 2) / (2 * vel.length() * rad0_mag))  # angle between initial velocity and turning radius
    ceta = acos((vel.length() ** 2 + (geo_pro * rad0_mag) ** 2 - rad0_mag ** 2) / (2 * vel.length() * geo_pro * rad0_mag))  # for verify only
    test = theta + beta + ceta  # should equal pi (180 deg)
    rad_0 = vec_trans(vel, rad0_mag, beta, direction)  # radius vector from origin for previous iteration
    rad0_mag = rad_0.length()
    return rad_0
