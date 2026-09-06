#include "AutomaticRecordingPolicy.h"

#include <algorithm>
#include <charconv>
#include <sstream>
#include <utility>

#ifdef _WIN32
#include <windows.h>
#endif

namespace graf::windows {
namespace {
using namespace std::chrono_literals;
constexpr std::size_t maximumPreferenceBytes = 64 * 1024;
constexpr std::string_view preferencesHeader = "graf.automatic-recording.v1\n";

bool validPreference(AutomaticRecordingPreference value) {
    return value == AutomaticRecordingPreference::always || value == AutomaticRecordingPreference::ask ||
        value == AutomaticRecordingPreference::never;
}

bool fresh(const TargetDetectionSnapshot& snapshot, DetectionClock::time_point now) {
    return snapshot.status == TargetDetectionStatus::ready && snapshot.observedAt <= now &&
        now - snapshot.observedAt <= 2s;
}

bool sameProcess(const TargetObservation& first, const TargetObservation& second) {
    return first.processId == second.processId && first.processCreatedAt == second.processCreatedAt &&
        VerifiedTargetRegistry::preferenceKey(first.identity) == VerifiedTargetRegistry::preferenceKey(second.identity);
}

bool validKey(std::string_view key) {
    const auto separator = key.find(':');
    if (separator == std::string_view::npos || separator == 0 || separator > 10 ||
        key.size() != separator + 130 || key[separator + 65] != ':') return false;
    std::uint32_t version = 0;
    const auto parsed = std::from_chars(key.data(), key.data() + separator, version);
    if (parsed.ec != std::errc{} || parsed.ptr != key.data() + separator || version == 0 ||
        std::to_string(version) != key.substr(0, separator)) return false;
    return VerifiedTargetRegistry::validIdentity({std::string(key.substr(separator + 1, 64)),
        std::string(key.substr(separator + 66, 64)), "Target", version});
}
} // namespace

std::string_view automaticRecordingPreferenceLabel(AutomaticRecordingPreference value) noexcept {
    switch (value) {
        case AutomaticRecordingPreference::always: return "Всегда";
        case AutomaticRecordingPreference::ask: return "Спрашивать";
        case AutomaticRecordingPreference::never: return "Никогда";
    }
    return "Спрашивать";
}

AutomaticRecordingPreferenceStore AutomaticRecordingPreferenceStore::native() {
#ifdef _WIN32
    // Old global booleans never granted a target permission. Deliberately do not
    // migrate/read them, and do not touch recordings, queue or package settings.
    constexpr auto key = L"Software\\GRAF\\Windows\\MeetingDetection";
    constexpr auto name = L"ApplicationRulesV1";
    return {
        [key, name]() -> std::optional<std::string> {
            DWORD bytes = 0;
            if (RegGetValueW(HKEY_CURRENT_USER, key, name, RRF_RT_REG_BINARY, nullptr, nullptr, &bytes) != ERROR_SUCCESS ||
                bytes > maximumPreferenceBytes) return std::nullopt;
            std::string value(bytes, '\0');
            if (RegGetValueW(HKEY_CURRENT_USER, key, name, RRF_RT_REG_BINARY, nullptr, value.data(), &bytes) != ERROR_SUCCESS)
                return std::nullopt;
            value.resize(bytes);
            return value;
        },
        [key, name](std::string_view value) {
            if (value.size() > maximumPreferenceBytes) return false;
            HKEY handle = nullptr;
            if (RegCreateKeyExW(HKEY_CURRENT_USER, key, 0, nullptr, 0, KEY_SET_VALUE, nullptr, &handle, nullptr) != ERROR_SUCCESS)
                return false;
            const auto result = RegSetValueExW(handle, name, 0, REG_BINARY,
                reinterpret_cast<const BYTE*>(value.data()), static_cast<DWORD>(value.size()));
            RegCloseKey(handle);
            return result == ERROR_SUCCESS;
        }
    };
#else
    return {[] { return std::optional<std::string>{}; }, [](std::string_view) { return false; }};
#endif
}

bool AutomaticRecordingPrerequisites::allowsStart() const {
    return visibleIndicatorAvailable && oneActionStopAvailable && !recordingAlreadyActive &&
        !suppressed && WindowsReadinessGate::evaluate(capture).recordingReady;
}

AutomaticRecordingPolicy::AutomaticRecordingPolicy(const VerifiedTargetRegistry& registry,
                                                   AutomaticRecordingPreferenceStore store)
    : registry_(registry), store_(std::move(store)) {
    const auto raw = store_.read ? store_.read() : std::nullopt;
    if (!raw || raw->size() > maximumPreferenceBytes || raw->compare(0, preferencesHeader.size(), preferencesHeader) != 0)
        return;
    std::istringstream input(raw->substr(preferencesHeader.size()));
    std::string line;
    std::map<std::string, AutomaticRecordingPreference> decoded;
    while (std::getline(input, line)) {
        const auto split = line.find('=');
        if (split == std::string::npos || !validKey(std::string_view(line).substr(0, split))) return;
        const auto value = line.substr(split + 1);
        if (value != "always" && value != "ask" && value != "never") return;
        if (!decoded.emplace(line.substr(0, split), value == "always" ? AutomaticRecordingPreference::always :
            value == "never" ? AutomaticRecordingPreference::never : AutomaticRecordingPreference::ask).second) return;
    }
    // A truncated last record must not accidentally authorize an Always rule.
    if (raw->back() != '\n') return;
    preferences_ = std::move(decoded);
}

AutomaticRecordingPreference AutomaticRecordingPolicy::preference(const VerifiedTargetIdentity& target) const {
    if (!registry_.contains(target.executableFingerprint, target.publisherFingerprint, target.registryVersion))
        return AutomaticRecordingPreference::ask;
    const auto found = preferences_.find(VerifiedTargetRegistry::preferenceKey(target));
    return found == preferences_.end() ? AutomaticRecordingPreference::ask : found->second;
}

bool AutomaticRecordingPolicy::save(std::map<std::string, AutomaticRecordingPreference> updated) {
    std::string bytes(preferencesHeader);
    for (const auto& [key, value] : updated) {
        if (!validKey(key) || !validPreference(value)) return false;
        bytes += key + "=" + (value == AutomaticRecordingPreference::always ? "always" :
            value == AutomaticRecordingPreference::never ? "never" : "ask") + "\n";
    }
    preferenceWriteFailed_ = bytes.size() > maximumPreferenceBytes || !store_.write || !store_.write(bytes);
    if (preferenceWriteFailed_) return false;
    preferences_ = std::move(updated);
    return true;
}

bool AutomaticRecordingPolicy::setPreference(const VerifiedTargetIdentity& target, AutomaticRecordingPreference value) {
    if (!validPreference(value) || !registry_.contains(target.executableFingerprint, target.publisherFingerprint,
                                                      target.registryVersion)) return false;
    auto updated = preferences_;
    updated[VerifiedTargetRegistry::preferenceKey(target)] = value;
    return save(std::move(updated));
}

bool AutomaticRecordingPolicy::setAllPreferences(AutomaticRecordingPreference value) {
    if (!validPreference(value) || registry_.targets().empty()) return false;
    auto updated = preferences_;
    for (const auto& target : registry_.targets()) updated[VerifiedTargetRegistry::preferenceKey(target)] = value;
    return save(std::move(updated));
}

AutomaticRecordingSettingsSnapshot AutomaticRecordingPolicy::settings() const {
    AutomaticRecordingSettingsSnapshot result;
    result.preferenceWriteFailed = preferenceWriteFailed_;
    for (const auto& target : registry_.targets()) result.applications.push_back({target, preference(target)});
    if (!result.applications.empty()) {
        const auto first = result.applications.front().preference;
        if (std::all_of(result.applications.begin(), result.applications.end(), [first](const auto& item) {
            return item.preference == first;
        })) result.bulkPreference = first;
    }
    return result;
}

bool AutomaticRecordingPolicy::currentTargetReady(const TargetDetectionSnapshot& snapshot,
                                                 DetectionClock::time_point now) const {
    return fresh(snapshot, now) && std::any_of(snapshot.observations.begin(), snapshot.observations.end(), [&](const auto& item) {
        return sameProcess(item, target_) && WindowsTargetDetector::isPromptCandidate(item, registry_);
    });
}

std::uint32_t AutomaticRecordingPolicy::secondsRemaining(DetectionClock::time_point now) const noexcept {
    if (state_ != AutomaticPromptState::countdown) return 0;
    if (now <= promptStartedAt_) return 8;
    const auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - promptStartedAt_).count();
    return elapsed >= 8 ? 0 : static_cast<std::uint32_t>(8 - elapsed);
}

