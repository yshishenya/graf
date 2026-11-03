#include "../../RecApp/Audio/RecordingAudioTimeline.h"
#include "../../RecApp/Recording/V5LocalRecordingWriter.h"
#include "../../RecApp/Shell/CabinetWindow.h"
#include "../../RecApp/Capture/WindowsCaptureSessionController.h"
#include "../../RecApp/Recording/LocalRecordingPackage.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <algorithm>
#include <atomic>
#include <cassert>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <thread>
#if defined(_MSC_VER) && defined(_DEBUG)
#include <crtdbg.h>
#endif
#include "../GeneratedRecordingFixtures.h"

namespace {
class FakeAec final : public graf::windows::IAec3Processor {
public:
    std::atomic<bool> fail{false};
    bool process(const float*, const float* mic, float* cleaned) noexcept override {
        if (fail.load()) return false;
        std::copy(mic, mic + 480, cleaned); return true;
    }
};
template<class Predicate> void waitFor(Predicate predicate,
    std::chrono::seconds timeout = std::chrono::seconds(10)) {
    const auto deadline = std::chrono::steady_clock::now()+timeout;
    while (!predicate()) {
        assert(std::chrono::steady_clock::now() < deadline);
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
}
}

namespace graf::windows {
struct CaptureSessionTestPeer {
    template<class Render, class Mic>
    static void devices(WindowsCaptureSessionController& controller, Render render, Mic mic) {
        controller.setEndpoints({"render", "Generated render", WasapiDataFlow::render, 48000, 1, true, false, 1},
            {"mic", "Generated mic", WasapiDataFlow::capture, 48000, 1, true, true, 1});
        controller.renderWorker_->deviceRunForTesting_ = std::move(render);
        controller.microphoneWorker_->deviceRunForTesting_ = std::move(mic);
    }
};
}

int main() {
#ifdef _MSC_VER
    _set_error_mode(_OUT_TO_STDERR);
    _set_abort_behavior(0, _WRITE_ABORT_MSG | _CALL_REPORTFAULT);
#ifdef _DEBUG
    _CrtSetReportMode(_CRT_ASSERT, _CRTDBG_MODE_FILE);
    _CrtSetReportFile(_CRT_ASSERT, _CRTDBG_FILE_STDERR);
#endif
#endif
    using namespace graf::windows;
    testing::GeneratedRecordingRoot portable;
    const auto failedDirectory = portable.parent/"fault-prefix";
    FakeAec aec; RecordingAudioTimeline timeline(aec);
#ifdef _WIN32
    testing::GeneratedProtectedRecording normal("offline-normal");
#endif
    assert(timeline.push({AudioSource::systemRender, 48000, 1, 0, 1, 1, false, std::vector<float>(480, 0.1F)}));
    assert(timeline.push({AudioSource::microphone, 48000, 1, 0, 1, 1, false, std::vector<float>(480, 0.1F)}));
    const auto cleaned = timeline.takeFrames(); assert(cleaned.size() == 1);
#ifdef _WIN32
    for (const auto& frame : cleaned) assert(normal.writer->append(frame));
#endif
    CabinetWindow cabinet; cabinet.webView().setRuntimeState(WebRuntimeState::unavailable);
    assert(cabinet.openCabinet().decision == RouteDecision::allow);
    assert(timeline.close());
#ifdef _WIN32
    const auto sealed = normal.writer->finalize();
    if (!sealed.normalPackage()) std::fprintf(stderr,
        "OFFLINE_NATIVE duration_ms=%llu error=%u storage=%u native=0x%08x phase=%u trusted_prefix=%u\n",
        static_cast<unsigned long long>(sealed.durationMs), static_cast<unsigned>(sealed.error),
        static_cast<unsigned>(sealed.storageError), sealed.nativeError, static_cast<unsigned>(sealed.packagePhase),
        static_cast<unsigned>(sealed.trustedPrefixRetained));
    // A 10-ms interruption must preserve the actual cleaned prefix. It cannot
    // promise usable AAC on every native encoder or bypass semantic checks.
    assert(sealed.semanticVerified && sealed.durationMs == 10 && !sealed.shortRecordingDiscarded);
    if (sealed.normalPackage()) assert(sealed.keepablePackage());
    else {
        assert(!sealed.ok() && !sealed.keepablePackage());
        assert(sealed.error == V5WriterError::integrityFailed && sealed.captureFailure == ReasonCode::finalizationFailed);
        assert(sealed.packagePhase == CustodyPackagePhase::sealedDegraded && sealed.trustedPrefixRetained);
    }
    {
        auto pair = normal.coldPair(); assert(pair.ok());
        auto inspected = LocalRecordingPackage::inspectProtected(normal.paths.root,*pair.value,normal.session,normal.cancel);
        assert(inspected.ok());
        const auto& evidence = (*inspected.value)->evidence();
        assert(evidence.durationMs == 10);
        if (sealed.normalPackage())
            assert(evidence.integrity == PackageIntegrity::valid && evidence.playback.decodedFrames > 0 && evidence.manifestSessionMatched);
        else assert(evidence.integrity == PackageIntegrity::degraded && evidence.trustedPrefixFrames == 1);
    } // Release cold native owners before the next actual encoder.
#else
    assert(!V5LocalRecordingWriter::open({}, "portable-native", {}).ok());
#endif

    // Only acquisition is generated: real readiness, worker-ready, dispatcher,
    // EOS and finalizer lifecycle. No test peer marks a session READY/recording.
    // Component test: the installed WebView failure callback and the native
    // storage worker's finalizer ownership still require their own acceptance.
    for (const bool injectFault : {false, true}) {
        cabinet.webView().setRuntimeState(WebRuntimeState::ready);
        FakeAec processor; RecordingAudioTimeline faultTimeline(processor);
#ifdef _WIN32
        testing::GeneratedProtectedRecording faulty(injectFault ? "offline-fault" : "offline-normal-stop");
#endif
        std::atomic<unsigned> emit{0}, written{0};
        int finalizations = 0;
        WindowsCaptureSessionController capture(injectFault ? "offline-fault" : "offline-normal-stop", [&](AudioBatch batch) {
            const bool healthy = faultTimeline.push(std::move(batch));
            for (const auto& frame : faultTimeline.takeFrames()) {
#ifdef _WIN32
                if (!faulty.writer->append(frame)) return false;
#else
                (void)frame;
#endif
                ++written;
            }
            return healthy;
        }, [&](ReasonCode reason, RecordingStopReason stopReason) {
            ++finalizations;
            if (!injectFault) {
                assert(reason == ReasonCode::none && stopReason == RecordingStopReason::userRequested);
                assert(faultTimeline.close() && written.load() == 3000);
#ifdef _WIN32
                const auto result = faulty.writer->finalize(reason, stopReason);
                assert(result.keepablePackage() && result.semanticVerified && result.durationMs == 30000);
                assert(!result.shortRecordingDiscarded);
#endif
                return CaptureFinalization{true, ReasonCode::none};
            }
            assert(reason != ReasonCode::none);
            (void)faultTimeline.close();
            assert(written.load() == 1);
#ifdef _WIN32
            const auto result = faulty.writer->finalize(ReasonCode::aecUnavailable);
            assert(!result.normalPackage() && result.trustedPrefixRetained);
            return CaptureFinalization{false, ReasonCode::aecUnavailable, result.trustedPrefixRetained};
#else
            // Portable evidence is only the old-format prefix/parser, not native V5.
            testing::writeGeneratedPrefix(failedDirectory, written.load(), ReasonCode::aecUnavailable);
            assert(LocalRecordingPackage::inspect(failedDirectory).integrity == PackageIntegrity::degraded);
            return CaptureFinalization{false, ReasonCode::aecUnavailable, true};
#endif
        });
        const auto device = [&](AudioSource source) {
            return [&, source](const auto& running, auto& ready, const auto& callback) {
                ready.store(true);
                unsigned packet = 0;
                while (running.load()) {
                    // Bound generated acquisition by actual sink progress. A CPU
                    // burst must not turn this scenario into a queue-overflow test.
                    if (packet < emit.load() && packet <= written.load()+8) {
                        const auto offset = static_cast<std::uint64_t>(packet)*480;
                        assert(callback({source, 48000, 1, static_cast<std::int64_t>(offset),
                            1, 1, false, std::vector<float>(480, packet ? 0.9F : 0.1F), offset}));
                        ++packet;
                    } else std::this_thread::yield();
                }
            };
        };
        CaptureSessionTestPeer::devices(capture, device(AudioSource::systemRender), device(AudioSource::microphone));
        ReadinessInputs prerequisites;
        prerequisites.microphonePermissionGranted = prerequisites.microphoneEndpointReady = true;
        prerequisites.renderEndpointReady = prerequisites.formatNormalizationReady = true;
        prerequisites.aecReady = prerequisites.aacEncoderReady = true; // Generated processors/devices.
#ifdef _WIN32
        prerequisites.storageWritable = faulty.writer->package()->current().phase == CustodyPackagePhase::capturing;
#else
        prerequisites.storageWritable = std::filesystem::is_directory(portable.parent); // Legacy-only portable fixture.
#endif
        assert(capture.record(prerequisites).state == SessionState::starting);
        waitFor([&] { return capture.pollHealth().state == SessionState::recording; });
        emit.store(1);
        waitFor([&] { return written.load() == 1; });
        cabinet.webView().setRuntimeState(WebRuntimeState::unavailable);
        assert(cabinet.openCabinet().decision == RouteDecision::allow);
        assert(capture.pollHealth().state == SessionState::recording);
        assert(capture.indicator().snapshot().visible && capture.indicator().snapshot().stopAvailable);
        if (!injectFault) {
            // 2999 more accepted frames after the web failure: no wall-clock padding
            // and no interruption exception to the ordinary 30-second keep rule.
            emit.store(3000);
            waitFor([&] {
                assert(capture.pollHealth().state == SessionState::recording);
                return written.load() == 3000;
            }, std::chrono::seconds(180));
            assert(capture.indicator().snapshot().visible && capture.indicator().snapshot().stopAvailable);
            assert(capture.stop().accepted());
            waitFor([&] { return capture.pollHealth().state == SessionState::savedLocal; });
            assert(capture.finalization().savedLocal && capture.finalization().reason == ReasonCode::none);
            assert(!capture.indicator().snapshot().visible && finalizations == 1);
        } else {
            processor.fail.store(true); emit.store(2);
            waitFor([&] { return capture.pollHealth().state == SessionState::failed; });
            assert(capture.finalization().trustedPrefixRetained);
        }
        assert(capture.stop().status == TransitionStatus::idempotent && finalizations == 1);
#ifdef _WIN32
        auto pair = faulty.coldPair(); assert(pair.ok());
        auto inspected = LocalRecordingPackage::inspectProtected(faulty.paths.root,*pair.value,faulty.session,faulty.cancel);
        assert(inspected.ok());
        const auto& evidence = (*inspected.value)->evidence();
        assert(evidence.integrity == (injectFault ? PackageIntegrity::degraded : PackageIntegrity::valid));
        if (injectFault) assert(evidence.trustedPrefixFrames == 1);
        else assert(evidence.durationMs == 30000 && evidence.playback.decodedFrames > 0 && evidence.manifestSessionMatched);
        assert(!std::filesystem::exists(faulty.paths.root/faulty.session/".canonical-mix.f32.tmp"));
#else
        if (injectFault) assert(std::filesystem::file_size(failedDirectory/".canonical-mix.f32.tmp") == 480*sizeof(float));
#endif
    }
    return 0;
}
