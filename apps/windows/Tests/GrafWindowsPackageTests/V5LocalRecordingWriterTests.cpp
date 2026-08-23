#include "../../RecApp/Recording/LocalRecordingPackage.h"
#include "../../RecApp/Storage/AtomicFileStore.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <fstream>

int main() {
    using namespace graf::windows;
    const auto directory = std::filesystem::temp_directory_path() / "graf-feature-200-writer";
    const auto custodyRoot = directory / "custody";
    const auto escape = directory.parent_path() / "graf-feature-200-writer-escape";
    std::filesystem::remove_all(directory);
    std::filesystem::remove_all(escape);
    std::filesystem::create_directories(custodyRoot);
    assert(!AtomicFileStore::isWithinRoot(custodyRoot, escape));
    V5LocalRecordingWriter escapedWriter(custodyRoot, escape, [](const auto& path, const auto&, std::uint64_t) {
        std::ofstream output(path, std::ios::binary); output << "must-not-write"; return output.good();
    });
    CanonicalAudioFrame escapedFrame; escapedFrame.mixed.fill(0.25F);
    assert(!escapedWriter.append(escapedFrame));
    assert(!std::filesystem::exists(escape));

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
    std::filesystem::remove_all(escape);
    return 0;
}
