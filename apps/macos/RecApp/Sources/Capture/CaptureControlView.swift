import SwiftUI
import TwoBrainRecShared

public struct CaptureControlView: View {
    private let session: CaptureSession?
    private let blockedReason: String?
    private let onRecord: () -> Void
    private let onStop: () -> Void

    public init(
        session: CaptureSession?,
        blockedReason: String? = nil,
        onRecord: @escaping () -> Void,
        onStop: @escaping () -> Void
    ) {
        self.session = session
        self.blockedReason = blockedReason
        self.onRecord = onRecord
        self.onStop = onStop
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            if let session {
                CaptureStatusItem(session: session, onStop: onStop)
            } else {
                Button(action: onRecord) {
                    Label("Record", systemImage: "record.circle")
                }
                .buttonStyle(.borderedProminent)
                .accessibilityLabel("Start recording")
            }

            if let blockedReason, !blockedReason.isEmpty {
                Label(blockedReason, systemImage: "exclamationmark.triangle.fill")
                    .font(.caption)
                    .foregroundStyle(.orange)
                    .accessibilityLabel(blockedReason)
            }
        }
    }
}
