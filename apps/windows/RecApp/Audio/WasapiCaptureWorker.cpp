#include "WasapiCaptureWorker.h"

#include "AudioNormalizer.h"
#include "ClockMapper.h"

#include <algorithm>
#include <array>
#include <atomic>
#include <limits>
#include <mutex>
#include <thread>

#ifdef _WIN32
#include <audioclient.h>
#include <ksmedia.h>
#include <mmdeviceapi.h>
#include <wrl/client.h>
#include <windows.h>

namespace {
struct PcmFormat {
    bool float32 = false;
    bool pcm16 = false;
};

PcmFormat inspectFormat(const WAVEFORMATEX& format) {
    PcmFormat result;
    if (format.wFormatTag == WAVE_FORMAT_IEEE_FLOAT && format.wBitsPerSample == 32) {
        result.float32 = true;
    } else if (format.wFormatTag == WAVE_FORMAT_PCM && format.wBitsPerSample == 16) {
        result.pcm16 = true;
    } else if (format.wFormatTag == WAVE_FORMAT_EXTENSIBLE &&
               format.cbSize >= sizeof(WAVEFORMATEXTENSIBLE) - sizeof(WAVEFORMATEX)) {
        const auto& extensible = reinterpret_cast<const WAVEFORMATEXTENSIBLE&>(format);
        result.float32 = extensible.SubFormat == KSDATAFORMAT_SUBTYPE_IEEE_FLOAT &&
            format.wBitsPerSample == 32;
        result.pcm16 = extensible.SubFormat == KSDATAFORMAT_SUBTYPE_PCM &&
            format.wBitsPerSample == 16;
    }
    const auto bytesPerSample = result.float32 || result.pcm16 ? format.wBitsPerSample / 8 : 0;
    if (format.nChannels == 0 || format.nChannels > 32 || format.nSamplesPerSec < 8'000 ||
        format.nSamplesPerSec > 192'000 ||
        bytesPerSample == 0 || format.nBlockAlign != format.nChannels * bytesPerSample ||
        format.nAvgBytesPerSec != format.nSamplesPerSec * format.nBlockAlign) {
        return {};
    }
    return result;
}
}
#endif

namespace graf::windows {

#ifdef _WIN32
std::wstring WasapiCaptureWorker::utf8ToWide(const std::string& value) {
    if (value.empty() || value.size() > static_cast<std::size_t>(std::numeric_limits<int>::max()) ||
        value.find('\0') != std::string::npos) return {};
    const auto bytes = static_cast<int>(value.size());
    const int length = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), bytes, nullptr, 0);
    if (length <= 0) return {};
    std::wstring result(static_cast<std::size_t>(length), L'\0');
    if (MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), bytes, result.data(), length) != length)
        return {};
    return result;
}
#endif

struct WasapiCaptureWorker::Impl {
    static constexpr std::size_t maxTraceEvents = 64;
    WasapiEndpointSnapshot endpoint;
    bool renderLoopback = false;
    CaptureWorkerConfig config;
    CaptureBatchCallback callback;
    std::atomic_bool running{false};
    std::atomic_bool ready{false};
    std::atomic_bool finished{true};
    std::chrono::steady_clock::time_point finishedAt{};
    std::atomic<CaptureWorkerError> error{CaptureWorkerError::none};
    std::atomic<ClockFault> clockFault{ClockFault::none};
    std::atomic<std::uint32_t> startupDiscardedFrames{0};
    mutable std::mutex traceMutex;
    std::array<CaptureStageTrace, maxTraceEvents> trace{};
    std::size_t traceStart = 0;
    std::size_t traceSize = 0;
    std::uint64_t nextTraceSequence = 0;
    std::thread thread;