AutomaticRecordingDecision AutomaticRecordingPolicy::start(AutomaticStartReason reason, bool rememberChoice) {
    const auto saved = rememberChoice && setPreference(target_.identity, AutomaticRecordingPreference::always);
    tracked_.at(VerifiedTargetRegistry::preferenceKey(target_.identity)).handled = true;
    state_ = AutomaticPromptState::started;
    return {state_, true, saved, reason};
}

AutomaticRecordingDecision AutomaticRecordingPolicy::update(const TargetDetectionSnapshot& snapshot,
    const AutomaticRecordingPrerequisites& prerequisites, DetectionClock::time_point now) {
    if (!fresh(snapshot, now)) {
        state_ = AutomaticPromptState::blocked;
        return {state_};
    }
    for (const auto& item : snapshot.observations) {
        if (!WindowsTargetDetector::isPromptCandidate(item, registry_)) continue;
        const auto key = VerifiedTargetRegistry::preferenceKey(item.identity);
        auto [it, inserted] = tracked_.try_emplace(key, TrackedTarget{item, snapshot.observedAt, snapshot.observedAt, false});
        auto& tracked = it->second;
        if (!inserted && snapshot.observedAt < tracked.lastSeen) continue;
        if (snapshot.observedAt - tracked.lastSeen > 2s || !sameProcess(tracked.observation, item))
            tracked.firstSeen = snapshot.observedAt;
        tracked.observation = item;
        tracked.lastSeen = snapshot.observedAt;
        // A manual recording already covers this meeting; Stop must not restart it.
        if (prerequisites.recordingAlreadyActive) tracked.handled = true;
    }
    for (auto it = tracked_.begin(); it != tracked_.end();) {
        if (snapshot.observedAt - it->second.lastSeen >= 15s) it = tracked_.erase(it);
        else ++it;
    }
    if (state_ == AutomaticPromptState::countdown) {
        if (!currentTargetReady(snapshot, now) || !prerequisites.allowsStart()) {
            state_ = AutomaticPromptState::blocked;
            return {state_};
        }
        const auto value = preference(target_.identity);
        if (value == AutomaticRecordingPreference::never) state_ = AutomaticPromptState::suppressed;
        else if (value == AutomaticRecordingPreference::always) return start(AutomaticStartReason::savedPreference, false);
        else if (secondsRemaining(now) == 0) return start(AutomaticStartReason::promptExpired, false);
        return {state_};
    }
    state_ = AutomaticPromptState::idle;
    for (auto& [key, tracked] : tracked_) {
        (void)key;
        if (tracked.handled || tracked.lastSeen != snapshot.observedAt) continue;
        target_ = tracked.observation;
        if (preference(target_.identity) == AutomaticRecordingPreference::never) {
            state_ = AutomaticPromptState::suppressed;
            continue;
        }
        if (tracked.lastSeen - tracked.firstSeen < 5s) { state_ = AutomaticPromptState::detecting; continue; }
        if (!prerequisites.allowsStart()) { state_ = AutomaticPromptState::blocked; return {state_}; }
        if (preference(target_.identity) == AutomaticRecordingPreference::always)
            return start(AutomaticStartReason::savedPreference, false);
        promptStartedAt_ = now;
        state_ = AutomaticPromptState::countdown;
        return {state_};
    }
    return {state_};
}

