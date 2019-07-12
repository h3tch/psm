
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
    const float segment_area =
        segment_height
        * ((2.0f / 3.0f) * chord_length
            + segment_height * segment_height / (2.0f * chord_length));

    return distance > 0 ? circle_area - segment_area
                        : segment_area;
}

float estimate_circle_line_overlap(const float radius,
                                   const float distance)
{
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
    const float line_nx = sin(line_angle);
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
    const int x = get_global_id(0);
    const int y = get_global_id(1);

    const float image_center_x = (float)width * 0.5f;
    const float image_center_y = (float)height * 0.5f;
    const float image_angle_sin = sin(image_angle);
    const float image_angle_cos = cos(image_angle);

    const float tmp_x = (float)x - image_center_x;
    const float tmp_y = (float)y - image_center_y;
    const float filter_x = image_angle_cos * tmp_x - image_angle_sin * tmp_y + image_center_x;
    const float filter_y = image_angle_sin * tmp_x + image_angle_cos * tmp_y + image_center_y;

    const float distance = distance_to_line(line_x, line_y, line_angle, filter_x, filter_y);

    const float color = estimate_circle_line_overlap(filter_radius, distance);

    write_imagef(result, (int2)(x, y), (float4)(color, 0.0f, 0.0f, 1.0f));
}
