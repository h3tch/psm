#pragma once
#include "box.hpp"
#include "generate.hpp"
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

namespace {
    template <typename return_t, typename real_t>
    inline return_t filter(const real_t center_x,
                           const real_t center_y,
                           const real_t line_x,
                           const real_t line_y,
                           const real_t line_angle,
                           const ssize_t artifact_size,
                           const ssize_t r0,
                           const ssize_t r1,
                           const ssize_t c0,
                           const ssize_t c1,
                           const ssize_t c,
                           const ssize_t r,
                           const real_t radius,
                           const size_t angle_samples)
    {
        size_t s = 0;
        real_t A = 0;
        const auto minimum = std::numeric_limits<return_t>::min();
        const auto maximum = std::numeric_limits<return_t>::max();

        for (size_t angle_sample = 1; angle_sample <= angle_samples;
             ++angle_sample) {
            const real_t angle = pi / (2 * angle_sample);
            const real_t cos = std::cos(angle);
            const real_t sin = std::sin(angle);

            const real_t c_ = cos * (c - center_x) - sin * (r - center_y);
            const real_t r_ = sin * (c - center_x) + cos * (r - center_y);

            const real_t lx_ =
                (line_x - center_x) * cos - (line_y - center_y) * sin;
            const real_t ly_ =
                (line_x - center_x) * sin + (line_y - center_y) * cos;

            const real_t alpha = line_angle - angle;

            const real_t ld_ = lx_ * std::cos(alpha) - ly_ * std::sin(alpha);

            for (ssize_t j = r0; j <= r1; ++j) {
                for (ssize_t i = c0; i <= c1; ++i) {
                    const ssize_t i_ =
                        ssize_t(cos * (i - center_x) - sin * (j - center_y));
                    const ssize_t j_ =
                        ssize_t(sin * (i - center_x) + cos * (j - center_y));

                    const auto a = box_circle_area(
                        i_ - 0.5, i_ + 0.5, j_ - 0.5, j_ + 0.5, c_, r_, radius);

                    const real_t x2_ = (i_ < 0 ? -1 : 1) * ((i_ < 0 ? artifact_size-i_ : i_) / artifact_size) * artifact_size;
                    const real_t y2_ = (j_ < 0 ? -1 : 1) * ((j_ < 0 ? artifact_size-j_ : j_) / artifact_size) * artifact_size;

                    const real_t d_ =
                        x2_ * std::cos(alpha) - y2_ * std::sin(alpha);

                    s += a * (d_ <= ld_ ? maximum : minimum);
                    A += a;
                }
            }
        }
        return return_t(s / A + 0.5);
    }

    // template <typename return_t, typename image_t, typename real_t>
    // inline return_t filter(const image_t& image,
    //                        const size_t r0,
    //                        const size_t r1,
    //                        const size_t c0,
    //                        const size_t c1,
    //                        const size_t c,
    //                        const size_t r,
    //                        const real_t radius)
    // {
    //     return_t s = 0;
    //     real_t A = 0;
    //     for (auto j = r0; j < r1; ++j) {
    //         for (auto i = c0; i < c1; ++i) {
    //             const auto a = box_circle_area(
    //                 i - 0.5, i + 0.5, j - 0.5, j + 0.5, c, r, radius);
    //             s += image(j, i) * a;
    //             A += a;
    //         }
    //     }
    //     return return_t(s / A + 0.5);
    // }

    template <typename real_t>
    inline real_t clip(const real_t value, const real_t min, const real_t max)
    {
        return std::min(std::max(value, min), max);
    }
} // namespace

template <typename pixel_t, typename real_t>
image_t<pixel_t> disk(const size_t width,
                      const size_t height,
                      const real_t line_x,
                      const real_t line_y,
                      const real_t line_angle,
                      const size_t artifact_size,
                      const real_t radius,
                      const pixel_t noise,
                      const size_t angle_samples)
{
    typedef typename std::make_signed<pixel_t>::type spixel_t;

    std::random_device rd;
    std::mt19937 generator(rd());
    std::uniform_int_distribution<spixel_t> random_noise(-noise, noise);

    image_t<pixel_t> result(height, width);
    const auto max_value = std::numeric_limits<pixel_t>::max();
    const auto R = ssize_t(radius + 0.5);

    const auto center_x = width * 0.5;
    const auto center_y = height * 0.5;
    // const auto nx = -std::sin(line_angle);
    // const auto ny = std::cos(line_angle);
    // const auto d = line_x * nx + line_y * ny;

    for (ssize_t r = 0; r < (ssize_t)height; ++r) {
        for (ssize_t c = 0; c < (ssize_t)width; ++c) {
            const pixel_t s = filter<pixel_t>(center_x,
                                              center_y,
                                              line_x,
                                              line_y,
                                              line_angle,
                                              (ssize_t)artifact_size,
                                              r - R,
                                              r + R,
                                              c - R,
                                              c + R,
                                              c,
                                              r,
                                              radius,
                                              angle_samples);
            result(r, c) = s;

            if (0 < s && s < max_value) {
                const auto n = random_noise(generator);

                if (n < 0) {
                    const auto n_ = -n;
                    result(r, c) -= n_ > s ? s : n_;
                } else {
                    const auto s_ = max_value - s;
                    result(r, c) += n > s_ ? s_ : n;
                }
            }
        }
    }

    return result;
}

// template <typename image_t, typename real_t>
// image_t disk(const image_t& image,
//              const real_t radius,
//              const scalar_t<image_t> noise)
// {
//     typedef scalar_t<image_t> pixel_t;
//     typedef typename std::make_signed<pixel_t>::type spixel_t;

//     std::random_device rd;
//     std::mt19937 generator(rd());
//     std::uniform_int_distribution<spixel_t> random_noise(-noise, noise);

//     image_t result(image.rows(), image.cols());
//     const auto max_value = std::numeric_limits<pixel_t>::max();
//     const auto R = size_t(radius + 0.5);
//     const auto width = (size_t)image.cols();
//     const auto height = (size_t)image.rows();

//     for (size_t r = 0; r < height; ++r) {
//         const size_t r0 = R > r ? 0 : r - R;
//         const size_t r1 = std::min(r + R + 1, height);

//         for (size_t c = 0; c < width; ++c) {
//             const size_t c0 = R > c ? 0 : c - R;
//             const size_t c1 = std::min(c + R + 1, width);

//             const pixel_t s =
//                 filter<size_t>(image, r0, r1, c0, c1, c, r, radius);
//             result(r, c) = s;

//             if (s != image(r, c)) {
//                 const auto n = random_noise(generator);

//                 if (n < 0) {
//                     const auto n_ = -n;
//                     result(r, c) -= n_ > s ? s : n_;
//                 } else {
//                     const auto s_ = max_value - s;
//                     result(r, c) += n > s_ ? s_ : n;
//                 }
//             }
//         }
//     }

//     return result;
// }
} // namespace psm