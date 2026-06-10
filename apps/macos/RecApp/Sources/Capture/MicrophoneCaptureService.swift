import Foundation
import TwoBrainRecShared
#if canImport(AVFoundation)
import AVFoundation
#endif

public protocol MicrophonePermissionAuthorizing: Sendable {
    func currentPermissionState() -> CapturePermissionState
    func requestPermission() async -> CapturePermissionState
}

public struct AVFoundationMicrophonePermissionAuthorizer: MicrophonePermissionAuthorizing {
    public init() {}

    public func currentPermissionState() -> CapturePermissionState {
        #if canImport(AVFoundation)
        switch AVCaptureDevice.authorizationStatus(for: .audio) {
        case .authorized:
            return .granted
        case .denied:
            return .denied
        case .restricted:
            return .restricted
        case .notDetermined:
            return .unknown
        @unknown default:
            return .unknown
        }
        #else
        return .unknown
        #endif
    }

    public func requestPermission() async -> CapturePermissionState {
        #if canImport(AVFoundation)
        let granted = await AVCaptureDevice.requestAccess(for: .audio)
        return granted ? .granted : currentPermissionState()
        #else
        return .unknown
        #endif
    }
}

public final class MicrophoneCaptureService: Sendable {
    private let authorizer: MicrophonePermissionAuthorizing

    public init(authorizer: MicrophonePermissionAuthorizing = AVFoundationMicrophonePermissionAuthorizer()) {
        self.authorizer = authorizer
    }

    public func preflight(
        sessionId: String,
        inputDeviceId: String? = nil,
        inputDisplayName: String = "Default Microphone"
    ) -> MicrophoneCaptureSession {
        MicrophoneCaptureSession(
            sessionId: sessionId,
            permissionState: authorizer.currentPermissionState(),
            inputDeviceId: inputDeviceId,
            inputDisplayName: inputDisplayName
        )
    }

    public func requestPermissionAndPreflight(
        sessionId: String,
        inputDeviceId: String? = nil,
        inputDisplayName: String = "Default Microphone"
    ) async -> MicrophoneCaptureSession {
        let state = await authorizer.requestPermission()
        return MicrophoneCaptureSession(
            sessionId: sessionId,
            permissionState: state,
            inputDeviceId: inputDeviceId,
            inputDisplayName: inputDisplayName
        )
    }
}
