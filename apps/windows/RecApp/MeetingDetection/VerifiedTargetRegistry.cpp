#include "VerifiedTargetRegistry.h"

#include <algorithm>

namespace graf::windows {

bool VerifiedTargetRegistry::validIdentity(const VerifiedTargetIdentity& identity) noexcept {
    const auto digest = [](std::string_view value) {
        return value.size() == 64 && std::all_of(value.begin(), value.end(), [](char c) {
            return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
        });
    };
    return digest(identity.executableFingerprint) && digest(identity.publisherFingerprint) &&
        identity.registryVersion != 0 && !identity.displayName.empty() && identity.displayName.size() <= 128 &&
        std::none_of(identity.displayName.begin(), identity.displayName.end(), [](unsigned char c) {
            return c < 32 || c == 127;
        });
}

std::string VerifiedTargetRegistry::preferenceKey(const VerifiedTargetIdentity& identity) {
    return std::to_string(identity.registryVersion) + ":" + identity.executableFingerprint + ":" +
        identity.publisherFingerprint;
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

bool VerifiedTargetRegistry::contains(std::string_view fingerprint, std::string_view publisherFingerprint,
                                      std::uint32_t version) const noexcept {
    for (const auto& target : targets_) {
        if (target.executableFingerprint == fingerprint && target.publisherFingerprint == publisherFingerprint &&
            target.registryVersion == version) return true;
    }
    return false;
}

} // namespace graf::windows
