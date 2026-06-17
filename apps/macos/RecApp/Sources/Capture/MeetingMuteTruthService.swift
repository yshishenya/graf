import Foundation
import TwoBrainRecShared

public struct MeetingMuteTruthService: Sendable {
    public static let limitationCopy =
        SystemAudioStatusLabels.meetingMuteTruthLimitationCopy

    public init() {}

    public func capability(for targetDisplayName: String?) -> TargetMuteCapability {
        let normalized = (targetDisplayName ?? "").lowercased()
        guard !normalized.isEmpty else {
            return .unknown
        }

        if normalized.contains("zoom") {
            return .zoomNative
        }

        if normalized.contains("telemost") || normalized.contains("телемост") {
            if normalized.contains("chrome") {
                return .chromeTelemost
            }
            if normalized.contains("opera") {
                return .operaTelemost
            }
            if normalized.contains("yandex") || normalized.contains("яндекс") {
                return .yandexTelemost
            }
            return .chromeTelemost
        }

        return .unknown
    }

    public func evidence(
        sessionId: String,
        capability: TargetMuteCapability,
        limitationCopyShown: Bool,
        recordedAt: Date = Date()
    ) -> MeetingMuteTruthEvidence {
        MeetingMuteTruthEvidence(
            evidenceId: "\(capability.targetId)-\(sessionId)-mute-truth",
            sessionId: sessionId,
            targetId: capability.targetId,
            targetDisplayName: capability.targetDisplayName,
            source: source(for: capability),
            status: status(for: capability),
            freshness: capability.meetingAppMuteAdapterSupported ? .fresh : .unavailable,
            limitationCopyShown: limitationCopyShown,
            recordedAt: recordedAt,
            adapterId: capability.meetingAppMuteAdapterSupported ? "\(capability.targetId)-adapter" : nil,
            diagnosticSafe: true
        )
    }

    private func source(for capability: TargetMuteCapability) -> MeetingMuteTruthSource {
        if capability.meetingAppMuteAdapterSupported {
            return .targetAdapter
        }
        switch capability.firstMatrixStatus {
        case .pauseValidated:
            return .productPause
        case .deferred:
            return .unknown
        case .unsupported:
            return .unsupported
        }
    }

    private func status(for capability: TargetMuteCapability) -> MeetingMuteTruthEvidenceStatus {
        if capability.meetingAppMuteAdapterSupported {
            return .accepted
        }
        switch capability.firstMatrixStatus {
        case .pauseValidated:
            return .meetingMuteUnproven
        case .deferred:
            return .deferred
        case .unsupported:
            return .unsupported
        }
    }
}
