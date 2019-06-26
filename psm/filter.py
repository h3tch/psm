import os
import random
import ctypes
import numpy as np

import vps_py.cpp
import psm


extra_args = ['-O0', '-g']

external = vps_py.cpp.fn(
    name='filter',
    dst_path=psm.info.bin_dir,
    sources=[os.path.join(psm.info.src_dir, 'py', 'filter.cpp')],
    include_dirs=psm.info.include_dirs,
    extra_compile_args=extra_args,
    extra_link_args=extra_args
)


# returns the positive root of intersection of line y = h with circle centered
# at the origin and radius r
def horizontal_line_circle_intersection(h, r):
    return np.sqrt(r * r - h * h) if h < r else 0


# indefinite integral of circle segment
def circle_segment_area(x, h, r):
    return 0.5 * (np.sqrt(1 - x * x / (r * r)) * x * r +
                  r * r * np.arcsin(x / r) -
                  2 * h * x)


# area of intersection of an infinitely tall box with left edge at x0, right
# edge at x1, bottom edge at h and top edge at infinity, with circle centered
# at the origin with radius r
def infinit_box_centered_circle_area(x0, x1, h, r):
    x = horizontal_line_circle_intersection(h, r)
    a0 = circle_segment_area(max(-x, min(x, x0)), h, r)
    a1 = circle_segment_area(max(-x, min(x, x1)), h, r)
    return a1 - a0


# area of the intersection of a finite box with
# a circle centered at the origin with radius r
def box_centered_circle_area(x0, x1, y0, y1, r):
    if y0 < 0:
        if y1 < 0:
            # the box is completely under, just flip it above and try again
            return box_centered_circle_area(x0, x1, -y1, -y0, r)
        # the box is both above and below, divide it to two boxes and go
        # again
        a0 = box_centered_circle_area(x0, x1, 0, -y0, r)
        a1 = box_centered_circle_area(x0, x1, 0, y1, r)
        return a0 + a1
    # area of the lower box minus area of the higher box
    a0 = infinit_box_centered_circle_area(x0, x1, y0, r)
    a1 = infinit_box_centered_circle_area(x0, x1, y1, r)
    return a0 - a1


# area of the intersection of a general box with a general circle
def box_circle_area(x0, x1, y0, y1, cx, cy, r):
    if x0 > x1:
        x1, x0 = x0, x1
    if y0 > y1:
        y1, y0 = y0, y1
    return box_centered_circle_area(x0 - cx, x1 - cx, y0 - cy, y1 - cy, r)


@external
def disk(width: int,
         height: int,
         line_x: float,
         line_y: float,
         line_angle: float,
         artifact_size: int,
         radius: float,
         noise: int = 0,
         angle_samples: int = 1) -> np.array:
    raise NotImplementedError


def disk_image(image: np.array, radius: float, noise: int = 0) -> np.array:
    R = int(radius + 0.5)
    result = np.empty_like(image)

    for r in range(image.shape[0]):
        r0 = int(max(r - R, 0))
        r1 = int(min(r + R + 1, image.shape[0]))

        for c in range(image.shape[1]):
            c0 = int(max(c - R, 0))
            c1 = int(min(c + R + 1, image.shape[1]))

            s = 0
            A = 0
            for j in range(r0, r1):
                for i in range(c0, c1):
                    color = image[j, i]
                    a = box_circle_area(
                        i - 0.5, i + 0.5, j - 0.5, j + 0.5, c, r, radius)
                    s += color * a
                    A += a

            s /= A
            n = random.randint(-noise, noise) if int(s +
                                                     0.5) != image[r, c] else 0
            result[r, c] = np.clip(s + n, 0, 255)

    return result
