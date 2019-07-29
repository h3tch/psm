
__kernel void clear(__write_only image2d_t result)
{
    const size_t col = get_global_id(0);
    const size_t row = get_global_id(1);
    write_imagef(result, (int2)(col, row), (float4)(0.0f, 0.0f, 0.0f, 1.0f));
}
