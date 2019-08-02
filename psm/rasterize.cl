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
    return y - rasterized_y < artifact_size * 0.5f ? rasterized_y : rasterized_y + artifact_size;
}


float next_line_step_x(const float artifact_size,
                       const float k,
                       const float d,
                       const float rasterized_y)
{
    const float half_artifact_size = artifact_size * 0.5f;
    const float max_x = (rasterized_y + half_artifact_size - d) / fabs(k);
    const float x = rasterize(artifact_size, max_x);
    return max_x - x < half_artifact_size ? x : x + artifact_size;
}