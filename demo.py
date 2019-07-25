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
        self.builder.add_from_file(glade_file)
        self.builder.connect_signals(handlers)

        self.canvas = self.builder.get_object("canvas")
        self.artifact_size = self.builder.get_object("artifact_size")
        self.filter_radius = self.builder.get_object("filter_radius")
        self.filter_noise = self.builder.get_object("filter_noise")
        self.line_angle = self.builder.get_object("line_angle")
        self.line_x = self.builder.get_object("line_x")
        self.line_y = self.builder.get_object("line_y")
        self.image_angle = self.builder.get_object("image_angle")
        self.filter_samples = self.builder.get_object("filter_samples")
        self.image_samples = self.builder.get_object("image_samples")

        self.window = self.builder.get_object("window")
        self.window.show_all()

        image_width = self.canvas.get_allocated_width()
        image_height = self.canvas.get_allocated_height()
        self.image_sum = np.zeros((image_height, image_width, 4), dtype=np.uint32)
        self.image_data = np.zeros((image_height, image_width, 4), dtype=np.uint8)
        self.image_sample = np.zeros((image_height, image_width, 4), dtype=np.uint8)
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
        filter_noise = self.filter_noise.get_value() / 255.0
        line_angle = np.deg2rad(self.line_angle.get_value())
        line_x = image_width / 2 + self.line_x.get_value()
        line_y = image_height / 2 + self.line_y.get_value()
        image_angle = np.deg2rad(self.image_angle.get_value())
        filter_samples = self.filter_samples.get_value()
        image_samples = int(self.image_samples.get_value())

        self.image_sum[:] = 0
        for i in range(image_samples):
            if i > 0:
                rotation = np.pi / (4 * i) - np.deg2rad(5)
                line_angle += rotation
                #image_angle += rotation
            self._draw_artifact_line(line_x,
                                     line_y,
                                     line_angle,
                                     artifact_size,
                                     filter_radius,
                                     filter_noise,
                                     filter_samples,
                                     image_angle,
                                     result=self.image_sample)
            self.image_sum += self.image_sample
        self.image_data[:] = self.image_sum / image_samples

        self.image_data[:, :, 3] = 255
        self.canvas.queue_draw()

Gui('demo.glade')
Gtk.main()