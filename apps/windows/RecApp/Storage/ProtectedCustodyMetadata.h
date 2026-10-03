#pragma once

#include "ProtectedCustodyFiles.h"
#include <atomic>

namespace graf::windows {

struct CustodyMetadataCommit {
private:
    // Actual object/32-owner admission survives the worker until result adoption.
    // Reverse member destruction closes the lease before releasing admission.
    std::optional<CustodyPin> pin_;
    friend CustodyMetadataCommit commitProtectedCustodyMetadata(const std::filesystem::path&,
        std::string_view, const CustodyContext&, std::uint64_t, const CustodyBytes&,
        std::shared_ptr<const std::atomic<bool>>);
public:
    CustodyMetadataCommit() = default;
    CustodyMetadataCommit(const CustodyMetadataCommit&) = delete;
    // Prepare the throwing snapshot move while source lease/pin still own it.
    // Declaration order stays unchanged: destruction releases snapshot first.
    CustodyMetadataCommit(CustodyMetadataCommit&& other)
        : snapshot(std::move(other.snapshot)), context(other.context),
          baseGeneration(other.baseGeneration), targetGeneration(other.targetGeneration),
          state(other.state), error(other.error), nativeError(other.nativeError) {
        if (other.pin_) pin_.emplace(std::move(*other.pin_));
        lease = std::move(other.lease);
    }
    CustodyMetadataCommit& operator=(CustodyMetadataCommit&&) = delete; // Pin is nonassignable.
    std::unique_ptr<ProtectedCustodyFiles> lease;
    std::optional<CustodySnapshot> snapshot;
    CustodyContext context{};
    std::uint64_t baseGeneration = 0, targetGeneration = 0;
    CustodyCommitState state = CustodyCommitState::notCommitted;
    CustodyFileError error = CustodyFileError::none;
    std::uint32_t nativeError = 0;
};

// Worker-only full-value metadata persistence (never UI/capture callback IO).
// base=0 means exclusive NEW object, not missing/corrupt-object recovery. Caller
// owns exact bounded value, semantic JSON/account validation and admission lease.
// This terminal worker result is NOT the async ticket, projection adoption,
// package sealing or permission for network/delete/GC effects. Release on worker.
[[nodiscard]] CustodyMetadataCommit commitProtectedCustodyMetadata(
    const std::filesystem::path& trustedRoot, std::string_view packageDirectoryId,
    const CustodyContext&, std::uint64_t baseGeneration, const CustodyBytes& value,
    std::shared_ptr<const std::atomic<bool>> cancellation);

} // namespace graf::windows
