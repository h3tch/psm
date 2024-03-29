#include "circle.cl"
#include "image_rotation.cl" // rotate_point_arround_image_center, rotate_point
#include "random.cl"

__kernel void filtered_line(const unsigned int width,
                            const unsigned int height,
                            const float line_x,
                            const float line_y,
                            const float line_angle,
                            const float filter_radius,
                            const float filter_noise,
                            const float filter_samples,
                            const float image_angle,
                            __write_only image2d_t result)
{
    const size_t col = get_global_id(0);
    const size_t row = get_global_id(1);
    const float cx = width * 0.5f;
    const float cy = height * 0.5f;

    float filter_x = (float)col;
    float filter_y = (float)row;

    rotate_point(cx, cy, image_angle, &filter_x, &filter_y);

    float color = estimate_circle_half_space_overlap(
        filter_x, filter_y, filter_radius, line_x, line_y, line_angle);

    if (0.0f < color && color < 1.0f)
        color += filter_noise * poisson_noise(filter_x, filter_y, filter_samples * color);

    color = min(max(color, 0.0f), 1.0f);

    write_imagef(result, (int2)(col, row), (float4)(color, color, color, 1.0f));
}
