#include "cmodel.hpp"
#include <fstream>
#include <iostream>
#include <limits>
#include <string>
// Minimal file-I/O harness, not a benchmark or Jansori test implementation.
namespace {
int ParseInt(const std::string& Text) {
    std::size_t End = 0;
    const int Value = std::stoi(Text, &End);
    if (End != Text.size()) throw std::invalid_argument("invalid integer");
    return Value;
}
std::string Token(std::istream& In) {
    std::string Text;
    while (In >> Text) {
        if (Text[0] == '#') { In.ignore(std::numeric_limits<std::streamsize>::max(), '\n'); continue; }
        return Text;
    }
    throw std::runtime_error("truncated PPM header");
}
cmodel::Image ReadImage(const std::string& Path) {
    std::ifstream In(Path, std::ios::binary);
    if (!In || Token(In) != "P6") throw std::runtime_error("P6 RGB8 PPM required");
    const int W = ParseInt(Token(In)), H = ParseInt(Token(In));
    if (Token(In) != "255" || W <= 0 || H <= 0 || W > 4096 || H > 4096)
        throw std::runtime_error("invalid PPM geometry or maxval");
    const auto Delimiter = In.get();
    if (Delimiter == '\r' && In.peek() == '\n') In.get();
    else if (Delimiter != '\n' && Delimiter != '\r' && Delimiter != ' ' && Delimiter != '\t')
        throw std::runtime_error("missing raster separator");
    cmodel::Image Image{W, H, std::vector<std::uint8_t>(static_cast<std::size_t>(W) * H * 3U)};
    In.read(reinterpret_cast<char*>(Image.Pixels.data()), static_cast<std::streamsize>(Image.Pixels.size()));
    if (In.gcount() != static_cast<std::streamsize>(Image.Pixels.size())) throw std::runtime_error("truncated raster");
    return Image;
}
void WriteImage(const std::string& Path, const cmodel::Image& Image) {
    std::ofstream Out(Path, std::ios::binary);
    if (!Out) throw std::runtime_error("cannot create output");
    Out << "P6\n" << Image.Width << ' ' << Image.Height << "\n255\n";
    Out.write(reinterpret_cast<const char*>(Image.Pixels.data()), static_cast<std::streamsize>(Image.Pixels.size()));
    if (!Out) throw std::runtime_error("output write failed");
}
}
int main(int Argc, char** Argv) {
    try {
        if (Argc < 3 || Argc > 6) {
            std::cerr << "usage: workload INPUT.ppm OUTPUT.ppm [RADIUS [STRENGTH_Q8 [GAIN_Q8]]]\n";
            return 2;
        }
        cmodel::Parameters P;
        if (Argc > 3) P.Radius = ParseInt(Argv[3]);
        if (Argc > 4) P.StrengthQ8 = ParseInt(Argv[4]);
        if (Argc > 5) P.GainQ8 = ParseInt(Argv[5]);
        const auto Input = ReadImage(Argv[1]);
        const auto Output = cmodel::DoProcess(Input, P);
        cmodel::Validate(Output, P);
        if (Output.Width != Input.Width || Output.Height != Input.Height)
            throw std::runtime_error("changed output dimensions");
        WriteImage(Argv[2], Output);
        std::cout << "processed " << Input.Width << 'x' << Input.Height << " RGB8\n";
        return 0;
    } catch (const std::exception& Error) {
        std::cerr << Error.what() << '\n'; return 1;
    }
}
