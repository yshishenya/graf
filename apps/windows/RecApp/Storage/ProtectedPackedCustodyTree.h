#pragma once

#include "ProtectedPackedCustodyOwner.h"

namespace graf::windows {
struct PackedPlainRead {
    // Prepare the potentially throwing byte move before transferring custody.
    CustodyBytes bytes = CustodyBytes(0);
    CustodyPin pin;
    std::shared_ptr<const ProtectedPackedCustodyTree> proof;
    explicit PackedPlainRead(CustodyPin&& held) : pin(std::move(held)) {}
    PackedPlainRead(PackedPlainRead&&) = default;
    PackedPlainRead(const PackedPlainRead&) = delete;
    ~PackedPlainRead(); // Wipe bytes BEFORE releasing proof/native owner/pin.
};

// Current-pair proof ONLY, not a package, historical-retainer, upload, GC or
// commit authority. Created exclusively after both HEADs and full closures.
// No caller-supplied descriptors/verified flags; no lazy cold authority/cache.
class ProtectedPackedCustodyTree final : public std::enable_shared_from_this<ProtectedPackedCustodyTree> {
public:
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<const ProtectedPackedCustodyTree>> verify(
        std::shared_ptr<ProtectedPackedCustodyOwner>);
    [[nodiscard]] std::uint64_t generation() const noexcept { return heads_[selected_].generation; }
    [[nodiscard]] std::uint64_t logicalBytes() const noexcept { return heads_[selected_].logicalBytes; }
    [[nodiscard]] std::uint32_t selectedSlot() const noexcept { return selected_; }
    [[nodiscard]] CustodyFileResult<PackedPlainRead> readBlock(std::uint64_t block) const;
    ProtectedPackedCustodyTree(const ProtectedPackedCustodyTree&) = delete;
    ProtectedPackedCustodyTree& operator=(const ProtectedPackedCustodyTree&) = delete;
private:
    using Guard = ProtectedPackedCustodyOwner::Guard;
    ProtectedPackedCustodyTree(CustodyPin&&, std::shared_ptr<ProtectedPackedCustodyOwner>,
        const std::array<PackedRootDescriptor, 2>&, std::uint32_t) noexcept;
    [[nodiscard]] static CustodyFileResult<bool> walk(Guard&, const PackedRootDescriptor&,
        const PackedReference&, std::uint64_t base);
    CustodyPin pin_; // Owner closes before pin release.
    std::shared_ptr<ProtectedPackedCustodyOwner> owner_;
    const std::array<PackedRootDescriptor, 2> heads_;
    const std::uint32_t selected_;
};
} // namespace graf::windows
