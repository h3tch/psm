#pragma once
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

const double pi = 3.141592653589793238462643383279502884197169399375;

// returns the positive root of intersection of line y = h with circle
// centered at the origin and radius r
template <typename real_t>
inline real_t horizontal_line_circle_intersection(const real_t h,
                                                    const real_t r)
{
    return h < r ? std::sqrt(r * r - h * h) : 0;
}

// indefinite integral of circle segment
template <typename real_t>
inline real_t
    circle_segment_area(const real_t x, const real_t h, const real_t r)
{
    return 0.5
            * (std::sqrt(1 - x * x / (r * r)) * x * r
                + r * r * std::asin(x / r) - 2 * h * x);
}

// area of intersection of an infinitely tall box with left edge at x0,
// right edge at x1, bottom edge at h and top edge at infinity, with circle
// centered at the origin with radius r
template <typename real_t>
inline real_t infinit_box_centered_circle_area(const real_t x0,
                                                const real_t x1,
                                                const real_t h,
                                                const real_t r)
{
    const auto x = horizontal_line_circle_intersection(h, r);
    const auto a0 =
        circle_segment_area(std::max(-x, std::min(x, x0)), h, r);
    const auto a1 =
        circle_segment_area(std::max(-x, std::min(x, x1)), h, r);
    return a1 - a0;
}

// area of the intersection of a finite box with
// a circle centered at the origin with radius r
template <typename real_t>
inline real_t box_centered_circle_area(const real_t x0,
                                        const real_t x1,
                                        const real_t y0,
                                        const real_t y1,
                                        const real_t r)
{
    if (y0 < 0) {
        if (y1 < 0)
            // the box is completely under, just flip it above and try again
            return box_centered_circle_area(x0, x1, -y1, -y0, r);
        // the box is both above and below, divide it to two boxes and go
        // again
        const auto a0 = box_centered_circle_area(x0, x1, real_t(0), -y0, r);
        const auto a1 = box_centered_circle_area(x0, x1, real_t(0), y1, r);
        return a0 + a1;
    }
    // area of the lower box minus area of the higher box
    const auto a0 = infinit_box_centered_circle_area(x0, x1, y0, r);
    const auto a1 = infinit_box_centered_circle_area(x0, x1, y1, r);
    return a0 - a1;
}

// area of the intersection of a general box with a general circle
template <typename real_t>
inline real_t box_circle_area(const real_t x0,
                                const real_t x1,
                                const real_t y0,
                                const real_t y1,
                                const real_t cx,
                                const real_t cy,
                                const real_t r)
{
    return box_centered_circle_area(x0 - cx, x1 - cx, y0 - cy, y1 - cy, r);
}

} // namespace psm