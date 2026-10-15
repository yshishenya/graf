// Feature 6796 parity with macOS: a normally stopped recording shorter than
// 30 seconds is not kept as a meeting. Nothing here touches a microphone, a
// render endpoint or real meeting audio; synthetic frames only.
#include "../../RecApp/Recording/V5LocalRecordingWriter.h"
#include "../../RecApp/Shell/RecordingNoticePresenter.h"
#include "../../RecApp/Upload/DesktopUploadQueueService.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include "../GeneratedRecordingFixtures.h"
#include <chrono>
#include <fstream>
#include <iterator>
#include <string>
#include "RecordingNoticePresenterTests.h"

namespace {

std::string readFile(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    return std::string((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
}

} // namespace

int main() {
    using namespace graf::windows;
    testF277RecordingNoticePresenter();

    // 1. The portable threshold is exact: 29.99 s is rejected, 30.0 s is kept,
    //    and no fault, interruption or empty capture ever authorizes a discard.
    //    The unit is the canonical 10 ms frame, so 30 s is exactly 3 000 frames.
    static_assert(kCanonicalFramesPerSecond == 100);
    static_assert(kShortRecordingMinimumFrames == 3'000);
    assert(isShortRecording(2'999, RecordingStopReason::userRequested, false));
    assert(!isShortRecording(3'000, RecordingStopReason::userRequested, false));
    assert(!isShortRecording(3'001, RecordingStopReason::userRequested, false));
    assert(!isShortRecording(0, RecordingStopReason::userRequested, false));
    assert(isShortRecording(100, RecordingStopReason::meetingEnded, false));
    assert(!isShortRecording(100, RecordingStopReason::interruption, false));
    assert(!isShortRecording(100, RecordingStopReason::userRequested, true));
    assert(!isShortRecording(kShortRecordingMinimumFrames, RecordingStopReason::interruption, false));

    const auto directory = std::filesystem::temp_directory_path() /
        ("graf-feature-6796-threshold-" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    const auto custodyRoot = directory / "custody";
    std::filesystem::create_directories(custodyRoot);
    CanonicalAudioFrame frame;
    frame.mixed.fill(0.25F);

    // Native writer decisions are durable state, never an early removal ACK.
#ifdef _WIN32
    for (const auto count : {2'999ULL, 3'000ULL}) {
        testing::GeneratedProtectedRecording capture("threshold-" + std::to_string(count));
        capture.append(count);
        const auto result = capture.writer->finalize(ReasonCode::none, RecordingStopReason::userRequested);
        assert(result.ok() && result.semanticVerified && result.durationMs == count*10);
        assert(result.shortRecordingDiscarded == (count < 3000));
        assert(result.keepablePackage() == (count == 3000));
        assert(result.packagePhase == (count < 3000 ? CustodyPackagePhase::discardPending : CustodyPackagePhase::sealedNormal));
        assert(result.captureFailure == ReasonCode::none);
        const auto repeated = capture.writer->finalize(ReasonCode::none, RecordingStopReason::userRequested);
        assert(repeated.shortRecordingDiscarded == result.shortRecordingDiscarded && repeated.packageGeneration == result.packageGeneration);
        auto pair = capture.coldPair(); assert(pair.ok());
        assert((*pair.value)->current().phase == result.packagePhase);
        assert((*pair.value)->current().shortRecordingDiscarded == result.shortRecordingDiscarded);
        // Actual bytes still exist: purge/removed ACK is a different operation.
        assert(std::filesystem::exists(capture.paths.root/capture.session));
    }
    {
        testing::GeneratedProtectedRecording capture("short-interrupted");
        capture.append(100);
        const auto result = capture.writer->finalize(ReasonCode::none, RecordingStopReason::interruption);
        assert(result.keepablePackage() && !result.shortRecordingDiscarded && result.durationMs == 1000);
    }
    {
        testing::GeneratedProtectedRecording capture("short-failed");
        capture.append(100);
        const auto result = capture.writer->finalize(ReasonCode::endpointInvalidated, RecordingStopReason::userRequested);
        assert(!result.shortRecordingDiscarded && !result.keepablePackage() && result.trustedPrefixRetained);
        assert(result.packagePhase == CustodyPackagePhase::sealedDegraded);
        auto pair = capture.coldPair(); assert(pair.ok());
        assert((*pair.value)->current().reason == ReasonCode::endpointInvalidated);
    }
#endif

    // Remaining cleanup scenarios describe historical plaintext packages only,
    // not protected purge admission or physical removal by the new writer.
    const auto shortDirectory = custodyRoot / "short-normal";
    const auto shortInput = testing::makeGeneratedLegacyPackage(shortDirectory, 2999,
        ReasonCode::none, RecordingStopReason::userRequested, "m4a-fixture");
    assert(shortInput.shortRecordingDiscarded && shortInput.durationMs == 29990);
    const auto manifest = readFile(shortInput.manifestPath);
    assert(manifest.find("\"short_recording_discarded\":true") != std::string::npos);
    assert(manifest.find("\"capture_status\":\"blocked\"") != std::string::npos);
    assert(manifest.find("\"capture_reason_code\":\"none\"") != std::string::npos);
    assert(DesktopUploadQueueService::isShortRecordingMarked(shortDirectory));
    const auto exactDirectory = custodyRoot / "exact-threshold";
    const auto exactInput = testing::makeGeneratedLegacyPackage(exactDirectory, 3000,
        ReasonCode::none, RecordingStopReason::userRequested, "m4a-fixture");
    assert(!exactInput.shortRecordingDiscarded && exactInput.durationMs == 30000);
    assert(!DesktopUploadQueueService::isShortRecordingMarked(exactDirectory));
    const auto interruptedDirectory = custodyRoot / "short-interrupted";
    const auto interruptedInput = testing::makeGeneratedLegacyPackage(interruptedDirectory, 100,
        ReasonCode::none, RecordingStopReason::interruption, "m4a-fixture");
    assert(!interruptedInput.shortRecordingDiscarded);
    assert(!DesktopUploadQueueService::isShortRecordingMarked(interruptedDirectory));
    const auto failedDirectory = custodyRoot / "short-failed";
    const auto failedInput = testing::makeGeneratedLegacyPackage(failedDirectory, 100,
        ReasonCode::endpointInvalidated, RecordingStopReason::userRequested, "m4a-fixture");
    assert(!failedInput.shortRecordingDiscarded);
    assert(!DesktopUploadQueueService::isShortRecordingMarked(failedDirectory));

    // 5. Discarding removes the ledger row and every byte, and the marker wins
    //    over a queue row that claims the recording is uploadable.
    const auto ledgerPath = custodyRoot / "desktop-upload-queue.v2";
    {
        DesktopUploadQueueService queue(ledgerPath, custodyRoot);
        assert(queue.load());
        assert(queue.enqueue({"short-normal", "short-normal", "session-short",
            shortDirectory, UploadQueueStatus::pending, {}, 0, {}, {}, {}}));
        assert(queue.items().size() == 1);
        assert(queue.discardShortRecording(shortDirectory) == ShortRecordingDiscardResult::discarded);
        assert(queue.items().empty());
        assert(!std::filesystem::exists(shortDirectory));
        // The ordinary 30-second package is never a discard candidate.
        assert(queue.discardShortRecording(exactDirectory) == ShortRecordingDiscardResult::notMarked);
        assert(std::filesystem::exists(exactDirectory));
    }

    // 6. A cleanup interrupted by a crash is finished by the next scan, and an
    //    unmarked package is never touched.
    const auto orphanDirectory = custodyRoot / "orphan-discarded";
    {
        const auto result = testing::makeGeneratedLegacyPackage(orphanDirectory, 10,
            ReasonCode::none, RecordingStopReason::userRequested, "m4a-fixture");
        assert(result.shortRecordingDiscarded);
    }
    {
        DesktopUploadQueueService queue(ledgerPath, custodyRoot);
        assert(queue.load());
        assert(queue.sweepDiscardedShortRecordings() == 1);
        assert(!std::filesystem::exists(orphanDirectory));
        assert(std::filesystem::exists(exactDirectory));
        assert(queue.sweepDiscardedShortRecordings() == 0);
    }

    // 7. A package holding anything other than regular files is refused, so a
    //    discard can never walk outside the reviewed package.
    const auto unsafeDirectory = custodyRoot / "unsafe-discarded";
    {
        assert(testing::makeGeneratedLegacyPackage(unsafeDirectory, 10,
            ReasonCode::none, RecordingStopReason::userRequested, "m4a-fixture").shortRecordingDiscarded);
        std::filesystem::create_directories(unsafeDirectory / "nested");
        DesktopUploadQueueService queue(ledgerPath, custodyRoot);
        assert(queue.load());
        assert(queue.discardShortRecording(unsafeDirectory) == ShortRecordingDiscardResult::unsafePath);
        assert(std::filesystem::exists(unsafeDirectory));
        // A path outside the custody root is refused before any inspection.
        assert(queue.discardShortRecording(custodyRoot) == ShortRecordingDiscardResult::unsafePath);
        assert(queue.discardShortRecording(directory) == ShortRecordingDiscardResult::unsafePath);
    }

    // 8. F277: repeat identity updates in place without extending its lifetime.
    {
        RecordingNoticePresenter presenter;
        presenter.interactionPermitProvider = [] { return InteractionPermit{true, 1}; };
        const auto start = std::chrono::steady_clock::now();
        assert(!presenter.visible());
        const NoticeContent shortNotice{NoticeKind::shortRecording, "same-result", L"", std::wstring(RecordingNoticePresenter::message()), {}};
        assert(presenter.present(shortNotice, start, start + std::chrono::seconds(20)));
        assert(presenter.visible());
        assert(!presenter.expired(start));
        assert(!presenter.expired(start + std::chrono::milliseconds(19'999)));
        assert(presenter.expired(start + std::chrono::milliseconds(20'000)));
        assert(presenter.present(shortNotice, start + std::chrono::seconds(1), start + std::chrono::seconds(21)));
        presenter.tick(start + std::chrono::milliseconds(20'000));
        assert(!presenter.visible());
        presenter.dismiss();
        assert(!presenter.visible());
        assert(RecordingNoticePresenter::message() == L"Запись не сохранена — короче 30 секунд");
    }

    std::filesystem::remove_all(directory);
    return 0;
}
