#include "../../RecApp/Audio/ClockMapper.h"
#include "../../RecApp/Audio/AudioNormalizer.h"
#include "../../RecApp/Capture/WindowsCaptureSessionController.h"
#include "AutomaticRecordingTestSupport.h"
#include "../../RecApp/Recording/LocalRecordingPackage.h"
#include "../../RecApp/Upload/DesktopUploadRecoveryScheduler.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <algorithm>
#include <cassert>
#include <atomic>
#include <stdexcept>
#include <thread>
#include <chrono>
#include <fstream>
#include <cstdlib>
#include <new>
#include <utility>

// Fail one samples allocation on the capture thread, not the process heap.
namespace { thread_local bool failSampleAllocation = false; }
void* operator new(std::size_t bytes) {
    if (failSampleAllocation && bytes == 480 * sizeof(float)) {
        failSampleAllocation = false;
        throw std::bad_alloc();
    }
    if (void* memory = std::malloc(bytes ? bytes : 1)) return memory;
    throw std::bad_alloc();
}
void operator delete(void* memory) noexcept { std::free(memory); }
void operator delete(void* memory, std::size_t) noexcept { std::free(memory); }

#ifdef _WIN32
#include <windows.h>
#include <mmdeviceapi.h>
#include <wrl/client.h>
#include <cstdio>
#include <process.h>
#else
#include <spawn.h>
#include <sys/wait.h>
extern char** environ;
#endif

