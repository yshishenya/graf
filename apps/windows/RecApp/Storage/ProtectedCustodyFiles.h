#pragma once

#include "ProtectedCustodyCodec.h"
#include <filesystem>
#include <memory>
#include <string_view>
#include <atomic>
#include <mutex>

namespace graf::windows {
class ProtectedCustodyStoreOwner;
class ProtectedCustodyRecordingPackage;
struct CustodyMetadataCommit;
#ifdef _WIN32
class ProtectedCustodyPackagePair;
struct CustodyReader;
using CustodyPackageReaders = std::array<std::array<CustodyReader, 5>, 2>;
#endif

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
struct CustodyMetadataIndices {
    std::array<CustodyIndex, 2> indices;
    std::uint32_t selectedSlot = 0;
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
    // Worker-only direct historical ciphertext, migrationIntent/position0 only.
    // Caller retains this lease and verifies the authenticated ref/content;
    // no historical index, tombstone path/conflict or recovery/GC authority.
    [[nodiscard]] CustodyFileResult<CustodyBytes> readMigrationBirthEnvelope(
        std::uint64_t version, std::uint32_t exactEnvelopeBytes);
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
    // Same physical validator, metadata roles only, BOTH complete indices.
    // The caller must retain/exclude the writer; a returned array alone is NOT
    // frozen ownership, semantic metadata authority, a package or GC admission.
    [[nodiscard]] CustodyFileResult<CustodyMetadataIndices> readValidatedMetadataPair();

private:
    friend class ProtectedCustodyStoreOwner;
    friend class ProtectedCustodyRecordingPackage;
    friend class ProtectedCustodyPackagePair;
    friend struct CustodyMetadataCommit;
    // Existing fixed package-state identity under a continuously held genuine store.
    // Read-only metadata lease, no create/repair or consumer/account authority.
    [[nodiscard]] static CustodyFileResult<std::unique_ptr<ProtectedCustodyFiles>> openPackageState(
        std::shared_ptr<const ProtectedCustodyFiles>, std::string_view,
        std::shared_ptr<const std::atomic<bool>>);
    [[nodiscard]] static CustodyFileResult<std::unique_ptr<ProtectedCustodyFiles>> openPackageMember(
        std::shared_ptr<const ProtectedCustodyFiles> packageState, const CustodyContext&,
        std::shared_ptr<const std::atomic<bool>>);
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<ProtectedCustodyFiles>> createPackageRoot(
        std::shared_ptr<const ProtectedCustodyFiles>, std::string_view,
        std::shared_ptr<const std::atomic<bool>>, std::shared_ptr<ProtectedCustodyFiles>* retainedFailure);
    [[nodiscard]] static CustodyFileResult<std::unique_ptr<ProtectedCustodyFiles>> createPackageRole(
        std::shared_ptr<const ProtectedCustodyFiles>, CustodyRole,
        std::unique_ptr<ProtectedCustodyFiles>* retainedFailure);
    [[nodiscard]] std::unique_lock<std::mutex> lockWriteGroup();
    [[nodiscard]] unsigned storagePressurePercent() const noexcept;
    [[nodiscard]] static CustodyFileResult<std::unique_ptr<ProtectedCustodyFiles>> lockStoreRoot(
        const std::filesystem::path&, std::shared_ptr<const std::atomic<bool>>, bool& birth);
    [[nodiscard]] static CustodyFileResult<std::unique_ptr<ProtectedCustodyFiles>> openStoreObject(
        std::shared_ptr<const ProtectedCustodyFiles> root, CustodyRole, bool birth);
    [[nodiscard]] CustodyFileResult<bool> validateStoreInventory(
        bool virgin, std::shared_ptr<const std::atomic<bool>>, bool completeBirth = false) const;
    friend class ProtectedCustodyBootstrapPair;
    friend class ProtectedCustodyMigrationPair;
    // Only retained metadata factories discover existing fixed identities.
    // Retains immutable store and exclusive object handles; never creates IDs.
    [[nodiscard]] static CustodyFileResult<std::unique_ptr<ProtectedCustodyFiles>> discover(
        const std::filesystem::path&, CustodyRole, std::string_view package = {});
    [[nodiscard]] static CustodyFileResult<std::unique_ptr<ProtectedCustodyFiles>> openImpl(
        const std::filesystem::path&, std::string_view, const CustodyContext&, CustodyFileAccess, bool discover);
    [[nodiscard]] const CustodyContext& context() const noexcept;
#ifdef _WIN32
    [[nodiscard]] const std::filesystem::path& trustedRoot() const noexcept;
    [[nodiscard]] std::filesystem::path packagePath() const;
    // Only the own-pair member consumer reuses BOTH validated snapshots. No
    // public audio metadata-pair API or second scanner/selection algorithm.
    friend CustodyFileResult<CustodyReader> openProtectedCustodyReader(
        const std::filesystem::path&, std::shared_ptr<const ProtectedCustodyPackagePair>,
        std::uint32_t, std::size_t, std::shared_ptr<const std::atomic<bool>>);
    friend CustodyFileResult<CustodyPackageReaders> openProtectedCustodyReaders(
        const std::filesystem::path&, std::shared_ptr<const ProtectedCustodyPackagePair>,
        std::shared_ptr<const std::atomic<bool>>);
    friend CustodyFileResult<CustodyPackageReaders> openProtectedCustodyReaders(
        std::shared_ptr<ProtectedCustodyRecordingPackage>, std::shared_ptr<const ProtectedCustodyPackagePair>,
        std::shared_ptr<const std::atomic<bool>>);
#endif
    friend class ProtectedPackedCustodyOwner; // Reuse confinement; no second path/security backend.
    struct State;
    explicit ProtectedCustodyFiles(std::unique_ptr<State>);
    [[nodiscard]] CustodyFileResult<CustodySnapshot> readValidatedSnapshotImpl(
        CustodyIndex* peer, std::uint32_t* selected);
    std::unique_ptr<State> state_;
};

} // namespace graf::windows
