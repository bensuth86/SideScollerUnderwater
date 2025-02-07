def interval_trigger(timer, interval, dt):

    trigger = ((timer % interval) + dt) // interval  # returns 1 at the end of every interval, else returns 0

    return trigger


def exceed_limit(n, threshold):
    """ Determin if above set threshold; Return 0 if n below threshold, 1 if above. Switch comparison operators for opposite result """

    output = 0 or +(n > threshold)
    return output
# def trigger(time_elapsed, interval, dt):
#
#     if (time_elapsed+dt) % interval < time_elapsed % interval:
#         print(time_elapsed, 'Boo!')
#         yield True
#
#     # For every randrange seconds switch from 1 to -1 for randrange duration
