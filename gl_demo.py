import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GObject
import time
import numpy as np

import glutil
import psm.filter


class Gui:
    def __init__(self, glade_file):
        handlers = {
            'onDestroy': Gtk.main_quit,
            'onCreateContext': self.on_create_context,
            'onRealize': self.on_realize,
            'onUnrealize': self.on_unrealize,
            'onResize': self.on_resize,
            'onRender': self.on_render,
        }

        self.builder = Gtk.Builder()
        self.builder.add_from_file(glade_file)
        self.builder.connect_signals(handlers)

        self._reference_image = None
        self._artifact_image = None
        self._draw_texture = None

        self._draw_line = None
        self._draw_artifact_line = None

        self._start_time = time.time()
        self._last_time = self._start_time

        self.window = self.builder.get_object("window")
        self.window.show_all()

    def on_create_context(self, gl_area):
        ctx = gl_area.get_window().create_gl_context()
        ctx.set_required_version(4, 6)
        ctx.set_debug_enabled(True)
        ctx.realize()
        ctx.make_current()

        psm.filter.init_opencl()

        return ctx

    def on_realize(self, gl_area):
        gl_area.get_context().make_current()

        self._reference_image = glutil.Texture2D(800, 800)
        self._draw_line = psm.filter.Line(800, 800, self._reference_image.obj)

        self._artifact_image = glutil.Texture2D(800, 800)
        self._draw_artifact_line = psm.filter.ArtifactLine(
            800, 800, self._artifact_image.obj)

        self._draw_texture = glutil.DrawTexture()

    def on_unrealize(self, gl_area):
        gl_area.get_context().make_current()

        self._draw_line = None
        self._draw_artifact_line = None

        del self._reference_image
        del self._artifact_image
        del self._draw_texture

    def on_resize(self, gl_area, width, height):
        pass

    def on_render(self, gl_area, gl_context):
        current_time = time.time()
        animation_time = self._start_time - current_time
        elapsed_time = self._last_time - current_time
        self._last_time = current_time
        self.window.set_title(f'User Study {int(1.0/elapsed_time)} fps')

        self._draw_line(400.0, 400.0, animation_time * np.pi / 4, 100.0, 10.0 / 255.0, 0.0)
        self._draw_artifact_line(400.0, 400.0, animation_time * np.pi / 4, 8, 100.0, 10.0 / 255.0, 0.0)

        self._draw_texture.bind()
        self._draw_texture.draw(0.0, 0.0, 0.5, 1.0, self._reference_image)
        self._draw_texture.draw(0.5, 0.0, 0.5, 1.0, self._artifact_image)

        gl_area.queue_draw()


Gui('gl.glade')
Gtk.main()