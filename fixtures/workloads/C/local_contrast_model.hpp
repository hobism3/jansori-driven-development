#pragma once
#include "cmodel.hpp"

// PUBLIC WORKLOAD API. This starter has no implemented lifecycle state yet.
// Add private state to complete the supplied task. This is not a Jansori component.
namespace cmodel {
class LocalContrastModel {
public:
    explicit LocalContrastModel(Parameters Params = Parameters{});
    Image DoRun(const Image& Input);
    bool IsReady() const;
    std::uint64_t GetFrameCount() const;
    void Reset();
private:
    Parameters m_parameters;
};
} // namespace cmodel
