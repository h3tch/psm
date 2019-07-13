// indefinite integral of circle segment
double _circle_segment_area(const double x, const double y, const double r)
{
    return 0.5
           * (sqrt(1.0 - x * x / (r * r)) * x * r + r * r * asin(x / r)
              - 2.0 * y * x);
}

// area of intersection of an infinitely tall box with left edge at x0,
// right edge at x1, bottom edge at h and top edge at infinity, with circle
// centered at the origin with radius r
double _infinit_box_centered_circle_area(const double x0,
                                         const double x1,
                                         const double y,
                                         const double r)
{
    if (y >= r)
        return 0.0f;
    const double x = sqrt(r * r - y * y);
    const double a0 = _circle_segment_area(min(max(x0, -x), x), y, r);
    const double a1 = _circle_segment_area(min(max(x1, -x), x), y, r);
    return (float)(a1 - a0);
}

// area of the intersection of a finite box with
// a circle centered at the origin with radius r
double _unsafe_box_centered_circle_area(const double x0,
                                        const double x1,
                                        const double y0,
                                        const double y1,
                                        const double r)
{
    // area of the lower box minus area of the higher box
    const double a0 = _infinit_box_centered_circle_area(x0, x1, y0, r);
    const double a1 = _infinit_box_centered_circle_area(x0, x1, y1, r);
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
            return _unsafe_box_centered_circle_area(x0, x1, -y1, -y0, r);
        // the box is both above and below, divide it to two boxes and go
        // again
        const double a0 = _unsafe_box_centered_circle_area(x0, x1, 0.0f, -y0, r);
        const double a1 = _unsafe_box_centered_circle_area(x0, x1, 0.0f, y1, r);
        return a0 + a1;
    }
    return _unsafe_box_centered_circle_area(x0, x1, y0, y1, r);
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