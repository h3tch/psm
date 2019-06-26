import os
import numpy as np

import vps_py.cpp
import psm


extra_args = ['-O0', '-g']

external = vps_py.cpp.fn(
    name='generate',
    dst_path=psm.info.bin_dir,
    sources=[os.path.join(psm.info.src_dir, 'py', 'generate.cpp')],
    include_dirs=psm.info.include_dirs,
    extra_compile_args=extra_args,
    extra_link_args=extra_args
)


@external
def line(width: int,
         height: int,
         cx: float,
         cy: float,
         angle: float,
         artifact_size: int
         ) -> object:
    alpha = np.deg2rad(angle)
    nx = -np.sin(alpha)
    ny = np.cos(alpha)

    X, Y = np.meshgrid(np.arange(-cx, width - cx, 1),
                       np.arange(-cy, height - cy, 1))

    line_y = X * nx + Y * ny

    return (255 * (line_y >= 0)).astype(np.uint8)
