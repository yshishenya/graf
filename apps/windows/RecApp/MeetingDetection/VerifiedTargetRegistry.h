#pragma once

#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

namespace graf::windows {

struct VerifiedTargetIdentity {
    std::string executableFingerprint;
    std::string publisherFingerprint;
    std::string displayName;
    std::uint32_t registryVersion = 0;
};

class VerifiedTargetRegistry final {
public:
    [[nodiscard]] bool registerTarget(VerifiedTargetIdentity identity);
    [[nodiscard]] bool removeTarget(std::string_view executableFingerprint);
    [[nodiscard]] bool contains(std::string_view executableFingerprint, std::uint32_t version) const noexcept;
    [[nodiscard]] const std::vector<VerifiedTargetIdentity>& targets() const noexcept { return targets_; }

private:
    std::vector<VerifiedTargetIdentity> targets_;
};

} // namespace graf::windows
