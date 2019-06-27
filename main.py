import matplotlib.pyplot as plot
import matplotlib.image as image
import numpy as np
from PIL import Image
import psm.filter
import psm.generate


artifact_size = 5
line_angles = [np.deg2rad(-5), np.deg2rad(-10), np.deg2rad(-20), np.deg2rad(-45)]
angle_samples = [1, 2]
filter_size = [1, 10, 15]
noise_intensity = [0, 5, 5]

images = [[psm.filter.disk(160, 160, 80, 80.5, np.deg2rad(-5), 5, filter_radius, noise, 10, 1)
           for noise, filter_radius in zip(noise_intensity, filter_size)]]

rows = len(images)
cols = max(len(i) for i in images)

for r, image_row in enumerate(images):
    for i, image in enumerate(image_row):
        plot.subplot(rows, cols, (cols * r) + i + 1)
        plot.imshow(image, cmap='gray', vmin=0, vmax=255)
plot.show()
