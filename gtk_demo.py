import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GObject
import os
import glob
import cairo
import numpy as np
import math
import threading
import time
import psychopy.data
import psm.filter
import questutil

base_condition = {
    'pThreshold': 0.63,
    'beta': 3.5,
    'delta': 0.01,
    'gamma': 0.5,
    'grain': 0.1
}

conditions = [{
#     'label': 'angle1 noise0 speed0',
#     'startVal': 0.7,
#     'startValSd': 0.2,
#     'artifact_size': 8,
#     'line_angle': np.deg2rad(1),
#     'velocity': 0.0,
#     'filter_noise': 0,
#     'filter_radius': 100.0
# }, {
#     'label': 'angle1 noise10 speed0',
#     'startVal': 0.7,
#     'startValSd': 0.2,
#     'artifact_size': 8,
#     'line_angle': np.deg2rad(1),
#     'velocity': 0.0,
#     'filter_noise': 10,
#     'filter_radius': 100.0
# }, {
    'label': 'angle0 noise0 speed300',
    'startVal': 0.7,
    'startValSd': 0.2,
    'artifact_size': 8,
    'line_angle': np.deg2rad(0),
    'velocity': 300.0,
    'filter_noise': 0,
    'filter_radius': 200.0
}, {
    'label': 'angle0 noise10 speed300',
    'startVal': 0.7,
    'startValSd': 0.2,
    'artifact_size': 8,
    'line_angle': np.deg2rad(0),
    'velocity': 300.0,
    'filter_noise': 10,
    'filter_radius': 200.0
}, {
    'label': 'angle0 noise0 speed200',
    'startVal': 0.7,
    'startValSd': 0.2,
    'artifact_size': 8,
    'line_angle': np.deg2rad(0),
    'velocity': 200.0,
    'filter_noise': 0,
    'filter_radius': 200.0
}, {
    'label': 'angle0 noise10 speed200',
    'startVal': 0.7,
    'startValSd': 0.2,
    'artifact_size': 8,
    'line_angle': np.deg2rad(0),
    'velocity': 200.0,
    'filter_noise': 10,
    'filter_radius': 200.0
}]

conditions = [{**base_condition, **c} for c in conditions]


class Render(threading.Thread):
    def __init__(self, window, target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._not_stopped = True
        self._drawing = False
        self._window = window
        self._draw_function = target

    def stop(self):
        self._not_stopped = False

    def run(self):
        def redraw(elapsed_time):
            self._window.set_title(f'User Study f{int(1/elapsed_time)} fps')
            self._window.left_image.queue_draw()
            self._window.right_image.queue_draw()
            self._drawing = False

        start_time = time.time()
        current_time = start_time

        while self._not_stopped:
            previous_time = current_time
            current_time = time.time()
            elapsed_time = current_time - previous_time
            if not self._drawing:
                if self._draw_function(current_time - start_time,
                                       elapsed_time):
                    self._drawing = True
                    GLib.idle_add(redraw, elapsed_time)
            time.sleep(0.001)


class Gui(Gtk.Window):
    def __init__(self, quests, user, image_size=800):
        super().__init__()

        self._quests = quests
        self._stimuli = questutil.Stimuli(image_size)

        self._draw_line = psm.filter.Line(image_size, image_size)
        self._draw_artifact_line = psm.filter.ArtifactLine(
            image_size, image_size)

        left_image_surface = cairo.ImageSurface.create_for_data(
            self._stimuli.left_image_data, cairo.FORMAT_ARGB32, image_size, image_size)
        right_image_surface = cairo.ImageSurface.create_for_data(
            self._stimuli.right_image_data, cairo.FORMAT_ARGB32, image_size, image_size)

        self.left_image = Gtk.Image.new_from_surface(left_image_surface)
        self.right_image = Gtk.Image.new_from_surface(right_image_surface)
        different_button = Gtk.Button(label="Different")
        cannot_decide_button = Gtk.Button(label="Cannot Decide")

        left_event_box = Gtk.EventBox()
        right_event_box = Gtk.EventBox()
        left_event_box.add(self.left_image)
        right_event_box.add(self.right_image)
        left_event_box.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK)
        right_event_box.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK)
        left_event_box.connect('button-press-event', self.on_different,
                               self.left_image)
        right_event_box.connect('button-press-event', self.on_different,
                                self.right_image)

        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(12)
        grid.attach(left_event_box, 0, 0, 10, 10)
        grid.attach(right_event_box, 10, 0, 10, 10)
        grid.attach(cannot_decide_button, 7, 10, 6, 1)

        different_button.connect("clicked", self.on_different)
        cannot_decide_button.connect("clicked", self.on_cannot_decide)
        self.connect("delete-event", self.quit)
        self.add(grid)
        self.show_all()

        self.lock = threading.Lock()
        self.setup_next_quest()

        self.thread = Render(window=self, target=self.render)
        self.thread.daemon = True
        self.thread.start()

    def render_settings(self, artifact_size, line_angle, filter_radius,
                        filter_noise, velocity):
        with self.lock:
            self._stimuli.settings(artifact_size, line_angle, filter_radius,
                                   filter_noise, velocity)

    def render(self, duration, elapsed):
        with self.lock:
            return self._stimuli.render()

    def quit(self, *args):
        self.thread.stop()
        self._quests.save()
        Gtk.main_quit(*args)

    def on_different(self, widget, event, *args):
        selected_left_image = self.left_image in args
        selected_right_image = self.right_image in args
        correct_response = self._stimuli.has_selected_artifact(
            selected_left_image, selected_right_image)

        self._quests.add_response(correct_response, event.x, event.y)
        self.setup_next_quest()

    def on_cannot_decide(self, widget):
        self._quests.cannot_decide_response()
        self.setup_next_quest()

    def setup_next_quest(self):
        try:
            intensity, condition = self._quests.next()
        except StopIteration:
            self.close()
            return

        artifact_size = condition['artifact_size']
        line_angle = condition['line_angle']
        filter_radius = condition['filter_radius'] * intensity
        filter_noise = condition['filter_noise']
        velocity = condition['velocity']

        self._stimuli.settings(artifact_size, line_angle, filter_radius,
                               filter_noise, velocity)


user = input('User:')

quests = questutil.Quests(user, conditions=conditions, n_trials=20)

Gui(quests=quests, user=user)

Gtk.main()