import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GObject
import time
import numpy as np
import json
import glutil
import questutil
import psm.filter
import os


class Study:
    def __init__(self, user, conditions=None, n_trials=20):
        if conditions is None:
            conditions = self._load_config()
        self.quests = questutil.MultiQuest(user=user, conditions=conditions)
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
        self.quests.saw_artifact_response('image', event.x, event.y)
        self.setup_next_quest()

    def on_cannot_decide(self, widget):
        self.quests.cannot_decide_response()
        self.setup_next_quest()

    def setup_next_quest(self):
        try:
            intensity, condition, rnd, quest_changed = self.quests.next()
            self._random_reference_trial = rnd
        except StopIteration:
            self.window.close()
            return

        percent = int(self.quests.percent_done)
        self.window.set_title(f'{percent}% done')

        artifact_size = condition['artifact_size']
        line_angle = condition['line_angle']
        filter_radius = condition['filter_radius'] * intensity
        filter_noise = condition['filter_noise']
        filter_samples = condition['filter_samples']
        velocity = condition['velocity']
        image_samples = condition['image_samples']

        if quest_changed:
            long_pause = ((self.quests.reversal_counter + 1) % 5) == 0
            pause = 10.0 if long_pause else 3.0
        else:
            pause = 0.0

        self.stimuli.settings(artifact_size, line_angle, filter_radius,
                              filter_noise, filter_samples, velocity,
                              image_samples, randomize=quest_changed,
                              pause=pause)

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
            int(gl_area.get_allocated_height()), 3.0)
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

    def _load_config(self):
        with open(os.path.join(os.path.dirname(__file__), 'config.json'), 'rt') as fp:
            config = json.load(fp)
            base_condition = config['base']
            conditions = config['conditions']
            conditions = [{**base_condition, **c} for c in conditions]
            for c in conditions:
                c['label'] = f'angle{c["line_angle"]}-noise{c["filter_noise"]}-imgsamples{c["image_samples"]}'
                c['line_angle'] = np.deg2rad(c['line_angle'])
        return conditions


Study(user=input('user:'))
Gtk.main()