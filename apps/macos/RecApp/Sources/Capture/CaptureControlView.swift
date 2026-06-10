import SwiftUI
import TwoBrainRecShared

public struct CaptureControlView: View {
    private let session: CaptureSession?
    private let blockedReason: String?
    private let localRecordingStatus: String?
    private let localRecordingLocation: String?
    private let routeSignalLevels: LiveRouteSignalLevels
    private let recordDisabled: Bool
    private let stopDisabled: Bool
    private let onRecord: () -> Void
    private let onStop: () -> Void

    public init(
        session: CaptureSession?,
        blockedReason: String? = nil,
        localRecordingStatus: String? = nil,
        localRecordingLocation: String? = nil,
        routeSignalLevels: LiveRouteSignalLevels = .inactive,
        recordDisabled: Bool = false,
        stopDisabled: Bool = false,
        onRecord: @escaping () -> Void,
        onStop: @escaping () -> Void
    ) {
        self.session = session
        self.blockedReason = blockedReason
        self.localRecordingStatus = localRecordingStatus
        self.localRecordingLocation = localRecordingLocation
        self.routeSignalLevels = routeSignalLevels
        self.recordDisabled = recordDisabled
        self.stopDisabled = stopDisabled
        self.onRecord = onRecord
        self.onStop = onStop
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(alignment: .center, spacing: 12) {
                if let session {
                    CaptureStatusItem(session: session, stopDisabled: stopDisabled, onStop: onStop)
                } else {
                    Label(SystemAudioStatusLabels.recordingIdle, systemImage: "record.circle")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                        .minimumScaleFactor(0.85)
                }

                Spacer()

                if Self.shouldShowRecordButton(for: session) {
                    Button(action: onRecord) {
                        Label(SystemAudioStatusLabels.recordButtonTitle, systemImage: "record.circle")
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(!Self.shouldEnableRecordButton(for: session, recordDisabled: recordDisabled))
                    .keyboardShortcut("r", modifiers: [.command, .shift])
                    .accessibilityLabel(SystemAudioStatusLabels.recordButtonAccessibilityLabel)
                    .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.recordButton)
                    .help(SystemAudioStatusLabels.recordButtonAccessibilityLabel)
                }
            }

            if let blockedReason, !blockedReason.isEmpty {
                Label(blockedReason, systemImage: "exclamationmark.triangle.fill")
                    .font(.caption)
                    .foregroundStyle(.orange)
                    .lineLimit(3)
                    .fixedSize(horizontal: false, vertical: true)
                    .accessibilityLabel(blockedReason)
                    .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.blockerBanner)
            }

