#pragma once

#include "ProtectedCustodyFiles.h"
#include "ProtectedPackedCustodyFormat.h"
#include "../Contracts/WindowsDesktopContracts.h"
#include <atomic>
#include <mutex>

namespace graf::windows {

struct CustodyMetadataCommit;
class ProtectedUploadQueueValue;
class ProtectedCustodyRecordingPackage;
class ProtectedCustodyPackagePair;
class ProtectedCustodyWriter;
class ProtectedPackedCustodyOwner;
template<class String> struct BasicLocalPurgeTask;
// Internal worker ownership, not a UI capability or consumer-ready flag.
// The persistent worker is the sole owner of all references/last release.
class ProtectedCustodyStoreOwner final {
public:
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<ProtectedCustodyStoreOwner>> open(
        const std::filesystem::path&, std::shared_ptr<const std::atomic<bool>> cancellation);
    [[nodiscard]] CustodyContext queueContext() const noexcept { return queueContext_; }
    [[nodiscard]] std::uint64_t queueGeneration() const noexcept { return queueGeneration_; }
    [[nodiscard]] CustodyFileResult<std::shared_ptr<const ProtectedUploadQueueValue>> readQueueValue(
        std::shared_ptr<const std::atomic<bool>> cancellation);
    [[nodiscard]] CustodyFileResult<std::shared_ptr<ProtectedCustodyRecordingPackage>> createPackage(
        std::string_view directory, std::shared_ptr<const std::atomic<bool>> cancellation);
    // Worker-only persisted identity discovery; metadata provenance, NOT a sealed
    // artifact/account/upload/delete capability. Caller must inspect BOTH closures.
    [[nodiscard]] CustodyFileResult<std::shared_ptr<const ProtectedCustodyPackagePair>> readPackage(
        std::string_view directory, std::shared_ptr<const std::atomic<bool>> cancellation);
    // Worker-only fresh semantic metadata ACK through readPackage's retained
    // read-only lease; not a standalone Pair::read or writer alias. Does not
    // grant account, playback, upload, mutation or delete rights.
    [[nodiscard]] CustodyFileResult<bool> revalidatePackage(
        std::shared_ptr<const ProtectedCustodyPackagePair>, std::shared_ptr<const std::atomic<bool>> cancellation);
    // Sole worker, after actual consumer drain. Revalidate durable scoped
    // intent; erase only the private candidate AFTER OS absence. Caller still
    // owes protected metadata commit and adoption, including after restart.
    [[nodiscard]] CustodyFileResult<bool> purgeLocalPackage(std::string_view localId, std::uint64_t expectedGeneration,
        ProtectedUploadQueueValue& candidate, std::uint64_t nowMs, std::shared_ptr<const std::atomic<bool>> cancellation,
        const BasicLocalPurgeTask<CustodyString>* serverTask = nullptr,
        std::string_view user = {}, std::string_view workspace = {});
    ~ProtectedCustodyStoreOwner();
    ProtectedCustodyStoreOwner(const ProtectedCustodyStoreOwner&) = delete;
private:
    explicit ProtectedCustodyStoreOwner(CustodyPin&&);
    [[nodiscard]] CustodyFileResult<bool> validate(std::shared_ptr<const std::atomic<bool>>,
        std::shared_ptr<const ProtectedUploadQueueValue>* selectedValue = nullptr);
    // Defined beside the existing charged queue decoder, not a second parser.
    [[nodiscard]] static CustodyFileResult<bool> validateQueueValue(std::string_view, const std::atomic<bool>*);
#ifdef _WIN32
    [[nodiscard]] const std::filesystem::path& rootPath() const noexcept { return root_->trustedRoot(); }
#endif
    friend CustodyMetadataCommit commitProtectedCustodyMetadata(
        std::shared_ptr<ProtectedCustodyStoreOwner>, const CustodyContext&, std::uint64_t,
        const CustodyBytes&, std::shared_ptr<const std::atomic<bool>>);
    std::optional<CustodyPin> pin_;
    std::shared_ptr<ProtectedCustodyFiles> root_; // Share only immutable root/store ownership, never queue authority.
    std::unique_ptr<ProtectedCustodyFiles> bootstrap_, queue_;
    std::shared_ptr<ProtectedCustodyRecordingPackage> failedPackage_; // Partial birth remains owned until worker reconciliation/release.
    CustodyContext queueContext_{{}, {}, CustodyRole::queue};
    std::uint64_t queueGeneration_ = 0;
    bool failed_ = false;
};

enum class CustodyBootstrapMode { migrating, protectedStore };
enum class CustodyMigrationSubject { queue, package };
enum class CustodyMigrationStage { prepared, copiedVerified, switched, cleanupPending, complete };
enum class CustodyMigrationSourceKind { ledger, manifest, canonical, media, playback, recovery };
enum class CustodyCleanupKind { ownerConfirmation, deletePurge };
struct CustodyMigrationAnchor {
    std::optional<CustodyId> objectId;
    std::optional<std::uint64_t> generation;
    std::uint64_t length = 0;
    std::array<std::uint8_t, 32> sha256{};
};
struct CustodyMigrationSource {
    CustodyMigrationSourceKind kind = CustodyMigrationSourceKind::ledger;
    std::uint64_t length = 0;
    std::array<std::uint8_t, 32> sha256{};
    CustodyId destinationObjectId{};
    std::optional<std::uint64_t> destinationGeneration, destinationLength;
    std::optional<std::array<std::uint8_t, 32>> destinationSha256;
    bool destinationPacked = false;
    std::optional<CustodyId> destinationContainerId;
    std::optional<std::uint64_t> destinationCommittedExtent;
    std::optional<ProtectedPackedCustodyFormat::Reference> destinationRootRef;
};
struct CustodyMigrationBarrier {
    CustodyId objectId{};
    std::uint64_t generation = 0, blockVersion = 0, envelopeBytes = 0;
    std::array<std::uint8_t, 32> sha256{};
};
struct CustodyCleanupAuthorization {
    CustodyCleanupKind kind = CustodyCleanupKind::ownerConfirmation;
    std::array<char, 301> operationId{}, actorUserId{}, workspaceId{};
    CustodyId queueObjectId{};
    std::uint64_t queueGeneration = 0;
};
// Structural tuple only, not durable intent, historical provenance, fixed
// queue/owner authority, permission to rename/switch/cleanup, or absence proof.
struct CustodyMigrationValue {
    unsigned schema = 1;
    CustodyContext context{{}, {}, CustodyRole::migrationIntent};
    std::uint64_t generation = 0;
    CustodyId transactionId{};
    CustodyMigrationSubject subject = CustodyMigrationSubject::queue;
    std::optional<std::array<char, 301>> directory;
    CustodyMigrationStage stage = CustodyMigrationStage::prepared;
    CustodyMigrationAnchor anchor;
    std::array<CustodyMigrationSource, 6> sources{};
    std::size_t sourceCount = 0;
    std::optional<CustodyMigrationBarrier> barrier;
    std::optional<CustodyCleanupAuthorization> authorization;
};
// Worker-only pure codec. All expectations come independently of this JSON;
// queue directory is empty, package directory an explicit validated identity.
[[nodiscard]] CustodyCodecResult<CustodyMigrationValue> readCustodyMigration(
    std::string_view, const CustodyContext&, std::uint64_t, const CustodyId&,
    CustodyMigrationSubject, std::string_view) noexcept;
[[nodiscard]] CustodyCodecResult<CustodyBytes> writeCustodyMigration(
    const CustodyMigrationValue&, const CustodyContext&, std::uint64_t, const CustodyId&,
    CustodyMigrationSubject, std::string_view);
// Worker-only historical content/relationship check against an independently
// authenticated current intent. The borrowed struct does NOT authenticate
// itself; this value grants no current-pair/path/owner/GC/effect authority.
[[nodiscard]] CustodyCodecResult<CustodyMigrationValue> readCustodyMigrationBirth(
    const CustodyBytes& envelope, const CustodyContext&, const CustodyMigrationValue& current,
    const CustodyId& transaction, CustodyMigrationSubject, std::string_view directory);
// Worker-only BOTH own intent slots, consistency and direct Birth content.
// NOT standalone tombstone/conflicting-copy validation, recovery authority,
// bootstrap/queue/account admission, retained-root closure or effect/GC rights.
// Missing direct Birth fails even if a standalone tombstone exists. Recovery
// must independently resolve ALL copies before granting any authority/effect.
class ProtectedCustodyBootstrapPair;
class ProtectedCustodyMigrationPair final {
public:
    // Worker-only bootstrap linkage, not startup admission or queue authority.
    // Fixed root/queue IDs and expected tuple come from the retained discovery
    // parent, never a caller path or this intent's JSON.
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<const ProtectedCustodyMigrationPair>> read(
        std::shared_ptr<const ProtectedCustodyBootstrapPair>,
        std::shared_ptr<const std::atomic<bool>> cancellation);
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<const ProtectedCustodyMigrationPair>> read(
        const std::filesystem::path&, const CustodyContext&, const CustodyId& transaction,
        CustodyMigrationSubject, std::string_view directory,
        std::shared_ptr<const std::atomic<bool>> cancellation);
    [[nodiscard]] const std::array<CustodyMigrationValue, 2>& slots() const noexcept { return values_; }
    [[nodiscard]] const CustodyMetadataIndices& indices() const noexcept { return indices_; }
    [[nodiscard]] std::uint32_t selectedSlot() const noexcept { return indices_.selectedSlot; }
    [[nodiscard]] const CustodyMigrationValue& current() const noexcept { return values_[selectedSlot()]; }
    ~ProtectedCustodyMigrationPair(); // Wipe before exclusive lease/pin release; no IO.
    ProtectedCustodyMigrationPair(const ProtectedCustodyMigrationPair&) = delete;
private:
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<const ProtectedCustodyMigrationPair>> readImpl(
        const std::filesystem::path&, CustodyContext, const CustodyId& transaction,
        CustodyMigrationSubject, std::string_view directory,
        std::shared_ptr<const std::atomic<bool>>, std::shared_ptr<const ProtectedCustodyBootstrapPair>);
    ProtectedCustodyMigrationPair(CustodyPin&&, std::shared_ptr<const ProtectedCustodyBootstrapPair>&&,
        std::unique_ptr<ProtectedCustodyFiles>&&,
        CustodyMetadataIndices&&, const std::array<CustodyMigrationValue, 2>&);
    std::optional<CustodyPin> pin_;
    std::shared_ptr<const ProtectedCustodyBootstrapPair> bootstrap_;
    std::unique_ptr<ProtectedCustodyFiles> lease_;
    CustodyMetadataIndices indices_;
    std::array<CustodyMigrationValue, 2> values_;
};
// Structural metadata only: not bootstrap/queue authority or permission for
// migration, upload, playback, deletion or GC. Independently verify both own
// slots, fixed queue and durable matching intent before any admission/effect.
struct CustodyBootstrapValue {
    unsigned schema = 1;
    CustodyContext context{{}, {}, CustodyRole::bootstrap};
    std::uint64_t generation = 0;
    CustodyId queueObjectId{};
    CustodyBootstrapMode mode = CustodyBootstrapMode::protectedStore;
    std::optional<CustodyId> transactionId;
    std::optional<CustodyMigrationSubject> subject;
    std::optional<std::array<char, 301>> directory;
};
// Borrowed input for this call only; expected context/target generation/queue
// ID must come independently of this JSON. No IO or retained input views.
[[nodiscard]] CustodyCodecResult<CustodyBootstrapValue> readCustodyBootstrap(
    std::string_view, const CustodyContext&, std::uint64_t, const CustodyId&) noexcept;
[[nodiscard]] CustodyCodecResult<CustodyBytes> writeCustodyBootstrap(
    const CustodyBootstrapValue&, const CustodyContext&, std::uint64_t, const CustodyId&);

// Worker-only own bootstrap provenance, BOTH semantic payloads and a retained
// readonly exclusive identity lease. Expected queue ID is independently supplied
// by the fixed-queue/reservation owner, NEVER taken from this JSON. This object
// does NOT prove queue/intent/account/inventory authority or grant admission,
// mutation, upload, playback, deletion, migration or GC. Release on a worker.
class ProtectedCustodyBootstrapPair final {
public:
    // Discover only existing fixed native IDs, retained to last release. A
    // reserved queue ID is NOT a validated ledger, empty queue or admission.
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<const ProtectedCustodyBootstrapPair>> read(
        const std::filesystem::path&, std::shared_ptr<const std::atomic<bool>> cancellation);
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<const ProtectedCustodyBootstrapPair>> read(
        const std::filesystem::path&, const CustodyContext&, const CustodyId& queueObjectId,
        std::shared_ptr<const std::atomic<bool>> cancellation);
    [[nodiscard]] const std::array<CustodyBootstrapValue, 2>& slots() const noexcept { return values_; }
    [[nodiscard]] const CustodyMetadataIndices& indices() const noexcept { return indices_; }
    [[nodiscard]] std::uint32_t selectedSlot() const noexcept { return indices_.selectedSlot; }
    [[nodiscard]] const CustodyBootstrapValue& current() const noexcept { return values_[selectedSlot()]; }
    ~ProtectedCustodyBootstrapPair();
    ProtectedCustodyBootstrapPair(const ProtectedCustodyBootstrapPair&) = delete;
private:
    friend class ProtectedCustodyQueueInput;
    friend class ProtectedCustodyMigrationPair;
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<const ProtectedCustodyBootstrapPair>> readImpl(
        const std::filesystem::path&, CustodyContext, CustodyId, bool discover,
        std::shared_ptr<const std::atomic<bool>> cancellation);
    ProtectedCustodyBootstrapPair(CustodyPin&&, std::unique_ptr<ProtectedCustodyFiles>&&,
        std::unique_ptr<ProtectedCustodyFiles>&&, CustodyMetadataIndices&&,
        const std::array<CustodyBootstrapValue, 2>&);
    std::optional<CustodyPin> pin_; // Close native lease before returning admission.
    std::unique_ptr<ProtectedCustodyFiles> lease_;
    std::unique_ptr<ProtectedCustodyFiles> queueLease_;
    mutable std::mutex queueRead_;
    CustodyMetadataIndices indices_;
    std::array<CustodyBootstrapValue, 2> values_;
};

// Worker-only immutable bytes of BOTH fixed queue slots, retaining the genuine
// discovery owner/leases. NOT a parsed ledger, intent/account authority, mutation
// ACK or permission for upload/playback/delete. Views live only with this owner.
class ProtectedCustodyQueueInput final {
public:
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<const ProtectedCustodyQueueInput>> read(
        std::shared_ptr<const ProtectedCustodyBootstrapPair>, std::shared_ptr<const std::atomic<bool>> cancellation);
    [[nodiscard]] const CustodyMetadataIndices& indices() const noexcept { return indices_; }
    [[nodiscard]] const std::array<CustodyBytes, 2>& payloads() const noexcept { return payloads_; }
    [[nodiscard]] CustodyContext context() const noexcept {
        return {bootstrap_->current().context.storeId, bootstrap_->current().queueObjectId, CustodyRole::queue};
    }
    ProtectedCustodyQueueInput(const ProtectedCustodyQueueInput&) = delete;
    ~ProtectedCustodyQueueInput() = default;
private:
    ProtectedCustodyQueueInput(CustodyPin&&, std::shared_ptr<const ProtectedCustodyBootstrapPair>&&,
        CustodyMetadataIndices&&, std::array<CustodyBytes, 2>&&);
    std::optional<CustodyPin> pin_;
    std::shared_ptr<const ProtectedCustodyBootstrapPair> bootstrap_;
    CustodyMetadataIndices indices_;
    std::array<CustodyBytes, 2> payloads_;
};

enum class CustodyPackagePhase { capturing, finalizing, sealedNormal, sealedDegraded, discardPending };
struct CustodyPackageReference {
    CustodyRole role = CustodyRole::canonical;
    CustodyId objectId{};
    bool sealed = false, packed = false;
    std::optional<std::uint64_t> generation, length;
    std::optional<std::array<std::uint8_t, 32>> sha256;
    std::optional<CustodyId> containerId;
    std::optional<std::uint64_t> committedExtent;
    std::optional<ProtectedPackedCustodyFormat::Reference> rootRef;
};
// Fixed structural value only, not a proof, lease, verified directory or right
// to upload/discard/GC. Actual member hashes, roots of BOTH metadata slots,
// protected manifest/prefix and account/admission must be verified separately.
struct CustodyPackageValue {
    unsigned schema = 1;
    CustodyContext context{{}, {}, CustodyRole::packageState};
    std::uint64_t generation = 0;
    std::array<char, 301> directory{};
    CustodyPackagePhase phase = CustodyPackagePhase::capturing;
    ReasonCode reason = ReasonCode::none;
    bool shortRecordingDiscarded = false;
    std::array<CustodyPackageReference, 5> refs{};
    std::size_t refCount = 0;
};
// Worker-only, borrowed input for this call, no IO/projection/effects. Expected
// context/generation/directory come from an independently pinned own record,
// NOT from the same untrusted JSON. Unknown data fails without a default value.
[[nodiscard]] CustodyCodecResult<CustodyPackageValue> readCustodyPackage(
    std::string_view, const CustodyContext&, std::uint64_t, std::string_view) noexcept;
[[nodiscard]] CustodyCodecResult<CustodyBytes> writeCustodyPackage(
    const CustodyPackageValue&, const CustodyContext&, std::uint64_t, std::string_view);

// Worker-only provenance of BOTH own protected package payloads, with an
// exclusive native identity lease through last release. NOT member integrity,
// manifest/short predicate, account authority, upload/playback/delete/GC or
// migration admission. Caller releases this readonly lease before metadata
// mutation and then revalidates; no writable Files/HANDLE is exposed.
class ProtectedCustodyPackagePair final {
public:
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<const ProtectedCustodyPackagePair>> read(
        const std::filesystem::path&, std::string_view, const CustodyContext&,
        std::shared_ptr<const std::atomic<bool>> cancellation);
    [[nodiscard]] const std::array<CustodyPackageValue, 2>& slots() const noexcept { return values_; }
    [[nodiscard]] const CustodyMetadataIndices& indices() const noexcept { return indices_; }
    [[nodiscard]] std::uint32_t selectedSlot() const noexcept { return indices_.selectedSlot; }
    [[nodiscard]] const CustodyPackageValue& current() const noexcept { return values_[selectedSlot()]; }
    ~ProtectedCustodyPackagePair(); // Wipe values before lease/pin release; no IO.
    ProtectedCustodyPackagePair(const ProtectedCustodyPackagePair&) = delete;
private:
    friend class ProtectedCustodyStoreOwner;
    friend class ProtectedCustodyRecordingPackage;
#ifdef _WIN32
    friend CustodyFileResult<CustodyPackageReaders> openProtectedCustodyReaders(
        const std::filesystem::path&, std::shared_ptr<const ProtectedCustodyPackagePair>,
        std::shared_ptr<const std::atomic<bool>>);
    friend CustodyFileResult<CustodyPackageReaders> openProtectedCustodyReaders(
        std::shared_ptr<ProtectedCustodyRecordingPackage>, std::shared_ptr<const ProtectedCustodyPackagePair>,
        std::shared_ptr<const std::atomic<bool>>);
#endif
    enum class LeaseOrigin { isolatedReadOnly, borrowedWriter };
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<const ProtectedCustodyPackagePair>> readImpl(
        const std::filesystem::path&, std::string_view, const CustodyContext&,
        std::shared_ptr<const std::atomic<bool>>, std::shared_ptr<ProtectedCustodyFiles> retained, LeaseOrigin);
    ProtectedCustodyPackagePair(CustodyPin&&, std::unique_ptr<ProtectedCustodyFiles>&&, CustodyMetadataIndices&&,
        const std::array<CustodyPackageValue, 2>&, std::shared_ptr<const std::atomic<bool>>, LeaseOrigin);
    std::optional<CustodyPin> pin_; // Native lease closes BEFORE admission release.
    std::unique_ptr<ProtectedCustodyFiles> lease_;
    std::shared_ptr<ProtectedCustodyFiles> retainedLease_;
    CustodyMetadataIndices indices_;
    std::array<CustodyPackageValue, 2> values_;
    std::shared_ptr<const std::atomic<bool>> cancellation_;
    LeaseOrigin origin_;
};

struct CustodyMetadataCommit {
private:
    // Actual object/32-owner admission survives the worker until result adoption.
    // Reverse member destruction closes the lease before releasing admission.
    std::optional<CustodyPin> pin_;
    friend CustodyMetadataCommit commitProtectedCustodyMetadata(const std::filesystem::path&,
        std::string_view, const CustodyContext&, std::uint64_t, const CustodyBytes&,
        std::shared_ptr<const std::atomic<bool>>);
    std::shared_ptr<ProtectedCustodyStoreOwner> owner_;
    std::shared_ptr<ProtectedCustodyRecordingPackage> package_;
    friend CustodyMetadataCommit commitProtectedCustodyMetadata(
        std::shared_ptr<ProtectedCustodyStoreOwner>, const CustodyContext&, std::uint64_t,
        const CustodyBytes&, std::shared_ptr<const std::atomic<bool>>);
    static CustodyMetadataCommit commitImpl(const std::filesystem::path&, std::string_view,
        const CustodyContext&, std::uint64_t, const CustodyBytes&,
        std::shared_ptr<const std::atomic<bool>>, ProtectedCustodyFiles*);
    friend class ProtectedCustodyStoreOwner;
    friend class ProtectedCustodyRecordingPackage;
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
        owner_ = std::move(other.owner_);
        package_ = std::move(other.package_);
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

// Genuine worker-owned package birth, not store queue/account/effect authority.
// Only the private root lease crosses into capture/finalizer workers. All methods
// and final release are worker-only; caller serializes the active mutator.
class ProtectedCustodyRecordingPackage final : public std::enable_shared_from_this<ProtectedCustodyRecordingPackage> {
public:
    [[nodiscard]] std::string_view directory() const noexcept { return {directory_.data(), directoryLength_}; }
    [[nodiscard]] std::filesystem::path path() const;
    [[nodiscard]] CustodyContext context() const noexcept { return context_; }
    [[nodiscard]] const CustodyPackageValue& current() const noexcept { return current_; }
    [[nodiscard]] unsigned storagePressurePercent() const noexcept { return root_->storagePressurePercent(); }
    [[nodiscard]] CustodyFileResult<std::shared_ptr<ProtectedCustodyWriter>> createWriter(CustodyRole);
    [[nodiscard]] CustodyFileResult<CustodyPackageReference> reference(CustodyRole) const;
    [[nodiscard]] CustodyMetadataCommit commitMetadata(CustodyRole, const CustodyBytes&);
    [[nodiscard]] CustodyMetadataCommit commit(const CustodyPackageValue&);
    [[nodiscard]] CustodyFileResult<std::shared_ptr<const ProtectedCustodyPackagePair>> readPair();
    ~ProtectedCustodyRecordingPackage();
    ProtectedCustodyRecordingPackage(const ProtectedCustodyRecordingPackage&) = delete;
private:
    friend class ProtectedCustodyStoreOwner;
#ifdef _WIN32
    friend CustodyFileResult<CustodyPackageReaders> openProtectedCustodyReaders(
        std::shared_ptr<ProtectedCustodyRecordingPackage>, std::shared_ptr<const ProtectedCustodyPackagePair>,
        std::shared_ptr<const std::atomic<bool>>);
#endif
    ProtectedCustodyRecordingPackage() = default;
    [[nodiscard]] CustodyMetadataCommit commitImpl(const CustodyPackageValue&, bool metadataCheckpoint);
    [[nodiscard]] CustodyFileResult<bool> validateRefs(const CustodyPackageValue&);
    std::optional<CustodyPin> pin_; // Native children release before parent/admission.
    std::shared_ptr<const ProtectedCustodyFiles> root_;
    std::shared_ptr<ProtectedCustodyFiles> packageRoot_;
    std::unique_ptr<ProtectedCustodyFiles> state_;
    std::array<std::unique_ptr<ProtectedCustodyFiles>, 5> roles_;
    std::array<std::shared_ptr<ProtectedPackedCustodyOwner>, 3> packed_;
    std::array<CustodyContext, 5> contexts_{};
    std::array<CustodyId, 3> containers_{};
    std::array<std::uint64_t, 5> metadataGenerations_{};
    std::shared_ptr<const std::atomic<bool>> cancellation_;
    std::array<char, 301> directory_{};
    std::size_t directoryLength_ = 0;
    CustodyContext context_{};
    CustodyPackageValue current_{};
    bool failed_ = false;
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

// Worker-only queue commit on the continuously retained writable lease.
// The returned result retains owner; it must never travel to/die on the UI.
[[nodiscard]] CustodyMetadataCommit commitProtectedCustodyMetadata(
    std::shared_ptr<ProtectedCustodyStoreOwner>, const CustodyContext& expectedContext,
    std::uint64_t expectedBaseGeneration, const CustodyBytes& fullValue,
    std::shared_ptr<const std::atomic<bool>> cancellation);

} // namespace graf::windows
