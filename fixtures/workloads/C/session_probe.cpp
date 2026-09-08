#include "local_contrast_model.hpp"
#include <iostream>

// Public-behavior observation only. No private-member naming rules or solution.
// Final evaluation uses the evaluator's fixed copy, not a workspace-edited copy.
namespace {
void PrintState(const char* Event, const cmodel::LocalContrastModel& Model,
                bool Rejected = false, const cmodel::Image* Output = nullptr) {
    std::cout << "{\"event\":\"" << Event << "\",\"ready\":" << std::boolalpha
              << Model.IsReady() << ",\"frame_count\":" << Model.GetFrameCount()
              << ",\"invalid_argument\":" << Rejected;
    if (Output != nullptr) {
        std::cout << ",\"image\":{\"width\":" << Output->Width
                  << ",\"height\":" << Output->Height << ",\"pixels\":[";
        for (std::size_t I = 0; I < Output->Pixels.size(); ++I) {
            if (I != 0) std::cout << ',';
            std::cout << static_cast<int>(Output->Pixels[I]);
        }
        std::cout << "]}";
    }
    std::cout << "}\n";
}
void RunAndPrint(const char* Event, cmodel::LocalContrastModel& Model,
                 const cmodel::Image& Input) {
    const auto Output = Model.DoRun(Input);
    PrintState(Event, Model, false, &Output);
}
void RejectAndPrint(const char* Event, cmodel::LocalContrastModel& Model) {
    bool Rejected = false;
    try { (void)Model.DoRun(cmodel::Image{2, 1, {10}}); }
    catch (const std::invalid_argument&) { Rejected = true; }
    PrintState(Event, Model, Rejected);
}
}
int main() {
    try {
        cmodel::LocalContrastModel Model;
        const cmodel::Image Valid{2, 1, {10, 40, 80, 90, 180, 250}};
        PrintState("constructed", Model);
        RunAndPrint("success_1", Model, Valid);
        RunAndPrint("success_2", Model, Valid);
        RejectAndPrint("invalid_input", Model);
        RunAndPrint("success_3", Model, Valid);
        Model.Reset(); PrintState("reset", Model);
        RunAndPrint("success_after_reset", Model, Valid);

        cmodel::LocalContrastModel Independent;
        PrintState("other_instance", Independent);
        PrintState("first_after_other_construction", Model);
        RunAndPrint("other_success", Independent, Valid);
        PrintState("first_after_other_success", Model);
        Independent.Reset(); PrintState("other_reset", Independent);
        PrintState("first_after_other_reset", Model);
        RunAndPrint("other_success_again", Independent, Valid);
        Model.Reset(); PrintState("first_reset_again", Model);
        PrintState("other_after_first_reset", Independent);

        const cmodel::Image NarrowRange{2, 1, {100, 100, 100, 110, 110, 110}};
        cmodel::LocalContrastModel Configured(cmodel::Parameters{1, 77, 128});
        PrintState("configured_constructed", Configured);
        RunAndPrint("configured_success", Configured, NarrowRange);
        Configured.Reset(); PrintState("configured_reset", Configured);
        RunAndPrint("configured_success_after_reset", Configured, NarrowRange);
        RejectAndPrint("configured_invalid_input", Configured);
        RunAndPrint("configured_after_failure_success", Configured, NarrowRange);

        cmodel::LocalContrastModel Fresh;
        RejectAndPrint("fresh_invalid_input", Fresh);
        RunAndPrint("fresh_success", Fresh, Valid);
        return 0; // Completion of observation is not a golden comparison PASS.
    } catch (const std::exception& Error) {
        std::cerr << Error.what() << '\n'; return 1;
    }
}
