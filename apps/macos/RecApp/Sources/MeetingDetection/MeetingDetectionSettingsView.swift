import AppKit
import SwiftUI
import TwoBrainRecShared

public struct MeetingDetectionSettingsView: View {
    public static let windowTitle = "Настройки"
    public static let sidebarTitle = "Встречи"
    public static let pageTitle = "Автозапись"
    public static let promptToggleTitle = "Запрашивать запись"
    public static let promptToggleDetail =
        "Если выключено, запросы не показываются и запись не запускается. Определение встреч продолжает работать."
    public static let assistedAutoStartTitle = "Разрешить запуск записи после таймера"
    public static let assistedAutoStartDetail =
        "Для найденной встречи GRAF покажет обычный prompt на 8 секунд. Автоматический старт по таймеру работает только после вашего явного разрешения."
    public static let autoRecordSectionTitle = "Приложения"
    public static let autoRecordSectionDetail =
        "После вашего разрешения отмеченные приложения пишутся автоматически. Остальные будут спрашивать перед записью."
    public static let autoRecordDisabledSectionDetail =
        "Автоматическая запись выключена. Выбранные приложения остаются в списке для определения встреч."
    public static let selectAllTitle = "Выбрать все"
    public static let clearAllTitle = "Снять все"
    private let store: MeetingDetectionSettingsStore
    private let registryStore: MeetingTargetRegistryStore
    private let notificationCenter: NotificationCenter

    @State private var settings: MeetingDetectionSettings
    @State private var promptCapableTargets: [MeetingTargetRegistryTarget] = []
    @State private var currentPolicy: AssistedAutoStartPolicySnapshot? = nil
    @State private var saveError: String?

    public init(
        store: MeetingDetectionSettingsStore = MeetingDetectionSettingsStore(),
        registryStore: MeetingTargetRegistryStore = MeetingTargetRegistryStore(
            cacheURL: MeetingDetectionAppModule.targetRegistryCacheURL()
        ),
        notificationCenter: NotificationCenter = .default
    ) {
        self.store = store
        self.registryStore = registryStore
        self.notificationCenter = notificationCenter
        _settings = State(initialValue: (try? store.load()) ?? MeetingDetectionSettings())
        _promptCapableTargets = State(initialValue: Self.loadPromptCapableTargets(from: registryStore))
    }

    public var body: some View {
        HStack(spacing: 0) {
            sidebar
            Divider()
            content
        }
        .frame(width: 760, height: 500)
        .background(Color(nsColor: .windowBackgroundColor))
        .tint(DesktopMeetingShellChrome.shellAccentColor)
        .onAppear {
            reloadRegistryTargets()
        }
        .onReceive(notificationCenter.publisher(for: .twoBrainRecMeetingDetectionSettingsDidChange)) { _ in
            reloadSettings()
            reloadRegistryTargets()
        }
        .onReceive(notificationCenter.publisher(for: .twoBrainRecMeetingTargetRegistryDidChange)) { _ in
            reloadRegistryTargets()
        }
    }

    private var sidebar: some View {
        VStack(alignment: .leading, spacing: 18) {
            Button {
                NSApp.keyWindow?.close()
            } label: {
                Label("Назад", systemImage: "chevron.left")
            }
            .buttonStyle(.plain)
            .foregroundStyle(.secondary)
            .padding(.top, 18)

            VStack(alignment: .leading, spacing: 7) {
                Text(Self.sidebarTitle)
                    .font(.caption)
                    .fontWeight(.semibold)
                    .foregroundStyle(.secondary)

                Label(Self.pageTitle, systemImage: "record.circle")
                    .font(.subheadline)
                    .fontWeight(.semibold)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(Color.accentColor.opacity(0.18), in: RoundedRectangle(cornerRadius: 6))
                    .accessibilityAddTraits(.isSelected)
            }

            Spacer()
        }
        .padding(.horizontal, 16)
        .frame(width: 176)
        .background(.bar)
    }

