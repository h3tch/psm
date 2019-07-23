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
        self._user = user
        self._start_time = time.time()

        self._data_folder = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(self._data_folder, exist_ok=True)
        count = len(glob.glob(os.path.join(self._data_folder, '*/'))) + 1
        self._data_folder = os.path.join(self._data_folder, f'{count}')
        os.makedirs(self._data_folder, exist_ok=True)
        self._backup_file = os.path.join(self._data_folder, 'backup')

        with open(os.path.join(self._data_folder, 'info.txt'), 'w') as file:
            file.write(f'user: {self._user}\n')

        self._draw_line = psm.filter.Line(image_size, image_size)
        self._draw_artifact_line = psm.filter.ArtifactLine(
            image_size, image_size)

        self.left_image_data = np.zeros((image_size, image_size, 4),
                                        dtype=np.uint8)
        self.right_image_data = np.zeros((image_size, image_size, 4),
                                         dtype=np.uint8)

        left_image_surface = cairo.ImageSurface.create_for_data(
            self.left_image_data, cairo.FORMAT_ARGB32, image_size, image_size)
        right_image_surface = cairo.ImageSurface.create_for_data(
            self.right_image_data, cairo.FORMAT_ARGB32, image_size, image_size)

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
        image_angle = np.random.rand() * np.pi * 2
        image_size = self.left_image_data.shape[0]
        half_image_size = image_size / 2.0

        line_angle = np.clip(line_angle, -np.pi / 4, np.pi / 4)
        line_nx = -np.sin(line_angle)
        line_ny = np.cos(line_angle)

        sin, cos = np.sin(image_angle), np.cos(image_angle)

        def rotate(x, y):
            u = x - half_image_size
            v = y - half_image_size
            x = cos * u - sin * v + half_image_size
            y = sin * u + cos * v + half_image_size
            return x, y

        min_size = -filter_radius
        max_size = image_size + filter_radius - 1
        corners = [(min_size, min_size), (max_size, min_size),
                   (min_size, max_size), (max_size, max_size)]
        corners = [rotate(corner[0], corner[1]) for corner in corners]

        corner_distances = [
            corner[0] * line_nx + corner[1] * line_ny for corner in corners
        ]

        with self.lock:
            self.artifact_size = max(1, artifact_size)
            self.line_x = half_image_size + artifact_size * (
                np.random.rand() * 2 - 1)
            self.line_y = half_image_size + artifact_size * (
                np.random.rand() * 2 - 1)
            self.current_line_x = self.line_x
            self.current_line_y = self.line_y
            self.line_angle = line_angle
            self.line_nx = line_nx
            self.line_ny = line_ny
            self.line_vx = self.line_nx * velocity
            self.line_vy = self.line_ny * velocity
            self.filter_radius = max(0.0, filter_radius)
            self.filter_noise = np.clip(filter_noise, 0, 255) / 255.0
            self.image_angle = image_angle
            self.flip_images = np.random.rand() >= 0.5
            self.min_image_d = min(corner_distances)
            self.max_image_d = max(corner_distances)
            self.frame = 0

    def render(self, duration, elapsed):
        with self.lock:
            # if there is no animation we do not need to render again
            if self.frame > 0 and self.line_vx == 0 and self.line_vy == 0:
                return False

            self._draw_line(self.current_line_x,
                            self.current_line_y,
                            self.line_angle,
                            self.filter_radius,
                            self.filter_noise,
                            self.image_angle,
                            result=self.right_image_data
                            if self.flip_images else self.left_image_data)
            self._draw_artifact_line(
                self.current_line_x,
                self.current_line_y,
                self.line_angle,
                self.artifact_size,
                self.filter_radius,
                self.filter_noise,
                self.image_angle,
                result=self.left_image_data
                if self.flip_images else self.right_image_data)

            self.current_line_x += self.line_vx * elapsed
            self.current_line_y += self.line_vy * elapsed
            current_line_d = self.current_line_x * self.line_nx + self.current_line_y * self.line_ny
            if current_line_d < self.min_image_d or self.max_image_d < current_line_d:
                current_line_d = min(max(current_line_d, self.min_image_d),
                                     self.max_image_d)
                self.current_line_x = self.line_nx * current_line_d
                self.current_line_y = self.line_ny * current_line_d
                self.line_vx = -self.line_vx
                self.line_vy = -self.line_vy

            self.frame += 1
            return True

    def quit(self, *args):
        self.thread.stop()
        self._quests.saveAsJson(os.path.join(self._data_folder, 'result.json'))
        self.save_csv(os.path.join(self._data_folder, 'result.csv'))
        Gtk.main_quit(*args)

    def save_csv(self, filename):
        with open(filename, 'w') as file:
            file.write(
                'label,artifact_size,line_angle,velocity,filter_noise,filter_radius,response\n'
            )
            for quest in self._quests.staircases:
                condition = quest.condition
                label = condition['label']
                artifact_size = condition['artifact_size']
                line_angle = np.rad2deg(condition['line_angle'])
                filter_radius = condition['filter_radius']
                filter_noise = condition['filter_noise']
                velocity = condition['velocity']
                for intensity, response in zip(quest.intensities, quest.data):
                    file.write(
                        f'{label},{artifact_size},{line_angle},{velocity},{filter_noise},{filter_radius*intensity},{response}\n'
                    )

    def add_response_info_to_current_quest(self,
                                           selected_left,
                                           selected_right,
                                           x=0,
                                           y=0):
        if selected_left:
            correct_response = (self.flip_images, x, y)
        elif selected_right:
            correct_response = (not self.flip_images, x, y)
        else:
            correct_response = None
        current_quest = self._quests.currentStaircase
        if current_quest.extraInfo is None:
            current_quest.extraInfo = []
        current_quest.extraInfo.append(correct_response)
        return correct_response

    def on_different(self, widget, event, *args):
        selected_left = self.left_image in args
        selected_right = self.right_image in args
        correct = self.add_response_info_to_current_quest(
            selected_left, selected_right, event.x, event.y)

        increase_radius = 0
        decrease_radius = 1
        self._quests.addResponse(
            increase_radius if correct else decrease_radius)
        self.setup_next_quest()

    def on_cannot_decide(self, widget):
        self.add_response_info_to_current_quest(selected_left=False,
                                                selected_right=False)

        decrease_radius = 1
        self._quests.addResponse(decrease_radius)
        self.setup_next_quest()

    def setup_next_quest(self):
        self._quests.saveAsPickle(self._backup_file)
        try:
            intensity, condition = self._quests.next()
        except StopIteration:
            self.close()
            return

        done_trials = self._quests.totalTrials
        number_of_trials = self._quests.nTrials * len(self._quests.staircases)
        remaining_trials = number_of_trials - done_trials

        running_time = time.time() - self._start_time
        average_time = running_time / done_trials if done_trials > 0 else 5.0
        remaining_time = int(np.ceil(average_time * remaining_trials / 60.0))

        percent = (100.0 * done_trials) / number_of_trials
        # self.set_title(f'User Study {percent}% (~{remaining_time} min left)')

        artifact_size = condition['artifact_size']
        line_angle = condition['line_angle']
        filter_radius = condition['filter_radius'] * intensity
        filter_noise = condition['filter_noise']
        velocity = condition['velocity']

        self.render_settings(artifact_size, line_angle, filter_radius,
                             filter_noise, velocity)


user = input('User:')

quests = psychopy.data.MultiStairHandler(conditions=conditions,
                                         nTrials=20,
                                         stairType='QUEST')
quests.next()

Gui(quests=quests, user=user)

Gtk.main()