#version 440 core

uniform uint artifact_size;
uniform vec3 line;
uniform float filter_radius;

in vec4 gl_FragCoord;
out vec4 fragColor;


float estimate_circle_area2(const float radius2)
{
    return (19.0 / 6.0) * radius2;
}


float estimate_circle_area(const float radius)
{
    return estimate_circle_area2(radius * radius);
}


float estimate_circle_segment_area(const float segment_height,
                                   const float chord_length)
{
    if (chord_length < 0.0001)
        return 0.0;
    const float inv_chord_length = 1.0 / (2.0 * chord_length);
    return segment_height
           * ((2.0 / 3.0) * chord_length
              + segment_height * segment_height * inv_chord_length);
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
        estimate_circle_segment_area(radius - x, 2.0 * circle_y);
    const float max_x_segment_area =
        estimate_circle_segment_area(radius - max_x, 2.0 * y);
    const float rect_area = (max_x - x) * y;
    return max((x_segment_area - max_x_segment_area) / 2.0 - rect_area, 0.0);
}


float estimate_circle_interval_area(const float x0,
                                    const float x1,
                                    const float radius,
                                    const float radius2)
{
    const float valid_x0 = min(abs(x0), radius);
    float left_area = estimate_circle_segment_area(
        radius - valid_x0, 2.0 * sqrt(radius2 - valid_x0 * valid_x0));

    const float valid_x1 = min(abs(x1), radius);
    float right_area = estimate_circle_segment_area(
        radius - valid_x1, 2.0 * sqrt(radius2 - valid_x1 * valid_x1));

    const float circle_area = estimate_circle_area2(radius2);

    if (x0 > 0.0)
        left_area = circle_area - left_area;
    if (x1 <= 0.0)
        right_area = circle_area - right_area;

    return circle_area - left_area - right_area;
}


float estimate_circle_infinite_bar_area(
    float x0, float x1, float y, const float radius, const float radius2)
{
    y = min(y, radius);
    const float max_x = sqrt(radius2 - y * y);

    const float segment_area =
        estimate_circle_segment_area(radius - y, 2.0 * max_x);

    float left_area = estimate_circle_segment_interval_area(
        abs(x0), y, max_x, radius, radius2);

    if (x0 > 0.0)
        left_area = segment_area - left_area;

    float right_area = estimate_circle_segment_interval_area(
        abs(x1), y, max_x, radius, radius2);

    if (x1 <= 0.0)
        right_area = segment_area - right_area;

    return segment_area - left_area - right_area;
}


float estimate_circle_segment_percentage(const float radius,
                                         const float radius2,
                                         const float distance,
                                         const float circle_area)
{
    if (distance > radius)
        return circle_area;

    if (distance < -radius)
        return 0.0;

    const float segment_height = radius - abs(distance);
    const float chord_length =
        2.0 * sqrt(radius2 - distance * distance);
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

    if (circle_radius <= 0.0)
        return distance_to_line >= circle_radius ? 1.0 : 0.0;

    const float circle_radius2 = circle_radius * circle_radius;
    const float circle_area = estimate_circle_area2(circle_radius2);
    const float segment_area = estimate_circle_segment_percentage(
        circle_radius, circle_radius2, distance_to_line, circle_area);

    return segment_area / circle_area;
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
    const float rasterized_y = rasterize(artifact_size, y);
    return y - rasterized_y < artifact_size * 0.5 ? rasterized_y : rasterized_y + artifact_size;
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
        return 0.0;
    if (filter_d + maxR < line_d)
        return 1.0;

    const float k = -line_nx / line_ny;
    const float d = line_y - k * line_x;
    const float pixel_center_shift = filter_x + artifact_size * 0.5;

    float c0 = rasterize(artifact_size, filter_x - filter_radius) - filter_x;
    const float filter_radius2 = filter_radius * filter_radius;

    if (filter_radius <= 0.0) {
        const float r1 =
            rasterize_line_y(artifact_size, k, d, c0 + pixel_center_shift)
            - filter_y;
        return r1 < 0.0 ? 0.0 : 1.0;
    }

    float area = 0.0;
    while (c0 <= filter_radius) {
        const float c1 = c0 + artifact_size;
        const float r1 =
            rasterize_line_y(artifact_size, k, d, c0 + pixel_center_shift)
            - filter_y;
        float a = estimate_circle_infinite_bar_area(
            c0, c1, abs(r1), filter_radius, filter_radius2);
        if (r1 > 0)
            a = estimate_circle_interval_area(
                    c0, c1, filter_radius, filter_radius2)
                - a;
        area += a;
        c0 = c1;
    }

    const float circle_area = estimate_circle_area2(filter_radius2);
    return min(max(area / circle_area, 0.0), 1.0);
}


void main()
{
    float filter_x = gl_FragCoord.x;
    float filter_y = gl_FragCoord.y;
    float radius = filter_radius;

    float color = filter_line(line.x,
                              line.y,
                              line.z,
                              artifact_size,
                              filter_x,
                              filter_y,
                              radius);

    fragColor.xyz = vec3(min(max(color, 0.0), 1.0));
    fragColor.w = 1.0;
}