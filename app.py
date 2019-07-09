import matplotlib.pyplot as plot
from matplotlib.widgets import TextBox
import numpy as np
import psm.filter
import json


kwargs = {
    'line_x': 80,
    'line_y': 80,
    'line_angle': -5,
    'artifact_size': 2,
    'radius': 12,
    'filter_noise': 0,
    'bg_noise': 0,
    'angle_samples': 1,
    'image_angle': 0
}

def submit(text):
    try:
        kwargs = json.loads(text)
        kwargs['line_angle'] = np.deg2rad(kwargs['line_angle'])
        kwargs['image_angle'] = np.deg2rad(kwargs['image_angle'])
        image = psm.filter.disk(160, 160, **kwargs)
        image_widget.set_data(image)
    except:
        pass
    plot.draw()

image_widget = plot.imshow(np.zeros((160, 160), np.uint8), cmap='gray', vmin=0, vmax=255)
image_widget.set_extent([0.02, 0.9, 0.15, 0.98])

axbox = plot.axes([0.15, 0.01, 0.8, 0.075])
text_box = TextBox(axbox, 'Evaluate', initial=json.dumps(kwargs))
text_box.on_submit(submit)

plot.show()
