import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GObject
import cairo
import numpy as np
import math
import threading
import time

import psm.filter

image_size = 500
draw_line = psm.filter.Line(image_size, image_size)
draw_artifact_line = psm.filter.ArtifactLine(image_size, image_size)


class Render(threading.Thread):
    def __init__(self, target, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._not_stopped = True
        self._drawing = False
        self._draw_function = target

    def _dummy_draw_function(self, *args):
        pass

    def stop(self):
        self._not_stopped = False

    def run(self):
        def redraw():
            window.left_image.queue_draw()
            window.right_image.queue_draw()
            self._drawing = False

        start_time = time.time()
        current_time = start_time

        while self._not_stopped:
            previous_time = current_time
            current_time = time.time()
            if not self._drawing:
                self._drawing = True
                self._draw_function(current_time - start_time,
                                    current_time - previous_time)
                GLib.idle_add(redraw)
            time.sleep(0.001)


class Gui(Gtk.Window):
    def __init__(self):
        super().__init__()

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
        left_button = Gtk.Button(label="Left")
        right_button = Gtk.Button(label="Right")

        grid = Gtk.Grid()
        grid.attach(self.left_image, 0, 0, 10, 10)
        grid.attach(self.right_image, 10, 0, 10, 10)
        grid.attach(left_button, 0, 10, 10, 1)
        grid.attach(right_button, 10, 10, 10, 1)

        self.connect("delete-event", self.quit)
        self.add(grid)
        self.show_all()

        self.lock = threading.Lock()
        self.thread = Render(target=self.render)
        self.thread.daemon = True
        self.thread.start()

        self.render_settings(1, 0.0, 0.0, 0, 0.0)

    def render_settings(self, artifact_size, line_angle, filter_radius,
                        filter_noise, velocity):
        corners = [(0, 0), (image_size - 1, 0), (0, image_size - 1),
                   (image_size - 1, image_size - 1)]
        with self.lock:
            self.artifact_size = max(1, artifact_size)
            self.line_x = image_size / 2.0
            self.line_y = image_size / 2.0
            self.current_line_x = self.line_x
            self.current_line_y = self.line_y
            self.line_angle = min(max(line_angle, -np.pi / 4), np.pi / 4)
            self.line_nx = -np.sin(self.line_angle)
            self.line_ny = np.cos(self.line_angle)
            self.line_vx = self.line_nx * velocity
            self.line_vy = self.line_ny * velocity
            self.filter_radius = max(0.0, filter_radius)
            self.filter_noise = min(max(filter_noise, 0), 255)
            self.image_angle = 0.0
            corner_distances = [corner[0] * self.line_nx + corner[1] * self.line_ny for corner in corners]
            self.min_image_d = min(corner_distances)
            self.max_image_d = max(corner_distances)

    def render(self, duration, elapsed):

        with self.lock:
            draw_line(self.current_line_x,
                      self.current_line_y,
                      self.line_angle,
                      self.filter_radius,
                      self.filter_noise,
                      self.image_angle,
                      result=window.left_image_data)
            draw_artifact_line(self.current_line_x,
                               self.current_line_y,
                               self.line_angle,
                               self.artifact_size,
                               self.filter_radius,
                               self.filter_noise,
                               self.image_angle,
                               result=window.right_image_data)

            self.current_line_x += self.line_vx * elapsed
            self.current_line_y += self.line_vy * elapsed
            current_line_d = self.current_line_x * self.line_nx + self.current_line_y * self.line_ny
            if current_line_d < self.min_image_d or self.max_image_d < current_line_d:
                current_line_d = min(max(line_d, self.min_image_d),
                                     self.max_image_d)
                self.line_x = self.line_x + self.line_nx * current_line_d
                self.line_y = self.line_y + self.line_ny * current_line_d
                self.line_vx = -self.line_vx
                self.line_vy = -self.line_vy

    def quit(self, *args):
        self.thread.stop()
        Gtk.main_quit(*args)


window = Gui()

Gtk.main()