import numpy as np
import psychopy.data
import psm.filter
import random
import matplotlib.pyplot as plot
from matplotlib.widgets import Button

increase_radius_response = 0
decrease_radius_response = 1
artifact_size = 8
image_size = 1000
max_filter_radius = 100.0

base_condition = {
    'pThreshold': 0.63,
    'beta': 3.0,
    'delta': 0.01,
    'grain': 0.1,
    'artifact_size': artifact_size,
    'image_width': image_size,
    'image_height': image_size,
    'line_x': image_size / 2,
    'line_y': image_size / 2,
    'max_filter_radius': max_filter_radius,
    'filter_noise': 0
}

conditions = [
    {
        'label': 'angle1',
        'startVal': 0.8,
        'startValSd': 0.2,
        'line_angle': np.deg2rad(1)
    },
    # {
    #     'label': 'angle10',
    #     'startVal': 0.7,
    #     'startValSd': 0.2,
    #     'line_angle': np.deg2rad(10)
    # },
    # {
    #     'label': 'angle25',
    #     'startVal': 0.7,
    #     'startValSd': 0.2,
    #     'line_angle': np.deg2rad(25)
    # },
    # {
    #     'label': 'angle45',
    #     'startVal': 0.6,
    #     'startValSd': 0.2,
    #     'line_angle': np.deg2rad(45)
    # },
]

conditions = [{**base_condition, **c} for c in conditions]

quests = psychopy.data.MultiStairHandler(conditions=conditions,
                                         nTrials=30,
                                         stairType='QUEST')


def extract_psm_filter_disk_arguments(condition):
    keys = ('image_width', 'image_height', 'line_x', 'line_y', 'line_angle',
            'artifact_size', 'filter_noise')
    result = dict((k, condition[k]) for k in keys)
    result['filter_radius'] = condition['max_filter_radius']
    result['line_x'] += 6 * (random.random() - 0.5) * condition['artifact_size']
    result['line_y'] += 6 * (random.random() - 0.5) * condition['artifact_size']
    result['filter_radius'] = condition['max_filter_radius']
    result['image_angle'] = np.deg2rad(random.randrange(0, 360))
    return result


def generate_line_image(intensity, filter_disk_arguments):
    kwargs = filter_disk_arguments.copy()
    del kwargs['artifact_size']
    kwargs['filter_radius'] *= intensity
    return psm.filter.line(**kwargs)


def generate_stimuli_image(intensity, filter_disk_arguments):
    kwargs = filter_disk_arguments.copy()
    kwargs['filter_radius'] *= intensity
    return psm.filter.artifact_line(**kwargs)


def generate_artifact_image(filter_disk_arguments):
    return generate_stimuli_image(0.0, filter_disk_arguments)


def show_next_stimuli_image():
    try:
        intensity, condition = quests.next()
    except StopIteration:
        quests.saveAsExcel('line_angle_quest.xlsx')
        # quests.saveAsJson('line_angle_quest.json')
        # quests.saveAsPickle('line_angle_quest.pickle')
        exit(0)

    filter_disk_arguments = extract_psm_filter_disk_arguments(condition)
    line_image = generate_line_image(intensity, filter_disk_arguments)
    stimuli_image = generate_stimuli_image(intensity, filter_disk_arguments)

    flip = random.random() < 0.5
    if flip:
        left_image, right_image = stimuli_image, line_image
    else:
        left_image, right_image = line_image, stimuli_image

    img_left.set_data(left_image)
    img_right.set_data(right_image)

    plot.draw()


def get_ax_size(ax):
    fig = plot.gcf()
    bbox = ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    width, height = bbox.width, bbox.height
    width *= fig.dpi
    height *= fig.dpi
    return width, height


def on_cannot_see_artifact(event):
    quests.addResponse(decrease_radius_response)
    show_next_stimuli_image()


def on_can_see_artifact(event):
    quests.addResponse(increase_radius_response)
    show_next_stimuli_image()


plot.subplot(1, 2, 1)
plot.axis('off')
img_left = plot.imshow(np.zeros((image_size, image_size), np.uint8),
                       cmap='gray',
                       vmin=0,
                       vmax=255,
                       interpolation='none')
plot.subplot(1, 2, 2)
plot.axis('off')
img_right = plot.imshow(np.zeros((image_size, image_size), np.uint8),
                          cmap='gray',
                          vmin=0,
                          vmax=255,
                          interpolation='none')

show_next_stimuli_image()

ax_is_line = plot.axes([0.1, 0.05, 0.1, 0.075])
ax_is_artifact = plot.axes([0.8, 0.05, 0.1, 0.075])

btn_line = Button(ax_is_line, 'Same')
btn_artifact = Button(ax_is_artifact, 'Different')

btn_line.on_clicked(on_cannot_see_artifact)
btn_artifact.on_clicked(on_can_see_artifact)

fig = plot.gcf()
fig.patch.set_facecolor((0.8, 0.8, 0.8))

plot.tight_layout()
plot.show()
