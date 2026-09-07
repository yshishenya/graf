#pragma once

#include "AudioTypes.h"
#include "ClockMapper.h"
#include "WasapiEndpointEnumerator.h"

#include <cstddef>
#include <atomic>
#include <cstdint>
#include <functional>
#include <memory>
#include <string>

namespace graf::windows {

class AudioNormalizer;

enum class CaptureWorkerError {
    none,
    alreadyRunning,
    invalidEndpoint,
    unsupportedFormat,
    initializationFailed,
    deviceInvalidated,
    bufferOverflow,
    clockDiscontinuity,
    unsupportedPlatform,
};

struct CaptureWorkerConfig {
    std::size_t maxBatchFrames = 4'800;
    std::uint64_t routeGeneration = 1;
    std::uint64_t clockDomain = 1;
};

using CaptureBatchCallback = std::function<bool(AudioBatch)>;

class WasapiCaptureWorker final {
public:
    WasapiCaptureWorker(WasapiEndpointSnapshot endpoint, bool renderLoopback,
                        CaptureWorkerConfig config = {});
    ~WasapiCaptureWorker();

    WasapiCaptureWorker(const WasapiCaptureWorker&) = delete;
    WasapiCaptureWorker& operator=(const WasapiCaptureWorker&) = delete;

    // UI-owner-thread commands. Start launches acquisition without waiting for
    // COM/device initialization; Stop requests cancellation without joining.
    [[nodiscard]] CaptureWorkerError start(CaptureBatchCallback callback);
    void stop() noexcept;
    [[nodiscard]] bool ready() const noexcept;
    [[nodiscard]] bool finished() const noexcept;
    [[nodiscard]] bool running() const noexcept;
    [[nodiscard]] CaptureWorkerError lastError() const noexcept;
    [[nodiscard]] CaptureClockDiagnostics clockDiagnostics() const noexcept;

private:
    friend struct CaptureSessionTestPeer;
    // The device loop and packet regressions share copy/release/normalization.
    [[nodiscard]] bool consumePacket(ClockMapper& mapper, AudioNormalizer& normalizer,
        ClockObservation packet, const void* data, std::uint16_t channels, bool float32,
        const std::function<bool(std::uint32_t)>& releaseBuffer);
#ifdef _WIN32
    [[nodiscard]] static std::wstring utf8ToWide(const std::string& value);
#endif
    // Tests replace only the device body, retaining the real thread, cancellation,
    // exception and completion lifecycle. No production device adapter is needed.
    using DeviceRun = std::function<void(const std::atomic_bool&, std::atomic_bool&, const CaptureBatchCallback&)>;
    DeviceRun deviceRunForTesting_;
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace graf::windows
