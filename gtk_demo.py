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

image_size = 1000
draw_line = psm.filter.Line(image_size, image_size)
draw_artifact_line = psm.filter.ArtifactLine(image_size, image_size)

left_image_data = np.zeros((image_size, image_size, 4), dtype=np.uint8)
right_image_data = np.zeros((image_size, image_size, 4), dtype=np.uint8)

left_image_surface = cairo.ImageSurface.create_for_data(
    left_image_data, cairo.FORMAT_ARGB32, image_size, image_size)
right_image_surface = cairo.ImageSurface.create_for_data(
    right_image_data, cairo.FORMAT_ARGB32, image_size, image_size)


class Render(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._not_stopped = True
        self._drawing = False

    def stop(self):
        self._not_stopped = False

    def run(self):
        def redraw():
            left_image.queue_draw()
            right_image.queue_draw()
            self._drawing = False

        start_time = time.time()

        while self._not_stopped:
            if not self._drawing:
                self._drawing = True
                elapsed_time = start_time - time.time()
                angle = np.pi * np.sin(elapsed_time) / 4
                draw_line(500.0, 500.0, angle, 100.0, 0.0, 0.0, result=left_image_data)
                draw_artifact_line(500.0, 500.0, angle, 8, 100.0, 0.0, 0.0, result=right_image_data)
                GLib.idle_add(redraw)
            time.sleep(0.001)


def quit(*args):
    thread.stop()
    Gtk.main_quit(*args)


left_image = Gtk.Image.new_from_surface(left_image_surface)
right_image = Gtk.Image.new_from_surface(right_image_surface)
left_button = Gtk.Button(label="Left")
right_button = Gtk.Button(label="Right")

grid = Gtk.Grid()
grid.attach(left_image, 0, 0, 10, 10)
grid.attach(right_image, 10, 0, 10, 10)
grid.attach(left_button, 0, 10, 10, 1)
grid.attach(right_button, 10, 10, 10, 1)

window = Gtk.Window()
window.connect("delete-event", quit)
window.add(grid)
window.show_all()

thread = Render()
thread.daemon = True
thread.start()

Gtk.main()