#include "WasapiCaptureWorker.h"

#include "AudioNormalizer.h"
#include "ClockMapper.h"

#include <algorithm>
#include <atomic>
#include <limits>
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
    WasapiEndpointSnapshot endpoint;
    bool renderLoopback = false;
    CaptureWorkerConfig config;
    CaptureBatchCallback callback;
    std::atomic_bool running{false};
    std::atomic_bool ready{false};
    std::atomic_bool finished{true};
    std::atomic<CaptureWorkerError> error{CaptureWorkerError::none};
    std::atomic<ClockFault> clockFault{ClockFault::none};
    std::atomic<std::uint32_t> startupDiscardedFrames{0};
    std::thread thread;
    void run(WasapiCaptureWorker& owner) {
#ifndef _WIN32
        (void)owner;
        error.store(CaptureWorkerError::unsupportedPlatform);
#else
        HRESULT init = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
        if (FAILED(init)) {
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
            if (FAILED(CoCreateInstance(__uuidof(MMDeviceEnumerator), nullptr, CLSCTX_ALL,
                                        IID_PPV_ARGS(&enumerator)))) { error = CaptureWorkerError::initializationFailed; break; }
            if (!running.load()) break;
            const auto id = WasapiCaptureWorker::utf8ToWide(endpoint.stableId);
            if (id.empty() || FAILED(enumerator->GetDevice(id.c_str(), &device))) {
                error = CaptureWorkerError::invalidEndpoint; break;
            }
            if (!running.load()) break;
            if (FAILED(device->Activate(__uuidof(IAudioClient), CLSCTX_ALL, nullptr,
                                        reinterpret_cast<void**>(client.GetAddressOf())))) {
                error = CaptureWorkerError::initializationFailed; break;
            }
            if (!running.load()) break;
            if (FAILED(client->GetMixFormat(&format))) { error = CaptureWorkerError::initializationFailed; break; }
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
            if (FAILED(client->Initialize(AUDCLNT_SHAREMODE_SHARED, flags, bufferDuration, 0,
                                           format, nullptr))) {
                error = CaptureWorkerError::initializationFailed; break;
            }
            if (!running.load()) break;
            if (FAILED(client->SetEventHandle(eventHandle))) { error = CaptureWorkerError::initializationFailed; break; }
            if (!running.load()) break;
            if (FAILED(client->GetService(IID_PPV_ARGS(&capture)))) {
                error.store(CaptureWorkerError::initializationFailed);
                break;
            }
            UINT64 audioClockFrequency = 0;
            if (FAILED(client->GetService(IID_PPV_ARGS(&audioClock))) ||
                FAILED(audioClock->GetFrequency(&audioClockFrequency)) || audioClockFrequency == 0) {
                error.store(CaptureWorkerError::initializationFailed);
                break;
            }
            if (!running.load()) break;
            if (FAILED(client->Start())) { error.store(CaptureWorkerError::initializationFailed); break; }
            static_assert(ClockObservation::dataDiscontinuity == AUDCLNT_BUFFERFLAGS_DATA_DISCONTINUITY &&
                ClockObservation::silent == AUDCLNT_BUFFERFLAGS_SILENT &&
                ClockObservation::timestampError == AUDCLNT_BUFFERFLAGS_TIMESTAMP_ERROR);
            ClockMapper clockMapper;
            AudioNormalizer normalizer(config.maxBatchFrames * 6);
            while (running.load() && error.load() == CaptureWorkerError::none) {
                if (WaitForSingleObject(eventHandle, 500) == WAIT_TIMEOUT) continue;
                if (!running.load()) break;
                UINT32 frames = 0;
                if (FAILED(capture->GetNextPacketSize(&frames))) {
                    error.store(CaptureWorkerError::deviceInvalidated);
                    break;
                }
                while (frames > 0 && running.load()) {
                    BYTE* data = nullptr; UINT32 count = 0; DWORD flagsRead = 0;
                    UINT64 devicePosition = 0; UINT64 qpcPosition = 0;
                    if (FAILED(capture->GetBuffer(&data, &count, &flagsRead, &devicePosition, &qpcPosition))) {
                        error.store(CaptureWorkerError::deviceInvalidated); break;
                    }
                    if (count == 0) {
                        if (FAILED(capture->ReleaseBuffer(0)) || FAILED(capture->GetNextPacketSize(&frames))) {
                            error.store(CaptureWorkerError::deviceInvalidated);
                            break;
                        }
                        continue;
                    }
                    UINT64 audioClockPosition = 0;
                    if (FAILED(audioClock->GetPosition(&audioClockPosition, nullptr))) {
                        error.store(CaptureWorkerError::deviceInvalidated);
                        if (FAILED(capture->ReleaseBuffer(count))) break;
                        break;
                    }
                    if (!owner.consumePacket(clockMapper, normalizer,
                            {qpcPosition, devicePosition, format->nSamplesPerSec, flagsRead, count,
                             audioClockPosition, audioClockFrequency},
                            data, format->nChannels, pcmFormat.float32,
                            [&](std::uint32_t consumed) { return SUCCEEDED(capture->ReleaseBuffer(consumed)); })) break;
                    if (FAILED(capture->GetNextPacketSize(&frames))) {
                        error.store(CaptureWorkerError::deviceInvalidated);
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
    const std::function<bool(std::uint32_t)>& releaseBuffer) {
    const auto release = [&] {
        if (releaseBuffer(packet.frameCount)) return true;
        impl_->error.store(CaptureWorkerError::deviceInvalidated);
        return false;
    };
    if (impl_->error.load() != CaptureWorkerError::none) { (void)release(); return false; }
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
        impl_->error.store(CaptureWorkerError::unsupportedFormat);
        (void)release();
        return false;
    }
    if (!release()) return false;
    AudioBatch normalized;
    // The normalizer validates finite samples as well as the packet format.
    if (!normalizer.normalize(std::move(batch), mapping.qpc100ns, normalized)) {
        impl_->error.store(CaptureWorkerError::unsupportedFormat);
        return false;
    }
    if (impl_->running.load() && !normalized.samples.empty()) {
        try {
            if (!impl_->callback(std::move(normalized))) {
                impl_->error.store(CaptureWorkerError::bufferOverflow);
                return false;
            }
        } catch (...) {
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
    impl_->ready.store(false);
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
            impl_->finished.store(true, std::memory_order_release);
        });
    } catch (...) {
        impl_->error.store(CaptureWorkerError::initializationFailed);
        impl_->running.store(false);
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

bool WasapiCaptureWorker::running() const noexcept { return impl_ != nullptr && impl_->running.load(); }

CaptureWorkerError WasapiCaptureWorker::lastError() const noexcept {
    return impl_ == nullptr ? CaptureWorkerError::initializationFailed : impl_->error.load();
}

CaptureClockDiagnostics WasapiCaptureWorker::clockDiagnostics() const noexcept {
    return {impl_->startupDiscardedFrames.load(), impl_->clockFault.load()};
}

} // namespace graf::windows