AutomaticRecordingDecision AutomaticRecordingPolicy::recordNow(bool rememberChoice, const TargetDetectionSnapshot& snapshot,
    const AutomaticRecordingPrerequisites& prerequisites, DetectionClock::time_point now) {
    if (state_ != AutomaticPromptState::countdown) return {state_};
    if (now < promptStartedAt_ || !currentTargetReady(snapshot, now) || !prerequisites.allowsStart() ||
        preference(target_.identity) == AutomaticRecordingPreference::never) {
        state_ = AutomaticPromptState::blocked;
        return {state_};
    }
    // A delayed UI callback after expiry is a timer outcome, never remembrance.
    return secondsRemaining(now) == 0 ? start(AutomaticStartReason::promptExpired, false) :
        start(AutomaticStartReason::promptButton, rememberChoice);
}

AutomaticRecordingDecision AutomaticRecordingPolicy::refuse(bool rememberChoice, DetectionClock::time_point now) {
    if (state_ != AutomaticPromptState::countdown || now < promptStartedAt_ || secondsRemaining(now) == 0) return {state_};
    const auto saved = rememberChoice && setPreference(target_.identity, AutomaticRecordingPreference::never);
    cancel();
    state_ = AutomaticPromptState::refused;
    return {state_, false, saved};
}

