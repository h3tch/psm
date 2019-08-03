import os
if 'WAYLAND_DISPLAY' in os.environ:
    os.environ['GDK_BACKEND'] = 'x11'
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GObject
import glutil
import itertools
import json
import numpy as np
import quest
import stimuli
import time


class Study:
    def __init__(self, glade_filename, settings, conditions, user):
        self.quests = quest.MultiQuest(user, conditions, **settings)
        self.stimuli = None
        self.drawer = None
        self.undo_button = None
        self.window = None
        self._trial_start_time = None
        self._window_title = ''
        if glade_filename is not None:
            self._init_ui(glade_filename)

    def _init_ui(self, glade_filename):
        handlers = {
            'onDestroy': self.on_quit,
            'onCreateContext': self.on_create_context,
            'onRealize': self.on_realize,
            'onUnrealize': self.on_unrealize,
            'onRender': self.on_render,
            'onCannotDecide': self.on_cannot_decide,
            'onIsLine': self.on_is_line,
            'onUndo': self.on_undo
        }

        builder = Gtk.Builder()
        builder.add_from_file(glade_filename)
        builder.connect_signals(handlers)
        event_box = builder.get_object('event_box')
        event_box.connect('button-press-event', self.on_different)
        self.undo_button = builder.get_object('undo_button')
        self.undo_button.set_sensitive(False)
        self.window = builder.get_object("window")
        self.window.set_title('User Study')
        self.window.show_all()

    def on_quit(self, *args):
        self.quests.save()
        if self.window is not None:
            Gtk.main_quit(*args)

    def on_different(self, widget, event, *args):
        if not self.stimuli.is_showing:
            return
        self.quests.saw_artifact_response(self.trial_duration, 'image',
                                          event.x, event.y)
        self.setup_next_quest()

    def on_cannot_decide(self, widget):
        if not self.stimuli.is_showing:
            return
        self.quests.cannot_decide_response(self.trial_duration)
        self.setup_next_quest()

    def on_is_line(self, widget):
        if not self.stimuli.is_showing:
            return
        self.quests.saw_line_response(self.trial_duration)
        self.setup_next_quest()

    def on_undo(self, widget):
        if not self.stimuli.is_showing or not self.quests.quest_changed:
            return
        self.quests.undo()
        self.setup_next_quest()

    def on_render(self, gl_area, gl_context):
        stimuli = self._render_stimuli()
        if self.window is not None:
            self.window.set_title(self.window_title)
        self.drawer.bind()
        self.drawer.draw(0.0, 0.0, 1.0, 1.0, stimuli)
        if gl_area is not None:
            gl_area.queue_render()

    def _render_stimuli(self):
        is_random_reference_quest = self.quests.is_reference
        self.stimuli.render(reference=is_random_reference_quest,
                            artifact=not is_random_reference_quest)
        if is_random_reference_quest:
            return self.stimuli.reference_image
        return self.stimuli.artifact_image

    def setup_next_quest(self):
        try:
            intensity, condition = self.quests.next()
            self._update_ui()
            self._update_stimuli(intensity, condition)
        except StopIteration:
            if self.window is not None:
                self.window.close()

    def _update_ui(self):
        if self.quests.quest_changed:
            percent = int(self.quests.percent_done)
            self._window_title = f'{percent}% done'
        if self.undo_button is not None:
            self.undo_button.set_sensitive(self.quests.quest_changed)

    def _update_stimuli(self, intensity, condition):
        pause = self._calculate_pause()
        self._trial_start_time = time.time() + pause
        self.stimuli.settings(condition['artifact_size'],
                              condition['line_angle'],
                              condition['filter_radius'] * intensity,
                              condition['filter_noise'],
                              condition['filter_samples'],
                              condition['velocity'],
                              condition['image_samples'],
                              randomize=self.quests.quest_changed,
                              pause=pause)

    def _calculate_pause(self):
        if self.quests.quest_changed:
            quest_changes = self.quests.quest_changes
            if (quest_changes % 30) == 0:
                return 30.0
            elif (quest_changes % 5) == 0:
                return 10.0
            else:
                return 3.0
        return 0.5

    def on_create_context(self, gl_area):
        ctx = gl_area.get_window().create_gl_context()
        ctx.set_required_version(4, 4)
        ctx.set_debug_enabled(True)
        ctx.realize()
        ctx.make_current()
        return ctx

    def on_realize(self, gl_area):
        if gl_area is not None:
            if isinstance(gl_area, int):
                gl_area_height = gl_area
            else:
                gl_area.get_context().make_current()
                gl_area_height = int(gl_area.get_allocated_height())
        self.stimuli = stimuli.Generator(gl_area_height)
        self.drawer = glutil.DrawTexture()
        self.setup_next_quest()

    def on_unrealize(self, gl_area):
        if gl_area is not None:
            gl_area.get_context().make_current()
        del self.stimuli
        del self.drawer

    @property
    def trial_duration(self):
        return time.time() - self._trial_start_time

    @property
    def window_title(self):
        # return f'{self._window_title} ({self.stimuli.fps} FPS)'
        return self._window_title


def load_config(*filenames):
    def load(filename):
        with open(os.path.join(os.path.dirname(__file__), filename), 'rt') as fp:
            config = json.load(fp)
            settings = config['settings']
            base_condition = config['base-condition']
            conditions = config['conditions']
            conditions = [{**base_condition, **c} for c in conditions]
            for c in conditions:
                c['label'] = '-'.join([
                    f'artifact{c["artifact_size"]}',
                    f'angle{c["line_angle"]}',
                    f'noise{c["filter_noise"]}',
                    f'speed{c["velocity"]}',
                    f'samples{c["image_samples"]}'
                ])
                c['line_angle'] = np.deg2rad(c['line_angle'])
        return settings, conditions

    configs = [load(filename) for filename in filenames]
    settings = configs[0][0]
    conditions = list(itertools.chain.from_iterable(config[1] for config in configs))
    return settings, conditions


if __name__ == "__main__":
    settings, conditions = load_config('study-angle.json')
    Study('study.glade', settings, conditions, user=input('user:'))
    Gtk.main()