#include "image_rotation.cl" // rotate_point_arround_image_center, rotate_point
#include "circle.cl"

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

    rotate_point_arround_image_center(
        width, height, image_angle, &filter_x, &filter_y);

    const float color = estimate_circle_half_space_overlap(
        filter_x, filter_y, filter_radius, line_x, line_y, line_angle);

    write_imagef(result, (int2)(col, row), (float4)(color, color, color, 1.0f));
}
