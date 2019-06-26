#include "generate.hpp"
#include <vps_py.h>


extern "C" PyObject* line(long width,
                          long height,
                          double line_x,
                          double line_y,
                          double line_angle,
                          long artifact_size)
{
    PyGIL lock;

    try {
        auto result = psm::line<uint8_t>(
            width, height, line_x, line_y, line_angle, artifact_size);
        return vps_py::py_object(result);
    } catch (...) {
        return exception2py();
    }
    return nullptr;
}


MOD_INIT(generate, 0)