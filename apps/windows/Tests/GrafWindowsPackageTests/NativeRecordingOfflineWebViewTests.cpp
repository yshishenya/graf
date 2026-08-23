#include "../../RecApp/Audio/RecordingAudioTimeline.h"
#include "../../RecApp/Recording/V5LocalRecordingWriter.h"
#include "../../RecApp/Shell/CabinetWindow.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <algorithm>
#include <cassert>
#include <fstream>

namespace {
class FakeAec final : public graf::windows::IAec3Processor {
public:
    bool process(const float*, const float* mic, float* cleaned) noexcept override {
        std::copy(mic, mic + 480, cleaned); return true;
    }
};
}

int main() {
    using namespace graf::windows;
    const auto directory = std::filesystem::temp_directory_path() / "graf-feature-200-package";
    std::filesystem::remove_all(directory);
    FakeAec aec; RecordingAudioTimeline timeline(aec);
    V5LocalRecordingWriter writer(directory, [](const auto& path, const auto&, std::uint64_t) {
        std::ofstream output(path, std::ios::binary); output << "synthetic playback fixture"; return output.good();
    });
    assert(timeline.push({AudioSource::systemRender, 48'000, 1, 0, 1, 1, false, std::vector<float>(480, 0.1F)}));
    assert(timeline.push({AudioSource::microphone, 48'000, 1, 0, 1, 1, false, std::vector<float>(480, 0.1F)}));
    for (const auto& frame : timeline.takeFrames()) assert(writer.append(frame));
    CabinetWindow cabinet; cabinet.webView().setRuntimeState(WebRuntimeState::unavailable);
    assert(cabinet.openCabinet().decision == RouteDecision::allow);
    const auto package = writer.finalize();
    assert(package.ok());
    assert(std::filesystem::exists(package.manifestPath));
    std::filesystem::remove_all(directory);
    return 0;
}
