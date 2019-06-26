#pragma once
#include "box.hpp"
#include <Eigen/Dense>
#include <cmath>
#include <cstddef>
#include <limits>
#include <random>
#include <utility>

namespace psm {

using std::size_t;

template <typename T>
using scalar_t = typename T::Scalar;

template <typename T>
using image_t = Eigen::Matrix<T, -1, -1, Eigen::RowMajor>;

const double pi = 3.14159265358979323846;

template <typename pixel_t, typename real_t>
inline pixel_t line_sample(const real_t nx,
                           const real_t ny,
                           const real_t d,
                           const size_t artifact_size,
                           const size_t x,
                           const size_t y)
{
    const auto minimum = std::numeric_limits<pixel_t>::min();
    const auto maximum = std::numeric_limits<pixel_t>::max() / 2;
    const auto c = (x / artifact_size) * artifact_size;
    const auto r = (y / artifact_size) * artifact_size;

    const real_t x2 = (ssize_t)(std::cos(pi / 4) * x - std::sin(pi / 4) * y);
    const real_t y2 = (ssize_t)(std::sin(pi / 4) * x + std::cos(pi / 4) * y);

    real_t x2_, y2_;
    if (x2 < 0) {
        x2_ = -(((artifact_size - x2) / artifact_size) * artifact_size
                + artifact_size * 0.5);
    } else {
        x2_ = (x2 / artifact_size) * artifact_size + artifact_size * 0.5;
    }
    if (y2 < 0) {
        y2_ = -(((artifact_size - y2) / artifact_size) * artifact_size
                + artifact_size * 0.5);
    } else {
        y2_ = (y2 / artifact_size) * artifact_size + artifact_size * 0.5;
    }

    const auto c2 = std::cos(-pi / 4) * x2_ - std::sin(-pi / 4) * y2_;
    const auto r2 = std::sin(-pi / 4) * x2_ + std::cos(-pi / 4) * y2_;

    return (c * nx + r * ny >= d ? maximum : minimum)
           + (c2 * nx + r2 * ny >= d ? maximum : minimum);
}

template <typename pixel_t, typename real_t>
image_t<pixel_t> line(const size_t width,
                      const size_t height,
                      const real_t x,
                      const real_t y,
                      const real_t angle,
                      const size_t artifact_size)
{
    const real_t nx = -std::sin(angle);
    const real_t ny = std::cos(angle);
    const real_t d = x * nx + y * ny;

    image_t<pixel_t> result(height, width);

    for (size_t r = 0; r < height; ++r) {
        for (size_t c = 0; c < width; ++c)
            result(r, c) = line_sample<pixel_t>(nx, ny, d, artifact_size, c, r);
    }

    return result;
}

} // namespace psm