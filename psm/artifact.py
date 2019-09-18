import itertools
import numpy as np
import matplotlib.pyplot as plt


def distance(angle):
    y = np.tan(angle)
    stair = 1.0 / y
    stair_size = np.round(stair)
    gap = stair - stair_size
    secondary_stair_distance = stair_size * np.floor(1 / np.abs(gap)) + np.sign(gap)
    secondary_stair_size = stair_size + np.sign(gap)

    return (stair_size, secondary_stair_size), (stair_size, secondary_stair_distance)


def distance2(angle):
    stair = 1.0 / np.tan(angle)
    return stair, 1.0 / (np.tan(angle) * np.abs(stair - np.round(stair)))


if __name__ == "__main__":
    max_y = 300
    step_size = 0.0001
    start = np.rad2deg(np.arctan2(1, max_y))
    angles = np.deg2rad(np.arange(start, 45 + step_size, step_size))

    stair_distance, secondary_stair_distance = distance2(angles)
    mask = secondary_stair_distance > max_y
    secondary_stair_distance[mask] = stair_distance[mask]

    fig = plt.figure("Stairs")
    ax = plt.axes()
    ax.plot(angles, stair_distance)
    ax.plot(angles, secondary_stair_distance)
    plt.show()
