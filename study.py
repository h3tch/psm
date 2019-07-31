import os
if 'WAYLAND_DISPLAY' in os.environ:
    os.environ['GDK_BACKEND'] = 'x11'
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GObject
import numpy as np
import json
import glutil
import quest
import stimuli


class Study:
    def __init__(self, user, conditions=None):
        if conditions is None:
            conditions = self._load_config()
        self.quests = quest.MultiQuest(user=user,
                                       conditions=conditions,
                                       random_reference_probability=0.2)
        self.stimuli = None
        self.drawer = None
        self.undo_button = None
        self.window = None
        self._is_random_reference_trial = False
        self._quest_has_changed = False

        self._init_ui('study.glade')

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
        Gtk.main_quit(*args)

    def on_different(self, widget, event, *args):
        if not self.stimuli.is_showing:
            return
        self.quests.saw_artifact_response('image', event.x, event.y)
        self.setup_next_quest()

    def on_cannot_decide(self, widget):
        if not self.stimuli.is_showing:
            return
        self.quests.cannot_decide_response()
        self.setup_next_quest()

    def on_is_line(self, widget):
        if not self.stimuli.is_showing:
            return
        self.quests.saw_line_response()
        self.setup_next_quest()

    def on_undo(self, widget):
        if not self.stimuli.is_showing:
            return
        self.quests.undo()
        self.setup_next_quest()

    def setup_next_quest(self):
        try:
            intensity, condition = self._update_quests()
            self._update_ui()
            self._update_stimuli(intensity, condition)
        except StopIteration:
            self.window.close()

    def _update_quests(self):
        intensity, condition, rnd, quest_changed = self.quests.next()
        self._is_random_reference_trial = rnd
        self._quest_has_changed = quest_changed
        return intensity, condition

    def _update_ui(self):
        if self._quest_has_changed:
            percent = int(self.quests.percent_done)
            self.window.set_title(f'{percent}% done')
        self.undo_button.set_sensitive(self._quest_has_changed)

    def _update_stimuli(self, intensity, condition):
        pause = self._calculate_pause()
        self.stimuli.settings(condition['artifact_size'],
                              condition['line_angle'],
                              condition['filter_radius'] * intensity,
                              condition['filter_noise'],
                              condition['filter_samples'],
                              condition['velocity'],
                              condition['image_samples'],
                              randomize=self._quest_has_changed,
                              pause=pause)

    def _calculate_pause(self):
        if self._quest_has_changed:
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
        gl_area.get_context().make_current()
        gl_area_height = int(gl_area.get_allocated_height())
        self.stimuli = stimuli.Generator(gl_area_height, 3.0)
        self.drawer = glutil.DrawTexture()
        self.setup_next_quest()

    def on_unrealize(self, gl_area):
        gl_area.get_context().make_current()
        del self.stimuli
        del self.drawer

    def on_render(self, gl_area, gl_context):
        stimuli = self._render_stimuli()
        self.drawer.bind()
        self.drawer.draw(0.0, 0.0, 1.0, 1.0, stimuli)
        gl_area.queue_draw()

    def _render_stimuli(self):
        self.stimuli.render(reference=self._is_random_reference_trial,
                            artifact=not self._is_random_reference_trial)
        if self._is_random_reference_trial:
            return self.stimuli.reference_image
        return self.stimuli.artifact_image

    def _load_config(self):
        with open(os.path.join(os.path.dirname(__file__), 'config.json'),
                  'rt') as fp:
            config = json.load(fp)
            base_condition = config['base']
            conditions = config['conditions']
            conditions = [{**base_condition, **c} for c in conditions]
            for c in conditions:
                c['label'] = f'angle{c["line_angle"]}-noise{c["filter_noise"]}-imgsamples{c["image_samples"]}'
                c['line_angle'] = np.deg2rad(c['line_angle'])
        return conditions


if __name__ == "__main__":
    Study(user=input('user:'))
    Gtk.main()