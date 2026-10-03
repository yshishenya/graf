#pragma once

#include "ProtectedCustodyCodec.h"
#include <filesystem>
#include <memory>
#include <string_view>

namespace graf::windows {

enum class CustodyFileError {
    none, unsupportedPlatform, invalidInput, unsafePath, unsafeFile,
    identityMismatch, ioFailed, invalidContent, conflict, writerFailed, allocationFailed,
    hashFailed, protectionFailed, recoveryRequired,
};
inline CustodyFileError codecFileError(CustodyCodecError error) noexcept {
    switch (error) {
    case CustodyCodecError::invalidInput: return CustodyFileError::invalidInput;
    case CustodyCodecError::invalidEnvelope:
    case CustodyCodecError::invalidPlaintext: return CustodyFileError::invalidContent;
    case CustodyCodecError::hashFailed: return CustodyFileError::hashFailed;
    case CustodyCodecError::allocationFailed: return CustodyFileError::allocationFailed;
    case CustodyCodecError::unsupportedPlatform: return CustodyFileError::unsupportedPlatform;
    default: return CustodyFileError::protectionFailed; // Native/unknown is not proven corruption.
    }
}
template<class T> struct CustodyFileResult {
    std::optional<T> value;
    CustodyFileError error = CustodyFileError::none;
    std::uint32_t nativeError = 0;
    [[nodiscard]] bool ok() const noexcept { return value.has_value(); }
};
enum class CustodyFileAccess { readExisting, writeExisting, createNew };
enum class CustodyPublishState { notPublished, published, ambiguous };
enum class CustodyCommitState { notCommitted, committed, ambiguous };
struct CustodyPublishResult {
    CustodyPublishState state = CustodyPublishState::notPublished;
    CustodyFileError error = CustodyFileError::none;
    std::uint32_t nativeError = 0;
};
enum class CustodySnapshotState { verified, trustedPrefix };
struct CustodySnapshot {
    CustodyIndex index;
    CustodySnapshotState state = CustodySnapshotState::trustedPrefix;
    CustodyFileError recoveryError = CustodyFileError::none;
    std::uint32_t nativeError = 0;
};

// Worker-only physical IO/checkpoint validation. The caller reserves its buffer
// budget and owns the logical snapshot/pins. A published slot is NOT a logical commit
// ACK (in particular, metadata birth requires the independently verified g1 pair).
// No bootstrap-ID regeneration, ledger authority, migration, GC or plaintext IO.
class ProtectedCustodyFiles final {
public:
    [[nodiscard]] static CustodyFileResult<std::unique_ptr<ProtectedCustodyFiles>> open(
        const std::filesystem::path& trustedRoot, std::string_view packageDirectoryId,
        const CustodyContext&, CustodyFileAccess);
    ~ProtectedCustodyFiles();
    ProtectedCustodyFiles(const ProtectedCustodyFiles&) = delete;
    ProtectedCustodyFiles& operator=(const ProtectedCustodyFiles&) = delete;

    // Envelopes must already have been sealed by the codec. They are decoded and
    // validated before writing and on every read; returned bytes stay ciphertext.
    [[nodiscard]] CustodyFileResult<CustodyBytes> readBlock(
        std::uint64_t position, std::uint64_t version, std::uint32_t payloadBytes,
        std::uint32_t exactEnvelopeBytes);
    [[nodiscard]] CustodyFileResult<std::uint32_t> writeBlock(
        std::uint64_t position, std::uint64_t version, std::uint32_t payloadBytes,
        const CustodyBytes& envelope);
    // Stream the confined inventory, including unreferenced orphan versions.
    // Never overwrite/reuse a version or treat enumeration failure as empty.
    [[nodiscard]] CustodyFileResult<std::uint64_t> nextBlockVersion(std::uint64_t position);
    // Physical peak before content writes, rounded conservatively per new file.
    // Does not replace inventory/device-retention or account/admission gates.
    [[nodiscard]] CustodyFileResult<std::uint64_t> checkWriteReserve(
        std::uint64_t peakBytes, std::uint32_t newFiles);
    [[nodiscard]] CustodyFileResult<CustodyBytes> readIndex(std::uint32_t slot);
    [[nodiscard]] CustodyPublishResult publishIndex(std::uint32_t slot, const CustodyBytes& envelope);
    // Retain handles/artifacts for inspection, but require a fresh instance for reconciliation.
    void blockWrites() noexcept;
    // Validate both indices AND every DATA ref before selection. A verified byte
    // checkpoint is not a sealed normal package, logical ACK or upload/delete
    // permission, nor proof that a higher generation never existed. The caller
    // must keep this object and its snapshot pins/ownership alive during use.
    // trustedPrefix retains the original fault and prohibits further writes;
    // reconciliation requires a fresh instance, never an automatic birth repair.
    [[nodiscard]] CustodyFileResult<CustodySnapshot> readValidatedSnapshot();

private:
    friend class ProtectedPackedCustodyOwner; // Reuse confinement; no second path/security backend.
    struct State;
    explicit ProtectedCustodyFiles(std::unique_ptr<State>);
    std::unique_ptr<State> state_;
};

} // namespace graf::windows