    void recordTrace(CaptureStage stage, std::int32_t hresult = 0, std::uint32_t flags = 0,
                     std::uint32_t frameCount = 0, std::uint64_t devicePosition = 0,
                     std::uint64_t qpcPosition = 0, std::uint64_t audioClockPosition = 0,
                     std::uint64_t audioClockFrequency = 0, bool released = false) noexcept {
        std::lock_guard<std::mutex> lock(traceMutex);
        CaptureStageTrace event;
        event.sequence = ++nextTraceSequence;
        event.stage = stage;
        event.hresult = hresult;
        event.flags = flags;
        event.frameCount = frameCount;
        event.devicePosition = devicePosition;
        event.qpcPosition = qpcPosition;
        event.audioClockPosition = audioClockPosition;
        event.audioClockFrequency = audioClockFrequency;
        event.released = released;
        const auto index = (traceStart + traceSize) % maxTraceEvents;
        if (traceSize < maxTraceEvents) ++traceSize;
        else traceStart = (traceStart + 1) % maxTraceEvents;
        trace[index] = event;
    }

    CaptureClockDiagnostics diagnostics() const noexcept {
        CaptureClockDiagnostics result;
        result.startupDiscardedFrames = startupDiscardedFrames.load();
        result.fault = clockFault.load();
        std::lock_guard<std::mutex> lock(traceMutex);
        result.traceCount = static_cast<std::uint32_t>(traceSize);
        if (traceSize != 0) {
            result.lastTrace = trace[(traceStart + traceSize - 1) % maxTraceEvents];
        }
        return result;
    }

