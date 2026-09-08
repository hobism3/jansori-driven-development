#include "local_contrast_model.hpp"
// Legacy image processing plus an unfinished lifecycle feature. Workload input only.
namespace cmodel {
namespace {
int neighborhood_mean(const Image& Frame, int X, int Y, int Plane, int R) {
    int Total = 0;
    for (int Row = Y - R; Row <= Y + R; ++Row)
        for (int Col = X - R; Col <= X + R; ++Col)
            Total += Frame.Pixels[Offset(std::clamp(Col, 0, Frame.Width - 1),
                std::clamp(Row, 0, Frame.Height - 1), Plane, Frame.Width)];
    const int Diameter = R * 2 + 1;
    return Total / (Diameter * Diameter);
}
std::uint8_t enhance_pixel(int Value, int Mean, int Gain) {
    const int Result = Value + (Value - Mean) * Gain / 256;
    return static_cast<std::uint8_t>(std::clamp(Result, 0, 255));
}
}
Image DoProcess(const Image& Input, const Parameters& Params) {
    Validate(Input, Params);
    Image Out{Input.Width, Input.Height, std::vector<std::uint8_t>(Input.Pixels.size())};
    for (int Y = 0; Y < Input.Height; ++Y)
        for (int X = 0; X < Input.Width; ++X)
            for (int C = 0; C < 3; ++C) {
                const auto I = Offset(X, Y, C, Input.Width);
                Out.Pixels[I] = enhance_pixel(Input.Pixels[I],
                    neighborhood_mean(Input, X, Y, C, Params.Radius), Params.GainQ8);
            }
    return Out;
}
} // namespace cmodel

namespace cmodel {
LocalContrastModel::LocalContrastModel(Parameters Params) : m_parameters(Params) {}
Image LocalContrastModel::DoRun(const Image& Input) {
    // TODO: record successful processing without changing the image algorithm.
    return DoProcess(Input, m_parameters);
}
bool LocalContrastModel::IsReady() const {
    // TODO: report this object's readiness.
    return false;
}
std::uint64_t LocalContrastModel::GetFrameCount() const {
    // TODO: report successful frames since construction/reset.
    return 0;
}
void LocalContrastModel::Reset() {
    // TODO: reset this object's lifecycle state; retain parameters.
}
} // namespace cmodel
