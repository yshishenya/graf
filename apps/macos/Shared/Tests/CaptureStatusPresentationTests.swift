import XCTest
import TwoBrainRecShared
@testable import TwoBrainRecAppCore

final class CaptureStatusPresentationTests: XCTestCase {
    func testCaptureStatusMatrix() {
        XCTAssertEqual(CaptureStatusPresentation.resolve(session: nil).title, "Готово к записи")

        let active = makeSession(state: .active)
        let activeStatus = CaptureStatusPresentation.resolve(session: active)
        XCTAssertEqual(activeStatus.title, "Идет запись")
        XCTAssertTrue(activeStatus.showsStop)
        XCTAssertTrue(activeStatus.showsPause)
        XCTAssertFalse(activeStatus.showsResume)

        let paused = CaptureStatusPresentation.resolve(session: makeSession(state: .paused))
        XCTAssertEqual(paused.title, "Идет запись · микрофон выключен")
        XCTAssertTrue(paused.showsStop)
        XCTAssertTrue(paused.showsResume)
        XCTAssertFalse(paused.showsPause)

        let failed = CaptureStatusPresentation.resolve(session: makeSession(state: .failed))
        XCTAssertEqual(failed.title, "Нужна помощь")
        XCTAssertFalse(failed.showsStop)
        XCTAssertEqual(failed.tone, .danger)
    }

    func testLocalRecordingStatusMatrixHasAttentionAndActions() {
        XCTAssertTrue(LocalRecordingPresentation.from(.degraded).requiresAttention)
        XCTAssertTrue(LocalRecordingPresentation.from(.blocked).requiresAttention)
        XCTAssertTrue(LocalRecordingPresentation.from(.failed).requiresAttention)
        XCTAssertFalse(LocalRecordingPresentation.from(.saved).requiresAttention)
        XCTAssertTrue(LocalRecordingPresentation.from(.saved).allowsOpen)
        XCTAssertTrue(LocalRecordingPresentation.from(.saved).allowsSend)
        XCTAssertTrue(LocalRecordingPresentation.from(.saved).allowsDelete)
        XCTAssertFalse(LocalRecordingPresentation.deleting.requiresAttention)
        XCTAssertTrue(LocalRecordingPresentation.corrupted.requiresAttention)
        XCTAssertTrue(LocalRecordingPresentation.expired.requiresAttention)
        XCTAssertTrue(LocalRecordingPresentation.expired.allowsOpen)
        XCTAssertTrue(LocalRecordingPresentation.expired.allowsDelete)
        XCTAssertEqual(LocalRecordingPresentation.uploading(percent: 42).detail, "Отправляем запись… 42%")
    }

    func testBlockerMatrixNeverForwardsInternalCodes() {
        let blockers: [RecordingBlockerPresentation] = [
            .init(kind: .permission, message: "Нужен доступ к микрофону."),
            .init(kind: .storage, message: "Недостаточно места."),
            .init(kind: .capture, message: "Запись не началась."),
            .init(kind: .policy, message: "Запись отключена."),
            .init(kind: .indicator, message: "Индикатор недоступен."),
            .init(kind: .source, message: "Источник не подтвержден."),
            .init(kind: .alreadyRecording, message: "Запись уже идёт."),
            .init(kind: .unknown, message: "Нужна повторная проверка.")
        ]
        for blocker in blockers {
            XCTAssertFalse(blocker.message.contains("_"))
            XCTAssertFalse(blocker.message.contains("source_overflow"))
            XCTAssertFalse(blocker.message.contains("/"))
            XCTAssertFalse(blocker.message.contains("sessionId"))
            XCTAssertFalse(blocker.title.isEmpty)
            XCTAssertFalse(blocker.systemImage.isEmpty)
        }
        XCTAssertFalse(RecordingBlockerPresentation(kind: .policy, message: "").isRetryable)
        XCTAssertEqual(RecordingBlockerPresentation(kind: .permission, message: "").recoveryAction, .openPermissions)
    }

    func testFailureDetailMapsKnownCodesToHumanCopy() {
        let detail = SystemAudioStatusLabels.captureFailureDetail(
            failureCode: "source_overflow",
            hasPlayableFragment: true
        )
        XCTAssertEqual(detail, "Запись остановлена: источник записи переполнен. Доступная часть сохранена локально.")
        XCTAssertFalse(detail.contains("source_overflow"))
    }

    private func makeSession(state: CaptureSessionState) -> CaptureSession {
        CaptureSession(
            id: "synthetic-\(state.rawValue)",
            mode: .audioRecording,
            state: state,
            sourceAppEligibility: .eligible,
            policySnapshotRef: "synthetic",
            triggerEvidence: [:],
            visibleIndicatorState: state == .failed ? .error : .active,
            stopActionAvailable: state != .failed && state != .stopped,
            bufferSummaryId: nil,
            startedAt: nil,
            stoppedAt: nil
        )
    }
}