    void run(WasapiCaptureWorker& owner) {
#ifndef _WIN32
        (void)owner;
        error.store(CaptureWorkerError::unsupportedPlatform);
#else
        HRESULT init = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
        if (FAILED(init)) {
            recordTrace(CaptureStage::initialize, static_cast<std::int32_t>(init));
            error.store(CaptureWorkerError::initializationFailed);
            return;
        }
        struct NativeResources {
            HANDLE eventHandle = nullptr;
            WAVEFORMATEX* format = nullptr;
            ~NativeResources() {
                if (format != nullptr) CoTaskMemFree(format);
                if (eventHandle != nullptr) CloseHandle(eventHandle);
                CoUninitialize();
            }
        } resources;
        // Declared after the apartment guard so COM interfaces release first,
        // including allocation/normalization exceptions during capture.
        Microsoft::WRL::ComPtr<IMMDeviceEnumerator> enumerator;
        Microsoft::WRL::ComPtr<IMMDevice> device;
        Microsoft::WRL::ComPtr<IAudioClient> client;
        Microsoft::WRL::ComPtr<IAudioCaptureClient> capture;
        Microsoft::WRL::ComPtr<IAudioClock> audioClock;
        auto& eventHandle = resources.eventHandle;
        auto& format = resources.format;
        do {
            if (!running.load()) break;
            const auto enumeratorResult = CoCreateInstance(__uuidof(MMDeviceEnumerator), nullptr, CLSCTX_ALL,
                                                           IID_PPV_ARGS(&enumerator));
            recordTrace(CaptureStage::initialize, static_cast<std::int32_t>(enumeratorResult));
            if (FAILED(enumeratorResult)) { error = CaptureWorkerError::initializationFailed; break; }
            if (!running.load()) break;
            const auto id = WasapiCaptureWorker::utf8ToWide(endpoint.stableId);
            const auto deviceResult = id.empty() ? E_INVALIDARG : enumerator->GetDevice(id.c_str(), &device);
            recordTrace(CaptureStage::initialize, static_cast<std::int32_t>(deviceResult));
            if (FAILED(deviceResult)) {
                error = CaptureWorkerError::invalidEndpoint; break;
            }
            if (!running.load()) break;
            const auto activateResult = device->Activate(__uuidof(IAudioClient), CLSCTX_ALL, nullptr,
                                                          reinterpret_cast<void**>(client.GetAddressOf()));
            if (FAILED(activateResult)) {
                error = activateResult == E_ACCESSDENIED ? CaptureWorkerError::accessDenied
                                                         : CaptureWorkerError::initializationFailed;
                break;
            }
            if (!running.load()) break;
            const auto formatResult = client->GetMixFormat(&format);
            recordTrace(CaptureStage::initialize, static_cast<std::int32_t>(formatResult));
            if (FAILED(formatResult)) { error = CaptureWorkerError::initializationFailed; break; }
            if (!running.load()) break;
            const auto pcmFormat = inspectFormat(*format);
            if (!pcmFormat.float32 && !pcmFormat.pcm16) {
                error.store(CaptureWorkerError::unsupportedFormat);
                break;
            }
            eventHandle = CreateEventW(nullptr, FALSE, FALSE, nullptr);
            if (eventHandle == nullptr) { error = CaptureWorkerError::initializationFailed; break; }
            constexpr REFERENCE_TIME bufferDuration = 100'000;
            DWORD flags = AUDCLNT_STREAMFLAGS_EVENTCALLBACK;
            if (renderLoopback) flags |= AUDCLNT_STREAMFLAGS_LOOPBACK;
            const auto initializeResult = client->Initialize(AUDCLNT_SHAREMODE_SHARED, flags, bufferDuration, 0,
                                                             format, nullptr);
            if (FAILED(initializeResult)) {
                error = initializeResult == E_ACCESSDENIED ? CaptureWorkerError::accessDenied
                                                           : CaptureWorkerError::initializationFailed;
                break;
            }
            if (!running.load()) break;
            const auto eventResult = client->SetEventHandle(eventHandle);
            recordTrace(CaptureStage::initialize, static_cast<std::int32_t>(eventResult));
            if (FAILED(eventResult)) { error = CaptureWorkerError::initializationFailed; break; }
            if (!running.load()) break;
            const auto captureResult = client->GetService(IID_PPV_ARGS(&capture));
            recordTrace(CaptureStage::initialize, static_cast<std::int32_t>(captureResult));
            if (FAILED(captureResult)) {
                error.store(CaptureWorkerError::initializationFailed);
                break;
            }
            UINT64 audioClockFrequency = 0;
            const auto audioClockResult = client->GetService(IID_PPV_ARGS(&audioClock));
            recordTrace(CaptureStage::audioClock, static_cast<std::int32_t>(audioClockResult),
                        0, 0, 0, 0, 0, audioClockFrequency);
            const auto frequencyResult = audioClockResult == S_OK
                ? audioClock->GetFrequency(&audioClockFrequency) : E_FAIL;
            recordTrace(CaptureStage::audioClock, static_cast<std::int32_t>(frequencyResult),
                        0, 0, 0, 0, 0, audioClockFrequency);
            if (audioClockResult != S_OK || frequencyResult != S_OK || audioClockFrequency == 0) {
                error.store(CaptureWorkerError::initializationFailed);
                break;
            }
            if (!running.load()) break;
            const auto startResult = client->Start();
            if (FAILED(startResult)) {
                error.store(startResult == E_ACCESSDENIED ? CaptureWorkerError::accessDenied
                                                          : CaptureWorkerError::initializationFailed);
                break;
            }
            static_assert(ClockObservation::dataDiscontinuity == AUDCLNT_BUFFERFLAGS_DATA_DISCONTINUITY &&
                ClockObservation::silent == AUDCLNT_BUFFERFLAGS_SILENT &&
                ClockObservation::timestampError == AUDCLNT_BUFFERFLAGS_TIMESTAMP_ERROR);
            ClockMapper clockMapper;
            AudioNormalizer normalizer(config.maxBatchFrames * 6);
            while (running.load() && error.load() == CaptureWorkerError::none) {
                const auto waitResult = WaitForSingleObject(eventHandle, 500);
                recordTrace(CaptureStage::wait, static_cast<std::int32_t>(waitResult));
                if (waitResult == WAIT_TIMEOUT) continue;
                if (waitResult != WAIT_OBJECT_0) {
                    error.store(CaptureWorkerError::waitFailed);
                    break;
                }
                if (!running.load()) break;
                UINT32 frames = 0;
                auto packetResult = capture->GetNextPacketSize(&frames);
                recordTrace(CaptureStage::nextPacketSize, static_cast<std::int32_t>(packetResult), 0, frames);
                if (FAILED(packetResult)) {
                    error.store(CaptureWorkerError::packetReadFailed);
                    break;
                }
                while (frames > 0 && running.load()) {
                    BYTE* data = nullptr; UINT32 count = 0; DWORD flagsRead = 0;
                    UINT64 devicePosition = 0; UINT64 qpcPosition = 0;
                    const auto bufferResult = capture->GetBuffer(&data, &count, &flagsRead,
                                                                 &devicePosition, &qpcPosition);
                    recordTrace(CaptureStage::getBuffer, static_cast<std::int32_t>(bufferResult), flagsRead,
                                count, devicePosition, qpcPosition);
                    if (FAILED(bufferResult)) {
                        error.store(CaptureWorkerError::bufferReadFailed); break;
                    }
                    if (count == 0) {
                        const auto releaseResult = capture->ReleaseBuffer(0);
                        recordTrace(CaptureStage::releaseBuffer, static_cast<std::int32_t>(releaseResult),
                                    flagsRead, count, devicePosition, qpcPosition, 0, audioClockFrequency,
                                    SUCCEEDED(releaseResult));
                        packetResult = capture->GetNextPacketSize(&frames);
                        recordTrace(CaptureStage::nextPacketSize, static_cast<std::int32_t>(packetResult),
                                    0, frames);
                        if (FAILED(releaseResult)) {
                            error.store(CaptureWorkerError::releaseFailed);
                            break;
                        }
                        if (FAILED(packetResult)) {
                            error.store(CaptureWorkerError::packetReadFailed);
                            break;
                        }
                        continue;
                    }
                    UINT64 audioClockPosition = 0;
                    const auto positionResult = audioClock->GetPosition(&audioClockPosition, nullptr);
                    recordTrace(CaptureStage::audioClock, static_cast<std::int32_t>(positionResult), flagsRead,
                                count, devicePosition, qpcPosition, audioClockPosition, audioClockFrequency);
                    if (!owner.consumePacket(clockMapper, normalizer,
                            {qpcPosition, devicePosition, format->nSamplesPerSec, flagsRead, count,
                             audioClockPosition, audioClockFrequency, static_cast<std::int32_t>(positionResult)},
                            data, format->nChannels, pcmFormat.float32,
                            [&](std::uint32_t consumed) {
                                const auto releaseResult = capture->ReleaseBuffer(consumed);
                                return CaptureReleaseResult{
                                    SUCCEEDED(releaseResult), static_cast<std::int32_t>(releaseResult)};
                            })) break;
                    packetResult = capture->GetNextPacketSize(&frames);
                    recordTrace(CaptureStage::nextPacketSize, static_cast<std::int32_t>(packetResult),
                                0, frames);
                    if (FAILED(packetResult)) {
                        error.store(CaptureWorkerError::packetReadFailed);
                        break;
                    }
                }
            }
            client->Stop();
        } while (false);
        // All native resources must be released before the outer thread wrapper
        // publishes finished; UI finalization relies on that completion fence.
#endif
    }
};

