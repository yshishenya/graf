import SwiftUI
import TwoBrainRecShared

public struct CaptureControlView: View {
    private let session: CaptureSession?
    private let onStop: () -> Void

    public init(session: CaptureSession?, onStop: @escaping () -> Void) {
        self.session = session
        self.onStop = onStop
    }

    public var body: some View {
        CaptureStatusItem(session: session, onStop: onStop)
    }
}
