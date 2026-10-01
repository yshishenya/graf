#pragma once

#include "WindowsTargetDetector.h"
#include "../Permissions/WindowsReadinessGate.h"

#include <functional>
#include <map>

namespace graf::windows {

enum class AutomaticRecordingPreference { always, ask, never };
[[nodiscard]] std::string_view automaticRecordingPreferenceLabel(AutomaticRecordingPreference preference) noexcept;
// The stored and published spelling. It is the same word in the registry value
// and in the cabinet's settings page, so the page can save what it was shown.
[[nodiscard]] std::string_view automaticRecordingPreferenceToken(AutomaticRecordingPreference preference) noexcept;
[[nodiscard]] std::optional<AutomaticRecordingPreference> automaticRecordingPreferenceFromToken(
    std::string_view token) noexcept;

// One bounded registry value is replaced atomically, including bulk edits.
// Injection is for deterministic tests; the default uses HKCU on Windows.
struct AutomaticRecordingPreferenceStore {
    std::function<std::optional<std::string>()> read;
    std::function<bool(std::string_view)> write;
    [[nodiscard]] static AutomaticRecordingPreferenceStore native();
};

struct AutomaticRecordingSetting {
    VerifiedTargetIdentity target;
    AutomaticRecordingPreference preference = AutomaticRecordingPreference::ask;
};

struct AutomaticRecordingSettingsSnapshot {
    std::vector<AutomaticRecordingSetting> applications;
    // nullopt = mixed (or no applications); never a fourth stored state.
    std::optional<AutomaticRecordingPreference> bulkPreference;
    bool preferenceWriteFailed = false;
};

struct AutomaticRecordingPrerequisites {
    ReadinessInputs capture;
    bool visibleIndicatorAvailable = false;
    bool oneActionStopAvailable = false;
    bool recordingAlreadyActive = false;
    bool suppressed = false;
    [[nodiscard]] bool allowsStart() const;
};

enum class AutomaticPromptState { idle, detecting, countdown, started, refused, suppressed, blocked };
enum class AutomaticStartReason { none, promptButton, promptExpired, savedPreference };

struct AutomaticRecordingDecision {
    AutomaticPromptState state = AutomaticPromptState::idle;
    // Edge-triggered intent, NOT a claim that capture successfully started.
    bool shouldStart = false;
    bool preferenceSaved = false;
    AutomaticStartReason startReason = AutomaticStartReason::none;
    std::uint64_t generation = 0;
};

// Single-owner (UI thread). Registry must outlive policy. Pass immutable worker
// snapshots; never mutate registry concurrently with enumeration.
class AutomaticRecordingPolicy final {
public:
    explicit AutomaticRecordingPolicy(const VerifiedTargetRegistry& registry,
        AutomaticRecordingPreferenceStore store = AutomaticRecordingPreferenceStore::native());
    [[nodiscard]] AutomaticRecordingPreference preference(const VerifiedTargetIdentity& target) const;
    [[nodiscard]] bool setPreference(const VerifiedTargetIdentity& target, AutomaticRecordingPreference preference);
    [[nodiscard]] bool setAllPreferences(AutomaticRecordingPreference preference);
    [[nodiscard]] AutomaticRecordingSettingsSnapshot settings() const;

    // 5 s stable observation, 8 s prompt, 15 s confirmed absence before the same
    // target may be offered again. Unavailable snapshots do not clear suppression.
    [[nodiscard]] AutomaticRecordingDecision update(const TargetDetectionSnapshot& snapshot,
        const AutomaticRecordingPrerequisites& prerequisites, DetectionClock::time_point now = DetectionClock::now());
    [[nodiscard]] AutomaticRecordingDecision recordNow(bool rememberChoice, const TargetDetectionSnapshot& snapshot,
        const AutomaticRecordingPrerequisites& prerequisites, DetectionClock::time_point now = DetectionClock::now());
    [[nodiscard]] AutomaticRecordingDecision refuse(bool rememberChoice,
        DetectionClock::time_point now = DetectionClock::now());
    // Called only after the native card confirms its first visible show. A
    // detected candidate alone never arms the Ask timeout or accepts a click.
    [[nodiscard]] bool confirmPromptPresented(DetectionClock::time_point shownAt = DetectionClock::now()) noexcept;
    // Arm only at final native acceptance, never merely upon entering starting.
    void captureAccepted();
    // Bind once before worker startup. A cancelled or consumed generation cannot
    // be rebound, and callbacks for another session cannot affect this one.
    [[nodiscard]] bool canBindStart(std::uint64_t generation) const noexcept;
    [[nodiscard]] bool bindStart(std::uint64_t generation, std::string_view sessionId);
    [[nodiscard]] bool hasPendingStart(std::string_view sessionId) const noexcept;
    // Called synchronously by the controller immediately before opening its sink.
    [[nodiscard]] bool acceptStart(std::uint64_t generation, std::string_view sessionId,
        const TargetDetectionSnapshot& snapshot, const AutomaticRecordingPrerequisites& prerequisites,
        DetectionClock::time_point now = DetectionClock::now());
    // Same verified app across PIDs; 15 s confirmed absence or 600 s without
    // positive evidence. Never controls manual capture. Stop is edge-triggered.
    [[nodiscard]] bool shouldStopCapture(const TargetDetectionSnapshot& snapshot, bool captureActive,
        DetectionClock::time_point now = DetectionClock::now());
    // Window dismissal / manual Stop suppresses this continuous candidate only.
    void cancel() noexcept;
    [[nodiscard]] AutomaticPromptState state() const noexcept { return state_; }
    [[nodiscard]] const VerifiedTargetIdentity& target() const noexcept { return target_.identity; }
    [[nodiscard]] std::uint32_t secondsRemaining(DetectionClock::time_point now = DetectionClock::now()) const noexcept;

private:
    struct TrackedTarget {
        TargetObservation observation;
        DetectionClock::time_point firstSeen{};
        DetectionClock::time_point lastSeen{};
        bool handled = false;
    };
    [[nodiscard]] bool save(std::map<std::string, AutomaticRecordingPreference> updated);
    [[nodiscard]] bool currentTargetReady(const TargetDetectionSnapshot& snapshot, DetectionClock::time_point now) const;
    [[nodiscard]] bool startStillAllowed(const TargetDetectionSnapshot& snapshot,
        const AutomaticRecordingPrerequisites& prerequisites, DetectionClock::time_point now) const;
    [[nodiscard]] AutomaticRecordingDecision start(AutomaticStartReason reason, bool rememberChoice);
    const VerifiedTargetRegistry& registry_;
    AutomaticRecordingPreferenceStore store_;
    std::map<std::string, AutomaticRecordingPreference> preferences_;
    std::map<std::string, TrackedTarget> tracked_;
    TargetObservation target_;
    DetectionClock::time_point promptStartedAt_{};
    bool promptPresented_ = false;
    AutomaticPromptState state_ = AutomaticPromptState::idle;
    bool preferenceWriteFailed_ = false;
    std::uint64_t startGeneration_ = 0;
    std::string pendingSessionId_;
    DetectionClock::time_point startEvidenceAt_{};
    std::optional<VerifiedTargetIdentity> recordingTarget_;
    DetectionClock::time_point lastCaptureEvidenceAt_{};
    DetectionClock::time_point lastCaptureSnapshotAt_{};
    std::optional<DetectionClock::time_point> captureAbsentSince_;
};

} // namespace graf::windows
