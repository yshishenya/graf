#include "../../RecApp/Audio/ClockMapper.h"
#include "../../RecApp/Audio/AudioNormalizer.h"
#include "../../RecApp/Capture/WindowsCaptureSessionController.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <atomic>
#include <stdexcept>
#include <thread>
#include <chrono>

#ifdef _WIN32
#include <windows.h>
#include <mmdeviceapi.h>
#include <wrl/client.h>
#include <cstdio>
#endif

namespace graf::windows {
// Exercise the real controller's sink/Stop/polling without requiring a microphone.
// Only acquisition is bypassed; production state, finalizer and worker errors run.
struct CaptureSessionTestPeer {
    template<class Run>
    static void device(WasapiCaptureWorker& worker, Run run) { worker.deviceRunForTesting_ = std::move(run); }
    static bool packet(WasapiCaptureWorker& worker, ClockMapper& mapper, AudioNormalizer& normalizer,
        ClockObservation packet, const void* data, const std::function<bool(std::uint32_t)>& release) {
        return worker.consumePacket(mapper, normalizer, packet, data, 1, true, release);
    }
    static bool packet(WindowsCaptureSessionController& controller, bool render,
                       ClockMapper& mapper, AudioNormalizer& normalizer, ClockObservation observation) {
        auto& worker = render ? controller.renderWorker_ : controller.microphoneWorker_;
        return packet(*worker, mapper, normalizer, observation, reinterpret_cast<const void*>(1),
            [](std::uint32_t frames) { assert(frames == 480); return true; });
    }
#ifdef _WIN32
    static std::wstring wideId(const std::string& value) { return WasapiCaptureWorker::utf8ToWide(value); }
    static std::string narrowId(const wchar_t* value) { return WasapiEndpointEnumerator::narrow(value); }
#endif
    template<class Render, class Microphone>
    static void devices(WindowsCaptureSessionController& controller, Render render, Microphone microphone) {
        controller.setEndpoints({"render", "Synthetic render", WasapiDataFlow::render, 48'000, 1, true, false, 1},
                                {"mic", "Synthetic microphone", WasapiDataFlow::capture, 48'000, 1, true, true, 1});
        controller.renderWorker_->deviceRunForTesting_ = std::move(render);
        controller.microphoneWorker_->deviceRunForTesting_ = std::move(microphone);
    }
    static void expireStartup(WindowsCaptureSessionController& controller) {
        controller.startupDeadline_ = std::chrono::steady_clock::now() - std::chrono::seconds(1);
    }
    static bool finished(const WindowsCaptureSessionController& controller) {
        return (!controller.renderWorker_ || controller.renderWorker_->finished()) &&
            (!controller.microphoneWorker_ || controller.microphoneWorker_->finished());
    }
    static bool microphoneFinished(const WindowsCaptureSessionController& controller) {
        return controller.microphoneWorker_->finished();
    }
    static void begin(WindowsCaptureSessionController& controller) {
        assert(controller.session_.beginReadinessCheck().accepted());
        assert(controller.session_.markReady().accepted());
        assert(controller.session_.beginStart().accepted());
        controller.acceptingBatches_.store(true);
        assert(controller.session_.startRecording().accepted());
        controller.indicator_.publish(controller.session_.state());
    }
    static bool push(WindowsCaptureSessionController& controller) {
        return controller.handleBatch({});
    }
    static void failWorker(WindowsCaptureSessionController& controller) {
        controller.renderWorker_ = std::make_unique<WasapiCaptureWorker>(WasapiEndpointSnapshot{}, true);
        assert(controller.renderWorker_->start([](AudioBatch) { return true; }) ==
               CaptureWorkerError::invalidEndpoint);
    }
    static bool stopped(const WindowsCaptureSessionController& controller) {
        return !controller.acceptingBatches_.load() &&
            (!controller.renderWorker_ || !controller.renderWorker_->running()) &&
            (!controller.microphoneWorker_ || !controller.microphoneWorker_->running());
    }
};
}

namespace {
template<class Predicate>
void waitUntil(Predicate predicate) {
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(3);
    while (!predicate()) {
        assert(std::chrono::steady_clock::now() < deadline);
        std::this_thread::yield();
    }
}

// Simulates device/COM calls that cannot return until explicitly released, but
// runs inside the actual WasapiCaptureWorker thread and cancellation lifecycle.
struct DeviceStage {
    std::atomic_bool entered{false}, allowStartup{false}, initialized{false};
    std::atomic_bool cleaning{false}, allowCleanup{false};
    std::atomic<int> callbacks{0};
    void run(const std::atomic_bool& running, std::atomic_bool& ready,
             const graf::windows::CaptureBatchCallback& callback) {
        entered.store(true);
        waitUntil([&] { return allowStartup.load(); });
        if (running.load()) ready.store(true);
        initialized.store(true);
        while (running.load()) {
            assert(callback({}));
            ++callbacks;
            std::this_thread::yield();
        }
        // A callback already in the device path when Stop won must be discarded.
        assert(callback({}));
        ++callbacks;
        cleaning.store(true);
        waitUntil([&] { return allowCleanup.load(); });
    }
};
}

int main() {
    using namespace graf::windows;
#ifdef _WIN32
    // Exercise the exact IMMDevice GetId -> enumeration -> GetDevice conversion
    // helpers. Synthetic Unicode includes both BMP and surrogate-pair characters.
    const std::wstring wideEndpoint = L"{0.0.1.00000000}.{00000000-0000-0000-0000-000000000001}-\u041c\u0438\u043a-\u97f3-\U0001F3A4";
    const std::string utf8Endpoint = u8"{0.0.1.00000000}.{00000000-0000-0000-0000-000000000001}-\u041c\u0438\u043a-\u97f3-\U0001F3A4";
    assert(CaptureSessionTestPeer::wideId(utf8Endpoint) == wideEndpoint);
    assert(CaptureSessionTestPeer::narrowId(wideEndpoint.c_str()) == utf8Endpoint);
    assert(CaptureSessionTestPeer::wideId("X") == L"X");
    assert(CaptureSessionTestPeer::narrowId(L"X") == "X");
    assert(CaptureSessionTestPeer::wideId({}).empty());
    assert(CaptureSessionTestPeer::narrowId(nullptr).empty());
    assert(CaptureSessionTestPeer::narrowId(L"").empty());
    assert(CaptureSessionTestPeer::wideId(std::string("a\0b", 3)).empty());
    assert(CaptureSessionTestPeer::wideId("\xC0\xAF").empty());
    assert(CaptureSessionTestPeer::wideId("\xE2\x82").empty());
    const std::wstring invalidUtf16(1, static_cast<wchar_t>(0xD800));
    assert(CaptureSessionTestPeer::narrowId(invalidUtf16.c_str()).empty());

    // Optional read-only VM check: no audio activation/capture and no device IDs
    // or names in output. Zero installed endpoints is valid on CI.
    unsigned roundtrips = 0;
    const auto com = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    if (SUCCEEDED(com)) {
        {
            Microsoft::WRL::ComPtr<IMMDeviceEnumerator> enumerator;
            Microsoft::WRL::ComPtr<IMMDeviceCollection> endpoints;
            if (SUCCEEDED(CoCreateInstance(__uuidof(MMDeviceEnumerator), nullptr, CLSCTX_ALL,
                    IID_PPV_ARGS(&enumerator))) &&
                SUCCEEDED(enumerator->EnumAudioEndpoints(eAll, DEVICE_STATE_ACTIVE, &endpoints))) {
                UINT count = 0;
                assert(SUCCEEDED(endpoints->GetCount(&count)));
                for (UINT index = 0; index < count; ++index) {
                    Microsoft::WRL::ComPtr<IMMDevice> endpoint, resolved;
                    if (FAILED(endpoints->Item(index, &endpoint))) continue;
                    LPWSTR raw = nullptr;
                    if (FAILED(endpoint->GetId(&raw)) || raw == nullptr) continue;
                    const auto roundtrip = CaptureSessionTestPeer::wideId(CaptureSessionTestPeer::narrowId(raw));
                    assert(roundtrip == raw);
                    CoTaskMemFree(raw);
                    assert(SUCCEEDED(enumerator->GetDevice(roundtrip.c_str(), &resolved)));
                    ++roundtrips;
                }
            }
        }
        CoUninitialize();
    }
    std::printf("Native endpoint ID roundtrips: %u (no capture)\n", roundtrips);
#endif
    ClockMapper mapper;
    // A discontinuous startup packet is not a usable clock origin. The next
    // clean packet may have unrelated positions; only it starts the segment.
    ClockMapper startupClock;
    const auto discarded = startupClock.observe({900'000, 8'000, 48'000, ClockObservation::dataDiscontinuity, 480});
    assert(!discarded.valid && discarded.discardStartup && discarded.fault == ClockFault::none);
    assert(startupClock.healthy());
    assert(startupClock.observe({100'000, 10, 48'000, 0, 480}).valid);
    assert(mapper.observe({0, 0, 48'000, 0, 480}).valid);
    assert(mapper.observe({100'000, 480, 48'000, 0, 480}).valid);
    assert(mapper.observe({90'000, 960, 48'000, 0, 480}).fault == ClockFault::nonMonotonic);
    ClockMapper longRun;
    assert(longRun.observe({300'000'000'000'001ULL, 1'440'000'000'000ULL, 48'000, 0, 480}).valid);
    assert(longRun.observe({300'000'000'100'001ULL, 1'440'000'000'480ULL, 48'000, 0, 480}).valid);
    // IAudioCaptureClient::GetBuffer has already converted QPC to 100 ns,
    // including on the observed 24 MHz ARM64 host. Never scale it again.
    ClockMapper wasapi;
    ClockObservation packet;
    packet.qpc100ns = 1'000'000'000;
    packet.deviceFrames = 240;
    packet.frameCount = 480;
    assert(wasapi.observe(packet).valid);
    packet.qpc100ns += 100'000;
    packet.deviceFrames += 480;
    const auto nextPacket = wasapi.observe(packet);
    assert(nextPacket.valid && nextPacket.driftPpm == 0 && nextPacket.qpc100ns == 1'000'100'000);
    packet.flags = ClockObservation::timestampError;
    assert(!wasapi.observe(packet).valid && !wasapi.healthy());
    wasapi.reset(2);
    packet.flags = 0;
    assert(wasapi.observe(packet).valid);
    ClockMapper missingTimestamp;
    packet.flags = ClockObservation::timestampError;
    assert(!missingTimestamp.observe(packet).valid);

    // Every first/next flag combination uses the same production decision.
    for (std::uint32_t flags = 0; flags <= 8; ++flags) {
        ClockMapper first;
        const auto observation = first.observe({100'000, 10, 48'000, flags, 480});
        assert(observation.valid == (flags == 0 || flags == ClockObservation::silent));
        assert(observation.discardStartup == (flags == ClockObservation::dataDiscontinuity));
        const auto fault = flags == 8 ? ClockFault::invalidPacket :
            (flags & ClockObservation::timestampError) ? ClockFault::timestampError :
            flags == 3 ? ClockFault::discontinuity : ClockFault::none;
        assert(observation.fault == fault);
        for (const auto initial : {0U, ClockObservation::dataDiscontinuity, ClockObservation::silent}) {
            ClockMapper next;
            (void)next.observe({100'000, 10, 48'000, initial, 480});
            const auto second = next.observe({200'000, 490, 48'000, flags, 480});
            assert(!second.discardStartup);
            assert(second.valid == (flags == 0 || flags == ClockObservation::silent));
            if (!second.valid) {
                assert(!next.healthy());
                assert(next.observe({300'000, 970, 48'000, 0, 480}).fault == second.fault);
            }
        }
    }
    for (const auto count : {0U, 4'801U}) {
        ClockMapper invalid;
        const auto result = invalid.observe({100'000, 10, 48'000, ClockObservation::dataDiscontinuity, count});
        assert(!result.discardStartup && result.fault == ClockFault::invalidPacket);
    }
    for (const auto rate : {7'999U, 192'001U}) {
        ClockMapper invalid;
        assert(invalid.observe({100'000, 10, rate, 1, 480}).fault == ClockFault::invalidPacket);
    }
    ClockMapper changedRate;
    assert(changedRate.observe({100'000, 10, 48'000, 1, 480}).discardStartup);
    assert(changedRate.observe({200'000, 490, 44'100, 0, 441}).fault == ClockFault::invalidPacket);
    ClockMapper mismatch, drift;
    assert(mismatch.observe({100'000, 0, 48'000, 0, 482}).valid);
    assert(mismatch.observe({201'522, 448, 48'000, 0, 487}).fault == ClockFault::sampleCountMismatch);
    assert(drift.observe({100'000, 0, 48'000, 0, 480}).valid);
    assert(drift.observe({250'000, 480, 48'000, 0, 480}).fault == ClockFault::clockDrift);

    // Run the actual packet consumer inside the real worker thread. An invalid
    // data pointer proves startup audio is never read; the release callback sees
    // the full count, and failures cannot claim discarded or recorded frames.
    for (const bool render : {false, true}) for (const bool releaseSucceeds : {false, true}) {
        WasapiCaptureWorker worker({"synthetic", "Synthetic", render ? WasapiDataFlow::render : WasapiDataFlow::capture,
                                    44'100, 1, true, true, 1}, render);
        std::atomic_bool consumed{false};
        AudioBatch output;
        int releases = 0, callbacks = 0;
        CaptureSessionTestPeer::device(worker, [&](const auto& running, auto&, const auto&) {
            ClockMapper clock;
            AudioNormalizer normalizer;
            const auto release = [&](std::uint32_t frames) {
                assert(frames == 441);
                ++releases;
                return releaseSucceeds;
            };
            assert(CaptureSessionTestPeer::packet(worker, clock, normalizer,
                {900'000, 8'000, 44'100, 1, 441}, reinterpret_cast<const void*>(1), release) == releaseSucceeds);
            assert(!worker.ready() && callbacks == 0 && normalizer.healthy());
            assert(worker.clockDiagnostics().startupDiscardedFrames == (releaseSucceeds ? 441U : 0U));
            const std::vector<float> samples(441, 0.25F);
            assert(CaptureSessionTestPeer::packet(worker, clock, normalizer,
                {100'000, 10, 44'100, 0, 441}, samples.data(), release) == releaseSucceeds);
            if (releaseSucceeds) {
                AudioNormalizer baseline;
                AudioBatch expected, input;
                input.sampleRate = 44'100; input.channels = 1;
                input.clockDomain = input.routeGeneration = 1; input.samples = samples;
                assert(baseline.normalize(std::move(input), 100'000, expected));
                assert(callbacks == 1 && worker.ready());
                assert(output.samples == expected.samples && output.ptsFrames == expected.ptsFrames);
                assert(output.normalizedFrameOffset == 0);
                assert(output.source == (render ? AudioSource::systemRender : AudioSource::microphone));
            }
            consumed.store(true);
            while (running.load()) std::this_thread::yield();
        });
        assert(worker.start([&](AudioBatch batch) { ++callbacks; output = std::move(batch); return true; }) == CaptureWorkerError::none);
        waitUntil([&] { return consumed.load(); });
        assert(worker.ready() == releaseSucceeds && releases == 2);
        assert(worker.lastError() == (releaseSucceeds ? CaptureWorkerError::none : CaptureWorkerError::deviceInvalidated));
        worker.stop();
        waitUntil([&] { return worker.finished(); });
        assert(!worker.ready() && worker.clockDiagnostics().fault == ClockFault::none);
    }

    // Regression: real worker error must not skip the finalizer, including startup.
    ReadinessInputs ready;
    ready.microphonePermissionGranted = true;
    ready.microphoneEndpointReady = ready.renderEndpointReady = true;
    ready.formatNormalizationReady = ready.aecReady = ready.storageWritable = ready.aacEncoderReady = true;
    int startupFinalizations = 0;
    WindowsCaptureSessionController startup("startup-failure", [](AudioBatch) { return true; },
        [&](ReasonCode reason) {
            ++startupFinalizations;
            assert(reason == ReasonCode::endpointInvalidated);
            return CaptureFinalization{false, reason};
        });
    startup.setEndpoints({}, {});
    assert(startup.record(ready).state == SessionState::failed);
    assert(startup.stop().status == TransitionStatus::idempotent && startupFinalizations == 1);

    // Discard alone never signals ready: with no usable data the original
    // deadline still wins. A following fault also survives terminal snapshotting.
    for (const bool clockFailure : {false, true}) {
        std::atomic<int> discardedSources{0};
        std::atomic_bool fail{false};
        int finalized = 0;
        WindowsCaptureSessionController controller("discard-startup", [](AudioBatch) {
            assert(false); return false;
        }, [&](ReasonCode reason) {
            assert(reason == (clockFailure ? ReasonCode::clockDiscontinuity : ReasonCode::endpointInvalidated));
            ++finalized;
            return CaptureFinalization{false, reason};
        });
        const auto run = [&](bool render, const auto& running) {
            ClockMapper mapper;
            AudioNormalizer normalizer;
            assert(CaptureSessionTestPeer::packet(controller, render, mapper, normalizer, {100'000, 0, 48'000, 1, 480}));
            ++discardedSources;
            while (running.load()) {
                if (!render && fail.load()) {
                    assert(!CaptureSessionTestPeer::packet(controller, render, mapper, normalizer, {200'000, 480, 48'000, 1, 480}));
                    return;
                }
                std::this_thread::yield();
            }
        };
        CaptureSessionTestPeer::devices(controller,
            [&](const auto& running, auto&, const auto&) { run(true, running); },
            [&](const auto& running, auto&, const auto&) { run(false, running); });
        assert(controller.record(ready).state == SessionState::starting);
        waitUntil([&] { return discardedSources.load() == 2; });
        assert(controller.pollHealth().state == SessionState::starting);
        assert(controller.indicator().snapshot().visible && controller.indicator().snapshot().stopAvailable);
        if (clockFailure) {
            fail.store(true);
            waitUntil([&] { return CaptureSessionTestPeer::microphoneFinished(controller); });
        } else CaptureSessionTestPeer::expireStartup(controller);
        (void)controller.pollHealth();
        waitUntil([&] { return CaptureSessionTestPeer::finished(controller); });
        assert(controller.pollHealth().state == SessionState::failed && finalized == 1);
        const auto render = controller.clockDiagnostics(AudioSource::systemRender);
        const auto microphone = controller.clockDiagnostics(AudioSource::microphone);
        assert(render.startupDiscardedFrames == 480 && microphone.startupDiscardedFrames == 480);
        assert(render.fault == ClockFault::none);
        assert(microphone.fault == (clockFailure ? ClockFault::discontinuity : ClockFault::none));
        assert(!controller.indicator().snapshot().visible);
        assert(controller.pollHealth().status == TransitionStatus::idempotent && finalized == 1);
        assert(controller.clockDiagnostics(AudioSource::microphone).fault == microphone.fault);
    }

    // Asynchronous two-endpoint startup, cancellation/deadline, and real worker
    // cleanup fences. The UI thread keeps ownership of the lease and finalizer.
    for (const int scenario : {0, 1, 2}) { // success, Stop during startup, deadline
        DeviceStage render, microphone;
        std::atomic<int> delivered{0};
        int finalized = 0;
        const auto uiThread = std::this_thread::get_id();
        WindowsCaptureSessionController* current = nullptr;
        WindowsCaptureSessionController controller("async-start", [&](AudioBatch) {
            ++delivered;
            return true;
        }, [&](ReasonCode reason) {
            assert(std::this_thread::get_id() == uiThread);
            assert(CaptureSessionTestPeer::finished(*current));
            assert(current->indicator().snapshot().visible);
            assert(current->stop().status == TransitionStatus::idempotent);
            WindowsDesktopSession competing("during-finalizer");
            assert(!competing.beginReadinessCheck().accepted());
            ++finalized;
            assert(reason == (scenario == 2 ? ReasonCode::endpointInvalidated : ReasonCode::none));
            return CaptureFinalization{scenario == 0, reason};
        });
        current = &controller;
        CaptureSessionTestPeer::devices(controller,
            [&](const auto& running, auto& deviceReady, const auto& callback) { render.run(running, deviceReady, callback); },
            [&](const auto& running, auto& deviceReady, const auto& callback) { microphone.run(running, deviceReady, callback); });
        const auto beforeStart = std::chrono::steady_clock::now();
        assert(controller.record(ready).state == SessionState::starting);
        assert(std::chrono::steady_clock::now() - beforeStart < std::chrono::milliseconds(500));
        waitUntil([&] { return render.entered.load() && microphone.entered.load(); });
        assert(controller.indicator().snapshot().visible && controller.indicator().snapshot().stopAvailable);
        assert(controller.record(ready).status == TransitionStatus::rejected);
        render.allowStartup.store(true);
        waitUntil([&] { return render.callbacks.load() > 2; });
        assert(delivered.load() == 0); // First endpoint cannot feed the timeline alone.
        assert(controller.pollHealth().state == SessionState::starting);
        if (scenario == 0) {
            microphone.allowStartup.store(true);
            waitUntil([&] { return microphone.initialized.load(); });
            assert(delivered.load() == 0); // Workers cannot publish UI state or open the sink.
            assert(controller.pollHealth().state == SessionState::recording);
            waitUntil([&] { return delivered.load() > 0; });
        }
        const auto beforeStop = std::chrono::steady_clock::now();
        if (scenario == 2) {
            CaptureSessionTestPeer::expireStartup(controller);
            assert(controller.pollHealth().state == SessionState::stopping);
        } else {
            const auto stopped = controller.stop();
            assert(stopped.state == SessionState::stopping && stopped.status == TransitionStatus::accepted);
        }
        assert(std::chrono::steady_clock::now() - beforeStop < std::chrono::milliseconds(500));
        assert(controller.stop().status == TransitionStatus::idempotent);
        assert(controller.pollHealth().state == SessionState::stopping && finalized == 0);
        assert(controller.indicator().snapshot().visible);
        WindowsDesktopSession competing("during-cleanup");
        assert(!competing.beginReadinessCheck().accepted());
        microphone.allowStartup.store(true);
        waitUntil([&] { return render.cleaning.load() && microphone.cleaning.load(); });
        const int stoppedAt = delivered.load();
        assert(CaptureSessionTestPeer::push(controller));
        assert(delivered.load() == stoppedAt);
        render.allowCleanup.store(true);
        assert(controller.pollHealth().state == SessionState::stopping && finalized == 0);
        microphone.allowCleanup.store(true);
        waitUntil([&] { return CaptureSessionTestPeer::finished(controller); });
        const auto terminal = controller.pollHealth();
        assert(terminal.state == (scenario == 0 ? SessionState::savedLocal : SessionState::failed));
        assert(!controller.indicator().snapshot().visible && finalized == 1);
        assert(controller.stop().status == TransitionStatus::idempotent);
        assert(controller.pollHealth().status == TransitionStatus::idempotent && finalized == 1);
        assert(competing.beginReadinessCheck().accepted());
    }

    // A real worker thread's startup exception cancels its still-initializing
    // peer, with no timeline writes or premature finalization.
    {
        DeviceStage render;
        std::atomic_bool failMicrophone{false};
        int finalized = 0;
        WindowsCaptureSessionController controller("async-failure", [](AudioBatch) {
            assert(false); return false;
        }, [&](ReasonCode reason) {
            assert(reason == ReasonCode::endpointInvalidated);
            ++finalized;
            return CaptureFinalization{false, reason};
        });
        CaptureSessionTestPeer::devices(controller,
            [&](const auto& running, auto& deviceReady, const auto& callback) { render.run(running, deviceReady, callback); },
            [&](const auto&, auto&, const auto&) {
                waitUntil([&] { return failMicrophone.load(); });
                throw std::runtime_error("synthetic device startup failure");
            });
        assert(controller.record(ready).state == SessionState::starting);
        waitUntil([&] { return render.entered.load(); });
        failMicrophone.store(true);
        waitUntil([&] { return CaptureSessionTestPeer::microphoneFinished(controller); });
        assert(controller.pollHealth().state == SessionState::stopping && finalized == 0);
        render.allowStartup.store(true);
        waitUntil([&] { return render.cleaning.load(); });
        assert(controller.pollHealth().state == SessionState::stopping && finalized == 0);
        render.allowCleanup.store(true);
        waitUntil([&] { return CaptureSessionTestPeer::finished(controller); });
        assert(controller.pollHealth().state == SessionState::failed && finalized == 1);
    }

    // Stop must not block on an already-entered writer callback either. The
    // completion fence holds finalization until that accepted batch returns.
    {
        DeviceStage render, microphone;
        render.allowStartup.store(true); microphone.allowStartup.store(true);
        render.allowCleanup.store(true); microphone.allowCleanup.store(true);
        std::atomic_bool sinkEntered{false}, releaseSink{false};
        int finalized = 0;
        WindowsCaptureSessionController controller("slow-sink", [&](AudioBatch) {
            sinkEntered.store(true);
            waitUntil([&] { return releaseSink.load(); });
            return true;
        }, [&](ReasonCode reason) {
            assert(releaseSink.load() && reason == ReasonCode::none);
            ++finalized;
            return CaptureFinalization{true, reason};
        });
        CaptureSessionTestPeer::devices(controller,
            [&](const auto& running, auto& deviceReady, const auto& callback) { render.run(running, deviceReady, callback); },
            [&](const auto& running, auto& deviceReady, const auto& callback) { microphone.run(running, deviceReady, callback); });
        assert(controller.record(ready).state == SessionState::starting);
        waitUntil([&] { return render.initialized.load() && microphone.initialized.load(); });
        assert(controller.pollHealth().state == SessionState::recording);
        waitUntil([&] { return sinkEntered.load(); });
        const auto beforeStop = std::chrono::steady_clock::now();
        assert(controller.stop().state == SessionState::stopping);
        assert(std::chrono::steady_clock::now() - beforeStop < std::chrono::milliseconds(500));
        assert(controller.pollHealth().state == SessionState::stopping && finalized == 0);
        releaseSink.store(true);
        waitUntil([&] { return CaptureSessionTestPeer::finished(controller); });
        assert(controller.pollHealth().state == SessionState::savedLocal && finalized == 1);
    }

    for (const bool workerFault : {false, true}) {
        int finalized = 0;
        int acceptedBatches = 0;
        bool reject = false;
        WindowsCaptureSessionController* current = nullptr;
        WindowsCaptureSessionController controller("fault", [&](AudioBatch) {
            ++acceptedBatches;
            return !reject;
        }, [&](ReasonCode reason) {
            ++finalized;
            assert(reason == (workerFault ? ReasonCode::endpointInvalidated : ReasonCode::clockDiscontinuity));
            assert(CaptureSessionTestPeer::stopped(*current));
            assert(current->indicator().snapshot().visible);
            assert(current->indicator().snapshot().state == SessionState::finalizing);
            assert(current->stop().status == TransitionStatus::idempotent);
            WindowsDesktopSession competing("competing");
            assert(!competing.beginReadinessCheck().accepted());
            // Even a faulty caller cannot relabel a retained prefix as normal.
            return CaptureFinalization{true, ReasonCode::none, true};
        });
        current = &controller;
        CaptureSessionTestPeer::begin(controller);
        assert(CaptureSessionTestPeer::push(controller));
        if (workerFault) CaptureSessionTestPeer::failWorker(controller);
        else {
            reject = true;
            std::thread producer([&] { assert(CaptureSessionTestPeer::push(controller)); });
            producer.join();
            // Worker callback must not mutate the UI-owned reference.
            assert(controller.session().state() == SessionState::recording);
            assert(controller.indicator().snapshot().visible);
        }
        assert(controller.pollHealth().state == SessionState::failed);
        assert(!controller.indicator().snapshot().visible);
        assert(controller.finalization().trustedPrefixRetained && !controller.finalization().savedLocal);
        const int beforeLateCallback = acceptedBatches;
        assert(CaptureSessionTestPeer::push(controller));
        assert(acceptedBatches == beforeLateCallback);
        assert(controller.pollHealth().status == TransitionStatus::idempotent);
        assert(controller.stop().status == TransitionStatus::idempotent && finalized == 1);
    }

    // Pending native writer work never releases the lease/indicator or blocks
    // Stop. Only UI health polls invoke the callback; completion is applied once.
    for (const bool fail : {false, true}) {
        int polls = 0, dispatches = 0;
        bool complete = false;
        const auto uiThread = std::this_thread::get_id();
        WindowsCaptureSessionController* current = nullptr;
        WindowsCaptureSessionController controller("pending-finalizer", [](AudioBatch) { return true; },
            [&](ReasonCode reason) -> std::optional<CaptureFinalization> {
                assert(std::this_thread::get_id() == uiThread && reason == ReasonCode::none);
                assert(current->session().state() == SessionState::finalizing);
                assert(current->indicator().snapshot().visible);
                assert(current->stop().status == TransitionStatus::idempotent);
                // Nested UI polling cannot re-enter the finalizer callback.
                assert(current->pollHealth().state == SessionState::finalizing);
                if (polls++ == 0) ++dispatches;
                if (!complete) return std::nullopt;
                if (fail) throw std::runtime_error("synthetic asynchronous finalizer failure");
                return CaptureFinalization{true, ReasonCode::none};
            });
        current = &controller;
        CaptureSessionTestPeer::begin(controller);
        assert(controller.stop().state == SessionState::finalizing && polls == 1);
        WindowsDesktopSession competing("pending-writer-lease");
        assert(!competing.beginReadinessCheck().accepted());
        for (int index = 0; index < 3; ++index) {
            const int previousPolls = polls;
            assert(controller.stop().status == TransitionStatus::idempotent && polls == previousPolls);
            assert(controller.pollHealth().state == SessionState::finalizing && polls == previousPolls + 1);
            assert(controller.indicator().snapshot().visible && dispatches == 1);
        }
        complete = true;
        const auto terminal = controller.pollHealth();
        assert(terminal.state == (fail ? SessionState::failed : SessionState::savedLocal));
        assert(!controller.indicator().snapshot().visible && dispatches == 1);
        const int finalPolls = polls;
        assert(controller.stop().status == TransitionStatus::idempotent);
        assert(controller.pollHealth().status == TransitionStatus::idempotent && polls == finalPolls);
        assert(competing.beginReadinessCheck().accepted());
    }

    // Concurrent producer vs UI snapshots, privacy pause, and Stop fencing.
    std::atomic<int> batches{0};
    std::atomic<bool> run{true};
    int normalFinalizations = 0;
    bool paused = false;
    WindowsCaptureSessionController normal("normal", [&](AudioBatch) {
        ++batches;
        return true;
    }, [&](ReasonCode reason) {
        assert(reason == ReasonCode::none);
        ++normalFinalizations;
        return CaptureFinalization{true, ReasonCode::none};
    }, [&](bool value) { paused = value; });
    CaptureSessionTestPeer::begin(normal);
    assert(normal.pause().state == SessionState::paused && paused);
    assert(normal.resume().state == SessionState::recording && !paused);
    std::thread producer([&] {
        while (run.load()) assert(CaptureSessionTestPeer::push(normal));
    });
    while (batches.load() == 0) std::this_thread::yield();
    for (int index = 0; index < 1000; ++index) {
        const auto snapshot = normal.indicator().snapshot();
        assert(snapshot.visible && snapshot.state == SessionState::recording);
    }
    const auto stopping = normal.stop();
    assert(stopping.state == SessionState::savedLocal || stopping.state == SessionState::stopping);
    run.store(false);
    producer.join();
    if (normal.session().state() == SessionState::stopping) assert(normal.pollHealth().state == SessionState::savedLocal);
    const int stoppedAt = batches.load();
    assert(CaptureSessionTestPeer::push(normal));
    assert(batches.load() == stoppedAt);
    assert(normal.stop().status == TransitionStatus::idempotent && normalFinalizations == 1);

    WindowsCaptureSessionController throwing("throwing", [](AudioBatch) { return true; },
        [](ReasonCode) -> CaptureFinalization { throw std::runtime_error("synthetic finalizer fault"); });
    CaptureSessionTestPeer::begin(throwing);
    assert(throwing.stop().reason == ReasonCode::finalizationFailed);
    assert(CaptureSessionTestPeer::stopped(throwing));
    assert(throwing.stop().status == TransitionStatus::idempotent);
    return 0;
}
