// #include "box_circle_area.cl" // box_circle_area
#include "image_rotation.cl" // rotate_point_arround_image_center
#include "rasterize.cl" // rasterize, rasterize_line_y
// indefinite integral of circle segment

float _circle_segment_area(const float x, const float y, const float r, const float r2)
{
    return 0.5 * (sqrt(1.0 - x * x / r2) * x * r + r2 * asin(x / r) - 2.0 * y * x);
}

// area of intersection of an infinitely tall box with left edge at x0,
// right edge at x1, bottom edge at h and top edge at infinity, with circle
// centered at the origin with radius r
float _infinit_box_centered_circle_area(const float x0,
                                         const float x1,
                                         const float y,
                                         const float r)
{
    const float r2 = r * r;
    const float x = sqrt(r2 - y * y);
    const float a0 = _circle_segment_area(min(max(x0, -x), x), y, r, r2);
    const float a1 = _circle_segment_area(min(max(x1, -x), x), y, r, r2);
    return a1 - a0;
}

float _segment_area(const float segment_height, const float chord_length)
{
    const float result = segment_height * ((2.0f / 3.0f) * chord_length
        + segment_height * segment_height / (2.0f * chord_length));
    return isfinite(result) ? result : 0.0f;
}

float _excess_area(float x, const float y, const float max_x, const float radius, const float radius2)
{
    x = min(x, max_x);
    const float circle_y = sqrt(radius2 - x * x);

    const float x_segment_area = _segment_area(radius - x, 2.0f * circle_y);
    const float max_x_segment_area = _segment_area(radius - max_x, 2.0f * y);
    const float rect_area = (max_x - x) * y;
    return (x_segment_area - max_x_segment_area) / 2.0f - rect_area;
}

float estimate_circle_interval_area(const float x0,
                                   const float x1,
                                   const float radius,
                                   const float radius2)
{
    float left_area = _segment_area(radius - min(fabs(x0), radius), 2.0f * sqrt(radius2 - x0 * x0));
    float right_area = _segment_area(radius - min(fabs(x1), radius), 2.0f * sqrt(radius2 - x1 * x1));
    const float circle_area = (19.0f / 6.0f) * radius2;

    if (x0 > 0.0f)
        left_area = circle_area - left_area;
    if (x1 < 0.0f)
        right_area = circle_area - right_area;

    return max(circle_area - left_area - right_area, 0.0f);
}

float estimate_circle_segment_area(float x0,
                                   float x1,
                                   float y,
                                   const float radius,
                                   const float radius2)
{
    y = min(y, radius);
    const float max_x = sqrt(radius2 - y * y);

    const float segment_area = _segment_area(radius - y, 2.0f * max_x);

    float left_area = _excess_area(fabs(x0), y, max_x, radius, radius2);
    if (x0 > 0.0f)
        left_area = segment_area - left_area;

    float right_area = _excess_area(fabs(x1), y, max_x, radius, radius2);
    if (x1 < 0.0f)
        right_area = segment_area - right_area;

    return max(segment_area - left_area - right_area, 0.0f);
}

float filter_line(const float line_x,
                   const float line_y,
                   const float line_angle,
                   const float artifact_size,
                   const float filter_x,
                   const float filter_y,
                   const float filter_radius)
{
    const float maxR = filter_radius + artifact_size;
    const float line_nx = -sin(line_angle);
    const float line_ny = cos(line_angle);
    const float line_d = line_x * line_nx + line_y * line_ny;
    const float filter_d = filter_x * line_nx + filter_y * line_ny;
    if (filter_d - maxR > line_d)
        return 0.0f;
    if (filter_d + maxR < line_d)
        return 1.0f;

    const float k = -line_nx / line_ny;
    const float d = line_y - k * line_x;
    const float pixel_center_shift = filter_x + artifact_size * 0.5;

    float c0 = rasterize(artifact_size, filter_x - filter_radius) - filter_x;
    const float filter_radius2 = filter_radius * filter_radius;

    if (filter_radius <= 0.0f) {
        const float r1 =
            rasterize_line_y(artifact_size, k, d, c0 + pixel_center_shift) - filter_y;
        return r1 < 0.0f ? 0.0f : 1.0f;
    }

    float area = 0.0f;
    while (c0 <= filter_radius) {
        const float c1 = c0 + artifact_size;
        const float r1 =
            rasterize_line_y(artifact_size, k, d, c0 + pixel_center_shift) - filter_y;
        float a = estimate_circle_segment_area(c0, c1, fabs(r1), filter_radius, filter_radius2);
        if (r1 > 0)
            a = estimate_circle_interval_area(c0, c1, filter_radius, filter_radius2) - a;
        area += a;
        c0 = c1;
    }

    const float circle_area = (19.0f / 6.0f) * filter_radius2;
    return min(max(area / circle_area, 0.0f), 1.0f);
}

__kernel void filtered_line_artifact(const unsigned int width,
                                     const unsigned int height,
                                     const unsigned int artifact_size,
                                     const float line_x,
                                     const float line_y,
                                     const float line_angle,
                                     const float filter_radius,
                                     const float image_angle,
                                     __write_only image2d_t result)
{
    const int col = get_global_id(0);
    const int row = get_global_id(1);

    float filter_x = (float)col;
    float filter_y = (float)row;

    rotate_point_arround_image_center(
        width, height, image_angle, &filter_x, &filter_y);

    const float color = filter_line((float)line_x,
                                    (float)line_y,
                                    (float)line_angle,
                                    (float)artifact_size,
                                    (float)filter_x,
                                    (float)filter_y,
                                    (float)filter_radius);

    write_imagef(result, (int2)(col, row), (float4)(color, color, color, 1.0f));
}