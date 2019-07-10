#include "disk.hpp"
#include <Eigen/Dense>
#include <vps_py.h>


template <typename T>
using Image = Eigen::Matrix<T, -1, -1, Eigen::RowMajor>;


template <typename T>
PyObject* npy_disk(const size_t width,
                   const size_t height,
                   const double line_x,
                   const double line_y,
                   const double line_angle,
                   const size_t artifact_size,
                   const double radius,
                   const int filter_noise,
                //    const int bg_noise,
                //    const size_t angle_samples,
                   const double image_angle)
{
    auto result = psm::disk(width,
                            height,
                            line_x,
                            line_y,
                            line_angle,
                            artifact_size,
                            radius,
                            (T)filter_noise,
                            // (T)bg_noise,
                            // angle_samples,
                            image_angle);
    return vps_py::py_object(result);
}


extern "C" PyObject* disk(long width,
                          long height,
                          double line_x,
                          double line_y,
                          double line_angle,
                          long artifact_size,
                          double radius,
                          long filter_noise,
                        //   long bg_noise,
                        //   long angle_samples,
                          double image_angle)
{
    PyGIL lock;

    try {
        return npy_disk<uint8_t>((size_t)width,
                                 (size_t)height,
                                 line_x,
                                 line_y,
                                 line_angle,
                                 (size_t)artifact_size,
                                 radius,
                                 (int)filter_noise,
                                //  (int)bg_noise,
                                //  (size_t)angle_samples,
                                 image_angle);
    } catch (...) {
        return exception2py();
    }
    return nullptr;
}


// template <typename T>
// PyObject* npy_disk(PyObject* image, double radius, int noise)
// {
//     const Image<T> tmp = vps_py::Map<Image<T>>(image);
//     auto result = psm::disk(tmp, radius, (T)noise);
//     return vps_py::py_object(result);
// }


// extern "C" PyObject* disk(PyObject* image, double radius, long noise)
// {
//     PyGIL lock;

//     try {
//         EXCEPTION_IF(vps_py::get_type(image) != NPY_UINT8,
//                      "Only uint8 images are supported.");
//         return npy_disk<uint8_t>(image, radius, (int)noise);
//     } catch (...) {
//         return exception2py();
//     }
//     return nullptr;
// }


MOD_INIT(filter, 0)