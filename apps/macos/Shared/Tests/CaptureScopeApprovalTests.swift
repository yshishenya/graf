import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class CaptureScopeApprovalTests: XCTestCase {
    func testApprovalTrimsDisplayNameAndMarksBackgroundAudioAsNonTrigger() throws {
        let service = CaptureScopeApprovalService(
            clock: { Date(timeIntervalSince1970: 42) },
            idFactory: { "scope-1" }
        )

        let approval = try service.approve(
            scopeKind: .window,
            sourceDisplayName: "  Meeting Window  ",
            approvalMode: .manualSelection,
            eligibleReason: .manualMeetingScope
        )

        XCTAssertEqual(approval.scopeApprovalId, "scope-1")
        XCTAssertEqual(approval.sourceDisplayName, "Meeting Window")
        XCTAssertEqual(approval.scopeKind, .window)
        XCTAssertTrue(approval.notTriggerForBackgroundAudio)
        XCTAssertTrue(approval.isAcceptedForMeetingRecording)
    }

    func testEmptyScopeNameIsRejected() {
        let service = CaptureScopeApprovalService()

        XCTAssertThrowsError(
            try service.approve(
                scopeKind: .application,
                sourceDisplayName: " ",
                approvalMode: .manualSelection,
                eligibleReason: .approvedMeetingApp
            )
        )
    }

    func testDetectorAssistedApprovalUsesSuggestedApplicationScope() throws {
        let service = CaptureScopeApprovalService(
            clock: { Date(timeIntervalSince1970: 43) },
            idFactory: { "scope-detector" }
        )

        let approval = try service.approveDetectorAssistedMeetingTarget(
            sourceDisplayName: "Yandex Telemost"
        )

        XCTAssertEqual(approval.scopeApprovalId, "scope-detector")
        XCTAssertEqual(approval.scopeKind, .application)
        XCTAssertEqual(approval.approvalMode, .userConfirmedSuggestedScope)
        XCTAssertEqual(approval.eligibleReason, .approvedMeetingApp)
        XCTAssertTrue(approval.isAcceptedForMeetingRecording)
    }
}
#endif
