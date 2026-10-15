#include "ProtectedLocalRecordingPlayback.h"
#ifdef _WIN32
#include <mfapi.h>
#include <mferror.h>
#include <cmath>
#include <exception>

namespace graf::windows {
struct ProtectedLocalRecordingPlayback::Events {
    std::atomic<HRESULT> error{S_OK};
};

// MF callbacks retain only bounded scalar observations, never a player, proof,
// account, window, Reader or raw controller pointer.
class ProtectedLocalRecordingPlayback::Notify final : public IMFMediaEngineNotify {
public:
    explicit Notify(std::shared_ptr<Events> events) : events_(std::move(events)) {}
    static void* operator new(std::size_t) { return CustodyAllocator<Notify>{}.allocate(1); }
    static void operator delete(void* p) noexcept { CustodyAllocator<Notify>{}.deallocate(static_cast<Notify*>(p),1); }
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID iid, void** out) noexcept override {
        if (!out) return E_POINTER;
        *out = nullptr;
        if (iid != __uuidof(IUnknown) && iid != __uuidof(IMFMediaEngineNotify)) return E_NOINTERFACE;
        *out = static_cast<IMFMediaEngineNotify*>(this); AddRef(); return S_OK;
    }
    ULONG STDMETHODCALLTYPE AddRef() noexcept override { return ++references_; }
    ULONG STDMETHODCALLTYPE Release() noexcept override {
        const auto left = --references_; if (!left) delete this; return left;
    }
    HRESULT STDMETHODCALLTYPE EventNotify(DWORD event, DWORD_PTR, DWORD detail) noexcept override {
        if (event == MF_MEDIA_ENGINE_EVENT_ERROR || event == MF_MEDIA_ENGINE_EVENT_STREAMRENDERINGERROR) {
            const auto error = event == MF_MEDIA_ENGINE_EVENT_ERROR && FAILED(static_cast<HRESULT>(detail)) ?
                static_cast<HRESULT>(detail) : E_FAIL;
            HRESULT healthy = S_OK; (void)events_->error.compare_exchange_strong(healthy,error);
        }
        return S_OK;
    }
private:
    std::atomic<ULONG> references_{1};
    std::shared_ptr<Events> events_;
};

ProtectedLocalRecordingPlayback::ProtectedLocalRecordingPlayback(
    std::shared_ptr<const LocalRecordingPackage::ProtectedInspection> proof,
    std::shared_ptr<std::atomic<bool>> cancellation, std::weak_ptr<const std::atomic<unsigned>> instances)
    : worker_(GetCurrentThreadId()), proof_(std::move(proof)), cancellation_(std::move(cancellation)),
      readerInstances_(std::move(instances)) {}

CustodyFileResult<std::unique_ptr<ProtectedLocalRecordingPlayback>> ProtectedLocalRecordingPlayback::open(
    std::shared_ptr<const LocalRecordingPackage::ProtectedInspection> proof,
    std::shared_ptr<std::atomic<bool>> cancellation, bool muted) try {
    if (!proof || !cancellation || proof->cancellation_.get() != cancellation.get() || !proof->pair_)
        return {std::nullopt,CustodyFileError::invalidInput,0};
    if (cancellation->load(std::memory_order_acquire))
        return {std::nullopt,CustodyFileError::ioFailed,ERROR_OPERATION_ABORTED};
    const auto& package = proof->pair_->current();
    const auto& evidence = proof->evidence_;
    if ((package.phase != CustodyPackagePhase::sealedNormal && package.phase != CustodyPackagePhase::sealedDegraded) ||
        (evidence.integrity != PackageIntegrity::valid && evidence.integrity != PackageIntegrity::degraded) ||
        !evidence.durationMs || !evidence.playback.decodedFrames || !evidence.playback.containerDuration100ns)
        return {std::nullopt,CustodyFileError::invalidContent,0};
    std::size_t index = 0;
    while (index < package.refCount && package.refs[index].role != CustodyRole::playback) ++index;
    if (index == package.refCount || !package.refs[index].sealed)
        return {std::nullopt,CustodyFileError::invalidContent,0};
    const auto& reader = proof->readers_[proof->pair_->selectedSlot()][index];
    const auto instances = reader.readerInstances.lock();
    if (!reader.stream || reader.state != CustodySnapshotState::verified || !instances ||
        instances->load(std::memory_order_acquire) != 1)
        return {std::nullopt,CustodyFileError::invalidContent,0};
    auto player = std::unique_ptr<ProtectedLocalRecordingPlayback>(
        new ProtectedLocalRecordingPlayback(proof,std::move(cancellation),reader.readerInstances));
    const auto hr = player->initialize(reader.stream.Get(),muted);
    if (FAILED(hr)) {
        player->error_ = hr; // The same actual close path also owns partial initialization.
        return {std::nullopt,CustodyFileError::ioFailed,static_cast<std::uint32_t>(hr)};
    }
    return {std::move(player),CustodyFileError::none,0};
} catch (const std::bad_alloc&) {
    return {std::nullopt,CustodyFileError::allocationFailed,ERROR_NOT_ENOUGH_MEMORY};
}