namespace graf::windows {
AudioBatch syntheticLifecycleBatch() {
    return {AudioSource::systemRender, 48'000, 1, 0, 1, 1, false,
            std::vector<float>(480, 0.0F)};
}

// Exercise the real controller's sink/Stop/polling without requiring a microphone.
// Only acquisition is bypassed; production state, finalizer and worker errors run.
struct CaptureSessionTestPeer {
    static void nativeStop(WasapiCaptureWorker& worker, std::int32_t result) {
        worker.completeNativeStop(result);
    }
    static void nativeStop(WindowsCaptureSessionController& controller, bool render, std::int32_t result) {
        nativeStop(*(render ? controller.renderWorker_ : controller.microphoneWorker_), result);
    }
    template<class Run>
    static void device(WasapiCaptureWorker& worker, Run run) { worker.deviceRunForTesting_ = std::move(run); }
    static bool packet(WasapiCaptureWorker& worker, ClockMapper& mapper, AudioNormalizer& normalizer,
        ClockObservation packet, const void* data,
        const std::function<CaptureReleaseResult(std::uint32_t)>& release) {
        return worker.consumePacket(mapper, normalizer, packet, data, 1, true, release);
    }
    static bool packet(WindowsCaptureSessionController& controller, bool render,
                       ClockMapper& mapper, AudioNormalizer& normalizer, ClockObservation observation) {
        auto& worker = render ? controller.renderWorker_ : controller.microphoneWorker_;
        return packet(*worker, mapper, normalizer, observation, reinterpret_cast<const void*>(1),
            [](std::uint32_t frames) { assert(frames == 480); return CaptureReleaseResult{true, 0}; });
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
    static bool renderFinished(const WindowsCaptureSessionController& controller) {
        return controller.renderWorker_->finished();
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
        return controller.handleBatch(syntheticLifecycleBatch());
    }
    static void failMicrophoneWorker(WindowsCaptureSessionController& controller) {
        // Пустой идентификатор устройства — тот же отказ, что видит человек,
        // когда микрофон пропадает на ходу.
        controller.microphoneWorker_ = std::make_unique<WasapiCaptureWorker>(WasapiEndpointSnapshot{}, false);
        assert(controller.microphoneWorker_->start([](AudioBatch) { return true; }) ==
               CaptureWorkerError::invalidEndpoint);
    }
    static void failRenderWorker(WindowsCaptureSessionController& controller) {
        // Отказ системного звука на ходу: устройство воспроизведения пропало.
        controller.renderWorker_ = std::make_unique<WasapiCaptureWorker>(WasapiEndpointSnapshot{}, true);
        assert(controller.renderWorker_->start([](AudioBatch) { return true; }) ==
               CaptureWorkerError::invalidEndpoint);
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
    static std::uint8_t sourceEndMask(const WindowsCaptureSessionController& controller) {
        return controller.sourceEndsProcessed_.load();
    }
    static void startDispatcher(WindowsCaptureSessionController& controller) {
        controller.dispatchFinished_.store(false);
        controller.dispatchThread_ = std::thread([&controller] { controller.dispatchLoop(); });
    }
    static bool dispatcherFinished(const WindowsCaptureSessionController& controller) {
        return controller.dispatchFinished_.load(std::memory_order_acquire);
    }
    static void drainDeadline(WindowsCaptureSessionController& controller,
                              std::chrono::steady_clock::time_point deadline) {
        controller.drainDeadline_ = deadline;
    }
    static void latchFault(WindowsCaptureSessionController& controller, ReasonCode reason) {
        controller.latchFault(reason);
    }
    static ReasonCode firstFault(const WindowsCaptureSessionController& controller) {
        return controller.captureFault_.load();
    }
    static bool enqueue(WindowsCaptureSessionController& controller, int sequence) {
        auto batch = syntheticLifecycleBatch();
        batch.ptsFrames = sequence;
        return controller.enqueueBatch(std::move(batch));
    }
    static std::size_t pending(WindowsCaptureSessionController& controller) {
        std::lock_guard<std::mutex> lock(controller.dispatchMutex_);
        return controller.pendingBatches_.size();
    }
    static bool dispatcherIdle(WindowsCaptureSessionController& controller) {
        std::lock_guard<std::mutex> lock(controller.dispatchMutex_);
        return !controller.dispatchBusy_.load(std::memory_order_acquire) &&
            controller.pendingBatches_.empty();
    }
};
}

namespace {
template<class Predicate>
void waitUntilImpl(Predicate predicate, const char* text, int line) {
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(3);
    while (!predicate()) {
        if (std::chrono::steady_clock::now() >= deadline) {
            // Место ожидания важнее самого факта: без него непонятно, какое
            // условие не наступило.
            std::fprintf(stderr, "waitUntil timeout at line %d: %s\n", line, text);
            std::fflush(stderr);
            assert(false);
        }
        std::this_thread::yield();
    }
}
#define waitUntil(predicate) waitUntilImpl((predicate), #predicate, __LINE__)

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
            assert(callback(graf::windows::syntheticLifecycleBatch()));
            ++callbacks;
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
        // A callback already in the device path when Stop won must be discarded.
        assert(callback(graf::windows::syntheticLifecycleBatch()));
        ++callbacks;
        cleaning.store(true);
        waitUntil([&] { return allowCleanup.load(); });
    }
};

void finalAutomaticStartGate() {
    using namespace graf::windows;
    using namespace graf::windows::testing;
    // Exercise all production callers of pollHealth, not just the timer path.
    for (int entry = 0; entry != 3; ++entry) for (int scenario = 0; scenario != 11; ++scenario) {
        const auto root = std::filesystem::temp_directory_path() /
            ("graf-start-gate-" + std::to_string(DetectionClock::now().time_since_epoch().count()) +
             "-" + std::to_string(entry) + "-" + std::to_string(scenario));
        assert(std::filesystem::create_directory(root));
        const std::string id = "11111111-1111-4111-8111-111111111111";
        const auto package = root / id;
        const auto ledger = root / "queue.json";
        VerifiedTargetRegistry registry;
        assert(registry.registerTarget(target()));
        Preferences storage;
        AutomaticRecordingPolicy policy(registry, storage.store());
        assert(policy.setPreference(target(), AutomaticRecordingPreference::always));
        const auto decision = observeFor(policy, 0, 5);
        assert(decision.shouldStart && policy.bindStart(decision.generation, id));
        auto observed = snapshot(at(6s));
        auto prerequisites = ready();
        auto now = at(6s);
        int checked = 0, finalized = 0;
        std::atomic<int> delivered{0};
        {
            DesktopUploadQueueService queue(ledger, root);
            assert(queue.load());
            V5LocalRecordingWriter writer(root, package, [](const auto& path, const auto&, std::uint64_t) {
                std::ofstream output(path, std::ios::binary); output << "synthetic-playback"; return output.good();
            });
            DeviceStage render, microphone;
            render.allowCleanup.store(true); microphone.allowCleanup.store(true);
            WindowsCaptureSessionController controller(id, [&](AudioBatch) {
                CanonicalAudioFrame frame;
                frame.ptsFrames = static_cast<std::int64_t>(writer.frameCount() * 480);
                assert(writer.append(frame));
                ++delivered;
                return true;
            }, [&](ReasonCode reason, RecordingStopReason stopReason) {
                ++finalized;
                const auto result = writer.finalize(reason, stopReason);
                if (result.keepablePackage()) {
                    UploadCustodyItem item;
                    item.localRecordingId = item.directoryId = item.sessionId = id;
                    item.packageDirectory = package;
                    item.ownerUserId = "22222222-2222-4222-8222-222222222222";
                    item.ownerWorkspaceId = "33333333-3333-4333-8333-333333333333";
                    assert(queue.enqueue(item));
                }
                return CaptureFinalization{result.keepablePackage(), reason};
            });
            CaptureSessionTestPeer::devices(controller,
                [&](const auto& running, auto& deviceReady, const auto& callback) { render.run(running, deviceReady, callback); },
                [&](const auto& running, auto& deviceReady, const auto& callback) { microphone.run(running, deviceReady, callback); });
            assert(controller.record(prerequisites.capture, [&](std::string_view session) {
                ++checked;
                assert(delivered.load() == 0 && writer.frameCount() == 0);
                if (scenario == 9) throw std::runtime_error("synthetic guard failure");
                if (scenario == 10) {
                    assert(controller.pollHealth().state == SessionState::starting);
                    assert(controller.resume().state == SessionState::starting);
                    (void)controller.stop();
                    return true; // A reentrant Stop must win even over a late true result.
                }
                return policy.acceptStart(decision.generation, session, observed, prerequisites, now);
            }).state == SessionState::starting);
            render.allowStartup.store(true);
            waitUntil([&] { return render.callbacks.load() > 2; });
            assert(controller.pollHealth().state == SessionState::starting);
            assert(!controller.record(prerequisites.capture).accepted()); // Cannot replace a bound guard with manual.
            assert(controller.pause().state == SessionState::starting);
            assert(controller.resume().state == SessionState::starting);
            assert(delivered.load() == 0 && checked == 0 && !std::filesystem::exists(package));
            switch (scenario) {
            case 1: policy.cancel(); break;
            case 2: assert(policy.setPreference(target(), AutomaticRecordingPreference::never)); break;
            case 3: observed.observations.clear(); break;
            case 4: ++observed.observations.front().processCreatedAt; break;
            case 5: now = at(9s); break;
            case 6: (void)controller.stop(); break;
            case 7: prerequisites.capture.microphonePermissionGranted = false; break;
            case 8: assert(policy.setAllPreferences(AutomaticRecordingPreference::ask)); break;
            }
            microphone.allowStartup.store(true);
            waitUntil([&] { return microphone.initialized.load(); });
            if (entry == 0) (void)controller.pollHealth();
            if (entry == 1) (void)controller.pause();
            if (entry == 2) (void)controller.resume();
            if (scenario == 0) {
                assert(controller.session().state() == (entry == 1 ? SessionState::paused : SessionState::recording));
                waitUntil([&] { return delivered.load() > 0; });
                (void)controller.pollHealth();
                assert(checked == 1);
                // Produce the existing 30 s keep threshold, then deliberately
                // Stop; short-recording policy is not bypassed by this test.
                while (delivered.load() < 3000) assert(CaptureSessionTestPeer::push(controller));
                (void)controller.stop();
            } else {
                assert(controller.session().state() != SessionState::recording &&
                       controller.session().state() != SessionState::paused);
                assert(delivered.load() == 0);
            }
            waitUntil([&] { (void)controller.pollHealth(); return !controller.indicator().snapshot().visible; });
            assert(finalized == 1 && checked == (scenario == 6 ? 0 : 1));
            assert((writer.frameCount() > 0) == (scenario == 0));
            assert((LocalRecordingPackage::inspect(package, root).integrity == PackageIntegrity::valid) == (scenario == 0));
        }
        // Reconstruct custody and recovery from disk; no in-memory policy or
        // controller state participates in this decision after restart.
        DesktopUploadQueueService restarted(ledger, root);
        assert(restarted.load());
        assert(restarted.requestRetry(id) == (scenario == 0));
        DesktopUploadRecoveryScheduler recovery(restarted);
        std::atomic<int> transportCalls{0};
        assert(recovery.startAsync(RecoveryTrigger::launch, [&](const auto&, const auto&) {
            ++transportCalls;
            DesktopTransportResult result;
            result.status = DesktopTransportStatus::uploaded;
            return result;
        }) == (scenario == 0));
        waitUntil([&] { (void)recovery.drain(); return !recovery.busy(); });
        assert(transportCalls.load() == (scenario == 0 ? 1 : 0));
        if (scenario != 0) assert(!std::filesystem::exists(package) && restarted.items().empty());
        std::filesystem::remove_all(root);
    }
}

[[noreturn]] void interruptBeforeAcceptance(const std::filesystem::path& root, bool cancelled) {
    using namespace graf::windows;
    using namespace graf::windows::testing;
    VerifiedTargetRegistry registry;
    assert(registry.registerTarget(target()));
    Preferences storage;
    AutomaticRecordingPolicy policy(registry, storage.store());
    assert(policy.setPreference(target(), AutomaticRecordingPreference::always));
    const auto decision = observeFor(policy, 0, 5);
    assert(policy.bindStart(decision.generation, "interrupted"));
    V5LocalRecordingWriter writer(root, root / "interrupted");
    DeviceStage render, microphone;
    WindowsCaptureSessionController controller("interrupted", [&](AudioBatch) {
        return writer.append(CanonicalAudioFrame{});
    });
    CaptureSessionTestPeer::devices(controller,
        [&](const auto& running, auto& ready, const auto& callback) { render.run(running, ready, callback); },
        [&](const auto& running, auto& ready, const auto& callback) { microphone.run(running, ready, callback); });
    assert(controller.record(ready().capture, [&](std::string_view session) {
        return policy.acceptStart(decision.generation, session, snapshot(at(6s)), ready(), at(6s));
    }).state == SessionState::starting);
    render.allowStartup.store(true);
    waitUntil([&] { return render.callbacks.load() > 2; });
    if (cancelled) policy.cancel();
    microphone.allowStartup.store(true);
    waitUntil([&] { return microphone.callbacks.load() > 2; });
    // Both workers deliver callbacks, but no owner-thread acceptance occurred.
    // Terminate the process without Stop, finalization or any C++ destructor.
    assert(writer.frameCount() == 0 && !std::filesystem::exists(root / "interrupted"));
    std::_Exit(73);
}

void interruptedStartRecovery(const char* executable) {
    using namespace graf::windows;
    for (const auto* mode : {"--interrupt-start-pending", "--interrupt-start-cancelled"}) {
        const auto root = std::filesystem::temp_directory_path() /
            ("graf-start-interrupted-" + std::to_string(DetectionClock::now().time_since_epoch().count()));
        assert(std::filesystem::create_directory(root));
        const auto path = root.string();
#ifdef _WIN32
        assert(_spawnl(_P_WAIT, executable, executable, mode, path.c_str(), static_cast<const char*>(nullptr)) == 73);
#else
        pid_t child = 0;
        char* arguments[] = {const_cast<char*>(executable), const_cast<char*>(mode),
                             const_cast<char*>(path.c_str()), nullptr};
        assert(posix_spawnp(&child, executable, nullptr, nullptr, arguments, environ) == 0);
        int status = 0;
        assert(waitpid(child, &status, 0) == child && WIFEXITED(status) && WEXITSTATUS(status) == 73);
#endif
        DesktopUploadQueueService queue(root / "queue.json", root);
        assert(queue.load());
        (void)queue.sweepDiscardedShortRecordings();
        assert(queue.items().empty() && !queue.requestRetry("interrupted"));
        assert(LocalRecordingPackage::inspect(root / "interrupted", root).integrity == PackageIntegrity::missing);
        DesktopUploadRecoveryScheduler recovery(queue);
        for (auto trigger : {RecoveryTrigger::launch, RecoveryTrigger::activation, RecoveryTrigger::authRecovered,
                             RecoveryTrigger::networkRecovered, RecoveryTrigger::wake, RecoveryTrigger::scheduled}) {
            assert(!recovery.startAsync(trigger, [](const auto&, const auto&) {
                assert(false); // No transport, even if auth/network return after restart.
                return DesktopTransportResult{};
            }));
        }
        assert(std::filesystem::is_empty(root));
        std::filesystem::remove(root);
    }
}

void oldDecisionCannotOpenNewSession() {
    using namespace graf::windows;
    using namespace graf::windows::testing;
    VerifiedTargetRegistry registry;
    assert(registry.registerTarget(target()));
    Preferences storage;
    AutomaticRecordingPolicy policy(registry, storage.store());
    assert(policy.setPreference(target(), AutomaticRecordingPreference::always));
    auto decision = observeFor(policy, 0, 5);
    const auto oldGeneration = decision.generation;
    for (int session = 0; session != 2; ++session) {
        const std::string id = session == 0 ? "A" : "B";
        const auto now = session == 0 ? at(6s) : at(28s);
        assert(policy.bindStart(decision.generation, id));
        DeviceStage render, microphone;
        render.allowCleanup.store(true); microphone.allowCleanup.store(true);
        std::atomic<int> delivered{0};
        int checks = 0;
        WindowsCaptureSessionController controller(id, [&](AudioBatch) { ++delivered; return true; });
        CaptureSessionTestPeer::devices(controller,
            [&](const auto& running, auto& ready, const auto& callback) { render.run(running, ready, callback); },
            [&](const auto& running, auto& ready, const auto& callback) { microphone.run(running, ready, callback); });
        assert(controller.record(ready().capture, [&](std::string_view actualSession) {
            ++checks;
            if (session == 1) {
                // A late callback cannot consume B's intent, even when handed
                // B's actual session id. B's own guard must still work afterward.
                assert(!policy.acceptStart(oldGeneration, actualSession, snapshot(now), ready(), now));
                assert(!policy.acceptStart(decision.generation, "A", snapshot(now), ready(), now));
            }
            return policy.acceptStart(decision.generation, actualSession, snapshot(now), ready(), now);
        }).state == SessionState::starting);
        render.allowStartup.store(true);
        waitUntil([&] { return render.callbacks.load() > 2; });
        if (session == 0) { policy.cancel(); (void)controller.stop(); }
        microphone.allowStartup.store(true);
        waitUntil([&] { return microphone.initialized.load(); });
        (void)controller.pollHealth();
        if (session == 1) {
            assert(controller.session().state() == SessionState::recording);
            (void)controller.pollHealth();
            assert(checks == 1);
            waitUntil([&] { return delivered.load() > 0; });
            (void)controller.stop();
        }
        waitUntil([&] { (void)controller.pollHealth(); return !controller.indicator().snapshot().visible; });
        if (session == 0) {
            assert(delivered.load() == 0 && checks == 0);
            auto absent = snapshot(at(21s)); absent.observations.clear();
            (void)policy.update(absent, ready(), at(21s));
            decision = observeFor(policy, 22, 27);
            assert(decision.shouldStart && decision.generation != oldGeneration);
        }
    }
}
}

