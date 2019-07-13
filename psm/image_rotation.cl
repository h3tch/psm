void rotate_point(const float rotation_center_x,
                  const float rotation_center_y,
                  const float rotation_angle,
                  float* x,
                  float* y)
{
    const float angle_sin = sin(rotation_angle);
    const float angle_cos = cos(rotation_angle);
    const float tmp_x = *x - rotation_center_x;
    const float tmp_y = *y - rotation_center_y;
    *x = angle_cos * tmp_x - angle_sin * tmp_y + rotation_center_x;
    *y = angle_sin * tmp_x + angle_cos * tmp_y + rotation_center_y;
}


void rotate_point_arround_image_center(const unsigned int width,
                                       const unsigned int height,
                                       const float image_angle,
                                       float* x,
                                       float* y)
{
    const float image_center_x = (float)width * 0.5f;
    const float image_center_y = (float)height * 0.5f;
    rotate_point(image_center_x, image_center_y, image_angle, x, y);
}