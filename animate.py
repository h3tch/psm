import matplotlib.pyplot as plot
import matplotlib.image as image
import matplotlib.animation as animation
import numpy as np
import psm.filter
import psm.generate


images_a = [psm.filter.disk(160, 160, 80, y, np.deg2rad(-92), 4, 16, 10, 0, 2)
            for y in np.arange(60, 100, 6)]
# images_b = [psm.filter.disk(160, 160, 84, 84, np.deg2rad(-angle), 4, 16, 10, 0, 2)
#             for angle in np.arange(87, 98, 7)]

# images = [((a.astype(np.uint16) + b.astype(np.uint16)) / 2).astype(np.uint8)
#           for a, b in zip(images_a, images_b)]

# images2 = [((images[i+1].astype(np.uint16) + image.astype(np.uint16)) / 2).astype(np.uint8)
#            for i, image in enumerate(images[:-1])]

fig = plot.figure()

frames = [[plot.imshow(image, cmap='gray', vmin=0, vmax=255)] for image in images_a]

ani = animation.ArtistAnimation(fig, frames + frames[::-1], interval=16)
plot.show()