            if let localRecordingStatus, !localRecordingStatus.isEmpty {
                Label(localRecordingStatus, systemImage: localRecordingStatusIcon)
                    .font(.caption)
                    .foregroundStyle(localRecordingStatusStyle)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
                    .accessibilityLabel(localRecordingStatus)
                    .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.localRecordingStatus)
            }

            if let localRecordingLocation, !localRecordingLocation.isEmpty {
                Text(localRecordingLocation)
                    .font(.caption2.monospaced())
                    .foregroundStyle(.secondary)
                    .textSelection(.enabled)
                    .lineLimit(2)
                    .truncationMode(.middle)
                    .accessibilityLabel(SystemAudioStatusLabels.localRecordingLocationAccessibilityLabel(localRecordingLocation))
                    .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.localRecordingLocation)
            }

            Divider()

            LiveRecordingMetersView(
                routeSignalLevels: routeSignalLevels
            )
        }
        .padding(16)
        .accessibilityElement(children: .contain)
        .accessibilityLabel(SystemAudioStatusLabels.captureRegion)
        .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.captureControls)
    }

    public static func shouldShowRecordButton(for session: CaptureSession?) -> Bool {
        guard let session else { return true }
        return !CaptureStatusItem.showsStopButton(for: session)
    }

    public static func shouldEnableRecordButton(
        for session: CaptureSession?,
        recordDisabled: Bool
    ) -> Bool {
        shouldShowRecordButton(for: session) && !recordDisabled
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
                    Text(SystemAudioStatusLabels.captureAudioTitle)
                        .font(.headline)
                        .lineLimit(1)
                        .minimumScaleFactor(0.85)
                    Text(liveSummary)
                        .font(.caption)
                        .foregroundStyle(summaryColor)
                        .lineLimit(2)
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer()
                Image(systemName: incomingIsLive ? "waveform.circle.fill" : "waveform.circle")
                    .font(.title3)
                    .foregroundStyle(summaryColor)
            }

            HStack(alignment: .top, spacing: 18) {
                meterRow(
                    title: SystemAudioStatusLabels.microphoneTitle,
                    detail: microphoneDetail,
                    icon: "mic.fill",
                    level: microphoneLevel,
                    isLive: microphoneIsLive,
                    warning: shouldWarnMicrophone
                )
                .frame(maxWidth: .infinity, alignment: .leading)

                meterRow(
                    title: SystemAudioStatusLabels.incomingTitle,
                    detail: incomingDetail,
                    icon: "speaker.wave.2.fill",
                    level: incomingLevel,
                    isLive: incomingIsLive,
                    warning: shouldWarnIncoming
                )
                .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.meters)
    }

    private var liveSummary: String {
        SystemAudioStatusLabels.liveSummary(
            routeIsActive: routeSignalLevels.isActive,
            microphoneIsLive: microphoneIsLive,
            incomingIsLive: incomingIsLive
        )
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
        SystemAudioStatusLabels.microphoneDetail(
            routeIsActive: routeSignalLevels.isActive,
            microphoneIsLive: microphoneIsLive
        )
    }

    private var incomingDetail: String {
        SystemAudioStatusLabels.incomingDetail(
            routeIsActive: routeSignalLevels.isActive,
            incomingIsLive: incomingIsLive
        )
    }

    private var microphoneLevel: Double {
        routeSignalLevels.microphoneLevel
    }

    private var incomingLevel: Double {
        routeSignalLevels.speakerLevel
    }

    private var microphoneIsLive: Bool {
        routeSignalLevels.microphoneIsLive(
            now: now,
            staleAfter: SystemAudioStatusLabels.recordingMeterFreshnessWindowSeconds
        )
    }

    private var incomingIsLive: Bool {
        routeSignalLevels.speakerIsLive(
            now: now,
            staleAfter: SystemAudioStatusLabels.recordingMeterFreshnessWindowSeconds
        )
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
                HStack(alignment: .center, spacing: 8) {
                    Text(title)
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .lineLimit(1)
                        .minimumScaleFactor(0.85)
                    Text(SystemAudioStatusLabels.meterState(isLive: isLive))
                        .font(.caption2)
                        .fontWeight(.semibold)
                        .foregroundStyle(warning ? .orange : (isLive ? .green : .secondary))
                        .lineLimit(1)
                    Spacer(minLength: 4)
                    EqualizerBars(level: level, isLive: isLive, warning: warning)
                }
                Text(detail)
                    .font(.caption)
                    .foregroundStyle(warning ? .orange : .secondary)
                    .lineLimit(2)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .layoutPriority(1)
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel(SystemAudioStatusLabels.meterAccessibilityLabel(title: title, detail: detail))
        .accessibilityIdentifier(
            title == SystemAudioStatusLabels.microphoneTitle
                ? SystemAudioAccessibilityIdentifier.microphoneMeter
                : SystemAudioAccessibilityIdentifier.incomingMeter
        )
    }
}

private struct EqualizerBars: View {
    let level: Double
    let isLive: Bool
    let warning: Bool

    private let bars = 10

    var body: some View {
        HStack(alignment: .bottom, spacing: 3) {
            ForEach(0..<bars, id: \.self) { index in
                RoundedRectangle(cornerRadius: 2)
                    .fill(color(for: index))
                    .frame(width: 6, height: height(for: index))
            }
        }
        .frame(width: 87, height: 22, alignment: .bottom)
        .animation(.linear(duration: 0.05), value: level)
        .animation(.linear(duration: 0.05), value: isLive)
        .accessibilityHidden(true)
    }

    private func height(for index: Int) -> CGFloat {
        let base = CGFloat(4 + (index % 3))
        guard isLive else { return base }
        let displayLevel = min(1, pow(max(level, 0) * 7, 0.72))
        let activeBars = max(1, Int((displayLevel * Double(bars)).rounded(.up)))
        guard index < activeBars else { return base }
        let shape = CGFloat([0.42, 0.7, 1.0, 0.56, 0.84][index % 5])
        return 6 + CGFloat(displayLevel) * 17 * shape
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
