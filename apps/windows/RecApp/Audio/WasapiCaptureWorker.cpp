#include "WasapiCaptureWorker.h"

#include "AudioNormalizer.h"
#include "ClockMapper.h"

#include <algorithm>
#include <atomic>
#include <condition_variable>
#include <cmath>
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
std::wstring utf8ToWide(const std::string& value) {
    if (value.empty()) return {};
    const int length = MultiByteToWideChar(CP_UTF8, 0, value.c_str(), -1, nullptr, 0);
    if (length <= 1) return {};
    std::wstring result(static_cast<std::size_t>(length - 1), L'\0');
    MultiByteToWideChar(CP_UTF8, 0, value.c_str(), -1, result.data(), static_cast<int>(result.size()));
    return result;
}

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

struct WasapiCaptureWorker::Impl {
    WasapiEndpointSnapshot endpoint;
    bool renderLoopback = false;
    CaptureWorkerConfig config;
    CaptureBatchCallback callback;
    std::atomic_bool running{false};
    std::atomic<CaptureWorkerError> error{CaptureWorkerError::none};
    std::thread thread;
    std::mutex startupMutex;
    std::condition_variable startupCondition;
    bool startupComplete = false;
    CaptureWorkerError startupError = CaptureWorkerError::initializationFailed;

    void reportStartup(CaptureWorkerError result) {
        {
            std::lock_guard<std::mutex> lock(startupMutex);
            startupError = result;
            startupComplete = true;
        }
        startupCondition.notify_one();
    }

    void run() {
#ifndef _WIN32
        error.store(CaptureWorkerError::unsupportedPlatform);
        reportStartup(CaptureWorkerError::unsupportedPlatform);
        running.store(false);
#else
        HRESULT init = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
        if (FAILED(init)) {
            error.store(CaptureWorkerError::initializationFailed);
            reportStartup(CaptureWorkerError::initializationFailed);
            running.store(false);
            return;
        }
        const bool uninitialize = true;
        Microsoft::WRL::ComPtr<IMMDeviceEnumerator> enumerator;
        Microsoft::WRL::ComPtr<IMMDevice> device;
        Microsoft::WRL::ComPtr<IAudioClient> client;
        Microsoft::WRL::ComPtr<IAudioCaptureClient> capture;
        HANDLE eventHandle = nullptr;
        WAVEFORMATEX* format = nullptr;
        bool startupReported = false;
        do {
            LARGE_INTEGER qpcFrequency{};
            if (!QueryPerformanceFrequency(&qpcFrequency) || qpcFrequency.QuadPart <= 0) {
                error.store(CaptureWorkerError::initializationFailed);
                break;
            }
            if (FAILED(CoCreateInstance(__uuidof(MMDeviceEnumerator), nullptr, CLSCTX_ALL,
                                        IID_PPV_ARGS(&enumerator)))) { error = CaptureWorkerError::initializationFailed; break; }
            const auto id = utf8ToWide(endpoint.stableId);
            if (endpoint.stableId.empty() || FAILED(enumerator->GetDevice(id.c_str(), &device))) {
                error = CaptureWorkerError::invalidEndpoint; break;
            }
            if (FAILED(device->Activate(__uuidof(IAudioClient), CLSCTX_ALL, nullptr,
                                        reinterpret_cast<void**>(client.GetAddressOf()))) ||
                FAILED(client->GetMixFormat(&format))) { error = CaptureWorkerError::initializationFailed; break; }
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
                                           format, nullptr)) || FAILED(client->SetEventHandle(eventHandle))) {
                error = CaptureWorkerError::initializationFailed; break;
            }
            if (FAILED(client->GetService(IID_PPV_ARGS(&capture)))) {
                error.store(CaptureWorkerError::initializationFailed);
                break;
            }
            if (FAILED(client->Start())) { error.store(CaptureWorkerError::initializationFailed); break; }
            reportStartup(CaptureWorkerError::none);
            startupReported = true;
            ClockMapper clockMapper(static_cast<std::uint64_t>(qpcFrequency.QuadPart));
            AudioNormalizer normalizer(config.maxBatchFrames * 6);
            while (running.load()) {
                if (WaitForSingleObject(eventHandle, 500) == WAIT_TIMEOUT) continue;
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
                    if (!normalized.samples.empty()) {
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
        if (!startupReported) {
            const auto startupResult = error.load() == CaptureWorkerError::none
                ? CaptureWorkerError::initializationFailed : error.load();
            reportStartup(startupResult);
        }
        if (format != nullptr) CoTaskMemFree(format);
        if (eventHandle != nullptr) CloseHandle(eventHandle);
        if (uninitialize) CoUninitialize();
        running.store(false);
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

WasapiCaptureWorker::~WasapiCaptureWorker() { stop(); }

CaptureWorkerError WasapiCaptureWorker::start(CaptureBatchCallback callback) {
    if (!callback) return CaptureWorkerError::initializationFailed;
    if (impl_->running.exchange(true)) return CaptureWorkerError::alreadyRunning;
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
    {
        std::lock_guard<std::mutex> lock(impl_->startupMutex);
        impl_->startupComplete = false;
        impl_->startupError = CaptureWorkerError::initializationFailed;
    }
    impl_->thread = std::thread([this] { impl_->run(); });
    std::unique_lock<std::mutex> lock(impl_->startupMutex);
    impl_->startupCondition.wait(lock, [this] { return impl_->startupComplete; });
    const auto startupError = impl_->startupError;
    lock.unlock();
    if (startupError != CaptureWorkerError::none) {
        impl_->running.store(false);
        if (impl_->thread.joinable()) impl_->thread.join();
        return startupError;
    }
    return CaptureWorkerError::none;
}

void WasapiCaptureWorker::stop() noexcept {
    if (impl_ == nullptr) return;
    impl_->running.store(false);
    if (impl_->thread.joinable()) impl_->thread.join();
}

bool WasapiCaptureWorker::running() const noexcept { return impl_ != nullptr && impl_->running.load(); }

CaptureWorkerError WasapiCaptureWorker::lastError() const noexcept {
    return impl_ == nullptr ? CaptureWorkerError::initializationFailed : impl_->error.load();
}

} // namespace graf::windows
