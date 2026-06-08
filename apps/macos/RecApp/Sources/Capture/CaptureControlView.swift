import SwiftUI
import TwoBrainRecShared

public struct CaptureControlView: View {
    private let session: CaptureSession?
    private let blockedReason: String?
    private let localRecordingStatus: String?
    private let localRecordingLocation: String?
    private let routeSignalLevels: LiveRouteSignalLevels
    private let onRecord: () -> Void
    private let onStop: () -> Void

    public init(
        session: CaptureSession?,
        blockedReason: String? = nil,
        localRecordingStatus: String? = nil,
        localRecordingLocation: String? = nil,
        routeSignalLevels: LiveRouteSignalLevels = .inactive,
        onRecord: @escaping () -> Void,
        onStop: @escaping () -> Void
    ) {
        self.session = session
        self.blockedReason = blockedReason
        self.localRecordingStatus = localRecordingStatus
        self.localRecordingLocation = localRecordingLocation
        self.routeSignalLevels = routeSignalLevels
        self.onRecord = onRecord
        self.onStop = onStop
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            LiveRecordingMetersView(
                routeSignalLevels: routeSignalLevels
            )

            Divider()

            HStack(alignment: .center, spacing: 12) {
                if let session {
                    CaptureStatusItem(session: session, onStop: onStop)
                } else {
                    Label("Recording idle", systemImage: "record.circle")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Spacer()

                if Self.shouldShowRecordButton(for: session) {
                    Button(action: onRecord) {
                        Label("Record System Audio", systemImage: "record.circle")
                    }
                    .buttonStyle(.borderedProminent)
                    .accessibilityLabel("Start system audio recording")
                }
            }

            if let blockedReason, !blockedReason.isEmpty {
                Label(blockedReason, systemImage: "exclamationmark.triangle.fill")
                    .font(.caption)
                    .foregroundStyle(.orange)
                    .accessibilityLabel(blockedReason)
            }

            if let localRecordingStatus, !localRecordingStatus.isEmpty {
                Label(localRecordingStatus, systemImage: localRecordingStatusIcon)
                    .font(.caption)
                    .foregroundStyle(localRecordingStatusStyle)
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
        .padding(16)
    }

    public static func shouldShowRecordButton(for session: CaptureSession?) -> Bool {
        guard let session else { return true }
        return !CaptureStatusItem.showsStopButton(for: session)
    }

    private var localRecordingStatusIcon: String {
        guard let localRecordingStatus else { return "waveform.path.badge.plus" }
        if localRecordingStatus.localizedCaseInsensitiveContains("blocked") ||
            localRecordingStatus.localizedCaseInsensitiveContains("permission") {
            return "lock.trianglebadge.exclamationmark"
        }
        if localRecordingStatus.localizedCaseInsensitiveContains("degraded") {
            return "exclamationmark.triangle.fill"
        }
        return "waveform.path.badge.plus"
    }

    private var localRecordingStatusStyle: Color {
        guard let localRecordingStatus else { return .secondary }
        if localRecordingStatus.localizedCaseInsensitiveContains("blocked") ||
            localRecordingStatus.localizedCaseInsensitiveContains("permission") ||
            localRecordingStatus.localizedCaseInsensitiveContains("degraded") {
            return .orange
        }
        return .secondary
    }
}

private struct LiveRecordingMetersView: View {
    let routeSignalLevels: LiveRouteSignalLevels
    private var now: Date { Date() }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 3) {
                    Text("Capture Audio")
                        .font(.headline)
                    Text(liveSummary)
                        .font(.caption)
                        .foregroundStyle(summaryColor)
                }
                Spacer()
                Image(systemName: incomingIsLive ? "waveform.circle.fill" : "waveform.circle")
                    .font(.title3)
                    .foregroundStyle(summaryColor)
            }

