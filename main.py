import matplotlib.pyplot as plot
import matplotlib.image as image
import numpy as np
from PIL import Image
import psm.filter

def poisson(expected, observed):
    return np.e**(-expected - 1) * (np.e*expected/observed)**observed

def random_poisson(expected, start, stop):
    n = 10
    p = np.random.rand()

    cdf = np.empty((n,))
    cdf[0] = poisson(expected, start)

    gen = enumerate(np.linspace(start, stop, n))
    next(gen)
    for i, k in gen:
        cdf[i] = cdf[i-1] + poisson(expected, k) - cdf[0]

    cdf[0] /= cdf[-1]
    gen = enumerate(cdf)
    next(gen)
    for i, q in gen:
        cdf[i] /= cdf[-1]
        if cdf[i] >= p:
            t = (cdf[i-1] - p) / (cdf[i-1] - cdf[i])
            rnd = ((i - 1) * (1 - t) + i * t) / n
            return rnd

random_poisson(32, 22, 42)

artifact_size = 2
line_angles = [
    np.deg2rad(-5),
    np.deg2rad(-10),
    np.deg2rad(-20),
    np.deg2rad(-45)
]
angle_samples = [1, 2]
filter_size = [24]
noise_intensity = [10]

# image1 = psm.filter.disk_image(160, 160, 80, 80, np.deg2rad(10), artifact_size,
#                                0, 0, np.deg2rad(0))
# image2 = psm.filter.disk_image(160, 160, 80, 80, np.deg2rad(55), artifact_size,
#                                0, 0, np.deg2rad(45))
# image = ((image1.astype(np.uint16) + image2.astype(np.uint16)) / 2).astype(
#     np.uint8)
# plot.imshow(image, cmap='gray', vmin=0, vmax=255)
# plot.show()

images = [[
    psm.filter.disk(1000, 1000, 500, 500, np.deg2rad(5), artifact_size,
                    filter_radius, noise)
    for noise, filter_radius in zip(noise_intensity, filter_size)
]]

rows = len(images)
cols = max(len(i) for i in images)

for r, image_row in enumerate(images):
    for i, image in enumerate(image_row):
        plot.subplot(rows, cols, (cols * r) + i + 1)
        plot.imshow(image, cmap='gray', vmin=0, vmax=255)
plot.show()
