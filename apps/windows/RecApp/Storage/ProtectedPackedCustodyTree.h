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

struct PackedTreeCommit {
    // Failed/ambiguous results retain the actual base owner until discarded.
    std::shared_ptr<const ProtectedPackedCustodyTree> lease;
    std::shared_ptr<const ProtectedPackedCustodyTree> snapshot; // Committed only.
    CustodyCommitState state = CustodyCommitState::notCommitted;
    CustodyFileError error = CustodyFileError::none;
    std::uint32_t nativeError = 0;
};

// Media root proof only, not a package, historical-retainer, upload or GC
// authority. Created after cold full closure or a checked same-owner transition.
// No caller-supplied descriptors/verified flags; no lazy cold authority/cache.
class ProtectedPackedCustodyTree final : public std::enable_shared_from_this<ProtectedPackedCustodyTree> {
public:
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<const ProtectedPackedCustodyTree>> verify(
        std::shared_ptr<ProtectedPackedCustodyOwner>);
    // Full cold closure of current pair AND a separately supplied historical
    // stamp. Context/stamp provenance remains the metadata caller's obligation;
    // this readonly media proof never grants package/upload/delete/GC authority.
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<const ProtectedPackedCustodyTree>> verifyRetained(
        std::shared_ptr<ProtectedPackedCustodyOwner>, const PackedCustodyContext&, const PackedRootDescriptor&);
    [[nodiscard]] const PackedRootDescriptor& descriptor() const noexcept { return retained_ ? *retained_ : heads_[selected_]; }
    [[nodiscard]] std::uint64_t generation() const noexcept { return descriptor().generation; }
    [[nodiscard]] std::uint64_t logicalBytes() const noexcept { return descriptor().logicalBytes; }
    // Slot of the validated current pair, not a physical slot for retained_.
    [[nodiscard]] std::uint32_t selectedSlot() const noexcept { return selected_; }
    [[nodiscard]] CustodyFileResult<bool> checkRead() const;
    [[nodiscard]] CustodyFileResult<PackedPlainRead> readBlock(std::uint64_t block) const;
    // Worker-only: one nonempty block at aligned EOF, or complete replacement
    // of one existing block (short tail: same size or growth, never shrink).
    // No arbitrary Write, app adoption or destructor IO yet.
    [[nodiscard]] PackedTreeCommit appendBlock(const CustodyBytes&) const;
    [[nodiscard]] PackedTreeCommit replaceBlock(std::uint64_t index, const CustodyBytes&) const;
    [[nodiscard]] PackedTreeCommit setSize(std::uint64_t length) const;
    ProtectedPackedCustodyTree(const ProtectedPackedCustodyTree&) = delete;
    ProtectedPackedCustodyTree& operator=(const ProtectedPackedCustodyTree&) = delete;
private:
    friend class ProtectedCustodyWriter;
    using Guard = ProtectedPackedCustodyOwner::Guard;
    [[nodiscard]] CustodyFileResult<bool> checkWrite() const;
    [[nodiscard]] PackedTreeCommit commitBlock(const CustodyBytes*, std::optional<std::uint64_t> index,
        std::optional<std::uint64_t> size = std::nullopt) const;
    ProtectedPackedCustodyTree(CustodyPin&&, std::shared_ptr<ProtectedPackedCustodyOwner>,
        const std::array<PackedRootDescriptor, 2>&, std::uint32_t, CustodyRole,
        std::optional<PackedRootDescriptor>) noexcept;
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<const ProtectedPackedCustodyTree>> verifyImpl(
        std::shared_ptr<ProtectedPackedCustodyOwner>, const PackedCustodyContext*, const PackedRootDescriptor*);
    [[nodiscard]] static CustodyFileResult<bool> walk(Guard&, const PackedRootDescriptor&,
        const PackedReference&, std::uint64_t base);
    [[nodiscard]] static std::shared_ptr<const ProtectedPackedCustodyTree> makeProof(
        CustodyPin&&, std::shared_ptr<ProtectedPackedCustodyOwner>,
        const std::array<PackedRootDescriptor, 2>&, std::uint32_t, CustodyRole,
        std::optional<PackedRootDescriptor> = std::nullopt);
    [[nodiscard]] static CustodyFileResult<std::array<PackedRootDescriptor, 2>> readHeads(Guard&);
    CustodyPin pin_; // Owner closes before pin release.
    std::shared_ptr<ProtectedPackedCustodyOwner> owner_;
    const std::array<PackedRootDescriptor, 2> heads_;
    const std::uint32_t selected_;
    const CustodyRole role_;
    const std::optional<PackedRootDescriptor> retained_; // Own immutable stamp; all writes rejected, even no-op.
};
} // namespace graf::windows
