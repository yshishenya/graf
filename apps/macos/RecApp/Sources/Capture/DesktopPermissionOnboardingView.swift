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
    public static let page = "desktop.permissionOnboarding.page"
    public static let microphoneButton = "desktop.permissionOnboarding.microphone"
    public static let systemAudioButton = "desktop.permissionOnboarding.systemAudio"
    public static let restartButton = "desktop.permissionOnboarding.restart"
    public static let finishButton = "desktop.permissionOnboarding.finish"
}

public struct DesktopPermissionOnboardingView: View {
    public static let title = "Чтобы вас было слышно"
    public static let subtitle = "Разрешите доступ к микрофону, чтобы ваш голос попал в запись встречи."
    public static let systemAudioStepDetail = "Так в записи будут слышны собеседники. GRAF получает звук с Mac и не сохраняет видео экрана."
    public static let startStepTitle = "Всё готово к записи"
    public static let startStepDetail = "Когда начнётся встреча, нажмите кнопку записи. Автозапись работает по вашим правилам."
    public static let openSettingsTitle = "Открыть настройки"
    public static let retryTitle = "Проверить ещё раз"
    public static var restartTitle: String { "Перезапустить \(GrafAppChannel.current.displayName)" }
    public static let restartDetail = "Если доступ включён, но проверка не помогает, можно перезапустить приложение. Вы вернётесь к этому шагу."
    public static let microphoneDeniedDetail = "Откройте настройки и включите доступ для приложения."
    public static let microphoneRestrictedDetail = "Настройки этого Mac не позволяют включить доступ. Попросите администратора разрешить его для приложения."
    public static let recordingBoundaryDetail = "Пока настраиваем звук, запись не идёт. После выхода действуют ваши правила автозаписи."

    public static func systemAudioStepDetail(for applicationName: String) -> String {
        "В настройках выберите «\(applicationName)» — то же имя, что в заголовке этого окна."
    }

    private let status: DesktopPermissionOnboardingStatus
    private let applicationName: String
    private let isRequesting: Bool
    private let isChecking: Bool
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
    @State private var helpExpanded = false

    public init(
        status: DesktopPermissionOnboardingStatus,
        applicationName: String = "GRAF",
        isRequesting: Bool,
        isChecking: Bool = false,
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
        self.isChecking = isChecking
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
        VStack(spacing: 0) {
            ViewThatFits(in: .vertical) {
                content
                ScrollView { content }
            }
            footer
        }
        .frame(width: 520)
        .frame(maxHeight: min(700, max(320, (NSApp.keyWindow?.screen?.visibleFrame.height ?? 860) - 160)))
        .tint(DesktopMeetingShellChrome.shellAccentColor)
        .accessibilityIdentifier(DesktopPermissionOnboardingAccessibilityIdentifier.page)
        .onExitCommand(perform: onDismiss)
        .onChange(of: status.nextPermission) { _, _ in
            helpExpanded = false
            settingsHelp = nil
        }
    }

    private var currentState: CapturePermissionState {
        status.nextPermission == .microphone ? status.microphone : status.systemAudio
    }

