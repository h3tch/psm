// indefinite integral of circle segment
double circle_segment_area(const double x, const double y, const double r)
{
    return 0.5
           * (sqrt(1.0 - x * x / (r * r)) * x * r
              + r * r * asin(x / r) - 2.0 * y * x);
}

// area of intersection of an infinitely tall box with left edge at x0,
// right edge at x1, bottom edge at h and top edge at infinity, with circle
// centered at the origin with radius r
double infinit_box_centered_circle_area(const double x0,
                                       const double x1,
                                       const double y,
                                       const double r)
{
    if (y >= r)
        return 0.0f;
    const double x = sqrt(r * r - y * y);
    const double a0 = circle_segment_area(min(max(x0, -x), x), y, r);
    const double a1 = circle_segment_area(min(max(x1, -x), x), y, r);
    return (float)(a1 - a0);
}

// area of the intersection of a finite box with
// a circle centered at the origin with radius r
double unsafe_box_centered_circle_area(const double x0,
                                      const double x1,
                                      const double y0,
                                      const double y1,
                                      const double r)
{
    // area of the lower box minus area of the higher box
    const double a0 = infinit_box_centered_circle_area(x0, x1, y0, r);
    const double a1 = infinit_box_centered_circle_area(x0, x1, y1, r);
    return a0 - a1;
}

// area of the intersection of a finite box with
// a circle centered at the origin with radius r
double box_centered_circle_area(const double x0,
                               const double x1,
                               const double y0,
                               const double y1,
                               const double r)
{
    if (y0 < 0.0f) {
        if (y1 < 0.0f)
            // the box is completely under, just flip it above and try again
            return unsafe_box_centered_circle_area(x0, x1, -y1, -y0, r);
        // the box is both above and below, divide it to two boxes and go
        // again
        const double a0 = unsafe_box_centered_circle_area(x0, x1, 0.0f, -y0, r);
        const double a1 = unsafe_box_centered_circle_area(x0, x1, 0.0f, y1, r);
        return a0 + a1;
    }
    return unsafe_box_centered_circle_area(x0, x1, y0, y1, r);
}

// area of the intersection of a general box with a general circle
double box_circle_area(const double x0,
                      const double x1,
                      const double y0,
                      const double y1,
                      const double cx,
                      const double cy,
                      const double r)
{
    return box_centered_circle_area(x0 - cx, x1 - cx, y0 - cy, y1 - cy, r);
}


float rasterize(const float raster_size, const float value)
{
    const float result = floor(value / raster_size) * raster_size;
    return result <= value ? result : result - raster_size;
}


float rasterize_line_y(const float artifact_size,
                       const float k,
                       const float d,
                       const float x)
{
    const float y = k * x + d;
    const float y0 = rasterize(artifact_size, y);
    return y - y0 < artifact_size * 0.5f ? y0 : y0 + artifact_size;
}


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
        return c0 <= filter_x && filter_x < c1 && r0 <= filter_y && filter_y < r1
               ? 1.0
               : 0.0;
    }

    double area = 0.0;
    while (c0 <= filter_x + filter_radius) {
        const double c1 = c0 + artifact_size;
        const double r1 =
            rasterize_line_y(artifact_size, k, d, c0 + pixel_center_shift);
        const double a = box_circle_area(
            c0, c1, min(r0, r1), max(r0, r1), filter_x, filter_y, filter_radius);
        if (a > 0.0)
            area += a;
        c0 = c1;
    }

    const double circle_area = filter_radius * filter_radius * M_PI;
    return min(max(area / circle_area, 0.0), 1.0);
}

void rotate_point_arround_image_center(const unsigned int width,
                                       const unsigned int height,
                                       const float image_angle,
                                       float* x,
                                       float* y)
{
    const float image_center_x = (float)width * 0.5f;
    const float image_center_y = (float)height * 0.5f;
    const float image_angle_sin = sin(image_angle);
    const float image_angle_cos = cos(image_angle);

    const float tmp_x = *x - image_center_x;
    const float tmp_y = *y - image_center_y;
    *x = image_angle_cos * tmp_x - image_angle_sin * tmp_y + image_center_x;
    *y = image_angle_sin * tmp_x + image_angle_cos * tmp_y + image_center_y;
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

    rotate_point_arround_image_center(width, height, image_angle, &filter_x, &filter_y);

    const float color = filter_line((double)line_x,
                                    (double)line_y,
                                    (double)line_angle,
                                    (double)artifact_size,
                                    (double)filter_x,
                                    (double)filter_y,
                                    (double)filter_radius);

    write_imagef(result, (int2)(col, row), (float4)(color, 0.0f, 0.0f, 1.0f));
}