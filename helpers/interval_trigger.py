def interval_trigger(timer, interval, dt):
    """ Return True (+1) every nth interval e.g. n = 3 returns 0, 0, 1, 0, 0, 1, 0, 0, 1 ....
    (where n increases by increment d every loop)"""
    trigger = ((timer % interval) + dt) // interval  # returns 1 at the end of every interval, else returns 0

    return trigger


def switch_interval(n, interval):
    """ Alternate between True & False (1 and 0) every nth interval e.g. n = 3 returns 0, 0, 0, 1, 1, 1, 0, 0, 0, 1 ,1 ,1 ....  """

    output = (n // interval) % 2

    return -output

# def trigger(time_elapsed, interval, dt):
#
#     if (time_elapsed+dt) % interval < time_elapsed % interval:
#         print(time_elapsed, 'Boo!')
#         yield True
#
#     # For every randrange seconds switch from 1 to -1 for randrange duration
