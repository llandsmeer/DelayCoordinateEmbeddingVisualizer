import numpy as np

def lorenz_step(x, y, z, s=10, r=28, b=2.667):
    x_dot = s * (y - x)
    y_dot = r * x - y - x * z
    z_dot = x * y - b * z
    return x_dot, y_dot, z_dot

def lorenz(dt=0.01, num_steps=10000):
    xs = np.empty((num_steps + 1,))
    ys = np.empty((num_steps + 1,))
    zs = np.empty((num_steps + 1,))
    xs[0], ys[0], zs[0] = (0., 1., 1.05)
    for i in range(num_steps):
        x_dot, y_dot, z_dot = lorenz_step(xs[i], ys[i], zs[i])
        xs[i + 1] = xs[i] + (x_dot * dt)
        ys[i + 1] = ys[i] + (y_dot * dt)
        zs[i + 1] = zs[i] + (z_dot * dt)
    return 4 * (xs - xs.min()) / (xs.max() - xs.min()) - 2