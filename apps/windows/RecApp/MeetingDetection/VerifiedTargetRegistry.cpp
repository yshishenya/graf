#include "VerifiedTargetRegistry.h"

#include <algorithm>

namespace graf::windows {

bool VerifiedTargetRegistry::validTargetKey(std::string_view key) noexcept {
    return !key.empty() && key.size() <= 64 && key.front() >= 'a' && key.front() <= 'z' &&
        std::all_of(key.begin(), key.end(), [](char c) {
            return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_';
        });
}

bool VerifiedTargetRegistry::validIdentity(const VerifiedTargetIdentity& identity) noexcept {
    const auto digest = [](std::string_view value) {
        return value.size() == 64 && std::all_of(value.begin(), value.end(), [](char c) {
            return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
        });
    };
    return validTargetKey(identity.targetKey) && digest(identity.executableFingerprint) && digest(identity.publisherFingerprint) &&
        identity.registryVersion != 0 && !identity.displayName.empty() && identity.displayName.size() <= 128 &&
        std::none_of(identity.displayName.begin(), identity.displayName.end(), [](unsigned char c) {
            return c < 32 || c == 127;
        });
}

std::string VerifiedTargetRegistry::identityKey(const VerifiedTargetIdentity& identity) {
    return std::to_string(identity.registryVersion) + ":" + identity.executableFingerprint + ":" +
        identity.publisherFingerprint;
}

VerifiedTargetRegistry VerifiedTargetRegistry::bundled() {
    VerifiedTargetRegistry registry;
    // Teams 26213.1006.5014.9784 ARM64, native WinVerifyTrust proof 2026-09-06.
    // Provenance: specs/200-windows-desktop-app/research.md (first Windows catalog).
    // Other versions are not enrolled by discovery; each needs reviewed pins.
    registry.targets_ = {{
        "d2538d0290c463a896e2710534b5e078066d4c9519e3111754186f7f38fe2dd4",
        "c4514cb03fff0842be711ecfec8560be9cc5fc7dbd1f7db95c68257ff77aae2f",
        "Microsoft Teams", 1, "microsoft_teams_new"
    }};
    return registry;
}

const VerifiedTargetIdentity* VerifiedTargetRegistry::find(std::string_view executable,
                                                          std::string_view publisher) const noexcept {
    for (const auto& target : targets_) {
        if (target.executableFingerprint == executable && target.publisherFingerprint == publisher) return &target;
    }
    return nullptr;
}

bool VerifiedTargetRegistry::registerTarget(VerifiedTargetIdentity identity) {
    if (!validIdentity(identity)) return false;
    for (const auto& target : targets_) {
        if ((target.executableFingerprint == identity.executableFingerprint && target.targetKey != identity.targetKey) ||
            (target.targetKey == identity.targetKey && target.displayName != identity.displayName)) return false;
    }
    for (auto& target : targets_) {
        if (target.executableFingerprint == identity.executableFingerprint) { target = std::move(identity); return true; }
    }
    if (targets_.size() >= maximumTargets) return false;
    targets_.push_back(std::move(identity));
    return true;
}

bool VerifiedTargetRegistry::removeTarget(std::string_view fingerprint) {
    for (auto it = targets_.begin(); it != targets_.end(); ++it) {
        if (it->executableFingerprint == fingerprint) { targets_.erase(it); return true; }
    }
    return false;
}

bool VerifiedTargetRegistry::contains(const VerifiedTargetIdentity& identity) const noexcept {
    const auto* target = find(identity.executableFingerprint, identity.publisherFingerprint);
    return target && target->registryVersion == identity.registryVersion && target->targetKey == identity.targetKey;
}

} // namespace graf::windows
