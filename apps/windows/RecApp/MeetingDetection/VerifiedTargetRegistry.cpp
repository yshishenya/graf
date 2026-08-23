#include "VerifiedTargetRegistry.h"

namespace graf::windows {

bool VerifiedTargetRegistry::registerTarget(VerifiedTargetIdentity identity) {
    if (identity.executableFingerprint.empty() || identity.publisherFingerprint.empty() ||
        identity.displayName.empty() || identity.registryVersion == 0) return false;
    for (auto& target : targets_) {
        if (target.executableFingerprint == identity.executableFingerprint) { target = std::move(identity); return true; }
    }
    targets_.push_back(std::move(identity));
    return true;
}

bool VerifiedTargetRegistry::removeTarget(std::string_view fingerprint) {
    for (auto it = targets_.begin(); it != targets_.end(); ++it) {
        if (it->executableFingerprint == fingerprint) { targets_.erase(it); return true; }
    }
    return false;
}

bool VerifiedTargetRegistry::contains(std::string_view fingerprint, std::uint32_t version) const noexcept {
    for (const auto& target : targets_) {
        if (target.executableFingerprint == fingerprint && target.registryVersion == version) return true;
    }
    return false;
}

} // namespace graf::windows
