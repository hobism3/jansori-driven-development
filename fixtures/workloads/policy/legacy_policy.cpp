// Small policy workload only. Deliberately missing two Top attribute definitions.
#include <iostream>
#include <map>
#include <string>
#include <vector>
class Top {
    std::map<std::string, int> Values{{"nr.enable", 1}, {"frame.bit_depth", 8}, {"rgbp.gain_q8", 256}};
public:
    bool SetAttribute(const std::string& Key, int Value) {
        auto It = Values.find(Key);
        if (It == Values.end()) return false;
        It->second = Value; return true;
    }
    int GetAttribute(const std::string& Key) const {
        auto It = Values.find(Key); return It == Values.end() ? 0 : It->second;
    }
};
class CModelBase {
protected:
    std::vector<int> InputBuffer;
    void PrepareInputBuffer(const std::vector<int>& Input) { InputBuffer = Input; }
    virtual void InitInputBuffer(const std::vector<int>& Input) = 0;
public:
    virtual ~CModelBase() = default;
};
class NoiseReduction {
    std::vector<int> InputBuffer;
public:
    void InitInputBuffer(const std::vector<int>& Input) { InputBuffer = Input; }
    int run_nr(const Top& Attributes, const std::vector<int>& Input) {
        InitInputBuffer(Input);
        const int Enable = Attributes.GetAttribute("nr.enable");
        const int Bits = Attributes.GetAttribute("frame.bit_depth");
        const int Strength = Attributes.GetAttribute("nr.strength");
        const int Threshold = Attributes.GetAttribute("nr.edge_threshold");
        return Enable && Bits > 0 ? InputBuffer.at(0) + Strength - Threshold : InputBuffer.at(0);
    }
};
class Rgbp {
public:
    int run_rgbp(const Top& Attributes) const {
        return Attributes.GetAttribute("rgbp.gain_q8") + Attributes.GetAttribute("frame.bit_depth");
    }
};
int main() {
    Top Attributes; NoiseReduction Nr; Rgbp Rgb;
    const int Before = Nr.run_nr(Attributes, {100});
    const bool Accepted = Attributes.SetAttribute("nr.strength", 64);
    const int After = Nr.run_nr(Attributes, {100});
    std::cout << "top_accepted=" << std::boolalpha << Accepted
              << " nr_before=" << Before << " nr_after=" << After
              << " rgbp=" << Rgb.run_rgbp(Attributes) << '\n';
}
