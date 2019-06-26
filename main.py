import matplotlib.pyplot as plot
import matplotlib.image as image
import numpy as np
from PIL import Image
import psm.filter
import psm.generate


# def resize_image(image, factor):
#     new_shape = tuple(i * 3 for i in image.shape)
#     return np.array(Image.fromarray(line_image).resize(new_shape))

# line_image = psm.generate.line(60, 60, 30, 30.1, np.deg2rad(-45), 5)
# plot.imshow(line_image, cmap='gray', vmin=0, vmax=255)
# plot.show()

image_0 = psm.filter.disk(60, 60, 30, 30.5, np.deg2rad(-45), 5, 1, 0, 1)
image_1 = psm.filter.disk(60, 60, 30, 30.5, np.deg2rad(-45), 5, 5, 30, 2)

plot.subplot(1, 2, 1)
plot.imshow(image_0, cmap='gray', vmin=0, vmax=255)
plot.subplot(1, 2, 2)
plot.imshow(image_1, cmap='gray', vmin=0, vmax=255)
plot.show()
