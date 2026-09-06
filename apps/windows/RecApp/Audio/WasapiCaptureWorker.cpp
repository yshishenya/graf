#include "WasapiCaptureWorker.h"

#include "AudioNormalizer.h"
#include "ClockMapper.h"

#include <algorithm>
#include <atomic>
#include <cmath>
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
    std::thread thread;
    void run() {
#ifndef _WIN32
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
        auto& eventHandle = resources.eventHandle;
        auto& format = resources.format;
        do {
            if (!running.load()) break;
            LARGE_INTEGER qpcFrequency{};
            if (!QueryPerformanceFrequency(&qpcFrequency) || qpcFrequency.QuadPart <= 0) {
                error.store(CaptureWorkerError::initializationFailed);
                break;
            }
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
            if (!running.load()) break;
            if (FAILED(client->Start())) { error.store(CaptureWorkerError::initializationFailed); break; }
            ready.store(true);
            ClockMapper clockMapper(static_cast<std::uint64_t>(qpcFrequency.QuadPart));
            AudioNormalizer normalizer(config.maxBatchFrames * 6);
            while (running.load() && error.load() == CaptureWorkerError::none) {
                if (WaitForSingleObject(eventHandle, 500) == WAIT_TIMEOUT) continue;
                if (!running.load()) break;
                UINT32 frames = 0;
                if (FAILED(client->GetCurrentPadding(&frames))) { error.store(CaptureWorkerError::deviceInvalidated); break; }
                while (frames > 0 && running.load()) {
                    BYTE* data = nullptr; UINT32 count = 0; DWORD flagsRead = 0;
                    UINT64 devicePosition = 0; UINT64 qpcPosition = 0;
                    if (FAILED(capture->GetBuffer(&data, &count, &flagsRead, &devicePosition, &qpcPosition))) {
                        error.store(CaptureWorkerError::deviceInvalidated); break;
                    }
                    if (count == 0) {
                        if (FAILED(capture->ReleaseBuffer(0)) || FAILED(client->GetCurrentPadding(&frames))) {
                            error.store(CaptureWorkerError::deviceInvalidated);
                            break;
                        }
                        continue;
                    }
                    if (count > config.maxBatchFrames || format->nChannels == 0 || format->nChannels > 32) {
                        capture->ReleaseBuffer(count); error.store(CaptureWorkerError::bufferOverflow); break;
                    }
                    AudioBatch batch;
                    batch.source = renderLoopback ? AudioSource::systemRender : AudioSource::microphone;
                    batch.sampleRate = format->nSamplesPerSec;
                    batch.channels = format->nChannels;
                    batch.routeGeneration = config.routeGeneration;
                    batch.clockDomain = config.clockDomain;
                    const auto mapping = clockMapper.observe({qpcPosition, devicePosition, batch.sampleRate});
                    if (!mapping.valid || mapping.ptsFrames < 0 ||
                        mapping.ptsFrames > std::numeric_limits<std::int64_t>::max() -
                            static_cast<std::int64_t>(count)) {
                        batch.discontinuity = true;
                        batch.ptsFrames = 0;
                    } else {
                        batch.ptsFrames = mapping.ptsFrames;
                    }
                    batch.samples.resize(static_cast<std::size_t>(count) * batch.channels);
                    batch.discontinuity = batch.discontinuity ||
                        (flagsRead & AUDCLNT_BUFFERFLAGS_DATA_DISCONTINUITY) != 0;
                    const bool silent = (flagsRead & AUDCLNT_BUFFERFLAGS_SILENT) != 0;
                    if (!silent && data != nullptr && pcmFormat.float32) {
                        const auto* samples = reinterpret_cast<const float*>(data);
                        std::copy(samples, samples + batch.samples.size(), batch.samples.begin());
                    } else if (!silent && data != nullptr && pcmFormat.pcm16) {
                        const auto* samples = reinterpret_cast<const std::int16_t*>(data);
                        for (std::size_t i = 0; i < batch.samples.size(); ++i) batch.samples[i] = samples[i] / 32768.0F;
                    } else if (silent) {
                        std::fill(batch.samples.begin(), batch.samples.end(), 0.0F);
                    } else {
                        capture->ReleaseBuffer(count);
                        error.store(CaptureWorkerError::unsupportedFormat);
                        break;
                    }
                    if (std::any_of(batch.samples.begin(), batch.samples.end(),
                                    [](float sample) { return !std::isfinite(sample); })) {
                        capture->ReleaseBuffer(count);
                        error.store(CaptureWorkerError::unsupportedFormat);
                        break;
                    }
                    capture->ReleaseBuffer(count);
                    AudioBatch normalized;
                    if (!normalizer.normalize(std::move(batch), normalized)) {
                        error.store(normalizer.healthy() ? CaptureWorkerError::bufferOverflow
                                                          : CaptureWorkerError::unsupportedFormat);
                        break;
                    }
                    if (running.load() && !normalized.samples.empty()) {
                        try {
                            if (!callback(std::move(normalized))) {
                                error.store(CaptureWorkerError::bufferOverflow);
                                running.store(false);
                                break;
                            }
                        } catch (...) {
                            error.store(CaptureWorkerError::initializationFailed);
                            running.store(false);
                            break;
                        }
                    }
                    if (FAILED(client->GetCurrentPadding(&frames))) { error.store(CaptureWorkerError::deviceInvalidated); break; }
                }
            }
            client->Stop();
        } while (false);
        // All native resources must be released before the outer thread wrapper
        // publishes finished; UI finalization relies on that completion fence.
#endif
    }
};

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
    impl_->ready.store(false);
    impl_->running.store(true);
    impl_->finished.store(false);
    try {
        impl_->thread = std::thread([this] {
            try {
                if (impl_->running.load()) {
                    if (deviceRunForTesting_) deviceRunForTesting_(impl_->running, impl_->ready, impl_->callback);
                    else impl_->run();
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

} // namespace graf::windows
