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