bool WasapiCaptureWorker::consumePacket(ClockMapper& mapper, AudioNormalizer& normalizer,
    ClockObservation packet, const void* data, std::uint16_t channels, bool float32,
    const std::function<CaptureReleaseResult(std::uint32_t)>& releaseBuffer) {
    const auto release = [&] {
        const auto result = releaseBuffer(packet.frameCount);
        impl_->recordTrace(CaptureStage::releaseBuffer, result.hresult, packet.flags,
                           packet.frameCount, packet.deviceFrames, packet.qpc100ns,
                           packet.audioClockPosition, packet.audioClockFrequency, result.succeeded);
        if (result.succeeded) return true;
        impl_->error.store(CaptureWorkerError::releaseFailed);
        return false;
    };
    if (impl_->error.load() != CaptureWorkerError::none) { (void)release(); return false; }
    if (packet.audioClockResult != 0) {
        impl_->error.store(CaptureWorkerError::audioClockFailed);
        (void)release();
        return false;
    }
    if (packet.frameCount > impl_->config.maxBatchFrames || channels == 0 || channels > 32) {
        impl_->clockFault.store(ClockFault::invalidPacket);
        impl_->error.store(CaptureWorkerError::bufferOverflow);
        (void)release();
        return false;
    }
    const auto mapping = mapper.observe(packet);
    if (mapping.discardStartup) {
        // Do not touch the audio pointer or advance normalizer/sink state.
        if (!release()) return false;
        impl_->startupDiscardedFrames.store(packet.frameCount);
        return true;
    }
    if (!mapping.valid) {
        impl_->clockFault.store(mapping.fault);
        impl_->error.store(CaptureWorkerError::clockDiscontinuity);
        (void)release();
        return false;
    }
    AudioBatch batch;
    batch.source = impl_->renderLoopback ? AudioSource::systemRender : AudioSource::microphone;
    batch.sampleRate = packet.sampleRate;
    batch.channels = channels;
    batch.routeGeneration = impl_->config.routeGeneration;
    batch.clockDomain = impl_->config.clockDomain;
    batch.samples.resize(static_cast<std::size_t>(packet.frameCount) * channels);
    const bool silent = (packet.flags & ClockObservation::silent) != 0;
    if (!silent && data != nullptr && float32) {
        const auto* samples = static_cast<const float*>(data);
        std::copy(samples, samples + batch.samples.size(), batch.samples.begin());
    } else if (!silent && data != nullptr) {
        const auto* samples = static_cast<const std::int16_t*>(data);
        for (std::size_t i = 0; i < batch.samples.size(); ++i) batch.samples[i] = samples[i] / 32768.0F;
    } else if (!silent) {
        impl_->error.store(CaptureWorkerError::normalizationFailed);
        (void)release();
        return false;
    }
    if (!release()) return false;
    AudioBatch normalized;
    // The normalizer validates finite samples as well as the packet format.
    const auto normalizedOk = normalizer.normalize(std::move(batch), mapping.qpc100ns, normalized);
    impl_->recordTrace(CaptureStage::normalize, normalizedOk ? 0 : -1, packet.flags,
                       packet.frameCount, packet.deviceFrames, packet.qpc100ns,
                       packet.audioClockPosition, packet.audioClockFrequency);
    if (!normalizedOk) {
        impl_->error.store(CaptureWorkerError::normalizationFailed);
        return false;
    }
    if (impl_->running.load() && !normalized.samples.empty()) {
        try {
            const auto accepted = impl_->callback(std::move(normalized));
            impl_->recordTrace(CaptureStage::callback, accepted ? 0 : -1, packet.flags,
                               packet.frameCount, packet.deviceFrames, packet.qpc100ns,
                               packet.audioClockPosition, packet.audioClockFrequency);
            if (!accepted) {
                impl_->error.store(CaptureWorkerError::sinkRejected);
                return false;
            }
        } catch (...) {
            impl_->recordTrace(CaptureStage::callback, -1, packet.flags, packet.frameCount,
                               packet.deviceFrames, packet.qpc100ns, packet.audioClockPosition,
                               packet.audioClockFrequency);
            impl_->error.store(CaptureWorkerError::initializationFailed);
            return false;
        }
        impl_->ready.store(true);
    }
    return true;
}

