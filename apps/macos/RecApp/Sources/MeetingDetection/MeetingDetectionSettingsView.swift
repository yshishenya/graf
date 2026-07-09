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
    public static let autoRecordSectionTitle = "Приложения"
    public static let autoRecordSectionDetail =
        "Отмеченные приложения пишутся автоматически. Остальные будут спрашивать перед записью."
    public static let selectAllTitle = "Выбрать все"
    public static let clearAllTitle = "Снять все"

    private let store: MeetingDetectionSettingsStore
    private let registryStore: MeetingTargetRegistryStore
    private let notificationCenter: NotificationCenter

    @State private var settings: MeetingDetectionSettings
    @State private var promptCapableTargets: [MeetingTargetRegistryTarget] = []
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
        VStack(alignment: .leading, spacing: 28) {
            Label(Self.pageTitle, systemImage: "dot.radiowaves.left.and.right")
                .font(.headline)

            VStack(alignment: .leading, spacing: 8) {
                HStack(alignment: .firstTextBaseline, spacing: 12) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(Self.promptToggleTitle)
                            .font(.subheadline)
                            .fontWeight(.semibold)
                        Text(Self.promptToggleDetail)
                            .font(.callout)
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    Spacer()
                    Toggle("", isOn: recordingPromptBinding)
                        .toggleStyle(.switch)
                        .labelsHidden()
                        .accessibilityLabel(Self.promptToggleTitle)
                        .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.meetingDetectionRecordingToggle)
                }
            }

            Divider()

            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .firstTextBaseline) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(Self.autoRecordSectionTitle)
                            .font(.subheadline)
                            .fontWeight(.semibold)
                        Text(Self.autoRecordSectionDetail)
                            .font(.callout)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    Button(Self.selectAllTitle, action: selectAllAutoRecordTargets)
                        .disabled(promptCapableTargets.isEmpty)
                    Button(Self.clearAllTitle, action: clearAutoRecordTargets)
                        .disabled(settings.autoRecordTargetIds.isEmpty)
                }

                if promptCapableTargets.isEmpty {
                    Text("Список появится после загрузки реестра.")
                        .font(.callout)
                        .foregroundStyle(.secondary)
                } else {
                    VStack(alignment: .leading, spacing: 8) {
                        ForEach(promptCapableTargets, id: \.id) { target in
                            Toggle(isOn: autoRecordBinding(for: target.id)) {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(target.displayName)
                                        .font(.callout)
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

            if let saveError {
                Label(saveError, systemImage: "exclamationmark.triangle.fill")
                    .font(.callout)
                    .foregroundStyle(.orange)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Spacer()
        }
        .padding(.horizontal, 34)
        .padding(.vertical, 28)
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
        promptCapableTargets = Self.loadPromptCapableTargets(from: registryStore)
    }

    private static func loadPromptCapableTargets(
        from registryStore: MeetingTargetRegistryStore
    ) -> [MeetingTargetRegistryTarget] {
        guard let registry = try? registryStore.loadCache().registry else {
            return []
        }
        return registry.targets
            .filter { target in
                target.mode == .promptEnabled &&
                    target.platform == .macos &&
                    target.targetFamily == .nativeApp
            }
            .sorted { $0.displayName.localizedCaseInsensitiveCompare($1.displayName) == .orderedAscending }
    }
}
