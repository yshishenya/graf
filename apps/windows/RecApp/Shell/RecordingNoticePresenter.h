#pragma once

#include "../Contracts/WindowsDesktopContracts.h"

#include <chrono>
#include <cstdint>
#include <string_view>

namespace graf::windows {

// Feature 6796 parity with macOS `DesktopRecordingNoticePresenter`: passive
// local feedback that is independent of system notification permissions, never
// takes focus, shows one notice at a time and expires on its own.
//
// The portable half owns the truth (visible, replaced, expired). The Windows
// half draws a topmost, non-activating popup and never becomes the foreground
// window, so a short recording cannot steal focus from the user's meeting.
class RecordingNoticePresenter final {
public:
    static constexpr std::uint64_t durationMilliseconds = 6'000;

    RecordingNoticePresenter() = default;
    ~RecordingNoticePresenter();

    RecordingNoticePresenter(const RecordingNoticePresenter&) = delete;
    RecordingNoticePresenter& operator=(const RecordingNoticePresenter&) = delete;

    // A repeat replaces the previous notice instead of stacking a second one.
    void showShortRecordingDiscarded(std::chrono::steady_clock::time_point now);
    void dismiss();
    // Called from the UI timer; expires the notice without user interaction.
    void tick(std::chrono::steady_clock::time_point now);

    [[nodiscard]] bool visible() const noexcept { return visible_; }
    [[nodiscard]] bool expired(std::chrono::steady_clock::time_point now) const noexcept {
        return visible_ &&
            std::chrono::duration_cast<std::chrono::milliseconds>(now - shownAt_).count() >=
                static_cast<std::int64_t>(durationMilliseconds);
    }
    [[nodiscard]] static std::wstring_view message() noexcept {
        return kShortRecordingDiscardedMessage;
    }

private:
    bool visible_ = false;
    std::chrono::steady_clock::time_point shownAt_{};
#ifdef _WIN32
    void createWindow();
    void destroyWindow();

    void* window_ = nullptr;
    void* label_ = nullptr;
    void* owner_ = nullptr;
#endif
};

} // namespace graf::windows
