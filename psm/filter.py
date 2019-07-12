import math
import os
import random
import ctypes
import numpy as np
import pyopencl as cl

import vps_py.cpp
import psm

platforms = cl.get_platforms()
device = platforms[-1].get_devices()
context = cl.Context(device)
command_queue = cl.CommandQueue(context)
mem = cl.mem_flags

with open(os.path.join(os.path.dirname(__file__), 'filtered_line.cl'),
          'r') as source_file:
    filter_line_src = source_file.read()

with open(os.path.join(os.path.dirname(__file__), 'filtered_line_artifact.cl'),
          'r') as source_file:
    filter_line_artifact_src = source_file.read()

filter_line_program = cl.Program(context, filter_line_src).build()
filter_line_artifact_program = cl.Program(context,
                                          filter_line_artifact_src).build()
result_image = None
artifact_result_image = None

extra_args = ['-O0', '-g']

external = vps_py.cpp.fn(
    name='filter',
    dst_path=psm.info.bin_dir,
    sources=[os.path.join(psm.info.src_dir, 'py', 'filter.cpp')],
    include_dirs=psm.info.include_dirs,
    extra_compile_args=extra_args,
    extra_link_args=extra_args)


# returns the positive root of intersection of line y = h with circle centered
# at the origin and radius r
def horizontal_line_circle_intersection(h, r):
    return np.sqrt(r * r - h * h) if h < r else 0


# indefinite integral of circle segment
def circle_segment_area(x, h, r):
    return 0.5 * (np.sqrt(1 - x * x / (r * r)) * x * r +
                  r * r * np.arcsin(x / r) - 2 * h * x)


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


def artifact_line(image_width: int,
                  image_height: int,
                  line_x: float,
                  line_y: float,
                  line_angle: float,
                  artifact_size: int,
                  filter_radius: float,
                  filter_noise: int = 0,
                  image_angle: float = 0) -> np.array:
    global artifact_result_image
    shape = (image_height, image_width)

    if artifact_result_image is None or artifact_result_image.width != image_width or artifact_result_image.height != image_height:
        fmt = cl.ImageFormat(cl.channel_order.R, cl.channel_type.FLOAT)
        artifact_result_image = cl.Image(context, mem.WRITE_ONLY, fmt, shape)

    filter_line_artifact_program.filtered_line_artifact(
        command_queue, shape, None, np.uint32(image_width),
        np.uint32(image_height), np.uint32(artifact_size), np.float32(line_x),
        np.float32(line_y), np.float32(line_angle), np.float32(filter_radius),
        np.float32(image_angle), artifact_result_image)

    result = np.zeros(shape, np.float32)
    cl.enqueue_copy(command_queue,
                    result,
                    artifact_result_image,
                    origin=(0, 0),
                    region=shape)
    return (255 * result).astype(np.uint8)


def line(image_width: int,
         image_height: int,
         line_x: float,
         line_y: float,
         line_angle: float,
         filter_radius: float,
         filter_noise: int = 0,
         image_angle: float = 0) -> np.array:
    global result_image
    shape = (image_height, image_width)

    if result_image is None or result_image.width != image_width or result_image.height != image_height:
        fmt = cl.ImageFormat(cl.channel_order.R, cl.channel_type.FLOAT)
        result_image = cl.Image(context, mem.WRITE_ONLY, fmt, shape)

    filter_line_program.filtered_line(command_queue, shape, None,
                                      np.uint32(image_width),
                                      np.uint32(image_height),
                                      np.float32(line_x), np.float32(line_y),
                                      np.float32(line_angle),
                                      np.float32(filter_radius),
                                      np.float32(image_angle), result_image)
    result = np.zeros(shape, np.float32)
    cl.enqueue_copy(command_queue,
                    result,
                    result_image,
                    origin=(0, 0),
                    region=shape)
    return (255 * result).astype(np.uint8)


def rotate(sin, cos, cx, cy, x, y):
    tmp_x = x - cx
    tmp_y = y - cy
    return cos * tmp_x - sin * tmp_y + cx, sin * tmp_x + cos * tmp_y + cy


def rasterize(raster_size, value):
    rasterized = int(value / raster_size) * raster_size
    return rasterized if rasterized <= value else rasterized - raster_size


def rasterize_line_y(artifact_size, k, d, x):
    y = k * x + d
    y0 = rasterize(artifact_size, y)
    return y0 if y - y0 < artifact_size / 2 else y0 + artifact_size


def line_filter(line_x, line_y, line_nx, line_ny, artifact_size, c, r, radius):
    k = -line_nx / line_ny
    d = line_y - k * line_x

    c0 = rasterize(artifact_size, c - radius)
    r0 = rasterize(artifact_size, r - radius)

    if radius <= 0:
        c1 = c0 + artifact_size
        r1 = rasterize_line_y(artifact_size, k, d, c0 + artifact_size / 2)
        return 1 if c0 <= c < c1 and r0 <= r < r1 else 0

    area = 0.0
    while c0 < c + radius:
        c1 = c0 + artifact_size
        r1 = rasterize_line_y(artifact_size, k, d, c0 + artifact_size / 2)
        area += box_circle_area(c0, c1, r0, r1, c, r, radius)
        c0 = c1

    circle_area = radius**2 * np.pi
    return area / circle_area


# def line(image_width: int, image_height: int, line_x: float, line_y: float,
#          line_angle: float, filter_radius: float, image_angle: float,
#          **kwargs) -> np.array:
#     result = np.empty((image_height, image_width), dtype=np.float64)

#     line_nx = -np.sin(line_angle)
#     line_ny = np.cos(line_angle)
#     line_d = line_nx * line_x + line_ny * line_y

#     sin = np.sin(image_angle)
#     cos = np.cos(image_angle)

#     circle_area = (19 / 6) * filter_radius**2

#     for r in range(image_height):
#         for c in range(image_width):
#             fx, fy = rotate(sin, cos, image_width / 2, image_height / 2, c, r)
#             filter_d = line_nx * fx + line_ny * fy
#             d = line_d - filter_d
#             if d > filter_radius:
#                 result[r, c] = 1.0
#             elif d < -filter_radius:
#                 result[r, c] = 0.0
#             else:
#                 h = filter_radius - abs(d)
#                 chord_length = 2 * math.sqrt(filter_radius**2 - d**2)
#                 area = (2 / 3) * chord_length * h + h**3 / (2 * chord_length)

#                 if d > 0:
#                     result[r, c] = 1 - area / circle_area
#                 else:
#                     result[r, c] = area / circle_area

#     return (255 * (result - result.min()) /
#             (result.max() - result.min())).astype(np.uint8)


def disk_image(width,
               height,
               line_x,
               line_y,
               line_angle,
               artifact_size,
               filter_radius: float,
               filter_noise: int = 0,
               image_rotation: float = 0) -> np.array:
    result = np.empty((width, height), dtype=np.float64)

    line_nx = -np.sin(line_angle)
    line_ny = np.cos(line_angle)

    sin = np.sin(image_rotation)
    cos = np.cos(image_rotation)

    for r in range(height):
        for c in range(width):
            fx, fy = rotate(sin, cos, width / 2, height / 2, c, r)
            result[r, c] = line_filter(line_x, line_y, line_nx, line_ny,
                                       artifact_size, fx, fy, filter_radius)

    return (255 * (result - result.min()) /
            (result.max() - result.min())).astype(np.uint8)
