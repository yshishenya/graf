#pragma once

#ifdef _WIN32
#include "LocalRecordingPackage.h"
#include <mfmediaengine.h>

namespace graf::windows {

// Single application-owned MTA worker: construction, commands, close and last
// release stay there. NOT current account/delete/UI authority. MF receives only
// a fresh Clone, never a path or the inspection's retained original Reader.
class ProtectedLocalRecordingPlayback final {
public:
    struct Snapshot {
        HRESULT error = S_OK;
        double positionSeconds = 0, durationSeconds = 0;
        bool ready = false, paused = true, seeking = false, ended = false, muted = false;
    };
    static void* operator new(std::size_t) { return CustodyAllocator<ProtectedLocalRecordingPlayback>{}.allocate(1); }
    static void operator delete(void* p) noexcept {
        CustodyAllocator<ProtectedLocalRecordingPlayback>{}.deallocate(static_cast<ProtectedLocalRecordingPlayback*>(p),1);
    }
    [[nodiscard]] static CustodyFileResult<std::unique_ptr<ProtectedLocalRecordingPlayback>> open(
        std::shared_ptr<const LocalRecordingPackage::ProtectedInspection>,
        std::shared_ptr<std::atomic<bool>> cancellation, bool muted);
    [[nodiscard]] HRESULT play() noexcept;
    [[nodiscard]] HRESULT pause() noexcept;
    [[nodiscard]] HRESULT seek(double seconds) noexcept;
    [[nodiscard]] Snapshot observe() const noexcept;
    // Cancels new reads/commands. False means ownership is still retained;
    // poll on the owning worker, never treat a timeout as a native drain.
    [[nodiscard]] bool startClose() noexcept;
    [[nodiscard]] bool drained() const noexcept { return drained_; }
    ~ProtectedLocalRecordingPlayback(); // Worker backstop: waits for actual close.
    ProtectedLocalRecordingPlayback(const ProtectedLocalRecordingPlayback&) = delete;
    ProtectedLocalRecordingPlayback& operator=(const ProtectedLocalRecordingPlayback&) = delete;
private:
    struct Events;
    class Notify;
    ProtectedLocalRecordingPlayback(std::shared_ptr<const LocalRecordingPackage::ProtectedInspection>,
        std::shared_ptr<std::atomic<bool>>, std::weak_ptr<const std::atomic<unsigned>>);
    [[nodiscard]] HRESULT initialize(IStream*, bool);
    [[nodiscard]] HRESULT commandError() const noexcept;
    DWORD worker_ = 0;
    bool com_ = false, mf_ = false, closing_ = false, drained_ = false;
    HRESULT error_ = S_OK;
    std::shared_ptr<const LocalRecordingPackage::ProtectedInspection> proof_;
    std::shared_ptr<std::atomic<bool>> cancellation_;
    std::weak_ptr<const std::atomic<unsigned>> readerInstances_;
    std::shared_ptr<Events> events_;
    Microsoft::WRL::ComPtr<IMFMediaEngine> engine_;
    Microsoft::WRL::ComPtr<IMFByteStream> bytes_;
    Microsoft::WRL::ComPtr<IStream> clone_;
};

} // namespace graf::windows
#endif