void AutomaticRecordingPolicy::captureAccepted() {
    if (state_ != AutomaticPromptState::started || recordingTarget_) return;
    recordingTarget_ = target_.identity;
    lastCaptureEvidenceAt_ = tracked_.at(VerifiedTargetRegistry::preferenceKey(*recordingTarget_)).lastSeen;
    lastCaptureSnapshotAt_ = lastCaptureEvidenceAt_;
    captureAbsentSince_.reset();
}

bool AutomaticRecordingPolicy::shouldStopCapture(const TargetDetectionSnapshot& snapshot, bool captureActive,
                                                 DetectionClock::time_point now) {
    if (!recordingTarget_) return false;
    if (!captureActive) {
        recordingTarget_.reset();
        captureAbsentSince_.reset();
        return false;
    }
    if (!fresh(snapshot, now) || snapshot.observedAt < lastCaptureSnapshotAt_) {
        captureAbsentSince_.reset();
    } else if (snapshot.observedAt > lastCaptureSnapshotAt_) {
        if (snapshot.observedAt - lastCaptureSnapshotAt_ > 2s) captureAbsentSince_.reset();
        lastCaptureSnapshotAt_ = snapshot.observedAt;
        const auto key = VerifiedTargetRegistry::preferenceKey(*recordingTarget_);
        const bool present = std::any_of(snapshot.observations.begin(), snapshot.observations.end(), [&](const auto& item) {
            return VerifiedTargetRegistry::preferenceKey(item.identity) == key &&
                WindowsTargetDetector::isPromptCandidate(item, registry_);
        });
        if (present) {
            lastCaptureEvidenceAt_ = snapshot.observedAt;
            captureAbsentSince_.reset();
        } else if (!captureAbsentSince_) {
            captureAbsentSince_ = snapshot.observedAt;
        }
    }
    if ((captureAbsentSince_ && lastCaptureSnapshotAt_ - *captureAbsentSince_ >= 15s) ||
        now - lastCaptureEvidenceAt_ >= 600s) {
        cancel();
        return true;
    }
    return false;
}

void AutomaticRecordingPolicy::cancel() noexcept {
    recordingTarget_.reset();
    captureAbsentSince_.reset();
    // Avoid allocating a key from a noexcept Stop/dismissal path.
    for (auto& [key, tracked] : tracked_) {
        (void)key;
        if (tracked.observation.identity.executableFingerprint == target_.identity.executableFingerprint &&
            tracked.observation.identity.publisherFingerprint == target_.identity.publisherFingerprint &&
            tracked.observation.identity.registryVersion == target_.identity.registryVersion) tracked.handled = true;
    }
    state_ = AutomaticPromptState::idle;
}

} // namespace graf::windows
