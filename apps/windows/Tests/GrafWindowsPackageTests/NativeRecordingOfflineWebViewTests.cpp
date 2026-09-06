#include "../../RecApp/Audio/RecordingAudioTimeline.h"
#include "../../RecApp/Recording/V5LocalRecordingWriter.h"
#include "../../RecApp/Shell/CabinetWindow.h"
#include "../../RecApp/Capture/WindowsCaptureSessionController.h"
#include "../../RecApp/Recording/LocalRecordingPackage.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <algorithm>
#include <cassert>
#include <fstream>

namespace {
class FakeAec final : public graf::windows::IAec3Processor {
public:
    bool fail = false;
    bool process(const float*, const float* mic, float* cleaned) noexcept override {
        if (fail) return false;
        std::copy(mic, mic + 480, cleaned); return true;
    }
};
}

namespace graf::windows {
struct CaptureSessionTestPeer {
    static void begin(WindowsCaptureSessionController& controller) {
        assert(controller.session_.beginReadinessCheck().accepted());
        assert(controller.session_.markReady().accepted());
        assert(controller.session_.beginStart().accepted());
        controller.acceptingBatches_.store(true);
        assert(controller.session_.startRecording().accepted());
        controller.indicator_.publish(controller.session_.state());
    }
    static bool push(WindowsCaptureSessionController& controller, AudioBatch batch) {
        return controller.handleBatch(std::move(batch));
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

    // Real controller -> timeline -> writer -> destruction, with AEC fault after
    // one cleaned frame. Neither web failure nor the fault may discard that frame.
    const auto failedDirectory = directory / "fault-prefix";
    {
        FakeAec processor;
        RecordingAudioTimeline faultTimeline(processor);
        V5LocalRecordingWriter faultWriter(failedDirectory,
            [](const auto& path, const auto&, std::uint64_t count) {
                assert(count == 1);
                std::ofstream output(path, std::ios::binary);
                output << "synthetic-playback";
                return output.good();
            });
        int finalizations = 0;
        WindowsCaptureSessionController capture("offline-fault", [&](AudioBatch batch) {
            const bool healthy = faultTimeline.push(std::move(batch));
            for (const auto& frame : faultTimeline.takeFrames()) if (!faultWriter.append(frame)) return false;
            return healthy;
        }, [&](ReasonCode reason) {
            ++finalizations;
            assert(reason != ReasonCode::none);
            const auto result = faultWriter.finalize(ReasonCode::aecUnavailable);
            assert(!result.normalPackage());
            return CaptureFinalization{false, ReasonCode::aecUnavailable, result.trustedPrefixRetained};
        });
        CaptureSessionTestPeer::begin(capture);
        for (const auto source : {AudioSource::systemRender, AudioSource::microphone}) {
            assert(CaptureSessionTestPeer::push(capture,
                {source, 48'000, 1, 0, 1, 1, false, std::vector<float>(480, 0.1F)}));
        }
        assert(faultWriter.frameCount() == 1);
        processor.fail = true;
        for (const auto source : {AudioSource::systemRender, AudioSource::microphone}) {
            assert(CaptureSessionTestPeer::push(capture,
                {source, 48'000, 1, 480, 1, 1, false, std::vector<float>(480, 0.9F)}));
        }
        assert(capture.pollHealth().state == SessionState::failed);
        assert(capture.finalization().trustedPrefixRetained);
        assert(capture.stop().status == TransitionStatus::idempotent && finalizations == 1);
    }
    assert(LocalRecordingPackage::inspect(failedDirectory).integrity == PackageIntegrity::degraded);
    assert(std::filesystem::file_size(failedDirectory / ".canonical-mix.f32.tmp") == 480 * sizeof(float));
    std::filesystem::remove_all(directory);
    return 0;
}