            meterRow(
                title: "Microphone",
                detail: microphoneDetail,
                icon: "mic.fill",
                level: microphoneLevel,
                isLive: microphoneIsLive,
                warning: shouldWarnMicrophone
            )
            meterRow(
                title: "Incoming",
                detail: incomingDetail,
                icon: "speaker.wave.2.fill",
                level: incomingLevel,
                isLive: incomingIsLive,
                warning: shouldWarnIncoming
            )
        }
        .accessibilityElement(children: .contain)
    }

    private var liveSummary: String {
        guard routeSignalLevels.isActive else {
            return "Meters start when recording"
        }
        if microphoneIsLive && incomingIsLive {
            return "Microphone and system audio are active"
        }
        if microphoneIsLive {
            return "Microphone active, system audio silent"
        }
        if incomingIsLive {
            return "System audio active, microphone silent"
        }
        return "No capture audio observed"
    }

    private var summaryColor: Color {
        if incomingIsLive && microphoneIsLive {
            return .green
        }
        if shouldWarnIncoming {
            return .orange
        }
        return .secondary
    }

    private var microphoneDetail: String {
        guard routeSignalLevels.isActive else { return "Waiting for recording audio" }
        return microphoneIsLive
            ? "Microphone audio is reaching the recorder."
            : "No microphone audio is reaching the recorder."
    }

    private var incomingDetail: String {
        guard routeSignalLevels.isActive else { return "Waiting for recording audio" }
        if incomingIsLive {
            return "System audio is reaching the recorder."
        }
        return "No system audio is reaching the recorder."
    }

    private var microphoneLevel: Double {
        routeSignalLevels.microphoneLevel
    }

    private var incomingLevel: Double {
        routeSignalLevels.speakerLevel
    }

    private var microphoneIsLive: Bool {
        routeSignalLevels.microphoneIsLive(now: now, staleAfter: 0.45)
    }

    private var incomingIsLive: Bool {
        routeSignalLevels.speakerIsLive(now: now, staleAfter: 0.45)
    }

    private var shouldWarnIncoming: Bool {
        routeSignalLevels.isActive && !incomingIsLive
    }

    private var shouldWarnMicrophone: Bool {
        routeSignalLevels.isActive && !microphoneIsLive
    }

    private func meterRow(
        title: String,
        detail: String,
        icon: String,
        level: Double,
        isLive: Bool,
        warning: Bool
    ) -> some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .foregroundStyle(warning ? .orange : (isLive ? .green : .secondary))
                .frame(width: 20)

            VStack(alignment: .leading, spacing: 5) {
                HStack(spacing: 8) {
                    Text(title)
                        .font(.subheadline)
                        .fontWeight(.medium)
                    Text(isLive ? "Active" : "Silent")
                        .font(.caption2)
                        .fontWeight(.semibold)
                        .foregroundStyle(warning ? .orange : (isLive ? .green : .secondary))
                }
                EqualizerBars(level: level, isLive: isLive, warning: warning)
                Text(detail)
                    .font(.caption)
                    .foregroundStyle(warning ? .orange : .secondary)
                    .lineLimit(2)
            }
            Spacer(minLength: 0)
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(title): \(detail)")
    }
}

private struct EqualizerBars: View {
    let level: Double
    let isLive: Bool
    let warning: Bool

    private let bars = 14

    var body: some View {
        HStack(alignment: .bottom, spacing: 3) {
            ForEach(0..<bars, id: \.self) { index in
                RoundedRectangle(cornerRadius: 2)
                    .fill(color(for: index))
                    .frame(width: 7, height: height(for: index))
            }
        }
        .frame(height: 28, alignment: .bottom)
        .animation(.linear(duration: 0.05), value: level)
        .animation(.linear(duration: 0.05), value: isLive)
    }

    private func height(for index: Int) -> CGFloat {
        let base = CGFloat(4 + (index % 3))
        guard isLive else { return base }
        let displayLevel = min(1, pow(max(level, 0) * 7, 0.72))
        let activeBars = max(1, Int((displayLevel * Double(bars)).rounded(.up)))
        guard index < activeBars else { return base }
        let shape = CGFloat([0.42, 0.7, 1.0, 0.56, 0.84][index % 5])
        return 7 + CGFloat(displayLevel) * 22 * shape
    }

    private func color(for index: Int) -> Color {
        guard isLive else {
            return warning ? .orange.opacity(0.28) : .secondary.opacity(0.22)
        }
        let displayLevel = min(1, pow(max(level, 0) * 7, 0.72))
        if index < max(1, Int((displayLevel * Double(bars)).rounded(.up))) {
            return warning ? .orange : .green
        }
        return .secondary.opacity(0.18)
    }
}
