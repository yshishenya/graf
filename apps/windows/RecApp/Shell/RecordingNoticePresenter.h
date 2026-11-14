#pragma once
#include "../Contracts/WindowsDesktopContracts.h"
#include "InteractionPermit.h"
#include <chrono>
#include <functional>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace graf::windows {
enum class NoticeKind { preview = 0, meeting = 1, shortRecording = 2, problem = 3, recordingPrompt = 4 };
enum class NoticeAction { joinAndRecord, join, record, skip, openRecording };
struct NoticeButton { std::wstring title; NoticeAction action; };
struct NoticeContent {
    NoticeKind kind = NoticeKind::preview;
    std::string id;
    std::wstring title, body;
    std::vector<NoticeButton> buttons;
    std::wstring checkboxTitle{};
    bool rememberChoice = false;
};

struct NoticePresentationHooks {
    // Synchronous durable claim, after hidden layout succeeds, BEFORE first show.
    // False/exception forbids show; a failed show never calls onPresented.
    std::function<bool()> beforeFirstShow;
    std::function<void()> onPresented;
    std::function<void()> onExpired;
    std::function<void()> onInvalidated;
    std::function<void(bool)> onRememberChanged;
};
struct NoticeHistoryEntry {
    std::uint64_t sequence;
    std::chrono::system_clock::time_point occurredAt;
    NoticeKind kind; // closed enum only: no titles, IDs, paths, links or actions
};
struct NoticeRect { int x = 0, y = 0, width = 0, height = 0; };
struct NoticePlacement { NoticeRect frame; int cardWidth = 0, cardHeight = 0; };

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
        std::function<void(NoticeAction)> onAction = {}, std::function<void()> onClose = {},
        NoticePresentationHooks hooks = {});
    void showShortRecordingDiscarded(Clock::time_point now, std::function<void()> onPresented = {});
    // Record immediately; replace the single pending candidate without showing it.
    void queueShortRecordingDiscarded(Clock::time_point now, std::function<void()> onPresented = {});
    void tick(Clock::time_point now);
    // Domain reconciliation order after a prompt: current problem, pending short,
    // current meeting. Native timer only expires; it never drains stale candidates.
    [[nodiscard]] bool presentPendingShort(Clock::time_point now);
    void dismiss();
    void close();
    void invoke(NoticeAction action);
    void invoke(NoticeAction action, std::uint64_t generation, Clock::time_point now);
    void close(std::uint64_t generation);
    void setRememberChoice(bool value);
    void focus();
    void setInteraction(bool hovered, bool focused, Clock::time_point now);
    void setQuiet(bool quiet);
    void resetContext(); // account/workspace/origin change, clears memory history
    // Call after the domain's durable claim, before quiet/pending arbitration.
    // History is not presentation; the bounded receipt retains its unshown state.
    void recordProblemHistory(const std::string& id, Clock::time_point until);
    void resolveProblem(const std::string& id); // confirmed resolution, not an incomplete snapshot
    void invalidate(); // sleep/lock/domain invalidation; no expiry/start callback
    void invalidatePresentation(); // lifecycle: discard pending, preserve history, never restore focus
    void setDarkTheme(bool dark);
    void reposition();
    // Current visible GRAF Stop rectangles in physical screen pixels, not foreign windows.
    std::function<std::vector<NoticeRect>()> protectedFramesProvider;
    // Native default denies; the non-Windows model defaults to {true, 1}.
    // Must be a fresh, non-reentrant query, not a cached bool or a UI callback.
    std::function<InteractionPermit()> interactionPermitProvider;
    [[nodiscard]] const std::vector<NoticeHistoryEntry>& history() const noexcept { return history_; }
    [[nodiscard]] static std::wstring_view historyMessage(NoticeKind kind) noexcept;
    [[nodiscard]] std::uint64_t generation() const noexcept { return generation_; }
    [[nodiscard]] Clock::time_point deadline() const noexcept { return deadline_; }
    // Pure placement in one coordinate space (DIP in tests, scaled pixels natively).
    [[nodiscard]] static std::optional<NoticePlacement> place(NoticeRect workArea, int desiredHeight,
        int minimumHeight, const std::vector<NoticeRect>& protectedFrames, int dpi = 96);
    [[nodiscard]] bool automaticPromptActive() const noexcept { return visible_ && content_.kind == NoticeKind::recordingPrompt; }
    [[nodiscard]] bool occupied() const noexcept { return visible_; }
    [[nodiscard]] bool visible() const noexcept { return visible_; }
    [[nodiscard]] NoticeKind kind() const noexcept { return content_.kind; }
    [[nodiscard]] const std::string& id() const noexcept { return content_.id; }
    [[nodiscard]] const NoticeContent& content() const noexcept { return content_; }
    [[nodiscard]] bool expired(Clock::time_point now) const noexcept { return visible_ && !holdStarted_ && now >= deadline_; }
    [[nodiscard]] static std::wstring_view message() noexcept { return L"Запись не сохранена — короче 30 секунд"; }
private:
    NoticeContent content_;
    bool visible_ = false;
    Clock::time_point deadline_{};
    std::function<void(NoticeAction)> onAction_;
    std::function<void()> onClose_;
    NoticePresentationHooks hooks_;
    std::uint64_t generation_ = 0, shortSequence_ = 0, historySequence_ = 0;
    bool quiet_ = false, dark_ = false, themeExplicit_ = false, preparing_ = false, actionPending_ = false;
    std::optional<Clock::time_point> holdStarted_;
    Clock::time_point lastTick_{};
    struct Seen { std::size_t identity; NoticeKind kind; Clock::time_point until; bool shown; };
    std::vector<Seen> seen_; // bounded, no private content; domain owns durable claims
    std::vector<NoticeHistoryEntry> history_;
    struct HistoryIdentity { std::size_t identity; bool consumed; };
    std::vector<std::optional<HistoryIdentity>> historyIdentities_; // private dedup, same <=50 bound
    struct PendingShort {
        NoticeContent content;
        Clock::time_point until;
        std::function<void(NoticeAction)> onAction;
        std::function<void()> onClose;
        NoticePresentationHooks hooks;
        std::uint64_t interactionEpoch;
    };
    std::optional<PendingShort> pendingShort_;
    void finish(bool invalidated);
    void recordHistory(const NoticeContent& content, Clock::time_point until);
    void markConsumed(const NoticeContent& content);
    [[nodiscard]] InteractionPermit readInteractionPermit() const noexcept;
    [[nodiscard]] bool requireInteraction();
    std::uint64_t interactionEpoch_ = 0;
    [[nodiscard]] bool allowsHold() const noexcept;
#ifdef _WIN32
    [[nodiscard]] bool createWindow();
    [[nodiscard]] bool updateWindow();
    [[nodiscard]] bool showWindow();
    void destroyWindow();
    void* window_ = nullptr;
    void* font_ = nullptr;
    void* background_ = nullptr;
    void* selectedMonitor_ = nullptr;
    void* previousForeground_ = nullptr;
    bool explicitFocus_ = false;
    bool updatingWindow_ = false;
#endif
};
} // namespace graf::windows
