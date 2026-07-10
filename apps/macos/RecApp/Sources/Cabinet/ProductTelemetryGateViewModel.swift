import Foundation
import TwoBrainRecShared

public struct ProductTelemetryGateViewModel: Equatable, Sendable {
    public let state: ProductTelemetryGateState
    public let copyVersion: String
    public let directDesktopEgressDisclosed: Bool

    public init(
        state: ProductTelemetryGateState = .notSeen,
        copyVersion: String = "2026-07-09.1",
        directDesktopEgressDisclosed: Bool = false
    ) {
        self.state = state
        self.copyVersion = copyVersion
        self.directDesktopEgressDisclosed = directDesktopEgressDisclosed
    }

    public var allowsNormalProductUse: Bool {
        state.allowsNormalProductUse
    }

    public var allowsProductAnalytics: Bool {
        state.allowsProductAnalytics
    }

    public var requiresAcceptance: Bool {
        state == .notSeen || state == .termsUpdateRequired
    }

    public var limitedAccessOnly: Bool {
        state == .withdrawn ||
            state == .refusedUpdatedTerms ||
            state == .limitedToAccountLegalExportDeletion
    }
}
