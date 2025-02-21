def logistic_growth_rate(x0, target_x, shift_factor, growth_rate):

    r = growth_rate
    x0 += shift_factor  # translate x0 to be greater than 0
    target_x += shift_factor  # translate target_x by equal amount
    dx_dt = r*x0*(1-(x0 / target_x))  # log growth iterative eqn
    x1 = x0 + dx_dt
    x1 -= shift_factor  # remove shiftfactor

    return x1
