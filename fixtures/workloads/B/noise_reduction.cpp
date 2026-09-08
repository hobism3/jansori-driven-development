#include "cmodel.hpp"
// B's legacy task. Correct functional behavior; deliberately repetitive calculation.
// Do not optimize this source during development of Jansori itself.
namespace cmodel {
namespace {
int compute_mean(const Image& Input, int X, int Y, int C, int Radius) {
    int Sum = 0;
    for (int Dy = -Radius; Dy <= Radius; ++Dy)
        for (int Dx = -Radius; Dx <= Radius; ++Dx) {
            const int Sx = std::clamp(X + Dx, 0, Input.Width - 1);
            const int Sy = std::clamp(Y + Dy, 0, Input.Height - 1);
            Sum += Input.Pixels[Offset(Sx, Sy, C, Input.Width)];
        }
    const int Side = 2 * Radius + 1;
    return Sum / (Side * Side);
}
std::uint8_t mix_pixel(int Original, int Mean, int Strength) {
    return static_cast<std::uint8_t>((Original * (256 - Strength) + Mean * Strength + 128) / 256);
}
}
Image DoProcess(const Image& Input, const Parameters& Params) {
    Validate(Input, Params);
    Image Out{Input.Width, Input.Height, std::vector<std::uint8_t>(Input.Pixels.size())};
    for (int Y = 0; Y < Input.Height; ++Y)
        for (int X = 0; X < Input.Width; ++X)
            for (int C = 0; C < 3; ++C) {
                const auto I = Offset(X, Y, C, Input.Width);
                Out.Pixels[I] = mix_pixel(Input.Pixels[I],
                    compute_mean(Input, X, Y, C, Params.Radius), Params.StrengthQ8);
            }
    return Out;
}
} // namespace cmodel
