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
        'line_angle': np.deg2rad(1),
        'velocity': 100.0
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


def compute_line_animation_samples(line_x,
                                   line_y,
                                   line_angle,
                                   velocity,
                                   samples_per_second):
    if velocity == 0.0:
        return [(line_x, line_y)]

    line_nx = -np.sin(line_angle)
    line_ny = np.cos(line_angle)

    sample_velocity = velocity / samples_per_second

    samples = np.append(np.arange(-velocity, velocity, sample_velocity),
                        velocity)

    return [(line_x + line_nx * d, line_y + line_ny * d) for d in samples]


def on_cannot_see_artifact(event):
    quests.addResponse(decrease_radius_response)
    show_next_stimuli_image()


def on_can_see_artifact(event):
    quests.addResponse(increase_radius_response)
    show_next_stimuli_image()


import threading
import time
import timeit
import sys
import math

# def _segment_area(segment_height, chord_length):
#     return segment_height * ((2.0 / 3.0) * chord_length + segment_height * segment_height / (2.0 * chord_length) if chord_length > 0.0 else 0.0)

# def _excess_area(x, y, max_x, radius, radius2):
#     x = min(x, max_x)
#     circle_y = math.sqrt(radius2 - x * x)

#     x_segment_area = _segment_area(radius - x, 2.0 * circle_y)
#     max_x_segment_area = _segment_area(radius - max_x, 2.0 * y)
#     rect_area = (max_x - x) * y
#     return (x_segment_area - max_x_segment_area) / 2.0 - rect_area

# def estimate_circle_interval_area(x0, x1, radius):
#     radius2 = radius * radius
#     left_area = _segment_area(radius - min(abs(x0), radius), 2.0 * math.sqrt(radius2 - x0 * x0))
#     right_area = _segment_area(radius - min(abs(x1), radius), 2.0 * math.sqrt(radius2 - x1 * x1))
#     circle_area = (19.0 / 6.0) * radius2

#     if x0 > 0:
#         left_area = circle_area - left_area
#     if x1 < 0:
#         right_area = circle_area - right_area

#     return circle_area - left_area - right_area

# def estimate_circle_segment_area(x0, x1, y, radius):
#     y = min(y, radius)
#     radius2 = radius * radius
#     max_x = math.sqrt(radius2 - y * y)

#     segment_area = _segment_area(radius - y, 2.0 * max_x)

#     left_area = _excess_area(abs(x0), y, max_x, radius, radius2)
#     if x0 > 0:
#         left_area = segment_area - left_area

#     right_area = _excess_area(abs(x1), y, max_x, radius, radius2)
#     if x1 < 0:
#         right_area = segment_area - right_area

#     return segment_area - left_area - right_area


# a0 = estimate_circle_interval_area(1, 3, 5)
# a0 = estimate_circle_segment_area(-6, 1, 0.1, 5)
# a0 = estimate_circle_segment_area(-6, 6, 0.1, 5)
# a0 = estimate_circle_segment_area(-6, 6, -1, 5)


def draw_image_on_canvas(canvas, tkimage):
    canvas.config(image=tkimage)
    canvas.image = tkimage


def np2tk(image):
    return PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(image))


def draw_stimuli(*args):
    global quests
    intensity = quests.currentStaircase.intensities[-1]
    condition = quests.currentStaircase.condition
    samples_per_second = 60

    line_x = condition['line_x']
    line_y = condition['line_y']
    line_angle = condition['line_angle']
    velocity = condition['velocity']
    artifact_size = condition['artifact_size']
    max_filter_radius = condition['max_filter_radius']
    filter_noise = condition['filter_noise']

    filter_radius = max_filter_radius * intensity
    line_x += 6 * (random.random() - 0.5) * artifact_size
    line_y += 6 * (random.random() - 0.5) * artifact_size
    image_angle = 2 * np.pi * random.random()

    line_positions = compute_line_animation_samples(line_x, line_y, line_angle,
                                                    velocity,
                                                    samples_per_second)

    def generate_line_image(point):
        return np2tk(line(point[0], point[1], line_angle, filter_radius, filter_noise,
                 image_angle))

    def generate_artifact_image(point):
        return np2tk(artifact_line(point[0], point[1], line_angle, artifact_size,
                          filter_radius, filter_noise, image_angle))

    start = time.time_ns()
    line_images = [generate_line_image(point) for point in line_positions]
    dt1 = time.time_ns() - start
    artifact_images = [generate_artifact_image(point) for point in line_positions]
    dt = time.time_ns() - start
    dt2 = dt - dt1

    print('dt:', dt / 1e9, '(s); dt1:', (dt1 / len(line_positions)) / 1e6, '(ms); dt2:', (dt2 / len(line_positions)) / 1e6, '(ms)')
    # exit(0)

    min_time = sys.maxsize

    while quests is not None:
        start = time.time_ns()
        draw_image_on_canvas(left_canvas, line_images[0])
        draw_image_on_canvas(right_canvas, artifact_images[0])
        end = time.time_ns()

        min_time = min(min_time, end - start)

        time.sleep(0.001)


quests.next()

root = tk.Tk()

# draw_stimuli()


left_canvas = tk.Label(root, width=image_size, height=image_size)
right_canvas = tk.Label(root, width=image_size, height=image_size)
different_button = tk.Button(root, text="Different")
cannot_decide_button = tk.Button(root, text="Cannot Decide")

left_canvas.grid(column=0, row=0, columnspan=10, rowspan=10)
right_canvas.grid(column=10, row=0, columnspan=10, rowspan=10)
different_button.grid(column=0, row=10, columnspan=10, rowspan=1)
cannot_decide_button.grid(column=10, row=10, columnspan=10, rowspan=1)

thread = threading.Thread(target=draw_stimuli,
                          args=(left_canvas, right_canvas))
thread.start()

root.mainloop()