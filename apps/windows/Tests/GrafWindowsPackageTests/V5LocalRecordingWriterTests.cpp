#include "../../RecApp/Recording/LocalRecordingPackage.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <fstream>

int main() {
    using namespace graf::windows;
    const auto directory = std::filesystem::temp_directory_path() / "graf-feature-200-writer";
    std::filesystem::remove_all(directory);
    V5LocalRecordingWriter writer(directory, [](const auto& path, const auto&, std::uint64_t) {
        std::ofstream output(path, std::ios::binary); output << "m4a-fixture"; return output.good();
    });
    CanonicalAudioFrame frame; frame.mixed.fill(0.25F);
    assert(writer.append(frame));
    const auto result = writer.finalize();
    assert(result.ok() && result.durationMs == 10 && result.wavBytes > 44 && !result.wavSha256.empty());
    const auto package = LocalRecordingPackage::inspect(directory);
    assert(package.integrity == PackageIntegrity::valid && package.durationMs == 10);
    std::filesystem::remove_all(directory);
    return 0;
}
