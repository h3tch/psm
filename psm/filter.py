import os
import random
import numpy as np
import pyopencl as cl
from pyopencl.tools import get_gl_sharing_context_properties


context = None
command_queue = None
mem = cl.mem_flags

def init_opencl():
    global context, command_queue
    platform = cl.get_platforms()[-1]
    devices = platform.get_devices()
    context = cl.Context(devices=devices,
                        properties=[(cl.context_properties.PLATFORM, platform)] +
                        get_gl_sharing_context_properties())
    command_queue = cl.CommandQueue(context)


class Base:
    context = None
    command_queue = None

    def __init__(self, image_width, image_height, opencl_file):
        init_opencl()

        with open(opencl_file, 'r') as f:
            source = f.read()

        self._program = cl.Program(
            context,
            source).build(options=['-I', f'"{os.path.dirname(opencl_file)}"'])

        shape = (image_height, image_width)
        fmt = cl.ImageFormat(cl.channel_order.RGBA, cl.channel_type.UNORM_INT8)
        self._result_image = cl.Image(context, mem.WRITE_ONLY, fmt, shape)


class Line(Base):
    def __init__(self, image_width, image_height):
        super().__init__(
            image_width, image_height,
            os.path.join(os.path.dirname(__file__), 'filtered_line.cl'))

    def __call__(self,
                 line_x: float,
                 line_y: float,
                 line_angle: float,
                 filter_radius: float,
                 filter_noise: float,
                 image_angle: float,
                 result: np.array = None) -> np.array:
        shape = self._result_image.shape

        self._program.filtered_line(command_queue, shape, None,
                                    np.uint32(shape[1]), np.uint32(shape[0]),
                                    np.float32(line_x), np.float32(line_y),
                                    np.float32(line_angle),
                                    np.float32(filter_radius),
                                    np.float32(filter_noise),
                                    np.float32(image_angle),
                                    self._result_image)

        if result is None:
            result = np.zeros(shape + (4, ), np.uint8)
        cl.enqueue_copy(command_queue,
                        result,
                        self._result_image,
                        origin=(0, 0),
                        region=shape)
        return result


class ArtifactLine(Base):
    def __init__(self, image_width, image_height):
        super().__init__(
            image_width, image_height,
            os.path.join(os.path.dirname(__file__),
                         'filtered_line_artifact.cl'))

    def __call__(self,
                 line_x: float,
                 line_y: float,
                 line_angle: float,
                 artifact_size: int,
                 filter_radius: float,
                 filter_noise: float,
                 image_angle: float,
                 result: np.array = None) -> np.array:
        shape = self._result_image.shape

        self._program.filtered_line_artifact(command_queue, shape, None,
                                             np.uint32(shape[1]),
                                             np.uint32(shape[0]),
                                             np.uint32(artifact_size),
                                             np.float32(line_x),
                                             np.float32(line_y),
                                             np.float32(line_angle),
                                             np.float32(filter_radius),
                                             np.float32(filter_noise),
                                             np.float32(image_angle),
                                             self._result_image)

        if result is None:
            result = np.zeros(shape + (4, ), np.uint8)
        cl.enqueue_copy(command_queue,
                        result,
                        self._result_image,
                        origin=(0, 0),
                        region=shape)
        return result
