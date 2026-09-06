import AppKit
import SwiftUI
import TwoBrainRecShared

public struct DesktopPermissionOnboardingStatus: Equatable, Sendable {
    public var microphone: CapturePermissionState
    public var systemAudio: CapturePermissionState

    public init(microphone: CapturePermissionState, systemAudio: CapturePermissionState) {
        self.microphone = microphone
        self.systemAudio = systemAudio
    }

    public static let unknown = Self(microphone: .unknown, systemAudio: .unknown)
    public var isReady: Bool { microphone == .granted && systemAudio == .granted }
    public var completedCount: Int { (microphone == .granted ? 1 : 0) + (systemAudio == .granted ? 1 : 0) }
    public var nextPermission: DesktopPermissionStep? {
        if microphone != .granted { return .microphone }
        return systemAudio == .granted ? nil : .systemAudio
    }

    public static func needsSettings(state: CapturePermissionState, attempted: Bool) -> Bool {
        state == .denied || (state == .unknown && attempted)
    }
}

public enum DesktopPermissionStep: Sendable {
    case microphone, systemAudio
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
    public static let restartButton = "desktop.permissionOnboarding.restart"
    public static let finishButton = "desktop.permissionOnboarding.finish"
}

public struct DesktopPermissionOnboardingView: View {
    public static var title: String { "Подготовим \(GrafAppChannel.current.displayName) к записи" }
    public static let subtitle = "Два разрешения macOS, чтобы в записи были слышны вы и собеседники."
    public static let systemAudioStepDetail = "Звук, который воспроизводится на Mac. GRAF не сохраняет видео экрана."
    public static let startStepTitle = "Всё готово к записи"
    public static let startStepDetail = "Используйте кнопку записи. Автозапись работает по вашим правилам."
    public static let openSettingsTitle = "Открыть настройки macOS"
    public static let retryTitle = "Проверить снова"
    public static var restartTitle: String { "Перезапустить \(GrafAppChannel.current.displayName)" }
    public static let restartDetail = "Доступ пока не удалось проверить. Попробуйте ещё раз. Если это не помогло, можно перезапустить приложение."
    public static let microphoneDeniedDetail = "Откройте настройки и включите доступ: повторный запрос после отказа macOS не показывает."
    public static let microphoneRestrictedDetail = "Доступ ограничен на этом Mac. Обратитесь к администратору устройства. GRAF не может обойти это ограничение."
    public static let recordingBoundaryDetail = "Настройка сама не запускает запись. После закрытия окна автозапись работает по вашим правилам."

    public static func systemAudioStepDetail(for applicationName: String) -> String {
        "\(systemAudioStepDetail) В настройках выберите «\(applicationName)»: разные копии приложения получают доступ отдельно."
    }

    private let status: DesktopPermissionOnboardingStatus
    private let applicationName: String
    private let isRequesting: Bool
    private let recoverySuggested: Bool
    private let restartAvailable: Bool
    private let microphoneAttempted: Bool
    private let systemAudioAttempted: Bool
    private let settingsError: String?
    private let onRequestMicrophone: () -> Void
    private let onRequestSystemAudio: () -> Void
    private let onOpenMicrophoneSettings: () -> Void
    private let onOpenSystemAudioSettings: () -> Void
    private let onRefresh: () -> Void
    private let onDismiss: () -> Void
    private let onFinish: () -> Void
    private let onRestart: () -> Void
    @State private var settingsHelp: DesktopPermissionStep?

    public init(
        status: DesktopPermissionOnboardingStatus,
        applicationName: String = "GRAF",
        isRequesting: Bool,
        recoverySuggested: Bool,
        restartAvailable: Bool = true,
        microphoneAttempted: Bool = false,
        systemAudioAttempted: Bool = false,
        settingsError: String? = nil,
        onRequestMicrophone: @escaping () -> Void,
        onRequestSystemAudio: @escaping () -> Void,
        onOpenMicrophoneSettings: @escaping () -> Void,
        onOpenSystemAudioSettings: @escaping () -> Void,
        onRefresh: @escaping () -> Void,
        onDismiss: @escaping () -> Void,
        onFinish: @escaping () -> Void,
        onRestart: @escaping () -> Void
    ) {
        self.status = status
        self.applicationName = applicationName
        self.isRequesting = isRequesting
        self.recoverySuggested = recoverySuggested
        self.restartAvailable = restartAvailable
        self.microphoneAttempted = microphoneAttempted
        self.systemAudioAttempted = systemAudioAttempted
        self.settingsError = settingsError
        self.onRequestMicrophone = onRequestMicrophone
        self.onRequestSystemAudio = onRequestSystemAudio
        self.onOpenMicrophoneSettings = onOpenMicrophoneSettings
        self.onOpenSystemAudioSettings = onOpenSystemAudioSettings
        self.onRefresh = onRefresh
        self.onDismiss = onDismiss
        self.onFinish = onFinish
        self.onRestart = onRestart
    }