HRESULT ProtectedLocalRecordingPlayback::initialize(IStream* input, bool muted) {
    using Microsoft::WRL::ComPtr;
    auto hr = CoInitializeEx(nullptr,COINIT_MULTITHREADED);
    if (FAILED(hr)) return hr;
    com_ = true;
    hr = MFStartup(MF_VERSION); if (FAILED(hr)) return hr;
    mf_ = true;
    events_ = std::allocate_shared<Events>(CustodyAllocator<Events>{});
    ComPtr<IMFMediaEngineNotify> notify; notify.Attach(new Notify(events_));
    ComPtr<IMFMediaEngineClassFactory> factory;
    ComPtr<IMFAttributes> attributes;
    const auto call = [&](auto action) {
        if (cancellation_->load(std::memory_order_acquire)) return HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED);
        const HRESULT result = action();
        return FAILED(result) ? result : cancellation_->load(std::memory_order_acquire) ?
            HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED) : result;
    };
    hr = call([&] { return CoCreateInstance(CLSID_MFMediaEngineClassFactory,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(&factory)); });
    if (SUCCEEDED(hr)) hr = call([&] { return MFCreateAttributes(&attributes,1); });
    if (SUCCEEDED(hr)) hr = call([&] { return attributes->SetUnknown(MF_MEDIA_ENGINE_CALLBACK,notify.Get()); });
    const DWORD flags = MF_MEDIA_ENGINE_AUDIOONLY | MF_MEDIA_ENGINE_DISABLE_LOCAL_PLUGINS |
        (muted ? static_cast<DWORD>(MF_MEDIA_ENGINE_FORCEMUTE) : 0U);
    if (SUCCEEDED(hr)) hr = call([&] { return factory->CreateInstance(flags,attributes.Get(),&engine_); });
    if (SUCCEEDED(hr)) hr = call([&] { return engine_->SetAutoPlay(FALSE); });
    if (SUCCEEDED(hr)) hr = call([&] { return engine_->SetMuted(muted ? TRUE : FALSE); });
    if (SUCCEEDED(hr)) hr = call([&] { return engine_->SetPreload(MF_MEDIA_ENGINE_PRELOAD_AUTOMATIC); });
    if (SUCCEEDED(hr)) hr = call([&] { return input->Clone(&clone_); });
    if (SUCCEEDED(hr)) hr = call([&] { return MFCreateMFByteStreamOnStream(clone_.Get(),&bytes_); });
    ComPtr<IMFMediaEngineEx> extended;
    if (SUCCEEDED(hr)) hr = call([&] { return engine_.As(&extended); });
    if (SUCCEEDED(hr)) {
        // Extension label only. Source bytes come exclusively from the retained
        // protected stream; no filesystem URL, export or network fallback.
        const auto label = SysAllocString(L"recording.m4a");
        if (!label) hr = E_OUTOFMEMORY;
        else { hr = call([&] { return extended->SetSourceFromByteStream(bytes_.Get(),label); }); SysFreeString(label); }
    }
    return hr;
}

