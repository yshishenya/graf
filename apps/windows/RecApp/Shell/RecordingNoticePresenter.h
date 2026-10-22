#pragma once
#include "../Contracts/WindowsDesktopContracts.h"
#include <chrono>
#include <functional>
#include <optional>
#include <string>
#include <vector>

namespace graf::windows {
enum class NoticeKind { preview = 1, meeting = 2, shortRecording = 3, problem = 4 };
enum class NoticeAction { joinAndRecord, join, record };
struct NoticeButton { std::wstring title; NoticeAction action; };
struct NoticeContent {
    NoticeKind kind = NoticeKind::preview;
    std::string id;
    std::wstring title, body;
    std::vector<NoticeButton> buttons;
};

// One surface for reminders, previews and short notices. Automatic presentation
// never activates it; F6 in the shell explicitly focuses accessible controls.
class RecordingNoticePresenter final {
public:
    using Clock = std::chrono::steady_clock;
    static constexpr std::uint64_t durationMilliseconds = 20'000;
    RecordingNoticePresenter() = default;
    ~RecordingNoticePresenter();
    RecordingNoticePresenter(const RecordingNoticePresenter&) = delete;
    RecordingNoticePresenter& operator=(const RecordingNoticePresenter&) = delete;
    [[nodiscard]] bool present(NoticeContent content, Clock::time_point now, Clock::time_point deadline,
        std::function<void(NoticeAction)> onAction = {}, std::function<void()> onClose = {});
    void showShortRecordingDiscarded(Clock::time_point now);
    void tick(Clock::time_point now);
    void dismiss();
    void close();
    void invoke(NoticeAction action);
    void focus();
    // UI-thread lease for the existing automatic-recording window (priority 3).
    // onReplaced synchronously confirms that window is hidden/closed, without
    // throwing. False keeps its lease/callback and dismisses the replacement.
    // Closed may release this generation during the callback, never a newer one.
    [[nodiscard]] bool acquireAutomaticPrompt(std::uint64_t generation, Clock::time_point now,
        std::function<bool()> onReplaced);
    void releaseAutomaticPrompt(std::uint64_t generation);
    [[nodiscard]] bool automaticPromptActive() const noexcept { return automaticPromptGeneration_.has_value(); }
    [[nodiscard]] bool occupied() const noexcept { return visible_ || automaticPromptActive(); }
    [[nodiscard]] bool visible() const noexcept { return visible_; }
    [[nodiscard]] NoticeKind kind() const noexcept { return content_.kind; }
    [[nodiscard]] const std::string& id() const noexcept { return content_.id; }
    [[nodiscard]] const NoticeContent& content() const noexcept { return content_; }
    [[nodiscard]] bool expired(Clock::time_point now) const noexcept { return visible_ && now >= deadline_; }
    [[nodiscard]] static std::wstring_view message() noexcept { return L"Записи короче 30 секунд не сохраняются."; }
private:
    NoticeContent content_;
    bool visible_ = false;
    Clock::time_point deadline_{};
    std::function<void(NoticeAction)> onAction_;
    std::function<void()> onClose_;
    std::optional<std::uint64_t> automaticPromptGeneration_;
    std::function<bool()> onAutomaticPromptReplaced_;
#ifdef _WIN32
    [[nodiscard]] bool createWindow();
    void destroyWindow();
    void* window_ = nullptr;
    void* font_ = nullptr;
#endif
};
} // namespace graf::windows
