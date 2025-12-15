from pygame.math import Vector2 as vec
from math import sin, cos, acos, atan2, sqrt, pi

from .maths_util import sign


def normalise(v):
    """Prevent division by zero if vector length is 0"""
    if v.length() == 0:
        return vec(0, 0)
    return v.normalize()


def rect_to_vectors(rect):
    """ return pygame rect as line vectors for top, right, bottom, left"""
    top_left, top_right = vec(rect.topleft), vec(rect.topright)
    bottom_left, bottom_right = vec(rect.bottomleft), vec(rect.bottomright)

    rect_sides = [
        (top_left, top_right),     # top
        (bottom_left, bottom_right),  # bottom
        (top_left, bottom_left),  # left
        (top_right, bottom_right)    # right
    ]

    return rect_sides


def get_orientation(A, B, C):
    """ return orientaion of three ordered point vectors"""
    # term1 = B * A.dot(C)
    # term2 = C * A.dot(B)
    orientation = (B[0] - A[0]) * (C[1] - A[1]) - (B[1] - A[1]) * (C[0] - A[0])
    return orientation


def vec_intersect(p1, p2, p3, p4):
    """ Return True if 2 vectors intersect with start/ end points (p1, p2) and (p3, p4"""

    ori1 = get_orientation(p1, p2, p3)
    ori2 = get_orientation(p1, p2, p4)
    ori3 = get_orientation(p3, p4, p1)
    ori4 = get_orientation(p3, p4, p2)

    if ori1*ori2 < 0 and ori3*ori4 < 0:
        return True


def turn_direction(vector1, vector2):
    """ From current velocity and target vectors, choose turning direction- anticlockwise: return -1, clockwise: return 1
        Direction used in vec_trans function to determine rotation matrix and therefore velocity direction"""
    det = sign(vector1.cross(vector2))  # sign of vector1 and vector2 cross product
    rot_direction = det

    return rot_direction


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
    """Radius from spiral origin to pition on previous iteration"""
    rad0_mag = sqrt((vel.length()**2)/((1+geo_pro**2) - (2*geo_pro*cos(theta))))  # cosine rule to get rad length
    beta = acos((vel.length() ** 2 + rad0_mag ** 2 - (geo_pro * rad0_mag) ** 2) / (2 * vel.length() * rad0_mag))  # angle between initial velocity and turning radius
    ceta = acos((vel.length() ** 2 + (geo_pro * rad0_mag) ** 2 - rad0_mag ** 2) / (2 * vel.length() * geo_pro * rad0_mag))  # for verification only
    test = theta + beta + ceta  # should equal pi (180 deg) - for verification only

    rad_0 = vec_trans(vel, rad0_mag, beta, direction)  # radius vector from origin for previous iteration
    return rad_0


def get_nearest_cardinal(vector_in):
    """Round a pygame.math.Vector2 to the nearest compass direction (N, E, S, W)"""

    if vector_in.length() == 0:
        raise ValueError("Zero vector has no direction.")

    unit_vec = vector_in.normalize()  # make it a unit vector

    compass_vectors = [
        vec(1, 0),   # East
        vec(0, -1),  # North
        vec(-1, 0),  # West
        vec(0, 1),   # South
    ]

    # Pick the compass vector with the max dot product
    nearest = max(compass_vectors, key=lambda d: unit_vec.dot(d))

    return nearest