int main(int argc, char** argv) {
    if (argc == 3 && std::string_view(argv[1]) == "--interrupt-start-pending") interruptBeforeAcceptance(argv[2], false);
    if (argc == 3 && std::string_view(argv[1]) == "--interrupt-start-cancelled") interruptBeforeAcceptance(argv[2], true);
    interruptedStartRecovery(argv[0]);
    finalAutomaticStartGate();
    oldDecisionCannotOpenNewSession();
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

    // Bounded packet timestamp jitter must not accumulate into a false clock
    // fault when every observation remains within the original QPC envelope.
    ClockMapper jitter;
    for (std::uint64_t packetIndex = 0; packetIndex < 65; ++packetIndex) {
        const auto jitter100ns = packetIndex % 2 == 0 ? -4'000LL : 4'000LL;
        const auto qpc = static_cast<std::uint64_t>(1'000'000'000LL +
            static_cast<std::int64_t>(packetIndex * 100'000) + jitter100ns);
        assert(jitter.observe({qpc, packetIndex * 480, 48'000, 0, 480}).valid);
    }

    // A single 2.5 ms timestamp step is rejected even when the next packet's
    // timestamp returns to the prior trajectory; the first fault is sticky.
    ClockMapper timestampStep;
    for (std::uint64_t packetIndex = 0; packetIndex <= 10; ++packetIndex) {
        const auto step100ns = packetIndex == 10 ? 25'000ULL : 0ULL;
        const auto observation = timestampStep.observe({
            1'000'000'000 + packetIndex * 100'000 + step100ns,
            packetIndex * 480, 48'000, 0, 480});
        if (packetIndex < 10) assert(observation.valid);
        else assert(!observation.valid && observation.fault == ClockFault::clockDrift);
    }
    const auto recoveredTimestamp = timestampStep.observe({1'001'100'000, 5'280, 48'000, 0, 480});
    assert(!recoveredTimestamp.valid && recoveredTimestamp.fault == ClockFault::clockDrift);

    // Pin the current drift boundary at 63 packet intervals: 1.08 ms remains
    // inside the fixed uncertainty, while 1.09 ms is outside it.
    for (const auto [extraQpc100ns, expectedFault] : {
             std::pair<std::uint64_t, ClockFault>{10'800, ClockFault::none},
             {10'900, ClockFault::clockDrift}}) {
        ClockMapper boundary;
        assert(boundary.observe({1'000'000'000, 0, 48'000, 0, 480}).valid);
        for (std::uint64_t packetIndex = 1; packetIndex < 63; ++packetIndex) {
            assert(boundary.observe({1'000'000'000 + packetIndex * 100'000,
                packetIndex * 480, 48'000, 0, 480}).valid);
        }
        const auto edge = boundary.observe({1'000'000'000 + 63 * 100'000 + extraQpc100ns,
            63 * 480, 48'000, 0, 480});
        assert(edge.valid == (expectedFault == ClockFault::none));
        assert(edge.fault == expectedFault);
    }

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
                return CaptureReleaseResult{releaseSucceeds, releaseSucceeds ? 0 : -1};
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
        assert(worker.lastError() == (releaseSucceeds ? CaptureWorkerError::none : CaptureWorkerError::releaseFailed));
        const auto diagnostics = worker.clockDiagnostics();
        assert(diagnostics.traceCount > 0 && diagnostics.lastTrace.frameCount == 441);
        assert(diagnostics.lastTrace.stage == (releaseSucceeds ? CaptureStage::callback : CaptureStage::releaseBuffer));
        worker.stop();
        waitUntil([&] { return worker.finished(); });
        assert(!worker.ready() && worker.clockDiagnostics().fault == ClockFault::none);
    }

    // Allocation failure must release before native Stop, without reading the
    // packet or advancing normalization/callbacks. Run both native source roles.
    for (const bool render : {false, true}) for (const bool releaseSucceeds : {false, true}) {
        WasapiCaptureWorker worker({"allocation", "Synthetic",
            render ? WasapiDataFlow::render : WasapiDataFlow::capture, 48'000, 1, true, true, 1}, render);
        AudioNormalizer normalizer;
        int releases = 0, callbacks = 0;
        bool stopped = false, rejected = false;
        CaptureSessionTestPeer::device(worker, [&](const auto&, auto&, const auto&) {
            ClockMapper clock;
            const std::function<CaptureReleaseResult(std::uint32_t)> release = [&](std::uint32_t frames) {
                assert(frames == 480 && !stopped);
                ++releases;
                return CaptureReleaseResult{releaseSucceeds, releaseSucceeds ? 0 : -2147024882};
            };
            failSampleAllocation = true;
            rejected = !CaptureSessionTestPeer::packet(worker, clock, normalizer,
                {100'000, 0, 48'000, 0, 480}, reinterpret_cast<const void*>(1), release);
            assert(!failSampleAllocation && releases == 1);
            const auto trace = worker.clockDiagnostics();
            assert(trace.traceCount == 1 && trace.lastTrace.stage == CaptureStage::releaseBuffer);
            assert(trace.lastTrace.frameCount == 480 && trace.lastTrace.released == releaseSucceeds);
            assert(trace.lastTrace.hresult == (releaseSucceeds ? 0 : -2147024882));
            CaptureSessionTestPeer::nativeStop(worker, 0);
            stopped = true;
        });
        assert(worker.start([&](AudioBatch) { ++callbacks; return true; }) == CaptureWorkerError::none);
        waitUntil([&] { return worker.finished(); });
        assert(releases == 1 && stopped && rejected && callbacks == 0 && !worker.ready());
        assert(worker.lastError() == (releaseSucceeds ? CaptureWorkerError::normalizationFailed :
            CaptureWorkerError::releaseFailed));
        const auto trace = worker.clockDiagnostics();
        assert(trace.traceCount == 2 && trace.lastTrace.stage == CaptureStage::stop && trace.lastTrace.hresult == 0);
        AudioBatch input, output;
        input.sampleRate = 48'000; input.channels = 1;
        input.routeGeneration = input.clockDomain = 1;
        input.samples.assign(480, 0.0F);
        assert(normalizer.normalize(std::move(input), 100'000, output));
        assert(output.normalizedFrameOffset == 0 && output.samples.size() == 480);
    }

    // AUDCLNT_BUFFERFLAGS_SILENT is a valid packet with no data pointer. The
    // worker must release it and deliver explicit zero samples, never read a
    // fabricated pointer or treat the packet as a missing source.
    {
        WasapiCaptureWorker worker({"silent", "Silent", WasapiDataFlow::capture,
                                    48'000, 1, true, true, 1}, false);
        std::atomic_bool consumed{false};
        AudioBatch output;
        CaptureSessionTestPeer::device(worker, [&](const auto& running, auto&, const auto&) {
            ClockMapper clock;
            AudioNormalizer normalizer;
            std::uint32_t releasedFrames = 0;
            const auto release = [&](std::uint32_t frames) {
                releasedFrames = frames;
                return CaptureReleaseResult{true, 0};
            };
            assert(CaptureSessionTestPeer::packet(worker, clock, normalizer,
                {100'000, 10, 48'000, ClockObservation::silent, 480}, nullptr, release));
            assert(releasedFrames == 480);
            consumed.store(true);
            while (running.load()) std::this_thread::yield();
        });
        assert(worker.start([&](AudioBatch batch) { output = std::move(batch); return true; }) == CaptureWorkerError::none);
        waitUntil([&] { return consumed.load(); });
        assert(worker.lastError() == CaptureWorkerError::none && worker.ready());
        assert(output.samples.size() == 480);
        assert(std::all_of(output.samples.begin(), output.samples.end(), [](float value) { return value == 0.0F; }));
        worker.stop();
        waitUntil([&] { return worker.finished(); });
    }

    // Only exact native clock measurements may publish audio. Positive S_FALSE
    // still releases the acquired packet once and fails before touching audio.
    for (const std::int32_t result : {1, -1}) {
        WasapiCaptureWorker worker({"clock-result", "Synthetic", WasapiDataFlow::capture,
                                    48'000, 1, true, true, 1}, false);
        int released = 0, callbacks = 0;
        CaptureSessionTestPeer::device(worker, [&](const auto&, auto&, const auto&) {
            ClockMapper clock;
            AudioNormalizer normalizer;
            assert(!CaptureSessionTestPeer::packet(worker, clock, normalizer,
                {100'000, 0, 48'000, 0, 480, 1'000, 384'000, result},
                reinterpret_cast<const void*>(1), [&](std::uint32_t frames) {
                    assert(frames == 480);
                    ++released;
                    return CaptureReleaseResult{true, 0};
                }));
        });
        assert(worker.start([&](AudioBatch) { ++callbacks; return true; }) == CaptureWorkerError::none);
        waitUntil([&] { return worker.finished(); });
        assert(released == 1 && callbacks == 0 && !worker.ready());
        assert(worker.lastError() == CaptureWorkerError::audioClockFailed);
    }

    // Trace storage wraps at 64 metadata events, sequence preserves evidence of
    // overwritten events, and a new worker attempt resets both size and sequence.
    {
        WasapiCaptureWorker worker({"trace", "Synthetic", WasapiDataFlow::capture,
                                    48'000, 1, true, true, 1}, false);
        for (const int packets : {40, 1}) {
            CaptureSessionTestPeer::device(worker, [&](const auto&, auto&, const auto&) {
                ClockMapper clock;
                AudioNormalizer normalizer;
                for (int i = 0; i < packets; ++i) {
                    assert(CaptureSessionTestPeer::packet(worker, clock, normalizer,
                        {100'000ULL + i * 100'000ULL, i * 480ULL, 48'000,
                         ClockObservation::silent, 480, 8'000, 384'000}, nullptr,
                        [](std::uint32_t) { return CaptureReleaseResult{true, 0}; }));
                }
            });
            assert(worker.start([](AudioBatch) { return true; }) == CaptureWorkerError::none);
            waitUntil([&] { return worker.finished(); });
            const auto trace = worker.clockDiagnostics();
            assert(trace.traceCount == static_cast<std::uint32_t>(std::min(64, packets * 3)));
            assert(trace.lastTrace.sequence == static_cast<std::uint64_t>(packets * 3));
            assert(trace.lastTrace.stage == CaptureStage::callback);
        }
    }

    // Completion is published only after cleanup, including exceptions. A new
    // attempt must not expose the preceding attempt's completion timestamp.
    {
        WasapiCaptureWorker worker({"completion", "Synthetic", WasapiDataFlow::capture,
                                    48'000, 1, true, true, 1}, false);
        assert(worker.finishedAt() == std::chrono::steady_clock::time_point{});
        auto previousCompletion = worker.finishedAt();
        for (const bool throws : {false, true}) {
            std::atomic_bool entered{false}, release{false};
            CaptureSessionTestPeer::device(worker, [&](const auto&, auto&, const auto&) {
                entered.store(true);
                waitUntil([&] { return release.load(); });
                if (throws) throw std::runtime_error("synthetic cleanup failure");
            });
            const auto beforeStart = std::chrono::steady_clock::now();
            assert(worker.start([](AudioBatch) { return true; }) == CaptureWorkerError::none);
            waitUntil([&] { return entered.load(); });
            worker.stop();
            assert(!worker.finished());
            assert(worker.finishedAt() == std::chrono::steady_clock::time_point{});
            const auto beforeRelease = std::chrono::steady_clock::now();
            release.store(true);
            waitUntil([&] { return worker.finished(); });
            const auto completed = worker.finishedAt();
            assert(completed >= beforeStart && completed >= beforeRelease && completed >= previousCompletion);
            assert(completed <= std::chrono::steady_clock::now());
            assert(worker.lastError() == (throws ? CaptureWorkerError::initializationFailed : CaptureWorkerError::none));
            previousCompletion = completed;
        }
    }

    // Native Stop results use HRESULT success semantics (including S_FALSE),
    // retain the exact result and cannot replace an earlier capture fault.
    for (const std::int32_t stopResult : {0, 1, -2147467259}) {
        for (const bool priorFault : {false, true}) {
            WasapiCaptureWorker worker({"native-stop", "Synthetic", WasapiDataFlow::capture,
                                        48'000, 1, true, true, 1}, false);
            CaptureSessionTestPeer::device(worker, [&](const auto&, auto&, const auto&) {
                if (priorFault) {
                    ClockMapper clock;
                    AudioNormalizer normalizer;
                    assert(!CaptureSessionTestPeer::packet(worker, clock, normalizer,
                        {100'000, 0, 48'000, 0, 0, 8'000, 384'000}, nullptr,
                        [](std::uint32_t frames) { assert(frames == 0); return CaptureReleaseResult{true, 0}; }));
                }
                CaptureSessionTestPeer::nativeStop(worker, stopResult);
            });
            assert(worker.start([](AudioBatch) { assert(false); return false; }) == CaptureWorkerError::none);
            waitUntil([&] { return worker.finished(); });
            assert(worker.lastError() == (priorFault ? CaptureWorkerError::clockDiscontinuity :
                stopResult < 0 ? CaptureWorkerError::stopFailed : CaptureWorkerError::none));
            const auto diagnostics = worker.clockDiagnostics();
            assert(diagnostics.lastTrace.stage == CaptureStage::stop);
            assert(diagnostics.lastTrace.hresult == stopResult);
            assert(diagnostics.lastTrace.frameCount == 0 && diagnostics.lastTrace.qpcPosition == 0);
        }
    }

    // Regression: real worker error must not skip the finalizer, including startup.
    ReadinessInputs ready;
    ready.microphonePermissionGranted = true;
    ready.microphoneEndpointReady = ready.renderEndpointReady = true;
    ready.formatNormalizationReady = ready.aecReady = ready.storageWritable = ready.aacEncoderReady = true;
    // Each native source reports its Stop result before the completion fence.
    // A finalizer attempting to return success must not erase a Stop failure.
    for (const bool failRender : {false, true}) for (const std::int32_t stopResult : {0, 1, -2147467259}) {
        int finalized = 0;
        WindowsCaptureSessionController controller("native-stop-result", [](AudioBatch) { return true; },
            [&](ReasonCode reason, RecordingStopReason) {
                ++finalized;
                assert(reason == (stopResult < 0 ? ReasonCode::finalizationFailed : ReasonCode::none));
                return CaptureFinalization{true, ReasonCode::none};
            });
        const auto run = [&](bool render, const auto& running, auto& sourceReady) {
            sourceReady.store(true);
            waitUntil([&] { return !running.load(); });
            CaptureSessionTestPeer::nativeStop(controller, render, render == failRender ? stopResult : 0);
        };
        CaptureSessionTestPeer::devices(controller,
            [&](const auto& running, auto& sourceReady, const auto&) { run(true, running, sourceReady); },
            [&](const auto& running, auto& sourceReady, const auto&) { run(false, running, sourceReady); });
        assert(controller.record(ready).state == SessionState::starting);
        waitUntil([&] { return controller.pollHealth().state == SessionState::recording; });
        (void)controller.stop();
        const auto expectedState = stopResult < 0 ? SessionState::failed : SessionState::savedLocal;
        waitUntil([&] { return controller.pollHealth().state == expectedState; });
        assert(finalized == 1);
        assert(controller.finalization().reason == (stopResult < 0 ? ReasonCode::finalizationFailed : ReasonCode::none));
        assert(controller.stop().status == TransitionStatus::idempotent && finalized == 1);
    }
    int startupFinalizations = 0;
    WindowsCaptureSessionController startup("startup-failure", [](AudioBatch) { return true; },
        [&](ReasonCode reason, RecordingStopReason) {
            ++startupFinalizations;
            // Пустой идентификатор устройства — это недоступное устройство, и
            // причина называется по источнику: первым стартует системный звук.
            // Раньше любая ошибка старта сводилась к «устройство отключилось»,
            // и человек читал неверное объяснение.
            assert(reason == ReasonCode::renderEndpointUnavailable);
            return CaptureFinalization{false, reason};
        });
    startup.setEndpoints({}, {});
    const auto startupFailure = startup.record(ready);
    assert(startupFailure.state == SessionState::stopping || startupFailure.state == SessionState::failed);
    waitUntil([&] { return startup.pollHealth().state == SessionState::failed; });
    assert(startup.stop().status == TransitionStatus::idempotent && startupFinalizations == 1);

    // Discard alone never signals ready: with no usable data the original
    // deadline still wins. A following fault also survives terminal snapshotting.
    for (const bool clockFailure : {false, true}) {
        std::atomic<int> discardedSources{0};
        std::atomic_bool fail{false};
        std::atomic<int> delivered{0};
        int finalized = 0;
        WindowsCaptureSessionController controller("discard-startup", [&](AudioBatch) {
            ++delivered;
            return true;
        }, [&](ReasonCode reason, RecordingStopReason) {
            assert(reason == (clockFailure ? ReasonCode::clockDiscontinuity : ReasonCode::renderEndpointUnavailable));
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
        } else {
            CaptureSessionTestPeer::expireStartup(controller);
        }
        const auto stopping = controller.pollHealth();
        assert(stopping.state == SessionState::stopping || stopping.state == SessionState::failed);
        assert(CaptureSessionTestPeer::stopped(controller));
        assert(delivered.load() == 0);
        waitUntil([&] { return controller.pollHealth().state == SessionState::failed; });
        const auto terminal = controller.pollHealth();
        assert(terminal.state == SessionState::failed && finalized == 1);
        assert(controller.finalization().reason ==
               (clockFailure ? ReasonCode::clockDiscontinuity : ReasonCode::renderEndpointUnavailable));
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
        }, [&](ReasonCode reason, RecordingStopReason) {
            assert(std::this_thread::get_id() == uiThread);
            assert(CaptureSessionTestPeer::finished(*current));
            assert(current->indicator().snapshot().visible);
            assert(current->stop().status == TransitionStatus::idempotent);
            WindowsDesktopSession competing("during-finalizer");
            assert(!competing.beginReadinessCheck().accepted());
            ++finalized;
            assert(reason == (scenario == 2 ? ReasonCode::microphoneEndpointUnavailable : ReasonCode::none));
            return CaptureFinalization{scenario != 1, reason};
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
            assert(controller.pollHealth().state == SessionState::stopping && finalized == 0);
            assert(delivered.load() == 0);
        }
        const auto stopped = controller.stop();
        assert(stopped.status == (scenario == 2 ? TransitionStatus::idempotent : TransitionStatus::accepted));
        assert(std::chrono::steady_clock::now() - beforeStop < std::chrono::milliseconds(500));
        assert(controller.stop().status == TransitionStatus::idempotent);
        assert(controller.pollHealth().state == SessionState::stopping && finalized == 0);
        assert(controller.indicator().snapshot().visible);
        WindowsDesktopSession competing("during-cleanup");
        assert(!competing.beginReadinessCheck().accepted());
        microphone.allowStartup.store(true);
        waitUntil([&] { return render.cleaning.load() && microphone.cleaning.load(); });
        // Stop fences new callbacks, but batches accepted before that fence are
        // still drained in FIFO order. Stabilize the observation before
        // checking that a late callback did not add work.
        waitUntil([&] { return CaptureSessionTestPeer::dispatcherIdle(controller); });
        const int stoppedAt = delivered.load();
        assert(CaptureSessionTestPeer::push(controller));
        assert(delivered.load() == stoppedAt);
        render.allowCleanup.store(true);
        assert(controller.pollHealth().state == SessionState::stopping && finalized == 0);
        microphone.allowCleanup.store(true);
        const auto expectedState = scenario == 0 ? SessionState::savedLocal : SessionState::failed;
        waitUntil([&] { return controller.pollHealth().state == expectedState; });
        const auto terminal = controller.pollHealth();
        assert(terminal.state == expectedState);
        assert(CaptureSessionTestPeer::sourceEndMask(controller) == 3);
        if (scenario == 2) {
            assert(controller.finalization().reason == ReasonCode::microphoneEndpointUnavailable);
        }
        assert(!controller.indicator().snapshot().visible && finalized == 1);
        assert(controller.stop().status == TransitionStatus::idempotent);
        assert(controller.pollHealth().status == TransitionStatus::idempotent && finalized == 1);
        assert(competing.beginReadinessCheck().accepted());
    }

    // Either mandatory source failing ends the trusted segment immediately.
    {
        DeviceStage render, microphone;
        int finalized = 0;
        WindowsCaptureSessionController controller("degraded-microphone", [](AudioBatch) { return true; },
            [&](ReasonCode reason, RecordingStopReason) {
                assert(reason == ReasonCode::microphoneEndpointUnavailable);
                ++finalized;
                return CaptureFinalization{false, reason, true};
            });
        render.allowStartup.store(true); microphone.allowStartup.store(true);
        render.allowCleanup.store(true); microphone.allowCleanup.store(true);
        CaptureSessionTestPeer::devices(controller,
            [&](const auto& running, auto& deviceReady, const auto& callback) { render.run(running, deviceReady, callback); },
            [&](const auto& running, auto& deviceReady, const auto& callback) { microphone.run(running, deviceReady, callback); });
        assert(controller.record(ready).state == SessionState::starting);
        waitUntil([&] { return render.initialized.load() && microphone.initialized.load(); });
        assert(controller.pollHealth().state == SessionState::recording);
        CaptureSessionTestPeer::failMicrophoneWorker(controller);
        (void)controller.pollHealth();
        assert(CaptureSessionTestPeer::stopped(controller));
        assert(CaptureSessionTestPeer::push(controller));
        assert(controller.stop().status == TransitionStatus::idempotent);
        render.allowCleanup.store(true);
        waitUntil([&] { return controller.pollHealth().state == SessionState::failed; });
        assert(finalized == 1);
        assert(!controller.finalization().savedLocal && controller.finalization().trustedPrefixRetained);
        assert(controller.finalization().reason == ReasonCode::microphoneEndpointUnavailable);
    }

    // The microphone must never continue unpaired after the render source fails.
    {
        DeviceStage render, microphone;
        std::atomic<int> delivered{0};
        int finalized = 0;
        WindowsCaptureSessionController controller("degraded-render", [&](AudioBatch) {
            ++delivered;
            return true;
        }, [&](ReasonCode reason, RecordingStopReason) {
            assert(reason == ReasonCode::renderEndpointUnavailable);
            ++finalized;
            return CaptureFinalization{false, reason, true};
        });
        render.allowStartup.store(true); microphone.allowStartup.store(true);
        render.allowCleanup.store(true); microphone.allowCleanup.store(true);
        CaptureSessionTestPeer::devices(controller,
            [&](const auto& running, auto& deviceReady, const auto& callback) { render.run(running, deviceReady, callback); },
            [&](const auto& running, auto& deviceReady, const auto& callback) { microphone.run(running, deviceReady, callback); });
        assert(controller.record(ready).state == SessionState::starting);
        waitUntil([&] { return render.initialized.load() && microphone.initialized.load(); });
        assert(controller.pollHealth().state == SessionState::recording);
        waitUntil([&] { return delivered.load() > 0; });
        CaptureSessionTestPeer::failRenderWorker(controller);
        (void)controller.pollHealth();
        assert(CaptureSessionTestPeer::stopped(controller));
        assert(controller.stop().status == TransitionStatus::idempotent);
        waitUntil([&] { return controller.pollHealth().state == SessionState::failed; });
        assert(finalized == 1);
        const auto stoppedAt = delivered.load();
        assert(CaptureSessionTestPeer::push(controller) && delivered.load() == stoppedAt);
        assert(!controller.finalization().savedLocal && controller.finalization().trustedPrefixRetained);
        assert(controller.finalization().reason == ReasonCode::renderEndpointUnavailable);
    }

    // A failed startup never opens the sink, even if the other source is live.
    {
        DeviceStage render;
        std::atomic_bool failMicrophone{false};
        std::atomic<int> delivered{0};
        int finalized = 0;
        WindowsCaptureSessionController controller("async-failure", [&](AudioBatch) {
            ++delivered;
            return true;
        }, [&](ReasonCode reason, RecordingStopReason) {
            assert(reason == ReasonCode::microphoneEndpointUnavailable);
            ++finalized;
            return CaptureFinalization{true, reason};
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
        assert(controller.indicator().snapshot().state == SessionState::stopping);
        render.allowStartup.store(true);
        waitUntil([&] { return render.initialized.load(); });
        assert(controller.pollHealth().state == SessionState::stopping);
        assert(delivered.load() == 0);
        render.allowCleanup.store(true);
        assert(controller.stop().status == TransitionStatus::idempotent);
        waitUntil([&] { return controller.pollHealth().state == SessionState::failed; });
        assert(finalized == 1);
        assert(controller.finalization().reason == ReasonCode::microphoneEndpointUnavailable);
    }

    // Exactly 254 data slots and two reserved typed EOS slots; accepted data
    // drain FIFO before finalization. Overflow and sink failure cannot save as normal.
    for (const int failure : {0, 1, 2, 3}) { // none, overflow, rejected/throwing sink
        std::atomic_bool entered{false}, release{false};
        std::vector<std::int64_t> delivered;
        int finalized = 0;
        WindowsCaptureSessionController* current = nullptr;
        WindowsCaptureSessionController controller("bounded-dispatch", [&](AudioBatch batch) {
            entered.store(true);
            waitUntil([&] { return release.load(); });
            delivered.push_back(batch.ptsFrames);
            if (failure == 3) throw std::runtime_error("synthetic sink failure");
            return failure != 2;
        }, [&](ReasonCode reason, RecordingStopReason) {
            assert(release.load());
            assert(CaptureSessionTestPeer::sourceEndMask(*current) == 3);
            assert(reason == (failure == 1 ? ReasonCode::queueOverflow :
                             failure == 2 ? ReasonCode::clockDiscontinuity :
                             failure == 3 ? ReasonCode::finalizationFailed : ReasonCode::none));
            ++finalized;
            return CaptureFinalization{true, ReasonCode::none};
        });
        current = &controller;
        CaptureSessionTestPeer::begin(controller);
        CaptureSessionTestPeer::startDispatcher(controller);
        assert(CaptureSessionTestPeer::enqueue(controller, 0));
        waitUntil([&] { return entered.load(); });
        for (int sequence = 1; sequence <= 254; ++sequence)
            assert(CaptureSessionTestPeer::enqueue(controller, sequence));
        assert(CaptureSessionTestPeer::pending(controller) == 254);
        if (failure == 1) assert(!CaptureSessionTestPeer::enqueue(controller, 255));
        const auto before = std::chrono::steady_clock::now();
        assert(controller.stop().state == SessionState::stopping);
        assert(std::chrono::steady_clock::now() - before < std::chrono::milliseconds(500));
        assert(CaptureSessionTestPeer::pending(controller) == 256);
        assert(CaptureSessionTestPeer::enqueue(controller, 256)); // late data discarded
        assert(CaptureSessionTestPeer::pending(controller) == 256);
        assert(controller.stop().status == TransitionStatus::idempotent && finalized == 0);
        release.store(true);
        const auto expected = failure == 0 ? SessionState::savedLocal : SessionState::failed;
        waitUntil([&] { return controller.pollHealth().state == expected; });
        assert(finalized == 1);
        assert(delivered.size() == (failure >= 2 ? 1U : 255U));
        for (std::size_t i = 0; i < delivered.size(); ++i) assert(delivered[i] == static_cast<std::int64_t>(i));
    }

    // Completion time, not UI polling cadence, decides whether drain expired.
    // Move only the deadline in these deterministic boundary cases; the existing
    // real five-second test below still checks the production duration.
    for (const bool late : {true, false}) for (const bool priorFault : {false, true}) {
        std::atomic_bool entered{false}, release{false};
        int finalized = 0;
        WindowsCaptureSessionController* current = nullptr;
        const auto expectedReason = late ? ReasonCode::finalizationFailed :
            priorFault ? ReasonCode::clockDiscontinuity : ReasonCode::none;
        WindowsCaptureSessionController controller("drain-between-polls", [&](AudioBatch) {
            entered.store(true);
            waitUntil([&] { return release.load(); });
            return true;
        }, [&](ReasonCode reason, RecordingStopReason) {
            assert(reason == expectedReason);
            assert(CaptureSessionTestPeer::sourceEndMask(*current) == 3);
            ++finalized;
            return CaptureFinalization{true, ReasonCode::none, true, late};
        });
        current = &controller;
        CaptureSessionTestPeer::begin(controller);
        CaptureSessionTestPeer::startDispatcher(controller);
        assert(CaptureSessionTestPeer::enqueue(controller, 0));
        waitUntil([&] { return entered.load(); });
        if (priorFault) CaptureSessionTestPeer::latchFault(controller, ReasonCode::clockDiscontinuity);
        assert(controller.stop().state == SessionState::stopping);
        if (late) CaptureSessionTestPeer::drainDeadline(controller, std::chrono::steady_clock::now());
        release.store(true);
        // No health poll while the sink returns and both EOS cross the queue.
        waitUntil([&] { return CaptureSessionTestPeer::dispatcherFinished(controller); });
        if (!late) CaptureSessionTestPeer::drainDeadline(controller, std::chrono::steady_clock::now());
        const auto terminal = controller.pollHealth();
        assert(terminal.state == (expectedReason == ReasonCode::none ? SessionState::savedLocal : SessionState::failed));
        assert(controller.finalization().reason == expectedReason && controller.finalization().trustedPrefixRetained);
        assert(!controller.finalization().shortRecordingDiscarded);
        assert(CaptureSessionTestPeer::firstFault(controller) ==
               (priorFault ? ReasonCode::clockDiscontinuity : ReasonCode::none));
        assert(controller.stop().status == TransitionStatus::idempotent);
        assert(controller.pollHealth().status == TransitionStatus::idempotent && finalized == 1);
    }

    // EOS and dispatcher completion must not wait for a UI health poll or for
    // device cleanup. Finalization still waits for both native completion fences.
    // A worker completing before the deadline cannot fail just because UI polls
    // later; either worker completing after it must fail even with an idle queue.
    for (const int lateSource : {-1, 0, 1}) {
        DeviceStage render, microphone;
        render.allowStartup.store(true); microphone.allowStartup.store(true);
        std::atomic<int> delivered{0};
        int finalized = 0;
        WindowsCaptureSessionController* current = nullptr;
        WindowsCaptureSessionController controller("worker-drain-between-polls", [&](AudioBatch) {
            ++delivered;
            return true;
        }, [&](ReasonCode reason, RecordingStopReason) {
            assert(reason == (lateSource < 0 ? ReasonCode::none : ReasonCode::finalizationFailed));
            assert(CaptureSessionTestPeer::finished(*current));
            assert(CaptureSessionTestPeer::sourceEndMask(*current) == 3);
            ++finalized;
            return CaptureFinalization{true, ReasonCode::none, true};
        });
        current = &controller;
        CaptureSessionTestPeer::devices(controller,
            [&](const auto& running, auto& deviceReady, const auto& callback) { render.run(running, deviceReady, callback); },
            [&](const auto& running, auto& deviceReady, const auto& callback) { microphone.run(running, deviceReady, callback); });
        assert(controller.record(ready).state == SessionState::starting);
        waitUntil([&] { return render.initialized.load() && microphone.initialized.load(); });
        assert(controller.pollHealth().state == SessionState::recording);
        waitUntil([&] { return delivered.load() > 0; });
        assert(controller.stop().state == SessionState::stopping && finalized == 0);
        waitUntil([&] { return render.cleaning.load() && microphone.cleaning.load(); });
        // Neither worker has returned, yet all accepted data and EOS can drain.
        waitUntil([&] { return CaptureSessionTestPeer::dispatcherFinished(controller); });
        assert(CaptureSessionTestPeer::sourceEndMask(controller) == 3 && finalized == 0);
        assert(!CaptureSessionTestPeer::finished(controller));
        const auto beforeCleanup = delivered.load();
        if (lateSource >= 0) {
            auto& onTime = lateSource == 0 ? microphone : render;
            onTime.allowCleanup.store(true);
            waitUntil([&] { return lateSource == 0
                ? CaptureSessionTestPeer::microphoneFinished(controller)
                : CaptureSessionTestPeer::renderFinished(controller); });
            CaptureSessionTestPeer::drainDeadline(controller, std::chrono::steady_clock::now());
        }
        render.allowCleanup.store(true); microphone.allowCleanup.store(true);
        waitUntil([&] { return CaptureSessionTestPeer::finished(controller); });
        if (lateSource < 0)
            CaptureSessionTestPeer::drainDeadline(controller, std::chrono::steady_clock::now());
        const auto terminal = controller.pollHealth();
        assert(terminal.state == (lateSource < 0 ? SessionState::savedLocal : SessionState::failed));
        assert(controller.finalization().trustedPrefixRetained && finalized == 1);
        assert(delivered.load() == beforeCleanup);
        assert(controller.stop().status == TransitionStatus::idempotent);
        assert(controller.pollHealth().status == TransitionStatus::idempotent && finalized == 1);
    }

    // The direct adapter also records actual sink completion. Acquiring its
    // fence on a later poll must neither hide a late sink nor blame a late UI.
    for (const bool late : {true, false}) {
        std::atomic_bool entered{false}, release{false};
        int finalized = 0;
        WindowsCaptureSessionController controller("direct-drain-between-polls", [&](AudioBatch) {
            entered.store(true);
            waitUntil([&] { return release.load(); });
            return true;
        }, [&](ReasonCode reason, RecordingStopReason) {
            assert(reason == (late ? ReasonCode::finalizationFailed : ReasonCode::none));
            ++finalized;
            return CaptureFinalization{true, ReasonCode::none, true};
        });
        CaptureSessionTestPeer::begin(controller);
        std::thread producer([&] { assert(CaptureSessionTestPeer::push(controller)); });
        waitUntil([&] { return entered.load(); });
        assert(controller.stop().state == SessionState::stopping && finalized == 0);
        if (late) CaptureSessionTestPeer::drainDeadline(controller, std::chrono::steady_clock::now());
        release.store(true);
        producer.join();
        if (!late) CaptureSessionTestPeer::drainDeadline(controller, std::chrono::steady_clock::now());
        assert(controller.pollHealth().state == (late ? SessionState::failed : SessionState::savedLocal));
        assert(controller.finalization().trustedPrefixRetained && finalized == 1);
        assert(controller.stop().status == TransitionStatus::idempotent);
        assert(controller.pollHealth().status == TransitionStatus::idempotent && finalized == 1);
    }

    // An observed timeout must survive an earlier source fault and an
    // asynchronous finalizer; no result may relabel it as a normal save.
    {
        std::atomic_bool entered{false}, release{false};
        int polls = 0;
        bool complete = false;
        WindowsCaptureSessionController controller("drain-timeout-sticky", [&](AudioBatch) {
            entered.store(true);
            waitUntil([&] { return release.load(); });
            return true;
        }, [&](ReasonCode reason, RecordingStopReason) -> std::optional<CaptureFinalization> {
            assert(reason == ReasonCode::finalizationFailed && release.load());
            ++polls;
            if (!complete) return std::nullopt;
            return CaptureFinalization{true, ReasonCode::clockDiscontinuity, true};
        });
        CaptureSessionTestPeer::begin(controller);
        CaptureSessionTestPeer::startDispatcher(controller);
        assert(CaptureSessionTestPeer::enqueue(controller, 0));
        waitUntil([&] { return entered.load(); });
        CaptureSessionTestPeer::latchFault(controller, ReasonCode::clockDiscontinuity);
        assert(controller.stop().state == SessionState::stopping);
        CaptureSessionTestPeer::drainDeadline(controller, std::chrono::steady_clock::now());
        assert(controller.pollHealth().reason == ReasonCode::finalizationFailed && polls == 0);
        release.store(true);
        waitUntil([&] { return CaptureSessionTestPeer::dispatcherFinished(controller); });
        assert(controller.pollHealth().state == SessionState::finalizing && polls == 1);
        assert(controller.pollHealth().reason == ReasonCode::finalizationFailed && polls == 2);
        complete = true;
        assert(controller.pollHealth().state == SessionState::failed && polls == 3);
        assert(controller.finalization().reason == ReasonCode::finalizationFailed);
        assert(!controller.finalization().savedLocal && controller.finalization().trustedPrefixRetained);
        assert(controller.pollHealth().status == TransitionStatus::idempotent && polls == 3);
    }

    // Five seconds is a visible failure deadline, not permission to detach a
    // live sink or finalize over its memory. Exercise real monotonic elapsed time.
    {
        std::atomic_bool entered{false}, release{false};
        int finalized = 0;
        WindowsCaptureSessionController controller("drain-deadline", [&](AudioBatch) {
            entered.store(true);
            while (!release.load()) std::this_thread::yield();
            return true;
        }, [&](ReasonCode reason, RecordingStopReason) {
            assert(release.load() && reason == ReasonCode::finalizationFailed);
            ++finalized;
            return CaptureFinalization{true, ReasonCode::none, true};
        });
        CaptureSessionTestPeer::begin(controller);
        CaptureSessionTestPeer::startDispatcher(controller);
        assert(CaptureSessionTestPeer::enqueue(controller, 0));
        waitUntil([&] { return entered.load(); });
        assert(controller.stop().state == SessionState::stopping);
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(5'050);
        while (std::chrono::steady_clock::now() < deadline) {
            assert(controller.pollHealth().state == SessionState::stopping && finalized == 0);
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
        const auto before = std::chrono::steady_clock::now();
        const auto pending = controller.pollHealth();
        assert(std::chrono::steady_clock::now() - before < std::chrono::milliseconds(500));
        assert(pending.state == SessionState::stopping && pending.reason == ReasonCode::finalizationFailed);
        assert(controller.indicator().snapshot().visible);
        assert(controller.indicator().snapshot().reason == ReasonCode::finalizationFailed);
        assert(controller.finalization().reason == ReasonCode::finalizationFailed && finalized == 0);
        WindowsDesktopSession competing("drain-still-owns-lease");
        assert(!competing.beginReadinessCheck().accepted());
        assert(controller.stop().status == TransitionStatus::idempotent);
        release.store(true);
        waitUntil([&] { return controller.pollHealth().state == SessionState::failed; });
        assert(!controller.finalization().savedLocal && finalized == 1);
        assert(competing.beginReadinessCheck().accepted());
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
        }, [&](ReasonCode reason, RecordingStopReason) {
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
        waitUntil([&] { return controller.pollHealth().state == SessionState::savedLocal; });
        assert(finalized == 1);
    }

    for (const bool workerFault : {false, true}) {
        int finalized = 0;
        int acceptedBatches = 0;
        bool reject = false;
        WindowsCaptureSessionController* current = nullptr;
        WindowsCaptureSessionController controller("fault", [&](AudioBatch) {
            ++acceptedBatches;
            return !reject;
        }, [&](ReasonCode reason, RecordingStopReason) {
            ++finalized;
            // Синтетический сбой подставлен системному звуку: пустой
            // идентификатор устройства называется недоступным устройством.
            assert(reason == (workerFault ? ReasonCode::renderEndpointUnavailable : ReasonCode::clockDiscontinuity));
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
            [&](ReasonCode reason, RecordingStopReason) -> std::optional<CaptureFinalization> {
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
        // Drain has already completed: its deadline must not time the separate
        // writer job or convert a late UI result poll into capture failure.
        CaptureSessionTestPeer::drainDeadline(controller, std::chrono::steady_clock::now());
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
    }, [&](ReasonCode reason, RecordingStopReason) {
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
    if (normal.session().state() == SessionState::stopping) {
        waitUntil([&] { return normal.pollHealth().state == SessionState::savedLocal; });
    }
    const int stoppedAt = batches.load();
    assert(CaptureSessionTestPeer::push(normal));
    assert(batches.load() == stoppedAt);
    assert(normal.stop().status == TransitionStatus::idempotent && normalFinalizations == 1);

    WindowsCaptureSessionController throwing("throwing", [](AudioBatch) { return true; },
        [](ReasonCode, RecordingStopReason) -> CaptureFinalization { throw std::runtime_error("synthetic finalizer fault"); });
    CaptureSessionTestPeer::begin(throwing);
    assert(throwing.stop().reason == ReasonCode::finalizationFailed);
    assert(CaptureSessionTestPeer::stopped(throwing));
    assert(throwing.stop().status == TransitionStatus::idempotent);
    return 0;
}
