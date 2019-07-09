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
    template <typename real_t, typename T>
    inline std::tuple<real_t, real_t> rotate(const real_t* sincos,
                                             const real_t cx,
                                             const real_t cy,
                                             const T x,
                                             const T y)
    {
        const real_t tmp_x = x - cx;
        const real_t tmp_y = y - cy;
        return std::make_tuple(sincos[1] * tmp_x - sincos[0] * tmp_y + cx,
                               sincos[0] * tmp_x + sincos[1] * tmp_y + cy);
    }


    template <typename real_t>
    inline real_t rasterize(const ssize_t raster_size, const real_t value)
    {
        return ssize_t(value / raster_size) * raster_size
               - (value < 0 ? raster_size : 0) + raster_size * 0.5;
    }


    template <typename return_t, typename real_t>
    inline return_t filter(const real_t center_x,
                           const real_t center_y,
                           const real_t line_x,
                           const real_t line_y,
                           const real_t line_angle,
                           const ssize_t artifact_size,
                           const real_t filter_x,
                           const real_t filter_y,
                           const real_t filter_radius,
                           const size_t angle_samples)
    {
        real_t fx, fy, lx, ly, sx, sy;

        const auto R = ssize_t(filter_radius + 0.5);
        const real_t maxR = filter_radius + artifact_size;
        const auto c0 = ssize_t(filter_x - R);
        const auto c1 = ssize_t(filter_x + R);
        const auto r0 = ssize_t(filter_y - R);
        const auto r1 = ssize_t(filter_y + R);
        const auto minimum = std::numeric_limits<return_t>::min();
        const auto maximum = std::numeric_limits<return_t>::max();

        size_t sum = 0;
        real_t summed_area = 0;

        for (size_t a = 1; a <= angle_samples; ++a) {
            const real_t offset = pi / (2 * a);
            const real_t sincos_offset[] = {std::sin(offset), std::cos(offset)};
            const real_t angle = line_angle - offset;
            const real_t line_vector_x = std::cos(angle);
            const real_t line_vector_y = std::sin(angle);

            std::tie(fx, fy) =
                rotate(sincos_offset, center_x, center_y, filter_x, filter_y);
            std::tie(lx, ly) =
                rotate(sincos_offset, center_x, center_y, line_x, line_y);

            const real_t ld = lx * line_vector_x - ly * line_vector_y;
            const real_t fd = fx * line_vector_x - fy * line_vector_y;
            if (fd - maxR > ld)
                return minimum;
            if (fd + maxR < ld)
                return maximum;

            for (ssize_t sample_y = r0; sample_y <= r1; ++sample_y) {
                for (ssize_t sample_x = c0; sample_x <= c1; ++sample_x) {
                    std::tie(sx, sy) = rotate(
                        sincos_offset, center_x, center_y, sample_x, sample_y);

                    const auto area = filter_radius == 0
                                          ? 1
                                          : box_circle_area(sx - 0.5,
                                                            sx + 0.5,
                                                            sy - 0.5,
                                                            sy + 0.5,
                                                            fx,
                                                            fy,
                                                            filter_radius);

                    const real_t raster_sx = rasterize(artifact_size, sx);
                    const real_t raster_sy = rasterize(artifact_size, sy);

                    const real_t d =
                        raster_sx * line_vector_x - raster_sy * line_vector_y;

                    sum += area * (d <= ld ? maximum : minimum);
                    summed_area += area;
                }
            }
        }
        return return_t(sum / summed_area + 0.5);
    }

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
                      const pixel_t filter_noise,
                      const pixel_t bg_noise,
                      const size_t angle_samples,
                      const real_t image_angle)
{
    typedef typename std::make_signed<pixel_t>::type spixel_t;

    std::random_device rd;
    std::mt19937 generator(rd());
    std::uniform_int_distribution<spixel_t> random_filter_noise(-filter_noise,
                                                                filter_noise);
    std::uniform_int_distribution<spixel_t> random_bg_noise(-bg_noise,
                                                            bg_noise);

    image_t<pixel_t> result(height, width);
    const auto max_value = std::numeric_limits<pixel_t>::max();

    real_t filter_x, filter_y, random_line_x, random_line_y;
    const auto center_x = width * 0.5;
    const auto center_y = height * 0.5;
    const real_t sincos[] = {std::sin(image_angle), std::cos(image_angle)};
    std::tie(random_line_x, random_line_y) =
        rotate(sincos, center_x, center_y, line_x, line_y);

    for (ssize_t r = 0; r < (ssize_t)height; ++r) {
        for (ssize_t c = 0; c < (ssize_t)width; ++c) {
            std::tie(filter_x, filter_y) =
                rotate(sincos, center_x, center_y, (real_t)c, (real_t)r);

            const pixel_t s = filter<pixel_t>(center_x,
                                              center_y,
                                              line_x,
                                              line_y,
                                              line_angle,
                                              (ssize_t)artifact_size,
                                              filter_x,
                                              filter_y,
                                              radius,
                                              angle_samples);

            auto noise = 0 < s && s < max_value ? random_filter_noise(generator) : 0;
            noise += s < 32 || max_value - 32 < s ? random_bg_noise(generator) : 0;

            if (noise < 0) {
                const auto n_ = -noise;
                result(r, c) = s - (n_ > s ? s : n_);
            } else {
                const auto s_ = max_value - s;
                result(r, c) = s + (noise > s_ ? s_ : noise);
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