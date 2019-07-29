#include "image_rotation.cl" // rotate_point_arround_image_center
#include "rasterize.cl"      // rasterize, rasterize_line_y
#include "circle.cl"
#include "random.cl"

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
            rasterize_line_y(artifact_size, k, d, c0 + pixel_center_shift)
            - filter_y;
        return r1 < 0.0f ? 0.0f : 1.0f;
    }

    float area = 0.0f;
    while (c0 <= filter_radius) {
        const float c1 = c0 + artifact_size;
        const float r1 =
            rasterize_line_y(artifact_size, k, d, c0 + pixel_center_shift)
            - filter_y;
        float a = estimate_circle_infinite_bar_area(
            c0, c1, fabs(r1), filter_radius, filter_radius2);
        if (r1 > 0)
            a = estimate_circle_interval_area(
                    c0, c1, filter_radius, filter_radius2)
                - a;
        area += a;
        c0 = c1;
    }

    const float circle_area = estimate_circle_area2(filter_radius2);
    return min(max(area / circle_area, 0.0f), 1.0f);
}

__kernel void filtered_line_artifact(const unsigned int width,
                                     const unsigned int height,
                                     const unsigned int artifact_size,
                                     const float line_x,
                                     const float line_y,
                                     const float line_angle,
                                     const float filter_radius,
                                     const float filter_noise,
                                     const float filter_samples,
                                     const float filter_radius_noise,
                                     const float image_angle,
                                     const unsigned int image_samples,
                                     __write_only image2d_t result)
{
    const float col = (float)get_global_id(0);
    const float row = (float)get_global_id(1);

    float filter_x = col;
    float filter_y = row;
    const float radius = filter_radius * (filter_radius_noise * randf(line_x + row, line_y + col) + (1.0f - filter_radius_noise / 2));

    rotate_point(line_x, line_y, image_angle, &filter_x, &filter_y);

    float color = filter_line(line_x,
                              line_y,
                              line_angle,
                              artifact_size,
                              filter_x,
                              filter_y,
                              radius);
    bool in_penumbra = 0.0f < color && color < 1.0f;

    for (unsigned int i = 1; i < image_samples; ++i) {
        const float rotation = (40.0f / i) * M_PI / 180.0f;

        filter_x = col;
        filter_y = row;

        rotate_point(line_x, line_y, image_angle + rotation, &filter_x, &filter_y);
        color += filter_line(line_x,
                             line_y,
                             line_angle + rotation,
                             artifact_size,
                             filter_x,
                             filter_y,
                             radius);
    }
    color /= (float)image_samples;

    if (in_penumbra)
        color += filter_noise * poisson_noise(filter_x, filter_y, filter_samples * color);

    color = min(max(color, 0.0f), 1.0f);

    write_imagef(result, (int2)(col, row), (float4)(color, color, color, 1.0f));
}