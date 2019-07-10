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
        const auto result = real_t(ssize_t(value / raster_size) * raster_size);
        return result <= value ? result : result - raster_size;
    }


    template <typename real_t>
    inline real_t rasterize_line_y(const ssize_t artifact_size,
                                   const real_t k,
                                   const real_t d,
                                   const real_t x)
    {
        const auto y = k * x + d;
        const auto y0 = rasterize(artifact_size, y);
        return y - y0 < artifact_size * 0.5 ? y0 : y0 + artifact_size;
    }

    template <typename real_t>
    inline real_t clip(const real_t value, const real_t min, const real_t max)
    {
        return std::min(std::max(value, min), max);
    }


    template <typename real_t>
    inline real_t filter_line(const real_t line_x,
                              const real_t line_y,
                              const real_t line_nx,
                              const real_t line_ny,
                              const ssize_t artifact_size,
                              const real_t filter_x,
                              const real_t filter_y,
                              const real_t filter_radius)
    {
        const real_t maxR = filter_radius + artifact_size;
        const real_t ld = line_x * line_nx + line_y * line_ny;
        const real_t fd = filter_x * line_nx + filter_y * line_ny;
        if (fd - maxR > ld)
            return 0;
        if (fd + maxR < ld)
            return 1;

        const auto k = -line_nx / line_ny;
        const auto d = line_y - k * line_x;
        const real_t pixel_center_shift = artifact_size * 0.5;

        auto c0 = rasterize(artifact_size, filter_x - filter_radius);
        const auto r0 = filter_y - filter_radius;

        if (filter_radius <= 0) {
            const auto c1 = c0 + artifact_size;
            const auto r1 =
                rasterize_line_y(artifact_size, k, d, c0 + pixel_center_shift);
            return c0 <= filter_x && filter_x < c1 && r0 <= filter_y
                           && filter_y < r1
                       ? 1.0
                       : 0.0;
        }

        real_t area = 0.0;
        while (c0 <= filter_x + filter_radius) {
            const auto c1 = c0 + artifact_size;
            const auto r1 =
                rasterize_line_y(artifact_size, k, d, c0 + pixel_center_shift);
            area += box_circle_area(
                c0, c1, r0, r1, filter_x, filter_y, filter_radius);
            c0 = c1;
        }

        const auto circle_area = filter_radius * filter_radius * pi;
        return clip(area / circle_area, 0.0, 1.0);
    }


    // template <typename return_t, typename real_t>
    // inline return_t filter(const real_t center_x,
    //                        const real_t center_y,
    //                        const real_t line_x,
    //                        const real_t line_y,
    //                        const real_t line_angle,
    //                        const ssize_t artifact_size,
    //                        const real_t filter_x,
    //                        const real_t filter_y,
    //                        const real_t filter_radius,
    //                        const size_t angle_samples)
    // {
    //     real_t fx, fy, lx, ly, sx, sy;

    //     const auto R = ssize_t(filter_radius + 0.5);
    //     const real_t maxR = filter_radius + artifact_size;
    //     const auto c0 = ssize_t(filter_x - R);
    //     const auto c1 = ssize_t(filter_x + R);
    //     const auto r0 = ssize_t(filter_y - R);
    //     const auto r1 = ssize_t(filter_y + R);
    //     const auto minimum = std::numeric_limits<return_t>::min();
    //     const auto maximum = std::numeric_limits<return_t>::max();

    //     size_t sum = 0;
    //     real_t summed_area = 0;

    //     for (size_t a = 1; a <= angle_samples; ++a) {
    //         const real_t offset = pi / (2 * a);
    //         const real_t sincos_offset[] = {std::sin(offset), std::cos(offset)};
    //         const real_t angle = line_angle - offset;
    //         const real_t line_vector_x = std::cos(angle);
    //         const real_t line_vector_y = std::sin(angle);

    //         std::tie(fx, fy) =
    //             rotate(sincos_offset, center_x, center_y, filter_x, filter_y);
    //         std::tie(lx, ly) =
    //             rotate(sincos_offset, center_x, center_y, line_x, line_y);

    //         const real_t ld = lx * line_vector_x - ly * line_vector_y;
    //         const real_t fd = fx * line_vector_x - fy * line_vector_y;
    //         if (fd - maxR > ld)
    //             return minimum;
    //         if (fd + maxR < ld)
    //             return maximum;

    //         for (ssize_t sample_y = r0; sample_y <= r1; ++sample_y) {
    //             for (ssize_t sample_x = c0; sample_x <= c1; ++sample_x) {
    //                 std::tie(sx, sy) = rotate(
    //                     sincos_offset, center_x, center_y, sample_x, sample_y);

    //                 const auto area = filter_radius == 0
    //                                       ? 1
    //                                       : box_circle_area(sx - 0.5,
    //                                                         sx + 0.5,
    //                                                         sy - 0.5,
    //                                                         sy + 0.5,
    //                                                         fx,
    //                                                         fy,
    //                                                         filter_radius);

    //                 const real_t raster_sx = rasterize(artifact_size, sx);
    //                 const real_t raster_sy = rasterize(artifact_size, sy);

    //                 const real_t d =
    //                     raster_sx * line_vector_x - raster_sy * line_vector_y;

    //                 sum += area * (d < ld ? maximum : minimum);
    //                 summed_area += area;
    //             }
    //         }
    //     }
    //     return return_t(sum / summed_area + 0.5);
    // }
} // namespace