    private var content: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 28) {
                Label(Self.pageTitle, systemImage: "dot.radiowaves.left.and.right")
                    .font(.headline)

                Form {
                    Section {
                        Toggle(isOn: assistedAutoStartBinding) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(Self.assistedAutoStartTitle)
                                    .fontWeight(.medium)
                                Text(Self.assistedAutoStartDetail)
                                    .font(.callout)
                                    .foregroundStyle(.secondary)
                                Text(assistedAutoStartPolicyStatus)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .toggleStyle(.switch)
                        .disabled(currentPolicy?.isActive() != true)
                        .accessibilityLabel(Self.assistedAutoStartTitle)

                        Toggle(isOn: recordingPromptBinding) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(Self.promptToggleTitle)
                                    .fontWeight(.medium)
                                Text(Self.promptToggleDetail)
                                    .font(.callout)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .toggleStyle(.switch)
                        .accessibilityLabel(Self.promptToggleTitle)
                        .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.meetingDetectionRecordingToggle)
                    }

                    Section(header: Text(Self.autoRecordSectionTitle).fontWeight(.medium)) {
                        Text(settings.detectionMode == .detectAndAsk ? Self.autoRecordSectionDetail : Self.autoRecordDisabledSectionDetail)
                            .font(.callout)
                            .foregroundStyle(.secondary)
                            .padding(.bottom, 4)

                        HStack {
                            Spacer()
                            Button(Self.selectAllTitle, action: selectAllAutoRecordTargets)
                                .disabled(promptCapableTargets.isEmpty)
                            Button(Self.clearAllTitle, action: clearAutoRecordTargets)
                                .disabled(settings.autoRecordTargetIds.isEmpty)
                        }
                        .buttonStyle(DesktopWebButtonStyle(.secondary))

                        if promptCapableTargets.isEmpty {
                            Text("Список появится после загрузки реестра.")
                                .font(.callout)
                                .foregroundStyle(.secondary)
                        } else {
                            ForEach(promptCapableTargets, id: \.id) { target in
                                Toggle(isOn: autoRecordBinding(for: target.id)) {
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(target.displayName)
                                        if let bundleID = target.nativeBundleIds.first {
                                            Text(bundleID)
                                                .font(.caption)
                                                .foregroundStyle(.secondary)
                                        }
                                    }
                                }
                                .toggleStyle(.checkbox)
                            }
                        }
                    }
                }
                .formStyle(.grouped)

                if let saveError {
                    Label(saveError, systemImage: "exclamationmark.triangle.fill")
                        .font(.callout)
                        .foregroundStyle(.orange)
                        .fixedSize(horizontal: false, vertical: true)
                }

                Spacer()
            }


            .frame(maxWidth: .infinity, alignment: .topLeading)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    private var recordingPromptBinding: Binding<Bool> {
        Binding(
            get: { settings.detectionMode == .detectAndAsk },
            set: { enabled in
                updateSettings { draft in
                    draft.detectionMode = enabled ? .detectAndAsk : .detectOnly
                }
            }
        )
    }

    private var assistedAutoStartBinding: Binding<Bool> {
        Binding(
            get: { settings.allowsAssistedAutoStart(policy: currentPolicy) },
            set: { enabled in
                updateSettings { draft in
                    if enabled, let policy = currentPolicy, policy.isActive() {
                        draft.assistedAutoStartAcknowledgement = AssistedAutoStartAcknowledgement(
                            policyRef: policy.policyRef,
                            subjectRef: policy.acknowledgementSubjectRef,
                            deviceRef: policy.deviceRef,
                            acknowledgementVersion: policy.acknowledgementVersion
                        )
                    } else {
                        draft.assistedAutoStartAcknowledgement = nil
                    }
                }
            }
        )
    }

    private var assistedAutoStartPolicyStatus: String {
        guard let policy = currentPolicy, policy.isActive() else {
            return "Политика workspace не разрешает автозапуск. Ручная запись доступна отдельно."
        }
        if settings.allowsAssistedAutoStart(policy: policy) {
            return "Разрешено по правилам \(policy.policyVersion) до \(policy.expiresAt.formatted(date: .abbreviated, time: .omitted))."
        }
        return "Нужно ваше явное разрешение для правил \(policy.policyVersion)."
    }

    private func autoRecordBinding(for targetID: String) -> Binding<Bool> {
        Binding(
            get: { settings.autoRecordTargetIds.contains(targetID) },
            set: { enabled in
                updateSettings { draft in
                    if enabled {
                        draft.autoRecordTargetIds.insert(targetID)
                    } else {
                        draft.autoRecordTargetIds.remove(targetID)
                    }
                    draft.targetScopedAutoRecordEnabled = !draft.autoRecordTargetIds.isEmpty
                }
            }
        )
    }

    private func selectAllAutoRecordTargets() {
        updateSettings { draft in
            draft.autoRecordTargetIds = Set(promptCapableTargets.map(\.id))
            draft.targetScopedAutoRecordEnabled = !draft.autoRecordTargetIds.isEmpty
        }
    }

    private func clearAutoRecordTargets() {
        updateSettings { draft in
            draft.autoRecordTargetIds.removeAll()
            draft.targetScopedAutoRecordEnabled = false
        }
    }

    private func updateSettings(_ transform: (inout MeetingDetectionSettings) -> Void) {
        var draft = settings
        transform(&draft)
        do {
            try store.save(draft)
            settings = draft
            saveError = nil
            notificationCenter.post(name: .twoBrainRecMeetingDetectionSettingsDidChange, object: nil)
        } catch {
            saveError = "Настройки временно не сохранены"
        }
    }

    private func reloadSettings() {
        guard let loaded = try? store.load() else {
            saveError = "Настройки временно недоступны"
            return
        }
        settings = loaded
        saveError = nil
    }

    private func reloadRegistryTargets() {
        guard let registry = try? registryStore.loadCache().registry else {
            promptCapableTargets = []
            currentPolicy = nil
            return
        }
        currentPolicy = registry.assistedAutoStartPolicy
        promptCapableTargets = Self.promptCapableTargets(in: registry)
    }

    private static func loadPromptCapableTargets(
        from registryStore: MeetingTargetRegistryStore
    ) -> [MeetingTargetRegistryTarget] {
        guard let registry = try? registryStore.loadCache().registry else {
            return []
        }
        return promptCapableTargets(in: registry)
    }

    private static func promptCapableTargets(
        in registry: MeetingTargetRegistryDocument
    ) -> [MeetingTargetRegistryTarget] {
        return registry.targets
            .filter(\.isVerifiedNativePromptTarget)
            .sorted { $0.displayName.localizedCaseInsensitiveCompare($1.displayName) == .orderedAscending }
    }
}
