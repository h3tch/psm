import math
import numpy as np
import psychopy.data
import psm.filter
import random
import matplotlib.animation
import matplotlib.pyplot as plot
from matplotlib.widgets import Button

import tkinter as tk
import PIL.Image
import PIL.ImageTk

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
        'startVal': 0.9,
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

line = psm.filter.Line(image_size, image_size)
artifact_line = psm.filter.ArtifactLine(image_size, image_size)


def generate_animation(generator_function, generator_arguments, velocity):
    kwargs = generator_arguments.copy()

    filter_radius = kwargs['filter_radius']
    line_x = kwargs['line_x']
    line_y = kwargs['line_y']
    line_angle = kwargs['line_angle']
    line_nx = -np.sin(line_angle)
    line_ny = np.cos(line_angle)

    if velocity == 0:
        start_x = line_x
        start_y = line_y
        step_x = 1
        step_y = 1
        stop_x = line_x + 1
        stop_y = line_y + 1
    else:
        image_radius = math.sqrt(2 * image_size**2) + filter_radius
        start_x = line_x - image_radius * line_nx
        start_y = line_y - image_radius * line_ny
        step_x = line_nx * velocity
        step_y = line_ny * velocity
        stop_x = line_x + image_radius * line_nx
        stop_y = line_y + image_radius * line_ny

    images = []
    for line_x, line_y in zip(np.arange(start_x, stop_x, step_x),
                              np.arange(start_y, stop_y, step_y)):
        kwargs['line_x'] = line_x
        kwargs['line_y'] = line_y
        images.append(generator_function(**kwargs))

    return images


def generate_line_image(line_function_arguments):
    kwargs = line_function_arguments.copy()
    del kwargs['artifact_size']
    return line(**kwargs)


def generate_stimuli_image(artifact_line_function_arguments):
    return artifact_line(**artifact_line_function_arguments)


def extract_psm_filter_disk_arguments(intensity, condition):
    keys = ('line_x', 'line_y', 'line_angle', 'artifact_size', 'filter_noise')
    result = dict((k, condition[k]) for k in keys)
    result['filter_radius'] = condition['max_filter_radius'] * intensity
    result['line_x'] += 6 * (random.random() -
                             0.5) * condition['artifact_size']
    result['line_y'] += 6 * (random.random() -
                             0.5) * condition['artifact_size']
    result['image_angle'] = np.deg2rad(random.randrange(0, 360))
    return result


def show_next_stimuli_image():
    try:
        quests.next()
    except StopIteration:
        quests.saveAsExcel('line_angle_quest.xlsx')
        # quests.saveAsJson('line_angle_quest.json')
        # quests.saveAsPickle('line_angle_quest.pickle')
        exit(0)

    intensity = quests.currentStaircase.intensities[-1]
    condition = quests.currentStaircase.condition

    filter_disk_arguments = extract_psm_filter_disk_arguments(intensity, condition)
    line_image = generate_line_image(filter_disk_arguments)
    stimuli_image = generate_stimuli_image(filter_disk_arguments)

    flip = random.random() < 0.5
    if flip:
        left_image, right_image = stimuli_image[0], line_image[0]
    else:
        left_image, right_image = line_image[0], stimuli_image[0]

    img_left.set_data(left_image)
    img_right.set_data(right_image)

    plot.draw()


def on_cannot_see_artifact(event):
    quests.addResponse(decrease_radius_response)
    show_next_stimuli_image()


def on_can_see_artifact(event):
    quests.addResponse(increase_radius_response)
    show_next_stimuli_image()

import threading
import time

def draw_stimuli(*args):
    while True:
        intensity = quests.currentStaircase.intensities[-1]
        condition = quests.currentStaircase.condition

        filter_disk_arguments = extract_psm_filter_disk_arguments(intensity, condition)
        line_image = generate_line_image(filter_disk_arguments)
        stimuli_image = generate_stimuli_image(filter_disk_arguments)

        img = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(line_image))
        left_canvas.config(image=img)
        left_canvas.image = img

        img = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(stimuli_image))
        right_canvas.config(image=img)
        right_canvas.image = img

        time.sleep(0.001)

quests.next()

root = tk.Tk()

left_canvas = tk.Label(root, width=image_size, height=image_size)
right_canvas = tk.Label(root, width=image_size, height=image_size)
different_button = tk.Button(root, text="Different")
cannot_decide_button = tk.Button(root, text="Cannot Decide")

left_canvas.grid(column=0, row=0, columnspan=10, rowspan=10)
right_canvas.grid(column=10, row=0, columnspan=10, rowspan=10)
different_button.grid(column=0, row=10, columnspan=10, rowspan=1)
cannot_decide_button.grid(column=10, row=10, columnspan=10, rowspan=1)

thread = threading.Thread(target=draw_stimuli, args=(left_canvas, right_canvas))
thread.start()

root.mainloop()