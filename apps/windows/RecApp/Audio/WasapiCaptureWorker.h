#pragma once

#include "AudioTypes.h"
#include "WasapiEndpointEnumerator.h"

#include <cstddef>
#include <cstdint>
#include <functional>
#include <memory>

namespace graf::windows {

enum class CaptureWorkerError {
    none,
    alreadyRunning,
    invalidEndpoint,
    initializationFailed,
    deviceInvalidated,
    bufferOverflow,
    unsupportedPlatform,
};

struct CaptureWorkerConfig {
    std::size_t maxBatchFrames = 4'800;
    std::size_t maxQueuedFrames = 960'000;
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

    [[nodiscard]] CaptureWorkerError start(CaptureBatchCallback callback);
    void stop() noexcept;
    [[nodiscard]] bool running() const noexcept;
    [[nodiscard]] CaptureWorkerError lastError() const noexcept;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace graf::windows
