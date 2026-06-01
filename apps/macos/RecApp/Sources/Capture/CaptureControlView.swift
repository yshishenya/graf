import SwiftUI
import TwoBrainRecShared

public struct CaptureControlView: View {
    private let session: CaptureSession?
    private let blockedReason: String?
    private let localRecordingStatus: String?
    private let localRecordingLocation: String?
    private let onRecord: () -> Void
    private let onStop: () -> Void

    public init(
        session: CaptureSession?,
        blockedReason: String? = nil,
        localRecordingStatus: String? = nil,
        localRecordingLocation: String? = nil,
        onRecord: @escaping () -> Void,
        onStop: @escaping () -> Void
    ) {
        self.session = session
        self.blockedReason = blockedReason
        self.localRecordingStatus = localRecordingStatus
        self.localRecordingLocation = localRecordingLocation
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

            if let localRecordingStatus, !localRecordingStatus.isEmpty {
                Label(localRecordingStatus, systemImage: "waveform.path.badge.plus")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .accessibilityLabel(localRecordingStatus)
            }

            if let localRecordingLocation, !localRecordingLocation.isEmpty {
                Text(localRecordingLocation)
                    .font(.caption2.monospaced())
                    .foregroundStyle(.secondary)
                    .textSelection(.enabled)
                    .lineLimit(2)
                    .accessibilityLabel("Local recording location: \(localRecordingLocation)")
            }
        }
    }
}
