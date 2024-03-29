import os
import random
import numpy as np
import pyopencl as cl
from pyopencl.tools import get_gl_sharing_context_properties

context = None
command_queue = None
mem = cl.mem_flags


def init_opencl(sharing=True):
    global context, command_queue
    if context is not None:
        return
    platform = cl.get_platforms()[-1]
    devices = platform.get_devices()
    if sharing:
        context = cl.Context(
            devices=devices,
            properties=[(cl.context_properties.PLATFORM, platform)] +
            get_gl_sharing_context_properties())
    else:
        context = cl.Context(devices=devices)
    command_queue = cl.CommandQueue(context)


class Clear:
    def __init__(self):
        init_opencl(True)

        opencl_file = os.path.join(os.path.dirname(__file__), 'clear.cl')

        with open(opencl_file, 'r') as f:
            source = f.read()

        self._program = cl.Program(
            context,
            source).build(options=['-I', f'"{os.path.dirname(opencl_file)}"'])

    def __call__(self, image):
        cl.enqueue_acquire_gl_objects(command_queue, [image])
        self._program.clear(command_queue, image.shape, (1, 1), image)
        cl.enqueue_release_gl_objects(command_queue, [image])


class Base:
    def __init__(self, image_width, image_height, opencl_file, gl_image=None):
        enable_gl_sharing = gl_image is not None
        init_opencl(enable_gl_sharing)

        with open(opencl_file, 'r') as f:
            source = f.read()

        self._program = cl.Program(
            context,
            source).build(options=['-I', f'"{os.path.dirname(opencl_file)}"'])

        if gl_image is None:
            shape = (image_height, image_width)
            fmt = cl.ImageFormat(cl.channel_order.RGBA, cl.channel_type.UNORM_INT8)
            self._result_image = cl.Image(context, mem.WRITE_ONLY, fmt, shape)
        else:
            from OpenGL.GL import GL_TEXTURE_2D
            self._result_image = cl.GLTexture(context,
                                              mem.WRITE_ONLY,
                                              GL_TEXTURE_2D,
                                              0,
                                              gl_image,
                                              dims=2)

    @property
    def cl_image(self):
        return self._result_image


class Line(Base):
    def __init__(self, image_width, image_height, gl_image=None):
        super().__init__(
            image_width, image_height,
            os.path.join(os.path.dirname(__file__), 'filtered_line.cl'),
            gl_image=gl_image)

    def __call__(self,
                 line_x: float,
                 line_y: float,
                 line_angle: float,
                 filter_radius: float,
                 filter_noise: float,
                 filter_samples: float,
                 image_angle: float,
                 result: np.array = None) -> np.array:
        shape = self._result_image.shape

        if hasattr(self._result_image, 'gl_object'):
            cl.enqueue_acquire_gl_objects(command_queue, [self._result_image])
        self._program.filtered_line(command_queue, shape, (1, 1),
                                    np.uint32(shape[1]), np.uint32(shape[0]),
                                    np.float32(line_x), np.float32(line_y),
                                    np.float32(line_angle),
                                    np.float32(max(1.0, filter_radius)),
                                    np.float32(filter_noise),
                                    np.float32(filter_samples),
                                    np.float32(image_angle),
                                    self._result_image)
        if hasattr(self._result_image, 'gl_object'):
            cl.enqueue_release_gl_objects(command_queue, [self._result_image])

        if result is not None:
            cl.enqueue_copy(command_queue,
                            result,
                            self._result_image,
                            origin=(0, 0),
                            region=shape)
            return result


class ArtifactLine(Base):
    def __init__(self, image_width, image_height, gl_image=None):
        super().__init__(
            image_width, image_height,
            os.path.join(os.path.dirname(__file__),
                         'filtered_line_artifact.cl'),
            gl_image=gl_image)

    def __call__(self,
                 line_x: float,
                 line_y: float,
                 line_angle: float,
                 artifact_size: int,
                 filter_radius: float,
                 filter_noise: float,
                 filter_samples: float,
                 filter_radius_noise: float,
                 image_angle: float,
                 image_samples: int,
                 result: np.array = None):
        shape = self._result_image.shape
        is_gl_texture = hasattr(self._result_image, 'gl_object')

        if is_gl_texture:
            cl.enqueue_acquire_gl_objects(command_queue, [self._result_image])
        self._program.filtered_line_artifact(command_queue, shape, (1, 1),
                                             np.uint32(shape[1]),
                                             np.uint32(shape[0]),
                                             np.uint32(artifact_size),
                                             np.float32(line_x),
                                             np.float32(line_y),
                                             np.float32(line_angle),
                                             np.float32(filter_radius),
                                             np.float32(filter_noise),
                                             np.float32(filter_samples),
                                             np.float32(filter_radius_noise),
                                             np.float32(image_angle),
                                             np.uint32(image_samples),
                                             self._result_image)
        if is_gl_texture:
            cl.enqueue_release_gl_objects(command_queue, [self._result_image])

        if result is not None:
            cl.enqueue_copy(command_queue,
                            result,
                            self._result_image,
                            origin=(0, 0),
                            region=shape)
            return result
