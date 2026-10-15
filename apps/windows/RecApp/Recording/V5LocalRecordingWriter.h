#pragma once

#include "../Audio/RecordingAudioTimeline.h"
#include "../Contracts/WindowsDesktopContracts.h"
#include "../Storage/ProtectedCustodyMetadata.h"

#include <cstdint>
#include <filesystem>
#include <memory>
#include <string>

namespace graf::windows {

enum class V5WriterError {
    none,
    storageUnavailable,
    emptyRecording,
    aacEncoderUnavailable,
    encodeFailed,
    integrityFailed,
};

struct V5WriterResult {
    V5WriterResult() = default;
    V5WriterResult(const V5WriterResult&) = default;
    V5WriterResult& operator=(const V5WriterResult&) = default;
    // Intentionally copy even rvalues: MSVC Debug noexcept moves allocate proxies.
    V5WriterError error = V5WriterError::none;
    // Explicit constructors remain throw-capable with MSVC Debug proxies.
    std::filesystem::path packageDirectory{L""};
    // Values only: these do not grant storage/account/upload authority.
    CustodyContext packageContext{};
    std::uint64_t packageGeneration = 0;
    CustodyPackagePhase packagePhase = CustodyPackagePhase::capturing;
    CustodyFileError storageError = CustodyFileError::none;
    std::uint32_t nativeError = 0;
    bool semanticVerified = false;
    std::uint64_t durationMs = 0;
    std::uint64_t wavBytes = 0;
    std::uint64_t playbackBytes = 0;
    // Wall-clock bounds of the captured audio, epoch milliseconds UTC, and the
    // display offset of the moment the recording started. The server needs them
    // to place the meeting on a timeline; a duration alone cannot.
    std::uint64_t startedAtMs = 0;
    std::uint64_t stoppedAtMs = 0;
    int displayTimezoneOffsetMinutes = 0;
    std::string wavSha256{std::size_t{0}, '\0'};
    std::string playbackSha256{std::size_t{0}, '\0'};
    ReasonCode captureFailure = ReasonCode::none;
    bool trustedPrefixRetained = false;
    // Durable discard intent, NOT physical removal or permission for an early
    // "not saved" notice. Purge/absence/removed ACK belongs to the owner worker.
    bool shortRecordingDiscarded = false;

    [[nodiscard]] bool ok() const noexcept { return error == V5WriterError::none; }
    [[nodiscard]] bool normalPackage() const noexcept {
        return ok() && semanticVerified && captureFailure == ReasonCode::none &&
            packagePhase == CustodyPackagePhase::sealedNormal;
    }
    [[nodiscard]] bool keepablePackage() const noexcept {
        return normalPackage() && !shortRecordingDiscarded;
    }
};

// Worker-only genuine protected package. No path constructor, plaintext
// encoder hook, destructor flush/recovery, or UI last native release.
class V5LocalRecordingWriter final {
public:
    static void* operator new(std::size_t) { return CustodyAllocator<V5LocalRecordingWriter>{}.allocate(1); }
    static void operator delete(void* p) noexcept {
        CustodyAllocator<V5LocalRecordingWriter>{}.deallocate(static_cast<V5LocalRecordingWriter*>(p), 1);
    }
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<V5LocalRecordingWriter>> open(
        std::shared_ptr<ProtectedCustodyStoreOwner>, std::string_view session,
        std::shared_ptr<const std::atomic<bool>> cancellation);
    ~V5LocalRecordingWriter();

    V5LocalRecordingWriter(const V5LocalRecordingWriter&) = delete;
    V5LocalRecordingWriter& operator=(const V5LocalRecordingWriter&) = delete;

    [[nodiscard]] bool append(const CanonicalAudioFrame& frame);
    // Metadata only, serialized with append/finalize on the existing worker.
    // Times are UTC epoch ms and monotonic ms relative to recording start.
    // OPEN success precedes microphone suppression; a failed OPEN is rolled back.
    // Successful false means idempotent (no new metadata commit).
    [[nodiscard]] CustodyFileResult<bool> pausePrivacy(std::uint64_t wallMs, std::uint64_t monotonicMs);
    // Call ONLY after the capture owner accepted its exact Resume/Stop boundary.
    // A failed CLOSE retains the closed in-memory history and does not undo that boundary.
    [[nodiscard]] CustodyFileResult<bool> closePrivacy(std::uint64_t wallMs, std::uint64_t monotonicMs);
    [[nodiscard]] V5WriterResult finalize(
        ReasonCode captureFailure = ReasonCode::none,
        RecordingStopReason stopReason = RecordingStopReason::interruption);

    [[nodiscard]] std::uint64_t frameCount() const noexcept { return frameCount_; }
    [[nodiscard]] bool healthy() const noexcept { return !finalized_ && result_.error == V5WriterError::none; }
    [[nodiscard]] CustodyContext packageContext() const noexcept;
    // Worker-only retained genuine owner, never a value-only UI result.
    [[nodiscard]] std::shared_ptr<ProtectedCustodyRecordingPackage> package() const noexcept;

private:
    struct State;
    explicit V5LocalRecordingWriter(std::shared_ptr<State>);
    [[nodiscard]] bool writeWav();
    [[nodiscard]] bool writePlayback();
    [[nodiscard]] bool sealAudio(CustodyRole, bool checkpoint = true);
    [[nodiscard]] bool sealMetadata(CustodyRole, const CustodyBytes&);
    [[nodiscard]] bool commitState(CustodyPackagePhase, ReasonCode, bool shortIntent = false);
    [[nodiscard]] bool retainPrefix(ReasonCode);
    [[nodiscard]] CustodyBytes manifestJson(bool capacityCheck = false) const;
    void fail(V5WriterError, CustodyFileError, std::uint32_t = 0) noexcept;
    [[nodiscard]] static std::int16_t toPcm16(float value) noexcept;

    std::shared_ptr<State> state_;
    std::uint64_t frameCount_ = 0;
    // Wall clock of the first accepted frame; zero until audio arrives.
    std::uint64_t startedAtMs_ = 0;
    bool finalized_ = false;
    V5WriterResult result_;
};

} // namespace graf::windows
