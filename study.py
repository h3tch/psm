import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GObject
import time
import numpy as np

import glutil
import questutil
import psm.filter

base_condition = {
    'pThreshold': 0.63,
    'beta': 3.5,
    'delta': 0.01,
    'gamma': 0.5,
    'grain': 0.1
}

conditions = [
    {
        'label': 'angle1 noise0 speed0',
        'startVal': 0.7,
        'startValSd': 0.2,
        'artifact_size': 8,
        'line_angle': np.deg2rad(1),
        'velocity': 0.0,
        'filter_noise': 0,
        'filter_radius': 100.0
    },
    {
        'label': 'angle1 noise10 speed0',
        'startVal': 0.7,
        'startValSd': 0.2,
        'artifact_size': 8,
        'line_angle': np.deg2rad(1),
        'velocity': 0.0,
        'filter_noise': 10,
        'filter_radius': 100.0
    },
    # {
        #     'label': 'angle0 noise0 speed300',
        #     'startVal': 0.7,
        #     'startValSd': 0.2,
        #     'artifact_size': 8,
        #     'line_angle': np.deg2rad(0),
        #     'velocity': 300.0,
        #     'filter_noise': 0,
        #     'filter_radius': 200.0
        # }, {
        #     'label': 'angle0 noise10 speed300',
        #     'startVal': 0.7,
        #     'startValSd': 0.2,
        #     'artifact_size': 8,
        #     'line_angle': np.deg2rad(0),
        #     'velocity': 300.0,
        #     'filter_noise': 10,
        #     'filter_radius': 200.0
        # }, {
    #     'label': 'angle0 noise0 speed200',
    #     'startVal': 0.7,
    #     'startValSd': 0.2,
    #     'artifact_size': 8,
    #     'line_angle': np.deg2rad(0),
    #     'velocity': 200.0,
    #     'filter_noise': 0,
    #     'filter_radius': 200.0
    # },
    # {
    #     'label': 'angle0 noise10 speed200',
    #     'startVal': 0.7,
    #     'startValSd': 0.2,
    #     'artifact_size': 8,
    #     'line_angle': np.deg2rad(0),
    #     'velocity': 200.0,
    #     'filter_noise': 10,
    #     'filter_radius': 200.0
    # }
]

conditions = [{**base_condition, **c} for c in conditions]


class Study:
    def __init__(self, user, conditions, n_trials=20):

        self.quests = questutil.Quests(user=user,
                                       conditions=conditions,
                                       n_trials=n_trials,
                                       random_trial_probability=0.5)
        self.stimuli = None
        self.drawer = None
        self._random_reference_trial = False

        handlers = {
            'onDestroy': self.on_quit,
            'onCreateContext': self.on_create_context,
            'onRealize': self.on_realize,
            'onUnrealize': self.on_unrealize,
            'onRender': self.on_render,
            'onCannotDecide': self.on_cannot_decide
        }

        self.builder = Gtk.Builder()
        self.builder.add_from_file('study.glade')
        self.builder.connect_signals(handlers)
        event_box = self.builder.get_object('event_box')
        event_box.connect('button-press-event', self.on_different)
        self.window = self.builder.get_object("window")
        self.window.show_all()

        self._start_time = time.time()
        self._last_time = self._start_time

    def on_quit(self, *args):
        self.quests.save()
        Gtk.main_quit(*args)

    def on_different(self, widget, event, *args):
        # selected_left_image = event.x < widget.get_allocated_width() / 2
        # correct_response = self.stimuli.has_selected_artifact(
        #     selected_left_image)
        selected_left_image = True
        correct_response = not self._random_reference_trial

        self.quests.add_response(selected_left_image, correct_response,
                                 event.x, event.y)
        self.setup_next_quest()

    def on_cannot_decide(self, widget):
        self.quests.cannot_decide_response()
        self.setup_next_quest()

    def setup_next_quest(self):
        try:
            intensity, condition, self._random_reference_trial = self.quests.next()
        except StopIteration:
            self.window.close()
            return

        percent = np.round(self.quests.percent_done, decimals=2)
        remainting = self.quests.estimated_minutes_remaining
        self.window.set_title(f'{percent}% (~{remainting}min remaining)')

        artifact_size = condition['artifact_size']
        line_angle = condition['line_angle']
        filter_radius = condition['filter_radius'] * intensity
        filter_noise = condition['filter_noise']
        velocity = condition['velocity']

        self.stimuli.settings(artifact_size, line_angle, filter_radius,
                              filter_noise, velocity)

    def on_create_context(self, gl_area):
        ctx = gl_area.get_window().create_gl_context()
        ctx.set_required_version(4, 6)
        ctx.set_debug_enabled(True)
        ctx.realize()
        ctx.make_current()
        return ctx

    def on_realize(self, gl_area):
        gl_area.get_context().make_current()
        self.stimuli = questutil.StimuliGenerator(
            int(gl_area.get_allocated_height()))
        self.drawer = glutil.DrawTexture()
        self.setup_next_quest()

    def on_unrealize(self, gl_area):
        gl_area.get_context().make_current()
        del self.stimuli
        del self.drawer

    def on_render(self, gl_area, gl_context):
        self.stimuli.render(reference=self._random_reference_trial,
                            artifact=not self._random_reference_trial)
        self.drawer.bind()
        # self.drawer.draw(0.0, 0.0, 0.5, 1.0, self.stimuli.reference_image)
        if self._random_reference_trial:
            self.drawer.draw(0.0, 0.0, 1.0, 1.0, self.stimuli.reference_image)
        else:
            self.drawer.draw(0.0, 0.0, 1.0, 1.0, self.stimuli.artifact_image)
        gl_area.queue_draw()


Study(user='user', conditions=conditions)
Gtk.main()