HRESULT ProtectedLocalRecordingPlayback::commandError() const noexcept {
    if (GetCurrentThreadId() != worker_) return RPC_E_WRONG_THREAD;
    if (closing_ || drained_ || !engine_) return MF_E_SHUTDOWN;
    if (cancellation_->load(std::memory_order_acquire)) return HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED);
    if (FAILED(error_)) return error_;
    return events_ ? events_->error.load(std::memory_order_acquire) : E_UNEXPECTED;
}

HRESULT ProtectedLocalRecordingPlayback::play() noexcept {
    const auto state = observe();
    if (FAILED(state.error)) return state.error;
    return state.ready && !state.seeking ? engine_->Play() : MF_E_NOTACCEPTING;
}
HRESULT ProtectedLocalRecordingPlayback::pause() noexcept {
    const auto hr = commandError(); return FAILED(hr) ? hr : engine_->Pause();
}
HRESULT ProtectedLocalRecordingPlayback::seek(double seconds) noexcept {
    const auto state = observe();
    if (FAILED(state.error)) return state.error;
    if (!std::isfinite(seconds) || seconds < 0 || seconds > state.durationSeconds) return E_INVALIDARG;
    return state.ready && !state.seeking ? engine_->SetCurrentTime(seconds) : MF_E_NOTACCEPTING;
}

ProtectedLocalRecordingPlayback::Snapshot ProtectedLocalRecordingPlayback::observe() const noexcept {
    Snapshot value; value.error = commandError();
    if (FAILED(value.error)) return value;
    const auto duration = engine_->GetDuration(), position = engine_->GetCurrentTime();
    value.durationSeconds = std::isfinite(duration) && duration > 0 ? duration : 0;
    value.positionSeconds = std::isfinite(position) && position >= 0 ? position : 0;
    value.paused = engine_->IsPaused() != FALSE;
    value.seeking = engine_->IsSeeking() != FALSE;
    value.ended = engine_->IsEnded() != FALSE;
    value.muted = engine_->GetMuted() != FALSE;
    value.ready = value.durationSeconds > 0 && engine_->HasAudio() &&
        engine_->GetReadyState() >= MF_MEDIA_ENGINE_READY_HAVE_FUTURE_DATA;
    value.error = commandError(); // Cancellation/error arriving during observation invalidates the result.
    if (FAILED(value.error)) value.ready = false;
    return value;
}

bool ProtectedLocalRecordingPlayback::startClose() noexcept {
    if (GetCurrentThreadId() != worker_) return false;
    if (drained_) return true;
    closing_ = true;
    cancellation_->store(true,std::memory_order_release);
    if (engine_) {
        const auto hr = engine_->Shutdown();
        if (FAILED(hr)) { error_ = hr; return false; } // Retain native custody on failed shutdown.
        engine_.Reset();
    }
    if (bytes_) {
        const auto hr = bytes_->Close();
        if (FAILED(hr)) { error_ = hr; return false; }
        bytes_.Reset();
    }
    clone_.Reset();
    if (proof_) {
        const auto instances = readerInstances_.lock();
        if (!instances || instances->load(std::memory_order_acquire) != 1) return false;
        proof_.reset(); // Only after the last MF Reader/Clone actually released.
        readerInstances_.reset();
    }
    if (mf_) {
        const auto hr = MFShutdown();
        if (FAILED(hr)) { error_ = hr; return false; }
        mf_ = false;
    }
    events_.reset();
    if (com_) { CoUninitialize(); com_ = false; }
    drained_ = true;
    return true;
}

ProtectedLocalRecordingPlayback::~ProtectedLocalRecordingPlayback() {
    if (GetCurrentThreadId() != worker_) std::terminate(); // Never release native ownership on a foreign/UI thread.
    while (!startClose()) Sleep(2); // No lock held; timeout cannot authorize releasing a live native owner.
}
} // namespace graf::windows
#endif