    public var body: some View {
        ViewThatFits(in: .vertical) {
            content
            ScrollView { content }
        }
        .frame(width: 520)
        .frame(maxHeight: min(700, max(320, (NSApp.keyWindow?.screen?.visibleFrame.height ?? 860) - 160)))
        .tint(DesktopMeetingShellChrome.shellAccentColor)
        .accessibilityIdentifier(DesktopPermissionOnboardingAccessibilityIdentifier.sheet)
    }

    private var content: some View {
        VStack(alignment: .leading, spacing: 20) {
            HStack(alignment: .top, spacing: 14) {
                Image(systemName: status.isReady ? "checkmark.circle.fill" : "waveform")
                    .font(.system(size: 26, weight: .medium))
                    .foregroundStyle(status.isReady ? Color.green : DesktopMeetingShellChrome.shellAccentColor)
                    .frame(width: 48, height: 48)
                    .background(Color.primary.opacity(0.05), in: RoundedRectangle(cornerRadius: 14))
                    .accessibilityHidden(true)
                VStack(alignment: .leading, spacing: 6) {
                    Text(status.isReady ? Self.startStepTitle : "Подготовим \(applicationName) к записи")
                        .font(.title2.weight(.semibold))
                        .accessibilityAddTraits(.isHeader)
                    Text(status.isReady ? Self.startStepDetail : Self.subtitle)
                        .font(.callout).foregroundStyle(.secondary)
                }
            }
            HStack {
                Text("Разрешения macOS").font(.callout.weight(.medium))
                Spacer()
                Text("\(status.completedCount) из 2 готовы").font(.caption).foregroundStyle(.secondary)
            }
            VStack(spacing: 10) {
                permissionRow(.microphone, title: "Ваш голос", detail: "Доступ к микрофону", icon: "mic", state: status.microphone)
                permissionRow(.systemAudio, title: "Голоса собеседников", detail: Self.systemAudioStepDetail, icon: "speaker.wave.2", state: status.systemAudio)
            }
            if isRequesting {
                HStack(spacing: 10) {
                    ProgressView().controlSize(.small)
                    Text("Ожидаем macOS… Если появилось системное окно, выберите действие в нём.")
                        .font(.caption).foregroundStyle(.secondary)
                }
                .accessibilityElement(children: .combine)
            }
            if let step = visibleSettingsHelp {
                settingsGuide(step)
            }
            if let settingsError {
                Label(settingsError, systemImage: "exclamationmark.triangle")
                    .font(.caption).foregroundStyle(.secondary)
            }
            if recoverySuggested {
                VStack(alignment: .leading, spacing: 8) {
                    Text(Self.restartDetail).font(.caption).foregroundStyle(.secondary)
                    Button("Перезапустить \(applicationName)", action: onRestart)
                        .buttonStyle(DesktopWebButtonStyle(.secondary))
                        .disabled(!restartAvailable || isRequesting)
                        .accessibilityIdentifier(DesktopPermissionOnboardingAccessibilityIdentifier.restartButton)
                    if !restartAvailable {
                        Text("Перезапуск станет доступен после завершения записи и сохранения файла.")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                }
            }
            Divider()
            Text(Self.recordingBoundaryDetail).font(.caption).foregroundStyle(.secondary)
            HStack {
                if !status.isReady {
                    Button("Позже", action: onDismiss).keyboardShortcut(.cancelAction)
                }
                Spacer()
                if status.isReady {
                    Button("Готово", action: onFinish)
                        .buttonStyle(DesktopWebButtonStyle(.primary))
                        .keyboardShortcut(.defaultAction)
                        .disabled(isRequesting)
                        .accessibilityIdentifier(DesktopPermissionOnboardingAccessibilityIdentifier.finishButton)
                }
            }
        }
        .padding(26)
        .fixedSize(horizontal: false, vertical: true)
    }

    private func permissionRow(_ step: DesktopPermissionStep, title: String, detail: String, icon: String, state: CapturePermissionState) -> some View {
        let active = status.nextPermission == step
        let attempted = step == .microphone ? microphoneAttempted : systemAudioAttempted
        let needsSettings = DesktopPermissionOnboardingStatus.needsSettings(state: state, attempted: attempted)
        return HStack(alignment: .top, spacing: 12) {
            Image(systemName: state == .granted ? "checkmark.circle.fill" : icon)
                .font(.title3).foregroundStyle(state == .granted ? Color.green : .secondary)
                .frame(width: 26, height: 26).accessibilityHidden(true)
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text(title).font(.callout.weight(.semibold))
                    Spacer()
                    if state == .granted { Text("Готово").font(.caption).foregroundStyle(.secondary) }
                }
                Text(state == .restricted ? Self.microphoneRestrictedDetail : detail)
                    .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                if active {
                    if state == .unknown && !attempted {
                        Text("Нажмите «Продолжить», затем ответьте на запрос macOS.")
                            .font(.caption).foregroundStyle(.secondary)
                    } else if needsSettings {
                        Text("Включите доступ для «\(applicationName)» в настройках macOS.")
                            .font(.caption).foregroundStyle(.secondary)
                    } else if state == .stale {
                        Text("Не удалось проверить доступ. Попробуйте ещё раз.")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                    HStack {
                        Button(needsSettings ? Self.openSettingsTitle : (state == .unknown ? "Продолжить" : Self.retryTitle)) {
                            if needsSettings { openSettings(step) }
                            else if state == .unknown {
                                if step == .microphone { onRequestMicrophone() } else { onRequestSystemAudio() }
                            } else { onRefresh() }
                        }
                        .buttonStyle(DesktopWebButtonStyle(.primary))
                        .disabled(isRequesting)
                        .keyboardShortcut(.defaultAction)
                        .accessibilityIdentifier(step == .microphone ? DesktopPermissionOnboardingAccessibilityIdentifier.microphoneButton : DesktopPermissionOnboardingAccessibilityIdentifier.systemAudioButton)
                        if needsSettings {
                            Button(Self.retryTitle, action: onRefresh)
                                .buttonStyle(DesktopWebButtonStyle(.secondary)).disabled(isRequesting)
                        }
                    }
                    DisclosureGroup("Нужна помощь?") {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Если запрос не появился или доступ уже включён, откройте настройки и найдите «\(applicationName)». Проверьте, что настраиваете именно запущенную копию приложения.")
                                .font(.caption).foregroundStyle(.secondary)
                            Button(Self.openSettingsTitle) { openSettings(step) }
                                .disabled(isRequesting)
                            if state == .unknown && attempted {
                                Text("Если «\(applicationName)» нет в списке, повторите системный запрос доступа.")
                                    .font(.caption).foregroundStyle(.secondary)
                                Button("Запросить доступ ещё раз", action: step == .microphone ? onRequestMicrophone : onRequestSystemAudio)
                                    .disabled(isRequesting)
                            }
                            if needsSettings && step == .systemAudio {
                                Text("Доступ уже включён, но статус не изменился? Нажмите «Проверить снова». Если macOS ещё не применила доступ к запущенному приложению, может помочь перезапуск.")
                                    .font(.caption).foregroundStyle(.secondary)
                                Button("Перезапустить \(applicationName)", action: onRestart)
                                    .disabled(isRequesting || !restartAvailable)
                            }
                        }.padding(.top, 6)
                    }.font(.caption)
                }
            }
        }
        .padding(14)
        .background(Color.primary.opacity(active ? 0.055 : 0.025), in: RoundedRectangle(cornerRadius: 12))
        .overlay(RoundedRectangle(cornerRadius: 12).strokeBorder(active ? DesktopMeetingShellChrome.shellAccentColor.opacity(0.4) : Color.primary.opacity(0.08)))
    }

    private var visibleSettingsHelp: DesktopPermissionStep? {
        guard let step = status.nextPermission else { return nil }
        let state = step == .microphone ? status.microphone : status.systemAudio
        let attempted = step == .microphone ? microphoneAttempted : systemAudioAttempted
        return settingsHelp == step || DesktopPermissionOnboardingStatus.needsSettings(state: state, attempted: attempted) ? step : nil
    }

    private func openSettings(_ step: DesktopPermissionStep) {
        settingsHelp = step
        if step == .microphone { onOpenMicrophoneSettings() } else { onOpenSystemAudioSettings() }
    }

    private func settingsGuide(_ step: DesktopPermissionStep) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Включите «\(applicationName)»").font(.callout.weight(.semibold))
            Text("Конфиденциальность и безопасность → \(step == .microphone ? "Микрофон" : "Запись экрана и системного звука")")
                .font(.caption).foregroundStyle(.secondary)
            HStack(spacing: 10) {
                Image(nsImage: NSApplication.shared.applicationIconImage).resizable().frame(width: 28, height: 28)
                Text(applicationName).font(.callout.weight(.medium))
                Spacer()
                Circle().fill(.white).frame(width: 16, height: 16)
                    .frame(width: 34, height: 22, alignment: .trailing).padding(.trailing, 3)
                    .background(Color.green, in: Capsule())
                Text("Вкл.").font(.caption)
            }
            .padding(10).background(Color.primary.opacity(0.04), in: RoundedRectangle(cornerRadius: 8))
            .accessibilityElement(children: .ignore)
            .accessibilityLabel("Пример: включите переключатель рядом с \(applicationName) в системных настройках")
            Text("Пример в настройках macOS. Название раздела может отличаться в вашей версии. Вернитесь сюда — статус обновится автоматически.")
                .font(.caption).foregroundStyle(.secondary)
        }
    }
}
