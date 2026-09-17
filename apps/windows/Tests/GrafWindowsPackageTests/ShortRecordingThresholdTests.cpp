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
#include <chrono>
#include <fstream>
#include <iterator>
#include <string>

namespace {

std::string readFile(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary);
    return std::string((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
}

bool writeFixture(const std::filesystem::path& path, const std::filesystem::path&, std::uint64_t) {
    std::ofstream output(path, std::ios::binary);
    output << "m4a-fixture";
    return output.good();
}

} // namespace

int main() {
    using namespace graf::windows;

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

    const auto directory = std::filesystem::temp_directory_path() / "graf-feature-6796-threshold";
    std::filesystem::remove_all(directory);
    const auto custodyRoot = directory / "custody";
    std::filesystem::create_directories(custodyRoot);
    CanonicalAudioFrame frame;
    frame.mixed.fill(0.25F);

    // 2. A normally stopped short recording is structurally complete, marked and
    //    written as blocked with no capture error.
    const auto shortDirectory = custodyRoot / "short-normal";
    {
        V5LocalRecordingWriter writer(custodyRoot, shortDirectory, writeFixture);
        for (int index = 0; index < 2'999; ++index) assert(writer.append(frame));
        const auto result = writer.finalize(ReasonCode::none, RecordingStopReason::userRequested);
        assert(result.ok() && result.normalPackage() && result.shortRecordingDiscarded);
        assert(!result.keepablePackage());
        assert(result.durationMs == 29'990);
        assert(result.captureFailure == ReasonCode::none);
        const auto manifest = readFile(result.manifestPath);
        assert(manifest.find("\"short_recording_discarded\":true") != std::string::npos);
        assert(manifest.find("\"capture_status\":\"blocked\"") != std::string::npos);
        assert(manifest.find("\"capture_reason_code\":\"none\"") != std::string::npos);
        assert(DesktopUploadQueueService::isShortRecordingMarked(shortDirectory));
        // A repeated finalize must not change the decision.
        const auto repeated = writer.finalize(ReasonCode::none, RecordingStopReason::userRequested);
        assert(repeated.shortRecordingDiscarded && repeated.durationMs == 29'990);
    }

    // 3. Exactly 30 seconds is kept whole and is not marked.
    const auto exactDirectory = custodyRoot / "exact-threshold";
    {
        V5LocalRecordingWriter writer(custodyRoot, exactDirectory, writeFixture);
        for (int index = 0; index < 3'000; ++index) assert(writer.append(frame));
        const auto result = writer.finalize(ReasonCode::none, RecordingStopReason::userRequested);
        assert(result.ok() && result.keepablePackage() && !result.shortRecordingDiscarded);
        assert(result.durationMs == 30'000);
        assert(!DesktopUploadQueueService::isShortRecordingMarked(exactDirectory));
    }

    // 4. Interruption and capture failure always keep the recoverable fragment,
    //    even far below the threshold.
    const auto interruptedDirectory = custodyRoot / "short-interrupted";
    {
        V5LocalRecordingWriter writer(custodyRoot, interruptedDirectory, writeFixture);
        for (int index = 0; index < 100; ++index) assert(writer.append(frame));
        const auto result = writer.finalize(ReasonCode::none, RecordingStopReason::interruption);
        assert(result.keepablePackage() && !result.shortRecordingDiscarded);
        assert(!DesktopUploadQueueService::isShortRecordingMarked(interruptedDirectory));
    }
    const auto failedDirectory = custodyRoot / "short-failed";
    {
        V5LocalRecordingWriter writer(custodyRoot, failedDirectory, writeFixture);
        for (int index = 0; index < 100; ++index) assert(writer.append(frame));
        const auto result =
            writer.finalize(ReasonCode::endpointInvalidated, RecordingStopReason::userRequested);
        assert(!result.shortRecordingDiscarded && !result.keepablePackage());
        assert(result.trustedPrefixRetained);
        assert(!DesktopUploadQueueService::isShortRecordingMarked(failedDirectory));
    }

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
        V5LocalRecordingWriter writer(custodyRoot, orphanDirectory, writeFixture);
        for (int index = 0; index < 10; ++index) assert(writer.append(frame));
        const auto result = writer.finalize(ReasonCode::none, RecordingStopReason::userRequested);
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
        V5LocalRecordingWriter writer(custodyRoot, unsafeDirectory, writeFixture);
        for (int index = 0; index < 10; ++index) assert(writer.append(frame));
        assert(writer.finalize(ReasonCode::none, RecordingStopReason::userRequested).shortRecordingDiscarded);
        std::filesystem::create_directories(unsafeDirectory / "nested");
        DesktopUploadQueueService queue(ledgerPath, custodyRoot);
        assert(queue.load());
        assert(queue.discardShortRecording(unsafeDirectory) == ShortRecordingDiscardResult::unsafePath);
        assert(std::filesystem::exists(unsafeDirectory));
        // A path outside the custody root is refused before any inspection.
        assert(queue.discardShortRecording(custodyRoot) == ShortRecordingDiscardResult::unsafePath);
        assert(queue.discardShortRecording(directory) == ShortRecordingDiscardResult::unsafePath);
    }

    // 8. Passive feedback: one notice at a time, replaced on repeat, expiring by
    //    itself after the designed interval without any user action.
    {
        RecordingNoticePresenter presenter;
        const auto start = std::chrono::steady_clock::now();
        assert(!presenter.visible());
        presenter.showShortRecordingDiscarded(start);
        assert(presenter.visible());
        assert(!presenter.expired(start));
        assert(!presenter.expired(start + std::chrono::milliseconds(5'999)));
        assert(presenter.expired(start + std::chrono::milliseconds(6'000)));
        // A repeat replaces the notice instead of stacking a second one.
        presenter.showShortRecordingDiscarded(start + std::chrono::milliseconds(1'000));
        presenter.tick(start + std::chrono::milliseconds(6'000));
        assert(presenter.visible());
        presenter.tick(start + std::chrono::milliseconds(7'000));
        assert(!presenter.visible());
        presenter.dismiss();
        assert(!presenter.visible());
        assert(RecordingNoticePresenter::message() == L"Запись короче 30 секунд не сохранена");
    }

    std::filesystem::remove_all(directory);
    return 0;
}
