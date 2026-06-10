import Foundation
import TwoBrainRecShared

public struct RecordingRouteMetadataService: Sendable {
    public init() {}

    public func snapshot(
        inputRouteClass: String? = nil,
        outputRouteClass: String? = nil,
        outputVolumeBucket: LeakageRouteVolumeBucket = .unknown,
        muteState: LeakageRouteMuteState = .unknown,
        browserTarget: String? = nil,
        routeChangeCount: Int = 0,
        coreaudiodState: String? = nil,
        sleepWakeObserved: Bool = false,
        selfRoutingRejected: Bool = false
    ) -> RecordingRouteMetadata {
        RecordingRouteMetadata(
            inputRouteClass: inputRouteClass,
            outputRouteClass: outputRouteClass,
            outputVolumeBucket: outputVolumeBucket,
            muteState: muteState,
            browserTarget: browserTarget,
            routeChangeCount: routeChangeCount,
            coreaudiodState: coreaudiodState,
            sleepWakeObserved: sleepWakeObserved,
            selfRoutingRejected: selfRoutingRejected
        )
    }
}
