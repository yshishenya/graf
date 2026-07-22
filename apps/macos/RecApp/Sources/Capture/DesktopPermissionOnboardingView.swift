import Foundation
import SwiftUI
import TwoBrainRecShared

public struct DesktopPermissionOnboardingStatus: Equatable, Sendable {
    public var microphone: CapturePermissionState
    public var systemAudio: CapturePermissionState

    public init(
        microphone: CapturePermissionState,
        systemAudio: CapturePermissionState
    ) {
        self.microphone = microphone
        self.systemAudio = systemAudio
    }

    public static let unknown = DesktopPermissionOnboardingStatus(
        microphone: .unknown,
        systemAudio: .unknown
    )

    public var isReady: Bool {
        microphone == .granted && systemAudio == .granted
    }
}

public enum DesktopPermissionOnboardingSettings {
    public static let microphoneURL = URL(
        string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"
    )!
    public static let screenAndSystemAudioURL = URL(
        string: "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
    )!
}

public enum DesktopPermissionOnboardingAccessibilityIdentifier {
    public static let sheet = "desktop.permissionOnboarding.sheet"
    public static let microphoneButton = "desktop.permissionOnboarding.microphone"
    public static let systemAudioButton = "desktop.permissionOnboarding.systemAudio"
    public static let finishButton = "desktop.permissionOnboarding.finish"
}

public struct DesktopPermissionOnboardingView: View {
    public static let title = "Подготовим GRAF к записи"
    public static let subtitle = "Разрешите доступы macOS заранее. Запись не начнется, пока вы не нажмете кнопку записи."
    public static let systemAudioStepDetail = "Нужна macOS, чтобы GRAF мог получить звук встречи. После настройки может потребоваться перезапуск GRAF."
    public static let startStepTitle = "Начните аудиозапись"
    public static let startStepDetail = "После разрешений используйте кнопку записи в правой панели управления."
    public static let openSettingsTitle = "Открыть настройки macOS"
    public static let retryTitle = "Проверить снова"

    private let status: DesktopPermissionOnboardingStatus
    private let isRequesting: Bool
    private let onRequestMicrophone: () -> Void
    private let onRequestSystemAudio: () -> Void
    private let onOpenMicrophoneSettings: () -> Void
    private let onOpenSystemAudioSettings: () -> Void
    private let onDismiss: () -> Void
    private let onFinish: () -> Void

    public init(
        status: DesktopPermissionOnboardingStatus,
        isRequesting: Bool,
        onRequestMicrophone: @escaping () -> Void,
        onRequestSystemAudio: @escaping () -> Void,
        onOpenMicrophoneSettings: @escaping () -> Void,
        onOpenSystemAudioSettings: @escaping () -> Void,
        onDismiss: @escaping () -> Void,
        onFinish: @escaping () -> Void
    ) {
        self.status = status
        self.isRequesting = isRequesting
        self.onRequestMicrophone = onRequestMicrophone
        self.onRequestSystemAudio = onRequestSystemAudio
        self.onOpenMicrophoneSettings = onOpenMicrophoneSettings
        self.onOpenSystemAudioSettings = onOpenSystemAudioSettings
        self.onDismiss = onDismiss
        self.onFinish = onFinish
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            Label(Self.title, systemImage: "record.circle")
                .font(.title3.weight(.semibold))

            Text(Self.subtitle)
                .font(.callout)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)

            VStack(spacing: 10) {
                PermissionOnboardingRow(
                    number: 1,
                    title: "Микрофон",
                    detail: "Нужен, чтобы сохранить вашу речь отдельной дорожкой.",
                    state: status.microphone,
                    primaryTitle: "Разрешить микрофон",
                    primaryIdentifier: DesktopPermissionOnboardingAccessibilityIdentifier.microphoneButton,
                    isRequesting: isRequesting,
                    onPrimary: onRequestMicrophone,
                    onSettings: onOpenMicrophoneSettings
                )

                PermissionOnboardingRow(
                    number: 2,
                    title: "Запись экрана и системного звука",
                    detail: Self.systemAudioStepDetail,
                    state: status.systemAudio,
                    primaryTitle: "Разрешить системный звук",
                    primaryIdentifier: DesktopPermissionOnboardingAccessibilityIdentifier.systemAudioButton,
                    isRequesting: isRequesting,
                    onPrimary: onRequestSystemAudio,
                    onSettings: onOpenSystemAudioSettings
                )

                HStack(alignment: .top, spacing: 12) {
                    Text("3")
                        .font(.caption.weight(.bold))
                        .frame(width: 24, height: 24)
                        .background(Color.accentColor.opacity(0.14), in: Circle())

                    VStack(alignment: .leading, spacing: 4) {
                        Text(Self.startStepTitle)
                            .font(.callout.weight(.semibold))
                        Text(Self.startStepDetail)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(12)
                .background(Color.primary.opacity(0.05), in: RoundedRectangle(cornerRadius: 8))
            }

            HStack {
                Button("Позже", action: onDismiss)
                Spacer()
                Button("Готово", action: onFinish)
                    .keyboardShortcut(.defaultAction)
                    .disabled(!status.isReady)
                    .accessibilityIdentifier(DesktopPermissionOnboardingAccessibilityIdentifier.finishButton)
            }
        }
        .padding(24)
        .frame(width: 540)
        .accessibilityIdentifier(DesktopPermissionOnboardingAccessibilityIdentifier.sheet)
    }
}

private struct PermissionOnboardingRow: View {
    let number: Int
    let title: String
    let detail: String
    let state: CapturePermissionState
    let primaryTitle: String
    let primaryIdentifier: String
    let isRequesting: Bool
    let onPrimary: () -> Void
    let onSettings: () -> Void

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Text("\(number)")
                .font(.caption.weight(.bold))
                .frame(width: 24, height: 24)
                .background(statusColor.opacity(0.16), in: Circle())

            VStack(alignment: .leading, spacing: 6) {
                HStack(alignment: .firstTextBaseline, spacing: 8) {
                    Text(title)
                        .font(.callout.weight(.semibold))
                    Text(statusText)
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(statusColor)
                }

                Text(detail)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)

                if state != .granted {
                    HStack(spacing: 8) {
                        Button(state == .unknown ? primaryTitle : DesktopPermissionOnboardingView.retryTitle, action: onPrimary)
                            .disabled(isRequesting)
                            .accessibilityIdentifier(primaryIdentifier)

                        Button(DesktopPermissionOnboardingView.openSettingsTitle, action: onSettings)
                            .disabled(isRequesting)
                    }
                    .controlSize(.small)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(Color.primary.opacity(0.05), in: RoundedRectangle(cornerRadius: 8))
    }

    private var statusText: String {
        switch state {
        case .granted:
            return "Готово"
        case .denied:
            return "Отклонено"
        case .restricted:
            return "Ограничено"
        case .stale:
            return "Нужно обновить"
        case .unknown:
            return "Нужно разрешение"
        }
    }

    private var statusColor: Color {
        switch state {
        case .granted:
            return .green
        case .denied, .restricted:
            return .red
        case .stale, .unknown:
            return .orange
        }
    }
}
