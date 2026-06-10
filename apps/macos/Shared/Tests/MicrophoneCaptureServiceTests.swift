import Foundation
import TwoBrainRecAppCore
import TwoBrainRecShared

#if canImport(XCTest)
import XCTest

final class MicrophoneCaptureServiceTests: XCTestCase {
    func testPreflightReportsCurrentPermissionState() {
        let service = MicrophoneCaptureService(
            authorizer: FakeMicrophoneAuthorizer(current: .denied, requested: .granted)
        )

        let session = service.preflight(
            sessionId: "session",
            inputDeviceId: "built-in",
            inputDisplayName: "Built-in Microphone"
        )

        XCTAssertEqual(session.permissionState, .denied)
        XCTAssertEqual(session.inputDeviceId, "built-in")
        XCTAssertFalse(session.canBeAccepted)
    }

    func testRequestPermissionAndPreflightUsesRequestedState() async {
        let service = MicrophoneCaptureService(
            authorizer: FakeMicrophoneAuthorizer(current: .unknown, requested: .granted)
        )

        let session = await service.requestPermissionAndPreflight(
            sessionId: "session",
            inputDisplayName: "Built-in Microphone"
        )

        XCTAssertEqual(session.permissionState, .granted)
        XCTAssertEqual(session.inputDisplayName, "Built-in Microphone")
    }
}

private struct FakeMicrophoneAuthorizer: MicrophonePermissionAuthorizing {
    let current: CapturePermissionState
    let requested: CapturePermissionState

    func currentPermissionState() -> CapturePermissionState {
        current
    }

    func requestPermission() async -> CapturePermissionState {
        requested
    }
}
#endif
