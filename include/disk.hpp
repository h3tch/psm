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
    inline real_t estimate_circle_area(const real_t radius)
    {
        return (19.0 / 6.0) * radius * radius;
    }


    template <typename real_t>
    inline real_t estimate_circle_segment_area(const real_t radius,
                                               const real_t distance)
    {
        if (distance > radius)
            return estimate_circle_area(radius);

        if (distance < -radius)
            return 0.0;

        const auto segment_height = radius - std::abs(distance);
        const auto chord_length =
            2.0 * std::sqrt(radius * radius - distance * distance);
        const auto segment_area =
            segment_height
            * ((2.0 / 3.0) * chord_length
               + segment_height * segment_height / (2.0 * chord_length));

        return distance > 0 ? estimate_circle_area(radius) - segment_area
                            : segment_area;
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
} // namespace

template <typename pixel_t, typename real_t>
image_t<pixel_t> artifact_line(const size_t width,
                               const size_t height,
                               const real_t line_x,
                               const real_t line_y,
                               const real_t line_angle,
                               const size_t artifact_size,
                               const real_t filter_radius,
                               const pixel_t filter_noise,
                               const real_t image_angle)
{
    typedef typename std::make_signed<pixel_t>::type spixel_t;

    std::random_device rd;
    std::mt19937 generator(rd());
    std::uniform_int_distribution<spixel_t> random_filter_noise(-filter_noise,
                                                                filter_noise);

    image_t<pixel_t> result(height, width);

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

            const auto s = pixel_t(0.5 + minimum
                                   + maximum
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


template <typename pixel_t, typename real_t>
image_t<pixel_t> line(const size_t width,
                      const size_t height,
                      const real_t line_x,
                      const real_t line_y,
                      const real_t line_angle,
                      const real_t filter_radius,
                      const pixel_t filter_noise,
                      const real_t image_angle)
{
    typedef typename std::make_signed<pixel_t>::type spixel_t;

    std::random_device rd;
    std::mt19937 generator(rd());
    std::uniform_int_distribution<spixel_t> random_filter_noise(-filter_noise,
                                                                filter_noise);

    image_t<pixel_t> result(height, width);

    real_t filter_x, filter_y;
    const auto center_x = width * 0.5;
    const auto center_y = height * 0.5;
    const auto line_nx = -std::sin(line_angle);
    const auto line_ny = std::cos(line_angle);
    const auto line_d = line_nx * line_x + line_ny * line_y;
    const real_t sincos[] = {std::sin(image_angle), std::cos(image_angle)};

    const auto minimum = std::numeric_limits<pixel_t>::min();
    const auto maximum = std::numeric_limits<pixel_t>::max();

    const auto circle_area = estimate_circle_area(filter_radius);

    for (ssize_t r = 0; r < (ssize_t)height; ++r) {
        for (ssize_t c = 0; c < (ssize_t)width; ++c) {
            std::tie(filter_x, filter_y) =
                rotate(sincos, center_x, center_y, (real_t)c, (real_t)r);

            const auto filter_d = line_nx * filter_x + line_ny * filter_y;
            const auto distance = line_d - filter_d;
            const auto segment_area =
                estimate_circle_segment_area(filter_radius, distance);

            const auto color =
                pixel_t(0.5 + minimum + maximum * (segment_area / circle_area));

            if (minimum < color && color < maximum) {
                const auto noise = random_filter_noise(generator);

                if (noise < 0) {
                    const auto n_ = -noise;
                    result(r, c) = color - (n_ > color ? color : n_);
                } else {
                    const auto inv_color = maximum - color;
                    result(r, c) =
                        color + (noise > inv_color ? inv_color : noise);
                }
            } else {
                result(r, c) = color;
            }
        }
    }

    return result;
}
} // namespace psm