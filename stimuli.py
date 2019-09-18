import numpy as np
import psm.filter
import time
import glutil


class Generator:
    def __init__(self, image_size):
        self._image_size = image_size

        self.reference_image = glutil.Texture2D(image_size, image_size)
        self.artifact_image = glutil.Texture2D(image_size, image_size)

        self._clear_image = psm.filter.Clear()

        self._draw_line = psm.filter.Line(image_size, image_size,
                                          self.reference_image.obj)

        self._draw_artifact_line = psm.filter.ArtifactLine(
            image_size, image_size, self.artifact_image.obj)

        self.settings(1, 0, 0, 0, 0, 0, 1, True, 0.0)
        self._last_time = time.time()
        self._fps = 0.0

    def __del__(self):
        del self.reference_image
        del self.artifact_image
        self._draw_line = None
        self._draw_artifact_line = None

    @property
    def is_showing(self):
        return time.time(
        ) - self._last_update_time >= self._black_screen_timeout

    def has_selected_artifact(self, selected_left):
        return self.flip_images if selected_left else not self.flip_images

    def settings(self, artifact_size, line_angle, filter_radius, filter_noise,
                 filter_samples, velocity, image_samples, randomize, pause):
        if randomize:
            # self.image_angle = np.random.rand() * np.pi * 2
            self.image_angle = np.random.randint(4) * np.pi / 2
        image_size = self._image_size
        half_image_size = image_size / 2.0

        line_angle = np.clip(line_angle, -np.pi / 4, np.pi / 4)
        line_nx = -np.sin(line_angle)
        line_ny = np.cos(line_angle)

        sin, cos = np.sin(self.image_angle), np.cos(self.image_angle)

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

        if randomize:
            self.rand_x = 100 * (np.random.rand() * 2 - 1)
            self.rand_y = 100 * (np.random.rand() * 2 - 1)

        self.artifact_size = max(1, artifact_size)
        self.line_x = half_image_size + self.rand_x
        self.line_y = half_image_size + self.rand_y
        self.current_line_x = self.line_x
        self.current_line_y = self.line_y
        self.line_samples = 2
        self.line_angle = line_angle
        self.line_nx = line_nx
        self.line_ny = line_ny
        self.line_vx = line_nx * velocity
        self.line_vy = line_ny * velocity
        self.filter_radius = max(0.0, filter_radius)
        self.filter_noise = np.clip(filter_noise, 0, 255) / 255.0
        self.filter_samples = max(0.0, filter_samples)
        self.image_samples = min(max(image_samples, 1), 8)
        self.flip_images = np.random.rand() >= 0.5
        self.min_image_d = min(corner_distances)
        self.max_image_d = max(corner_distances)
        self.frame = 0
        if pause > 0.0:
            self._last_update_time = time.time()
            self._black_screen_timeout = pause

    def render(self, reference=True, artifact=True):
        current_time = time.time()
        elapsed_time = current_time - self._last_time
        self._last_time = current_time
        self._fps = 1.0 / elapsed_time

        if current_time - self._last_update_time < self._black_screen_timeout:
            if reference:
                self._clear_image(self._draw_line.cl_image)
            if artifact:
                self._clear_image(self._draw_artifact_line.cl_image)
            time.sleep(0.01)
            return True

        # if there is no animation we do not need to render again
        if self.frame > 0 and self.line_vx == 0 and self.line_vy == 0:
            return False

        if reference:
            self._draw_line(self.current_line_x, self.current_line_y,
                            self.line_angle, max(1.0, self.filter_radius),
                            self.filter_noise, self.filter_samples,
                            self.image_angle)
        if artifact:
            self._draw_artifact_line(self.current_line_x, self.current_line_y,
                                     self.line_angle, self.artifact_size,
                                     self.filter_radius, self.filter_noise,
                                     self.filter_samples, 0.1,
                                     self.image_angle, self.image_samples)

        self.current_line_x += self.line_vx * elapsed_time
        self.current_line_y += self.line_vy * elapsed_time
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

    @property
    def fps(self):
        return int(self._fps)
