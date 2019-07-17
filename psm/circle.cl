
float estimate_circle_area2(const float radius2)
{
    return (19.0f / 6.0f) * radius2;
}

float estimate_circle_area(const float radius)
{
    return estimate_circle_area2(radius * radius);
}

float estimate_circle_segment_area(const float segment_height,
                                   const float chord_length)
{
    if (chord_length < 1e-8)
        return 0.0f;
    return segment_height
           * ((2.0f / 3.0f) * chord_length
              + segment_height * segment_height / (2.0f * chord_length));
}

float estimate_circle_segment_interval_area(float x,
                                            const float y,
                                            const float max_x,
                                            const float radius,
                                            const float radius2)
{
    x = min(x, max_x);
    const float circle_y = sqrt(radius2 - x * x);

    const float x_segment_area =
        estimate_circle_segment_area(radius - x, 2.0f * circle_y);
    const float max_x_segment_area =
        estimate_circle_segment_area(radius - max_x, 2.0f * y);
    const float rect_area = (max_x - x) * y;
    return (x_segment_area - max_x_segment_area) / 2.0f - rect_area;
}

float estimate_circle_interval_area(const float x0,
                                    const float x1,
                                    const float radius,
                                    const float radius2)
{
    const float valid_x0 = min(fabs(x0), radius);
    float left_area = estimate_circle_segment_area(
        radius - valid_x0, 2.0f * sqrt(radius2 - valid_x0 * valid_x0));

    const float valid_x1 = min(fabs(x1), radius);
    float right_area = estimate_circle_segment_area(
        radius - valid_x1, 2.0f * sqrt(radius2 - valid_x1 * valid_x1));

    const float circle_area = estimate_circle_area2(radius2);

    if (x0 > 0.0f)
        left_area = circle_area - left_area;
    if (x1 < 0.0f)
        right_area = circle_area - right_area;

    return max(circle_area - left_area - right_area, 0.0f);
}

float estimate_circle_infinite_bar_area(
    float x0, float x1, float y, const float radius, const float radius2)
{
    y = min(y, radius);
    const float max_x = sqrt(radius2 - y * y);

    const float segment_area =
        estimate_circle_segment_area(radius - y, 2.0f * max_x);

    float left_area = estimate_circle_segment_interval_area(
        fabs(x0), y, max_x, radius, radius2);

    if (x0 > 0.0f)
        left_area = segment_area - left_area;

    float right_area = estimate_circle_segment_interval_area(
        fabs(x1), y, max_x, radius, radius2);

    if (x1 < 0.0f)
        right_area = segment_area - right_area;

    return max(segment_area - left_area - right_area, 0.0f);
}

float estimate_circle_segment_percentage(const float radius,
                                         const float radius2,
                                         const float distance,
                                         const float circle_area)
{
    if (distance > radius)
        return circle_area;

    if (distance < -radius)
        return 0.0f;

    const float segment_height = radius - fabs(distance);
    const float chord_length =
        2.0f * sqrt(radius2 - distance * distance);
    const float segment_area =
        estimate_circle_segment_area(segment_height, chord_length);

    return distance > 0 ? circle_area - segment_area : segment_area;
}

float estimate_circle_half_space_overlap(const float circle_x,
                                         const float circle_y,
                                         const float circle_radius,
                                         const float line_x,
                                         const float line_y,
                                         const float line_angle)
{
    const float distance_to_line =
        cos(line_angle) * (line_y - circle_y)
        - sin(line_angle) * (line_x - circle_x);

    if (circle_radius <= 0.0f)
        return distance_to_line >= circle_radius ? 1.0f : 0.0f;

    const float circle_radius2 = circle_radius * circle_radius;
    const float circle_area = estimate_circle_area2(circle_radius2);
    const float segment_area = estimate_circle_segment_percentage(
        circle_radius, circle_radius2, distance_to_line, circle_area);

    return segment_area / circle_area;
}