template <typename pixel_t, typename real_t>
image_t<pixel_t> disk(const size_t width,
                      const size_t height,
                      const real_t line_x,
                      const real_t line_y,
                      const real_t line_angle,
                      const size_t artifact_size,
                      const real_t filter_radius,
                      const pixel_t filter_noise,
                    //   const pixel_t bg_noise,
                    //   const size_t angle_samples,
                      const real_t image_angle)
{
    typedef typename std::make_signed<pixel_t>::type spixel_t;

    std::random_device rd;
    std::mt19937 generator(rd());
    std::uniform_int_distribution<spixel_t> random_filter_noise(-filter_noise,
                                                                filter_noise);

    image_t<pixel_t> result(height, width);
    // const auto max_value = std::numeric_limits<pixel_t>::max();

    real_t filter_x, filter_y;
    const auto center_x = width * 0.5;
    const auto center_y = height * 0.5;
    const auto line_nx = -std::sin(line_angle);
    const auto line_ny = std::cos(line_angle);
    const real_t sincos[] = {std::sin(image_angle), std::cos(image_angle)};

    const auto minimum = std::numeric_limits<pixel_t>::min();
    const auto maximum = std::numeric_limits<pixel_t>::max();

    for (ssize_t r = 0; r < (ssize_t)height; ++r) {
        for (ssize_t c = 0; c < (ssize_t)width; ++c) {
            std::tie(filter_x, filter_y) =
                rotate(sincos, center_x, center_y, (real_t)c, (real_t)r);

            // const pixel_t s = filter<pixel_t>(center_x,
            //                                   center_y,
            //                                   line_x,
            //                                   line_y,
            //                                   line_angle,
            //                                   (ssize_t)artifact_size,
            //                                   filter_x,
            //                                   filter_y,
            //                                   filter_radius,
            //                                   angle_samples);
            const auto s = pixel_t(0.5 + minimum + maximum
                                         * filter_line(line_x,
                                                       line_y,
                                                       line_nx,
                                                       line_ny,
                                                       artifact_size,
                                                       filter_x,
                                                       filter_y,
                                                       filter_radius));

            if (minimum < s && s < maximum) {
                const auto noise = random_filter_noise(generator);

                if (noise < 0) {
                    const auto n_ = -noise;
                    result(r, c) = s - (n_ > s ? s : n_);
                } else {
                    const auto s_ = maximum - s;
                    result(r, c) = s + (noise > s_ ? s_ : noise);
                }
            } else {
                result(r, c) = s;
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