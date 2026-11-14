#pragma once

#include "V5LocalRecordingWriter.h"

#include <filesystem>
#include <array>
#include <string>
#ifdef _WIN32
#include "../Storage/ProtectedCustodyMetadata.h"
#include "../Storage/ProtectedCustodyReader.h"
#endif

namespace graf::windows {

enum class PackageIntegrity {
    missing,
    valid,
    malformed,
    degraded,
    discardPending,
};

struct LocalRecordingPackageSnapshot {
    std::filesystem::path directory;
    std::string recordingId;
    PackageIntegrity integrity = PackageIntegrity::missing;
    std::uint64_t durationMs = 0;
    bool playbackAvailable = false;
    // Display-only values from the background inspection, never upload authority.
    std::array<std::uint64_t, 3> trackBytes{}; // manifest, media, playback
    // Wall clock of the captured audio, epoch milliseconds UTC, and the display
    // offset of its start. Zero means the package predates these fields or the
    // manifest did not carry a usable pair.
    std::uint64_t startedAtMs = 0;
    std::uint64_t stoppedAtMs = 0;
    int displayTimezoneOffsetMinutes = 0;
};

class LocalRecordingPackage final {
public:
    [[nodiscard]] static LocalRecordingPackageSnapshot inspect(
        const std::filesystem::path& directory,
        const std::filesystem::path& custodyRoot = {});
#ifdef _WIN32
    struct PlaybackEvidence {
        std::uint64_t decodedFrames = 0;
        std::uint64_t containerDuration100ns = 0;
    };
    struct ProtectedEvidence {
        PackageIntegrity integrity = PackageIntegrity::malformed;
        std::uint64_t durationMs = 0, startedAtMs = 0, stoppedAtMs = 0;
        int displayTimezoneOffsetMinutes = 0;
        std::uint64_t trustedPrefixFrames = 0;
        PlaybackEvidence playback;
        bool manifestSessionMatched = false;
    };
    // Cold committed cleaned audio only, not a sealed package, session/history
    // validation or account/playback/upload/delete authority. Worker-only last
    // release; the entire BOTH group remains held, with no writable access.
    class UnfinishedInspection final {
    public:
        [[nodiscard]] std::uint64_t completeFrames() const noexcept { return frames_; }
        ~UnfinishedInspection() = default;
        UnfinishedInspection(const UnfinishedInspection&) = delete;
    private:
        friend class LocalRecordingPackage;
        UnfinishedInspection(std::shared_ptr<const ProtectedCustodyPackagePair>,
            CustodyPackageReaders&&, std::shared_ptr<const std::atomic<bool>>, std::uint64_t);
        std::shared_ptr<const ProtectedCustodyPackagePair> pair_;
        CustodyPackageReaders readers_;
        std::shared_ptr<const std::atomic<bool>> cancellation_;
        std::uint64_t frames_;
    };
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<const UnfinishedInspection>> inspectUnfinished(
        std::shared_ptr<ProtectedCustodyStoreOwner>, std::string_view directory,
        std::shared_ptr<const std::atomic<bool>> cancellation);
    // Semantic evidence for these exact retained bytes, NOT current account,
    // bootstrap, queue, upload/playback/delete or short-discard authority.
    // Worker-only construction/use/last release; no plaintext path or repair.
    class ProtectedInspection final {
    public:
        [[nodiscard]] const ProtectedEvidence& evidence() const noexcept { return evidence_; }
        ~ProtectedInspection();
        ProtectedInspection(const ProtectedInspection&) = delete;
    private:
        friend class LocalRecordingPackage;
        friend class DesktopHttpTransport;
        friend class ProtectedLocalRecordingPlayback;
        ProtectedInspection(std::shared_ptr<const ProtectedCustodyPackagePair>,
            CustodyPackageReaders&&, CustodyBytes&&, CustodyBytes&&, const ProtectedEvidence&,
            std::shared_ptr<const std::atomic<bool>>);
        std::shared_ptr<const ProtectedCustodyPackagePair> pair_;
        CustodyPackageReaders readers_;
        CustodyBytes manifest_;
        CustodyBytes session_; // Exact session already matched by the semantic validator.
        ProtectedEvidence evidence_;
        std::shared_ptr<const std::atomic<bool>> cancellation_;
    };
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<const ProtectedInspection>> inspectProtected(
        const std::filesystem::path& trustedRoot,
        std::shared_ptr<const ProtectedCustodyPackagePair>, std::string_view expectedSession,
        std::shared_ptr<const std::atomic<bool>> cancellation);
    // Same semantic validator on actual retained package/role owners. No path
    // reopen, caller-created proof or release of writable custody for inspection.
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<const ProtectedInspection>> inspectProtected(
        std::shared_ptr<ProtectedCustodyRecordingPackage>, std::string_view expectedSession,
        std::shared_ptr<const std::atomic<bool>> cancellation);
    // Full inspection runs off the storage worker. This bridge accepts only its
    // retained proof, then freshly validates the owner and exact reserved row.
    // A private candidate change still requires durable commit and adoption.
    [[nodiscard]] static CustodyFileResult<bool> recoverPreparedRecording(ProtectedCustodyStoreOwner&,
        ProtectedUploadQueueValue& candidate, const ProtectedUploadQueueValue& reservation,
        std::string_view session, const std::shared_ptr<const ProtectedInspection>&,
        std::uint64_t nowMs, std::shared_ptr<const std::atomic<bool>> cancellation,
        std::string_view claimUser = {}, std::string_view claimWorkspace = {});
    // Worker-only codec evidence from BOTH-slot immutable owners. The duration
    // is a bound/comparison, NOT validated manifest/account/effect authority.
    // No normal/upload/playback/delete capability or retained proof is returned.
    [[nodiscard]] static CustodyFileResult<PlaybackEvidence> readProtectedPlayback(
        const std::filesystem::path& trustedRoot,
        std::shared_ptr<const ProtectedCustodyPackagePair>, std::uint64_t manifestDurationMs,
        std::shared_ptr<const std::atomic<bool>> cancellation);
    // Actual immutable output before sealed package publication. Codec evidence
    // only, not a normal-package proof or permission for any external effect.
    [[nodiscard]] static CustodyFileResult<PlaybackEvidence> readProtectedPlayback(
        std::shared_ptr<const ProtectedPackedCustodyTree>, std::uint64_t durationMs,
        std::shared_ptr<const std::atomic<bool>> cancellation);
private:
    friend class ProtectedCustodyMigration;
    [[nodiscard]] static CustodyFileResult<bool> classifyMigrationContent(
        CustodyPackageValue&, const CustodyBytes&, const CustodyBytes&, std::string_view);
    friend class V5LocalRecordingWriter;
    friend class ProtectedCustodyStoreOwner;
    // Bounded routing value only. Slot coordinates belong to manifest metadata,
    // not package-state. Terminal checks BOTH; normal checks bound histories.
    [[nodiscard]] static CustodyFileResult<ReasonCode> classifyRecoveryManifest(
        const std::array<CustodyBytes,2>&, unsigned selectedSlot,
        const std::array<bool,2>& boundSlots, std::string_view session);
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<const ProtectedInspection>> completeUnfinished(
        std::shared_ptr<ProtectedCustodyRecordingPackage>, std::string_view,
        std::shared_ptr<const std::atomic<bool>>);
    // Value-only format/semantic checks. No phase/proof/effect authority is created.
    [[nodiscard]] static CustodyFileResult<ProtectedEvidence> validateProtectedContent(
        const CustodyPackageValue&, const std::array<IStream*,3>&,
        const CustodyBytes& manifest, const CustodyBytes& recovery,
        std::string_view, const std::shared_ptr<const std::atomic<bool>>&);
    struct UnfinishedHistory {
        CustodyBytes privacy;
        ProtectedEvidence evidence;
    };
    [[nodiscard]] static CustodyFileResult<UnfinishedHistory> unfinishedHistory(
        const UnfinishedInspection&,std::string_view);
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<const UnfinishedInspection>> inspectUnfinished(
        std::shared_ptr<ProtectedCustodyRecordingPackage>,std::shared_ptr<const std::atomic<bool>>);
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<const UnfinishedInspection>> inspectUnfinishedImpl(
        std::shared_ptr<const ProtectedCustodyPackagePair>,CustodyPackageReaders&&,
        std::shared_ptr<const std::atomic<bool>>);
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<const ProtectedInspection>> inspectProtectedImpl(
        std::shared_ptr<const ProtectedCustodyPackagePair>, CustodyPackageReaders&&,
        std::string_view expectedSession, std::shared_ptr<const std::atomic<bool>> cancellation);
#endif
};

} // namespace graf::windows