    private var content: some View {
        VStack(alignment: .leading, spacing: 24) {
            HStack(spacing: 12) {
                progressStep(.microphone, title: "Ваш голос", number: "1", state: status.microphone)
                Image(systemName: "chevron.right").font(.caption).foregroundStyle(.tertiary).accessibilityHidden(true)
                progressStep(.systemAudio, title: "Собеседники", number: "2", state: status.systemAudio)
            }
            VStack(alignment: .leading, spacing: 12) {
                Image(systemName: status.isReady ? "checkmark" : (status.nextPermission == .microphone ? "mic" : "speaker.wave.2"))
                    .font(.system(size: 28, weight: .medium))
                    .foregroundStyle(status.isReady ? Color.green : DesktopMeetingShellChrome.shellAccentColor)
                    .frame(width: 60, height: 60)
                    .background(DesktopMeetingShellChrome.shellAccentColor.opacity(0.08), in: RoundedRectangle(cornerRadius: 18))
                    .accessibilityHidden(true)
                Text(status.isReady ? Self.startStepTitle : (status.nextPermission == .microphone ? Self.title : "Теперь — собеседников"))
                    .font(.system(size: 26, weight: .semibold))
                    .accessibilityAddTraits(.isHeader)
                Text(status.isReady ? Self.startStepDetail : (status.nextPermission == .microphone ? Self.subtitle : Self.systemAudioStepDetail))
                    .font(.body).foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            if isRequesting {
                HStack(alignment: .top, spacing: 12) {
                    ProgressView().controlSize(.small)
                    VStack(alignment: .leading, spacing: 4) {
                        Text(isChecking ? "Проверяем, всё ли готово…" : "Ответьте на запрос macOS")
                            .font(.body.weight(.medium))
                        Text(isChecking ? "Это займёт несколько секунд." : "Выберите «Разрешить» в системном окне, чтобы продолжить настройку.")
                            .font(.callout).foregroundStyle(.secondary)
                    }
                }
                .accessibilityElement(children: .combine)
            } else if currentState == .restricted {
                Text(Self.microphoneRestrictedDetail).font(.body).foregroundStyle(.secondary)
            } else if let step = visibleSettingsHelp {
                settingsGuide(step)
            } else if currentState == .stale {
                Text("Пока не удалось проверить разрешение. Попробуем ещё раз — повторно выдавать доступ не нужно.")
                    .font(.body).foregroundStyle(.secondary)
            } else if !status.isReady {
                Label("После «Продолжить» macOS попросит разрешение для «\(applicationName)».", systemImage: "macwindow")
                    .font(.callout).foregroundStyle(.secondary)
            }
            if let settingsError {
                Label(settingsError, systemImage: "exclamationmark.triangle")
                    .font(.callout).foregroundStyle(.secondary)
            }
            if let step = status.nextPermission {
                DisclosureGroup("Не получается?", isExpanded: $helpExpanded) {
                    help(step).padding(.top, 10)
                }
                .font(.callout)
            }
        }
        .padding(.horizontal, 26)
        .padding(.top, 26)
        .padding(.bottom, 8)
        .fixedSize(horizontal: false, vertical: true)
    }

    private var footer: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(spacing: 12) {
                if !status.isReady && currentState != .restricted {
                    Button(action: onDismiss) {
                        Text("Настроить позже").frame(minHeight: 44).contentShape(Rectangle())
                    }
                        .buttonStyle(.plain)
                        .accessibilityIdentifier("desktop.permissionOnboarding.later")
                }
                Spacer()
                Button(action: performPrimaryAction) {
                    Text(primaryActionTitle).frame(minHeight: 44)
                }
                    .buttonStyle(DesktopWebButtonStyle(.primary))
                    .keyboardShortcut(.defaultAction)
                    .disabled(isRequesting)
                    .accessibilityIdentifier(status.isReady ? DesktopPermissionOnboardingAccessibilityIdentifier.finishButton : (status.nextPermission == .microphone ? DesktopPermissionOnboardingAccessibilityIdentifier.microphoneButton : DesktopPermissionOnboardingAccessibilityIdentifier.systemAudioButton))
            }
            if !status.isReady {
                Text(Self.recordingBoundaryDetail)
                    .font(.caption).foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(26)
        .fixedSize(horizontal: false, vertical: true)
    }

    private var primaryActionTitle: String {
        if isRequesting { return isChecking ? "Проверяем…" : "Ожидаем ответа…" }
        if status.isReady { return "Готово" }
        if currentState == .restricted { return "Вернуться в GRAF" }
        if needsSettings { return Self.openSettingsTitle }
        return currentState == .unknown ? "Продолжить" : Self.retryTitle
    }

    private func performPrimaryAction() {
        if status.isReady { onFinish() }
        else if currentState == .restricted { onDismiss() }
        else if needsSettings, let step = status.nextPermission { openSettings(step) }
        else if currentState == .unknown {
            if status.nextPermission == .microphone { onRequestMicrophone() } else { onRequestSystemAudio() }
        } else { onRefresh() }
    }

    private func progressStep(_ step: DesktopPermissionStep, title: String, number: String, state: CapturePermissionState) -> some View {
        let active = status.nextPermission == step
        return HStack(spacing: 8) {
            if state == .granted {
                Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
            } else {
                Text(number).font(.caption.weight(.semibold))
                    .frame(width: 22, height: 22)
                    .background(Color.primary.opacity(0.06), in: Circle())
            }
            Text(title).font(.callout.weight(active ? .semibold : .regular))
        }
        .foregroundStyle(active ? Color.primary : .secondary)
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .background(active ? DesktopMeetingShellChrome.shellAccentColor.opacity(0.08) : .clear, in: RoundedRectangle(cornerRadius: 10))
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(title): \(state == .granted ? "готово" : (active ? "текущий шаг" : "следующий шаг"))")
    }

    private var needsSettings: Bool {
        let attempted = status.nextPermission == .microphone ? microphoneAttempted : systemAudioAttempted
        return DesktopPermissionOnboardingStatus.needsSettings(state: currentState, attempted: attempted)
    }

    private var visibleSettingsHelp: DesktopPermissionStep? {
        guard let step = status.nextPermission else { return nil }
        return settingsHelp == step || needsSettings ? step : nil
    }

    private func openSettings(_ step: DesktopPermissionStep) {
        settingsHelp = step
        if step == .microphone { onOpenMicrophoneSettings() } else { onOpenSystemAudioSettings() }
    }

    private func settingsGuide(_ step: DesktopPermissionStep) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Включите «\(applicationName)» в настройках")
                .font(.body.weight(.medium))
            Text("Конфиденциальность и безопасность → \(step == .microphone ? "Микрофон" : "Запись экрана и системного звука")")
                .font(.callout).foregroundStyle(.secondary)
            HStack(spacing: 10) {
                Image(nsImage: NSApplication.shared.applicationIconImage).resizable().frame(width: 28, height: 28)
                Text(applicationName).font(.callout.weight(.medium))
                Spacer()
                Circle().fill(.white).frame(width: 16, height: 16)
                    .frame(width: 34, height: 22, alignment: .trailing).padding(.trailing, 3)
                    .background(Color.green, in: Capsule())
                Text("Вкл.").font(.caption)
            }
            .padding(12).background(Color.primary.opacity(0.04), in: RoundedRectangle(cornerRadius: 10))
            .accessibilityElement(children: .ignore)
            .accessibilityLabel("Пример: включите переключатель рядом с \(applicationName) в системных настройках")
            Text("Пример в настройках macOS. Затем вернитесь сюда — мы проверим доступ автоматически.")
                .font(.callout).foregroundStyle(.secondary)
            if step == .systemAudio {
                Text("macOS просит «Завершить и открыть снова»? Подтвердите — после запуска вы продолжите с этого места.")
                    .font(.callout).foregroundStyle(.secondary)
            }
        }
    }

    private func help(_ step: DesktopPermissionStep) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Уже включили доступ? Проверим ещё раз.")
                .foregroundStyle(.secondary)
            Button(Self.retryTitle, action: onRefresh).disabled(isRequesting)
            if !needsSettings && currentState != .restricted {
                Button(Self.openSettingsTitle) { openSettings(step) }.disabled(isRequesting)
            }
            let attempted = step == .microphone ? microphoneAttempted : systemAudioAttempted
            if currentState == .unknown && attempted {
                Text("Не видите «\(applicationName)» в списке? Повторите запрос, чтобы приложение появилось в настройках.")
                    .foregroundStyle(.secondary)
                Button("Повторить запрос", action: step == .microphone ? onRequestMicrophone : onRequestSystemAudio)
                    .disabled(isRequesting)
            }
            if step == .systemAudio && (recoverySuggested || visibleSettingsHelp != nil) {
                Text(Self.restartDetail).foregroundStyle(.secondary)
                Button("Перезапустить \(applicationName)", action: onRestart)
                    .disabled(isRequesting || !restartAvailable)
                    .accessibilityIdentifier(DesktopPermissionOnboardingAccessibilityIdentifier.restartButton)
                if !restartAvailable {
                    Text("Сначала дождитесь окончания записи и сохранения файла.").foregroundStyle(.secondary)
                }
            }
            Text(Self.systemAudioStepDetail(for: applicationName)).foregroundStyle(.secondary)
            Text("Название раздела может немного отличаться в вашей версии macOS.").foregroundStyle(.secondary)
        }
    }
}
