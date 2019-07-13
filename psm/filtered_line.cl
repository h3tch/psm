#include "image_rotation.cl" // rotate_point_arround_image_center, rotate_point
#include "box_circle_area.cl" // box_circle_area


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

    rotate_point(line_x, line_y, line_angle, &filter_x, &filter_y);

    const double radius = (double)filter_radius;
    const double c0 = -(double)width;
    const double c1 = 2 * (double)width;
    const double r0 = -(double)height;
    const double r1 = (double)line_y;
    const double area = box_circle_area(c0, c1, r0, r1, (double)filter_x, (double)filter_y, radius);
    const double circle_area = radius * radius * M_PI;

    const float color = (float)(area / circle_area);

    write_imagef(result, (int2)(col, row), (float4)(color, 0.0f, 0.0f, 1.0f));
}
