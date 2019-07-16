#include "image_rotation.cl" // rotate_point_arround_image_center, rotate_point

float _segment_area(const float segment_height, const float chord_length)
{
    const float result = segment_height * ((2.0f / 3.0f) * chord_length
        + segment_height * segment_height / (2.0f * chord_length));
    return isfinite(result) ? result : 0.0f;
}

float estimate_circle_area(const float radius)
{
    return (19.0f / 6.0f) * radius * radius;
}

float estimate_circle_segment_area(const float radius,
                                   const float distance,
                                   const float circle_area)
{
    if (distance > radius)
        return circle_area;

    if (distance < -radius)
        return 0.0f;

    const float segment_height = radius - fabs(distance);
    const float chord_length =
        2.0f * sqrt(radius * radius - distance * distance);
    const float segment_area = _segment_area(segment_height, chord_length);

    return distance > 0 ? circle_area - segment_area
                        : segment_area;
}

float estimate_circle_line_overlap(const float radius,
                                   const float distance)
{
    if (radius <= 0.0f)
        return distance >= radius ? 1.0f : 0.0f;
    const float filter_area = estimate_circle_area(radius);
    const float segment_area =
        estimate_circle_segment_area(radius, distance, filter_area);
    return segment_area / filter_area;
}

float distance_to_line(const float line_x,
                       const float line_y,
                       const float line_angle,
                       const float x,
                       const float y)
{
    const float line_nx = -sin(line_angle);
    const float line_ny = cos(line_angle);
    const float line_d = line_nx * line_x + line_ny * line_y;
    const float d = line_nx * x + line_ny * y;
    return line_d - d;
}

__kernel void filtered_line(const unsigned int width,
                            const unsigned int height,
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

    rotate_point_arround_image_center(width, height, image_angle, &filter_x, &filter_y);

    const float distance = distance_to_line(line_x, line_y, line_angle, filter_x, filter_y);

    const float color = estimate_circle_line_overlap(filter_radius, distance);

    write_imagef(result, (int2)(col, row), (float4)(color, color, color, 1.0f));
}
