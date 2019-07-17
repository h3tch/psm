float randf(const float x, const float y)
{
    float floor_part;
    return fract(sin(dot((float2)(x, y), (float2)(12.9898f, 78.233f))) * 43758.5453f, &floor_part);
}