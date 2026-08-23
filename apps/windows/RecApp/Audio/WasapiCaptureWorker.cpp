#include "WasapiCaptureWorker.h"

#include <algorithm>
#include <atomic>
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

    void run() {
#ifndef _WIN32
        error = CaptureWorkerError::unsupportedPlatform;
        running.store(false);
#else
        HRESULT init = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
        const bool uninitialize = SUCCEEDED(init);
        Microsoft::WRL::ComPtr<IMMDeviceEnumerator> enumerator;
        Microsoft::WRL::ComPtr<IMMDevice> device;
        Microsoft::WRL::ComPtr<IAudioClient> client;
        Microsoft::WRL::ComPtr<IAudioCaptureClient> capture;
        HANDLE eventHandle = nullptr;
        WAVEFORMATEX* format = nullptr;
        bool qpcInitialized = false;
        std::uint64_t firstQpc = 0;
        do {
            if (FAILED(CoCreateInstance(__uuidof(MMDeviceEnumerator), nullptr, CLSCTX_ALL,
                                        IID_PPV_ARGS(&enumerator)))) { error = CaptureWorkerError::initializationFailed; break; }
            const auto id = utf8ToWide(endpoint.stableId);
            if (endpoint.stableId.empty() || FAILED(enumerator->GetDevice(id.c_str(), &device))) {
                error = CaptureWorkerError::invalidEndpoint; break;
            }
            if (FAILED(device->Activate(__uuidof(IAudioClient), CLSCTX_ALL, nullptr,
                                        reinterpret_cast<void**>(client.GetAddressOf()))) ||
                FAILED(client->GetMixFormat(&format))) { error = CaptureWorkerError::initializationFailed; break; }
            eventHandle = CreateEventW(nullptr, FALSE, FALSE, nullptr);
            if (eventHandle == nullptr) { error = CaptureWorkerError::initializationFailed; break; }
            constexpr REFERENCE_TIME bufferDuration = 100'000;
            DWORD flags = AUDCLNT_STREAMFLAGS_EVENTCALLBACK;
            if (renderLoopback) flags |= AUDCLNT_STREAMFLAGS_LOOPBACK;
            if (FAILED(client->Initialize(AUDCLNT_SHAREMODE_SHARED, flags, bufferDuration, 0,
                                           format, nullptr)) || FAILED(client->SetEventHandle(eventHandle)) ||
                FAILED(client->GetService(IID_PPV_ARGS(&capture)))) {
                error = CaptureWorkerError::initializationFailed; break;
            }
            if (FAILED(client->Start())) { error = CaptureWorkerError::initializationFailed; break; }
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
                    if (count > config.maxBatchFrames || format->nChannels == 0 || format->nChannels > 32) {
                        capture->ReleaseBuffer(count); error.store(CaptureWorkerError::bufferOverflow); break;
                    }
                    AudioBatch batch;
                    batch.source = renderLoopback ? AudioSource::systemRender : AudioSource::microphone;
                    batch.sampleRate = format->nSamplesPerSec;
                    batch.channels = format->nChannels;
                    batch.routeGeneration = config.routeGeneration;
                    batch.clockDomain = config.clockDomain;
                    if (qpcPosition != 0) {
                        if (!qpcInitialized) { firstQpc = qpcPosition; qpcInitialized = true; }
                        if (qpcPosition < firstQpc) {
                            batch.discontinuity = true;
                            batch.ptsFrames = 0;
                        } else {
                            const auto qpcDelta = qpcPosition - firstQpc;
                            batch.ptsFrames = static_cast<std::int64_t>(
                                (static_cast<long double>(qpcDelta) * batch.sampleRate) / 10'000'000.0L);
                        }
                    } else {
                        batch.ptsFrames = static_cast<std::int64_t>(devicePosition);
                    }
                    batch.samples.resize(static_cast<std::size_t>(count) * batch.channels);
                    batch.discontinuity = batch.discontinuity ||
                        (flagsRead & AUDCLNT_BUFFERFLAGS_DATA_DISCONTINUITY) != 0;
                    const bool silent = (flagsRead & AUDCLNT_BUFFERFLAGS_SILENT) != 0;
                    bool isFloat32 = format->wFormatTag == WAVE_FORMAT_IEEE_FLOAT;
                    bool isPcm16 = format->wFormatTag == WAVE_FORMAT_PCM;
                    if (format->wFormatTag == WAVE_FORMAT_EXTENSIBLE && format->cbSize >= sizeof(WAVEFORMATEXTENSIBLE) - sizeof(WAVEFORMATEX)) {
                        const auto* extensible = reinterpret_cast<const WAVEFORMATEXTENSIBLE*>(format);
                        isFloat32 = extensible->SubFormat == KSDATAFORMAT_SUBTYPE_IEEE_FLOAT;
                        isPcm16 = extensible->SubFormat == KSDATAFORMAT_SUBTYPE_PCM;
                    }
                    if (!silent && data != nullptr && format->wBitsPerSample == 32 && isFloat32) {
                        const auto* samples = reinterpret_cast<const float*>(data);
                        std::copy(samples, samples + batch.samples.size(), batch.samples.begin());
                    } else if (!silent && data != nullptr && format->wBitsPerSample == 16 && isPcm16) {
                        const auto* samples = reinterpret_cast<const std::int16_t*>(data);
                        for (std::size_t i = 0; i < batch.samples.size(); ++i) batch.samples[i] = samples[i] / 32768.0F;
                    } else {
                        std::fill(batch.samples.begin(), batch.samples.end(), 0.0F);
                    }
                    capture->ReleaseBuffer(count);
                    try {
                        if (!callback(std::move(batch))) {
                            error.store(CaptureWorkerError::bufferOverflow);
                            running.store(false);
                            break;
                        }
                    } catch (...) {
                        error.store(CaptureWorkerError::initializationFailed);
                        running.store(false);
                        break;
                    }
                    if (FAILED(client->GetCurrentPadding(&frames))) { error.store(CaptureWorkerError::deviceInvalidated); break; }
                }
            }
            client->Stop();
        } while (false);
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
    impl_->thread = std::thread([this] { impl_->run(); });
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
