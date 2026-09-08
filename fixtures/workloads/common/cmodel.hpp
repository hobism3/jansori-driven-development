#pragma once
#include <algorithm>
#include <cstdint>
#include <stdexcept>
#include <vector>

// WORKLOAD INPUT ONLY: not a Jansori component or a real product ISP model.
namespace cmodel {
struct Image {
    int Width = 0;
    int Height = 0;
    std::vector<std::uint8_t> Pixels;
};
struct Parameters {
    int Radius = 4;
    int StrengthQ8 = 160;
    int GainQ8 = 256;
};
inline void Validate(const Image& Input, const Parameters& Params) {
    if (Input.Width <= 0 || Input.Height <= 0 || Input.Width > 4096 || Input.Height > 4096 ||
        Input.Pixels.size() != static_cast<std::size_t>(Input.Width) * Input.Height * 3U)
        throw std::invalid_argument("invalid RGB8 image");
    if (Params.Radius < 0 || Params.Radius > 64 || Params.StrengthQ8 < 0 ||
        Params.StrengthQ8 > 256 || Params.GainQ8 < 0 || Params.GainQ8 > 1024)
        throw std::invalid_argument("invalid parameters");
}
inline std::size_t Offset(int X, int Y, int C, int Width) {
    return (static_cast<std::size_t>(Y) * Width + X) * 3U + C;
}
Image DoProcess(const Image& Input, const Parameters& Params);
} // namespace cmodel
