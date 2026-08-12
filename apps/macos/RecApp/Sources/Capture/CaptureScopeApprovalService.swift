import Foundation
import TwoBrainRecShared

public enum CaptureScopeApprovalServiceError: Error, Equatable {
    case emptySourceDisplayName
}

public struct CaptureScopeApprovalService: Sendable {
    public typealias Clock = @Sendable () -> Date
    public typealias IdFactory = @Sendable () -> String

    private let clock: Clock
    private let idFactory: IdFactory

    public init(
        clock: @escaping Clock = Date.init,
        idFactory: @escaping IdFactory = { UUID().uuidString }
    ) {
        self.clock = clock
        self.idFactory = idFactory
    }

    public func approve(
        scopeKind: SystemAudioCaptureScopeKind,
        sourceDisplayName: String,
        approvalMode: CaptureScopeApprovalMode,
        eligibleReason: CaptureScopeEligibleReason
    ) throws -> CaptureScopeApproval {
        let trimmed = sourceDisplayName.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            throw CaptureScopeApprovalServiceError.emptySourceDisplayName
        }
        return CaptureScopeApproval(
            scopeApprovalId: idFactory(),
            scopeKind: scopeKind,
            sourceDisplayName: trimmed,
            approvedAt: clock(),
            approvalMode: approvalMode,
            eligibleReason: eligibleReason
        )
    }

    public func approveDetectorAssistedMeetingTarget(
        sourceDisplayName: String,
        startReason: MeetingDetectionStartReason
    ) throws -> CaptureScopeApproval {
        try approve(
            scopeKind: .application,
            sourceDisplayName: sourceDisplayName,
            approvalMode: startReason == .promptButton
                ? .userConfirmedSuggestedScope
                : .priorUserAuthorization,
            eligibleReason: .approvedMeetingApp
        )
    }
}
