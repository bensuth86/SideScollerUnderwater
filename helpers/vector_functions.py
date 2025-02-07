from pygame.math import Vector2 as vec
from math import sin, cos, acos, atan2, sqrt, pi

#  Vector function for turning


def sign(x):
    """ Return the sign of a value; -1 ofx<0, 0 if x==0, 1 if x>0"""
    sign = -1 if x < 0 else (1 if x > 0 else 0)
    return sign


def turn_direction(pos, vel, target):
    """ From current velocity and target vectors, choose turning direction- anticlockwise: return -1, clockwise: return 1
        Direction used in vec_trans function to determine rotation matrix and therefore velocity direction"""
    det = sign(vel.cross(target))  # sign of velocity and target vector cross product
    dot = sign(vel.dot(target))  # sign of velocity and target vector dot product
    y_direction = sign(pos.y - target.y)
    direction = sign((1+dot)*det + (1 - dot)*y_direction)  # takes longer turn direction along y axis i.e. if clockwise is shorter path to player will turn anticlockwise
    direction = det

    return direction


def vec_trans(vector_in, const, angle, direction):
    """ Rotate input vector by angle (rot matrix) clockwise or anticlockwise per direction, then resize by variable const"""
    vector_out = vec(0, 0)  # starting radius from origin
    vector_out.x = (vector_in.x * cos(angle) - (direction * vector_in.y * sin(angle)))
    vector_out.y = (direction * vector_in.x * sin(angle) + (vector_in.y * cos(angle)))
    vector_out = vector_out.normalize()  # unit vector
    return vector_out * const


def get_angle(vec1, vec2):
    """Dot product between vec1 and vec2 to return angle between them"""

    angle = acos(vec1.dot(vec2) / (vec1.length() * vec2.length()))  # rounding prevents value greater than 1 and subsequant math domain error

    return angle


def get_angleii(vec1, vec2, d):
    """ https://stackoverflow.com/questions/14066933/direct-way-of-computing-the-clockwise-angle-between-two-vectors """
    dot = vec1.x*vec2.x + vec1.y*vec2.y  # dot product
    det = d*(vec1.x*vec2.y) - d*(vec1.y*vec2.x)  # cross product

    angle = atan2(-det, -dot) + pi  # returnclockwise angle between 0, 360 deg
    # angle = atan2(det, dot)  # returnclockwise angle between -180, 180 deg

    return angle


def get_radius_vector(vel, theta, geo_pro, direction):
    """Radius from spiral origin to position on previous iteration"""
    rad0_mag = sqrt((vel.length()**2)/((1+geo_pro**2) - (2*geo_pro*cos(theta))))  # cosine rule to get rad length
    beta = acos((vel.length() ** 2 + rad0_mag ** 2 - (geo_pro * rad0_mag) ** 2) / (2 * vel.length() * rad0_mag))  # angle between initial velocity and turning radius
    ceta = acos((vel.length() ** 2 + (geo_pro * rad0_mag) ** 2 - rad0_mag ** 2) / (2 * vel.length() * geo_pro * rad0_mag))  # for verification only
    test = theta + beta + ceta  # should equal pi (180 deg) - for verification only
    rad_0 = vec_trans(vel, rad0_mag, beta, direction)  # radius vector from origin for previous iteration
    return rad_0
