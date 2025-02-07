def interval_trigger(timer, interval, dt):

    trigger = ((timer % interval) + dt) // interval  # returns 1 at the end of every interval, else returns 0

    return trigger


# def trigger(time_elapsed, interval, dt):
#
#     if (time_elapsed+dt) % interval < time_elapsed % interval:
#         print(time_elapsed, 'Boo!')
#         yield True
#
#     # For every randrange seconds switch from 1 to -1 for randrange duration
