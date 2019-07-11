import os
import numpy as np
from PIL import Image
import psm.filter

line_angles = [1, 3, 10, 15, 30, 45]
random_rotations = 360 * np.random.rand(len(line_angles))
filter_radii = [0]#[2, 4, 6, 8, 12, 16, 20, 24]
artifact_size = 2

width = 100
height = width
line_x = width / 2 + artifact_size / 2
line_y = height / 2 + artifact_size / 2

output_folder = os.path.join('stimuli', 'angle-vs-radius')
os.makedirs(output_folder, exist_ok=True)

for random_rotation, line_angle in zip(random_rotations, line_angles):
    for filter_radius in filter_radii:
        image = psm.filter.disk(width, height, line_x, line_y,
                                np.deg2rad(line_angle), artifact_size,
                                filter_radius)
        im = Image.fromarray(image)
        im.save(
            os.path.join(output_folder, f'{line_angle}-{filter_radius}.png'))
