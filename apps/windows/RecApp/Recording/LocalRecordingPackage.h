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
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<const ProtectedInspection>> inspectProtectedImpl(
        std::shared_ptr<const ProtectedCustodyPackagePair>, CustodyPackageReaders&&,
        std::string_view expectedSession, std::shared_ptr<const std::atomic<bool>> cancellation);
#endif
};

} // namespace graf::windows
