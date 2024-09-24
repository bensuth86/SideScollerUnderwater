

def trigger(time_elapsed, interval, dt):

    if (time_elapsed+dt) % interval < time_elapsed % interval:
        print(time_elapsed, 'Boo!')
        yield True

