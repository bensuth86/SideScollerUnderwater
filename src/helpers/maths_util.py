def clamp(val, min_val, max_val):
    return max(min_val, min(val, max_val))


def sign(x):
    """ Return the sign of a value; -1 ofx<0, 0 if x==0, 1 if x>0"""
    sign = -1 if x < 0 else (1 if x > 0 else 0)
    return sign