WasapiCaptureWorker::WasapiCaptureWorker(WasapiEndpointSnapshot endpoint, bool renderLoopback,
                                         CaptureWorkerConfig config)
    : impl_(std::make_unique<Impl>()) {
    impl_->endpoint = std::move(endpoint);
    impl_->renderLoopback = renderLoopback;
    impl_->config = config;
}

WasapiCaptureWorker::~WasapiCaptureWorker() {
    stop();
    // Destruction is the final ownership fence, not a cancellable UI operation.
    // A driver/COM call cannot safely be force-terminated or detached with its sink.
    if (impl_->thread.joinable()) impl_->thread.join();
}

CaptureWorkerError WasapiCaptureWorker::start(CaptureBatchCallback callback) {
    if (!callback) return CaptureWorkerError::initializationFailed;
    if (!finished()) return CaptureWorkerError::alreadyRunning;
    if (impl_->endpoint.stableId.empty() || impl_->endpoint.channels == 0 ||
        (impl_->renderLoopback && impl_->endpoint.flow != WasapiDataFlow::render) ||
        (!impl_->renderLoopback && !WasapiEndpointEnumerator::isAllowedMicrophone(impl_->endpoint))) {
        impl_->error.store(CaptureWorkerError::invalidEndpoint);
        impl_->running.store(false);
        return CaptureWorkerError::invalidEndpoint;
    }
    if (impl_->thread.joinable()) impl_->thread.join();
    impl_->callback = std::move(callback);
    impl_->error.store(CaptureWorkerError::none);
    impl_->clockFault.store(ClockFault::none);
    impl_->startupDiscardedFrames.store(0);
    {
        std::lock_guard<std::mutex> lock(impl_->traceMutex);
        impl_->traceStart = 0;
        impl_->traceSize = 0;
        impl_->nextTraceSequence = 0;
    }
    impl_->ready.store(false);
    impl_->finishedAt = {};
    impl_->running.store(true);
    impl_->finished.store(false);
    try {
        impl_->thread = std::thread([this] {
            try {
                if (impl_->running.load()) {
                    if (deviceRunForTesting_) deviceRunForTesting_(impl_->running, impl_->ready, impl_->callback);
                    else impl_->run(*this);
                }
            } catch (...) { impl_->error.store(CaptureWorkerError::initializationFailed); }
            impl_->running.store(false);
            // run() has returned: native resources and the final callback are
            // gone. Publish their actual completion, not a later UI poll time.
            impl_->finishedAt = std::chrono::steady_clock::now();
            impl_->finished.store(true, std::memory_order_release);
        });
    } catch (...) {
        impl_->error.store(CaptureWorkerError::initializationFailed);
        impl_->running.store(false);
        impl_->finishedAt = std::chrono::steady_clock::now();
        impl_->finished.store(true, std::memory_order_release);
        return CaptureWorkerError::initializationFailed;
    }
    return CaptureWorkerError::none;
}

void WasapiCaptureWorker::stop() noexcept {
    if (impl_ == nullptr) return;
    impl_->running.store(false);
}

bool WasapiCaptureWorker::ready() const noexcept { return impl_->ready.load() && impl_->running.load(); }

bool WasapiCaptureWorker::finished() const noexcept { return impl_->finished.load(std::memory_order_acquire); }

std::chrono::steady_clock::time_point WasapiCaptureWorker::finishedAt() const noexcept {
    return finished() ? impl_->finishedAt : std::chrono::steady_clock::time_point{};
}

bool WasapiCaptureWorker::running() const noexcept { return impl_ != nullptr && impl_->running.load(); }

CaptureWorkerError WasapiCaptureWorker::lastError() const noexcept {
    return impl_ == nullptr ? CaptureWorkerError::initializationFailed : impl_->error.load();
}

CaptureClockDiagnostics WasapiCaptureWorker::clockDiagnostics() const noexcept {
    return impl_->diagnostics();
}

} // namespace graf::windows
