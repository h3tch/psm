#include "define.cl"

float randf(const float seedx, const float seedy)
{
    float floor_part;
    return fract(sin(dot((float2)(seedx, seedy), (float2)(12.9898f, 78.233f)))
                     * 43758.5453f,
                 &floor_part);
}

float poison_distribution(const float expected, const float observed)
{
    return exp(-expected - 1.0f)
           * powr((float)M_E * expected / observed, observed);
}

float random_poisson(const float seedx,
                     const float seedy,
                     const float expected,
                     float start,
                     float stop)
{
#define n 10
    float cdf[n];

    start = max(0.0f, start);
    stop = max(0.0f, stop);

    const float p = randf(seedx, seedy);

    cdf[0] = poison_distribution(expected, start);

    const float step = (stop - start) / (float)n;
    for (uint i = 1; i < n; ++i) {
        start += step;
        cdf[i] = cdf[i - 1] - cdf[0] + poison_distribution(expected, start);
    }

    cdf[0] /= cdf[n - 1];

    for (uint i = 1; i < n; ++i) {
        cdf[i] /= cdf[n - 1];
        if (cdf[i] >= p) {
            const float f = (float)i;
            const float t = (cdf[i - 1] - p) / (cdf[i - 1] - cdf[i]);
            return ((f - 1.0f) * (1.0f - t) + f * t) / (float)n;
        }
    }

    return p;
#undef n
}

float poisson_noise(const float seedx, const float seedy, const float samples)
{
    const float rnd =
        random_poisson(seedx, seedy, samples, 0.0f, 2 * samples);
    return 2.0f * rnd - 1.0f;
}