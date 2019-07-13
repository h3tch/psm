#include "box_circle_area.cl" // box_circle_area
#include "image_rotation.cl" // rotate_point_arround_image_center
#include "rasterize.cl" // rasterize, rasterize_line_y


double filter_line(const double line_x,
                   const double line_y,
                   const double line_angle,
                   const double artifact_size,
                   const double filter_x,
                   const double filter_y,
                   const double filter_radius)
{
    const double maxR = filter_radius + artifact_size;
    const double line_nx = sin(line_angle);
    const double line_ny = cos(line_angle);
    const double line_d = line_x * line_nx + line_y * line_ny;
    const double filter_d = filter_x * line_nx + filter_y * line_ny;
    if (filter_d - maxR > line_d)
        return 0.0;
    if (filter_d + maxR < line_d)
        return 1.0;

    const double k = -line_nx / line_ny;
    const double d = line_y - k * line_x;
    const double pixel_center_shift = artifact_size * 0.5;

    double c0 = rasterize(artifact_size, filter_x - filter_radius);
    const double r0 = filter_y - filter_radius;

    if (filter_radius <= 0.0) {
        const double c1 = c0 + artifact_size;
        const double r1 =
            rasterize_line_y(artifact_size, k, d, c0 + pixel_center_shift);
        return c0 <= filter_x && filter_x < c1 && r0 <= filter_y
                       && filter_y < r1
                   ? 1.0
                   : 0.0;
    }

    double area = 0.0;
    while (c0 <= filter_x + filter_radius) {
        const double c1 = c0 + artifact_size;
        const double r1 =
            rasterize_line_y(artifact_size, k, d, c0 + pixel_center_shift);
        const double a = box_circle_area(c0,
                                         c1,
                                         r0,
                                         r1,
                                         filter_x,
                                         filter_y,
                                         filter_radius);
        if (a > 0.0)
            area += a;
        c0 = c1;
    }

    const double circle_area = filter_radius * filter_radius * M_PI;
    return min(max(area / circle_area, 0.0), 1.0);
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

    const float color = filter_line((double)line_x,
                                    (double)line_y,
                                    (double)line_angle,
                                    (double)artifact_size,
                                    (double)filter_x,
                                    (double)filter_y,
                                    (double)filter_radius);

    write_imagef(result, (int2)(col, row), (float4)(color, 0.0f, 0.0f, 1.0f));
}