import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GObject
import cairo
import numpy as np

import psm.filter


class Gui:
    def __init__(self, glade_file):
        handlers = {
            "onDestroy": Gtk.main_quit,
            "onValueChanged": self.on_value_changed
        }

        self.builder = Gtk.Builder()
        self.builder.add_from_file("demo.glade")
        self.builder.connect_signals(handlers)

        self.canvas = self.builder.get_object("canvas")
        self.artifact_size = self.builder.get_object("artifact_size")
        self.filter_radius = self.builder.get_object("filter_radius")
        self.filter_noise = self.builder.get_object("filter_noise")
        self.line_angle = self.builder.get_object("line_angle")
        self.line_x = self.builder.get_object("line_x")
        self.line_y = self.builder.get_object("line_y")

        self.window = self.builder.get_object("window")
        self.window.show_all()

        image_width = self.canvas.get_allocated_width()
        image_height = self.canvas.get_allocated_height()
        self.image_data = np.zeros((image_height, image_width, 4), dtype=np.uint8)
        image_surface = cairo.ImageSurface.create_for_data(
            self.image_data, cairo.FORMAT_ARGB32, image_width, image_height)
        self.canvas.set_from_surface(image_surface)

        self._draw_artifact_line = psm.filter.ArtifactLine(
            image_width, image_height)

        self.draw()

    def on_value_changed(self, widget, *args):
        self.draw()

    def draw(self):
        image_width = self.image_data.shape[1]
        image_height = self.image_data.shape[0]
        artifact_size = self.artifact_size.get_value_as_int()
        filter_radius = self.filter_radius.get_value()
        filter_noise = self.filter_noise.get_value()
        line_angle = np.deg2rad(self.line_angle.get_value())
        line_x = self.line_x.get_value()
        line_y = self.line_y.get_value()

        self._draw_artifact_line(image_width / 2 + line_x,
                                 image_height / 2 + line_y,
                                 line_angle,
                                 artifact_size,
                                 filter_radius,
                                 filter_noise / 255.0,
                                 0.0,
                                 result=self.image_data)

        self.image_data[:, :, 3] = 255
        self.canvas.queue_draw()

Gui('demo.glade')
Gtk.main()