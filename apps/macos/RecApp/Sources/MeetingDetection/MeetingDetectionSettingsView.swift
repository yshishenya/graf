import AppKit
import SwiftUI
import TwoBrainRecShared

public struct MeetingDetectionSettingsView: View {
    public static let windowTitle = "Настройки"
    public static let windowSize = NSSize(width: 1040, height: 800)
    public static let pageTitle = "Запись встреч"
    public static let autoRecordSectionTitle = "Автозапись для приложений"
    public static let applyToAllTitle = "Для всех приложений"
    private let store: MeetingDetectionSettingsStore
    private let registryStore: MeetingTargetRegistryStore
    private let notificationCenter: NotificationCenter

    @State private var settings: MeetingDetectionSettings
    @State private var promptCapableTargets: [MeetingTargetRegistryTarget] = []
    @State private var saveError: String?
    @State private var pendingRules: [String: AutomaticRecordingRule] = [:]
    @State private var search = ""
    @State private var settingsAvailable: Bool

    public init(
        store: MeetingDetectionSettingsStore = MeetingDetectionSettingsStore(),
        registryStore: MeetingTargetRegistryStore = MeetingTargetRegistryStore(
            cacheURL: MeetingDetectionAppModule.targetRegistryCacheURL(),
            bundledRegistryURL: MeetingDetectionAppModule.bundledTargetRegistryURL
        ),
        notificationCenter: NotificationCenter = .default
    ) {
        self.store = store
        self.registryStore = registryStore
        self.notificationCenter = notificationCenter
        let loaded = try? store.load()
        _settings = State(initialValue: loaded ?? MeetingDetectionSettings())
        _settingsAvailable = State(initialValue: loaded != nil)
        _promptCapableTargets = State(initialValue: Self.loadPromptCapableTargets(from: registryStore))
    }

    public var body: some View {
        content
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(nsColor: .windowBackgroundColor))
        .tint(DesktopMeetingShellChrome.shellAccentColor)
        .onAppear {
            reloadSettings()
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

    private var filteredTargets: [MeetingTargetRegistryTarget] {
        promptCapableTargets.filter { NativeSettingsComboBox.matchesSearch($0.displayName, query: search) }
    }

    private var content: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                VStack(alignment: .leading, spacing: 10) {
                    Text(Self.pageTitle)
                        .font(.title2.weight(.semibold))
                        .foregroundStyle(.primary)
                    Text("«Спрашивать»: запись начнется через 8 секунд, если не отказаться.")
                }
                .font(.callout)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)

                if let saveError {
                    HStack {
                        Text(saveError).foregroundStyle(DesktopDesignTokens.red)
                        Button("Повторить") {
                            if pendingRules.isEmpty { reloadSettings() } else { updateRules(pendingRules) }
                        }
                        .frame(minHeight: 40)
                    }.font(.callout)
                }
                VStack(alignment: .leading, spacing: 16) {
                    Text(Self.autoRecordSectionTitle)
                        .font(.headline)

                    VStack(alignment: .leading, spacing: 8) {
                        HStack(spacing: 12) {
                            Text(Self.applyToAllTitle)
                                .fontWeight(.medium)
                                .frame(maxWidth: .infinity, alignment: .leading)
                            AutomaticRecordingRulePicker(
                                title: Self.applyToAllTitle,
                                selection: bulkRuleBinding,
                                isDisabled: promptCapableTargets.isEmpty || !settingsAvailable
                            )
                        }
                        if !promptCapableTargets.isEmpty && bulkRuleBinding.wrappedValue == nil {
                            Text("Для приложений выбраны разные правила.")
                                .font(.callout)
                                .foregroundStyle(.secondary)
                        }
                    }

                    NativeSettingsComboBox(
                        title: "Приложения",
                        options: promptCapableTargets.map { .init(id: $0.id, label: $0.displayName) },
                        placeholder: "Выберите приложение или начните вводить",
                        filter: $search
                    )
                    .frame(maxWidth: 380)
                    .frame(height: 32)
                    Divider()
                    if promptCapableTargets.isEmpty {
                        Text("Список приложений пока недоступен. Попробуйте открыть настройки позже.")
                            .font(.callout)
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                        Button("Повторить загрузку") { reloadRegistryTargets() }
                            .frame(minHeight: 40)
                    } else if filteredTargets.isEmpty {
                        Text("Приложения не найдены. Измените поиск.").foregroundStyle(.secondary)
                    } else {
                        VStack(spacing: 0) {
                            ForEach(filteredTargets, id: \.id) { target in
                                HStack(spacing: 12) {
                                    Text(target.displayName)
                                        .fontWeight(.medium)
                                        .fixedSize(horizontal: false, vertical: true)
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                    AutomaticRecordingRulePicker(
                                        title: target.displayName,
                                        selection: ruleBinding(for: target.id),
                                        isDisabled: promptCapableTargets.isEmpty || !settingsAvailable
                                    )
                                }
                                .frame(minHeight: 40)
                                if target.id != filteredTargets.last?.id {
                                    Divider()
                                }
                            }
                        }
                    }
                }
            }
            .padding(24)
            .frame(maxWidth: .infinity, alignment: .topLeading)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    private var bulkRuleBinding: Binding<AutomaticRecordingRule?> {
        Binding(
            get: {
                let rules = promptCapableTargets.map { pendingRules[$0.id] ?? settings.recordingRule(for: $0.id) }
                guard let first = rules.first, rules.allSatisfy({ $0 == first }) else { return nil }
                return first
            },
            set: { rule in
                guard let rule else { return }
                updateRules(Dictionary(uniqueKeysWithValues: promptCapableTargets.map { ($0.id, rule) }))
            }
        )
    }

    private func ruleBinding(for targetID: String) -> Binding<AutomaticRecordingRule> {
        Binding(
            get: { pendingRules[targetID] ?? settings.recordingRule(for: targetID) },
            set: { rule in
                updateRules([targetID: rule])
            }
        )
    }

    private func updateRules(_ changes: [String: AutomaticRecordingRule]) {
        let changes = pendingRules.merging(changes) { _, latest in latest }
        do {
            settings = try store.update { draft in
                for (targetID, rule) in changes { draft.setRecordingRule(rule, for: targetID) }
            }
            pendingRules = [:]
            settingsAvailable = true
            saveError = nil
            notificationCenter.post(name: .twoBrainRecMeetingDetectionSettingsDidChange, object: nil)
        } catch {
            pendingRules = changes
            saveError = "Не сохранено. Повторите попытку."
        }
    }

    private func reloadSettings() {
        guard let loaded = try? store.load() else {
            settingsAvailable = false
            saveError = "Настройки временно недоступны"
            return
        }
        settings = loaded
        settingsAvailable = true
        if pendingRules.isEmpty { saveError = nil }
    }

    private func reloadRegistryTargets() {
        guard let registry = try? registryStore.resolve().document else {
            promptCapableTargets = []
            return
        }
        promptCapableTargets = Self.promptCapableTargets(in: registry)
    }

    private static func loadPromptCapableTargets(
        from registryStore: MeetingTargetRegistryStore
    ) -> [MeetingTargetRegistryTarget] {
        guard let registry = try? registryStore.resolve().document else {
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

private struct AutomaticRecordingRulePicker: View {
    let title: String
    @Binding var selection: AutomaticRecordingRule?
    var isDisabled = false

    init(
        title: String,
        selection: Binding<AutomaticRecordingRule>,
        isDisabled: Bool = false
    ) {
        self.title = title
        _selection = Binding(
            get: { selection.wrappedValue },
            set: { selection.wrappedValue = $0 ?? .ask }
        )
        self.isDisabled = isDisabled
    }

    init(
        title: String,
        selection: Binding<AutomaticRecordingRule?>,
        isDisabled: Bool = false
    ) {
        self.title = title
        _selection = selection
        self.isDisabled = isDisabled
    }

    var body: some View {
        NativeSettingsComboBox(
            title: title,
            options: AutomaticRecordingRule.allCases.map { rule in
                .init(id: rule.rawValue, label: rule.displayName)
            },
            selectedID: selection?.rawValue,
            placeholder: selection?.displayName ?? "Разные правила"
        ) { value in
            guard let rule = AutomaticRecordingRule(rawValue: value) else { return }
            selection = rule
        }
        .frame(width: 172, height: 32)
        .disabled(isDisabled)
    }
}

/// Local controls remain reachable while the cabinet is unavailable.
public enum LocalSettingsSection: String, CaseIterable, Equatable, Sendable {
    case account
    case recording
    case notifications
    case calendar
    case billing

    public var title: String {
        switch self {
        case .account: "Аккаунт"
        case .recording: "Запись"
        case .notifications: "Уведомления"
        case .calendar: "Календарь"
        case .billing: "Биллинг"
        }
    }

    public var isAvailableLocally: Bool {
        self == .recording || self == .notifications
    }

    public var unavailableMessage: String {
        switch self {
        case .account:
            "Аккаунт, вход и устройства доступны в кабинете GRAF."
        case .calendar:
            "Календарь и подключение провайдеров доступны в кабинете GRAF."
        case .billing:
            "Тариф, оплата и история платежей доступны в кабинете GRAF."
        case .recording, .notifications:
            ""
        }
    }
}

public struct LocalSettingsFallbackView: View {
    @State private var selected: LocalSettingsSection
    @ScaledMetric(relativeTo: .body) private var sidebarWidth: CGFloat = 208
    private let onOpenAll: () -> Void

    public init(section: String, onOpenAll: @escaping () -> Void) {
        selected = LocalSettingsSection(rawValue: section) ?? .recording
        self.onOpenAll = onOpenAll
    }

    public init(notifications: Bool, onOpenAll: @escaping () -> Void) {
        self.init(section: notifications ? "notifications" : "recording", onOpenAll: onOpenAll)
    }

    public var body: some View {
        HStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 12) {
                Button(action: onOpenAll) {
                    Label("Все настройки GRAF", systemImage: "chevron.left")
                }
                .buttonStyle(.plain)
                .frame(minHeight: 40)

                Text("На этом Mac")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .padding(.top, 16)

                ForEach([LocalSettingsSection.recording, .notifications], id: \.rawValue) { section in
                    Button {
                        selected = section
                    } label: {
                        Label(section.title, systemImage: section == .notifications ? "bell" : "record.circle")
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(10)
                            .background(
                                selected == section ? DesktopDesignTokens.accentSurface : .clear,
                                in: RoundedRectangle(cornerRadius: DesktopDesignTokens.Radius.xs)
                            )
                    }
                    .buttonStyle(.plain)
                    .frame(minHeight: 40)
                    .accessibilityAddTraits(selected == section ? .isSelected : [])
                }

                Spacer()

                Text("Кабинет недоступен. Локальные настройки продолжают работать.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(16)
            .frame(width: min(max(sidebarWidth, 208), 280))
            .frame(maxHeight: .infinity)
            .background(DesktopDesignTokens.surface2)

            Divider()

            content
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .accessibilityIdentifier("desktop.localSettingsFallback")
    }

    @ViewBuilder
    private var content: some View {
        if selected.isAvailableLocally {
            if selected == .notifications {
                DesktopNotificationsSettingsView()
            } else {
                MeetingDetectionSettingsView()
            }
        } else {
            unavailableSection
        }
    }

    private var unavailableSection: some View {
        VStack(alignment: .center, spacing: 16) {
            Image(systemName: "lock.trianglebadge.exclamationmark")
                .font(.system(size: 26, weight: .semibold))
                .foregroundStyle(DesktopDesignTokens.amber)
            Text(selected.title)
                .font(.title3.weight(.semibold))
            Text(selected.unavailableMessage)
                .font(.callout)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: 420)
            HStack(spacing: 12) {
                Button("Повторить") {
                    onOpenAll()
                }
                .buttonStyle(DesktopWebButtonStyle(.primary))
                .frame(minHeight: 40)
                Button("Локальные настройки") {
                    selected = .recording
                }
                .buttonStyle(DesktopWebButtonStyle(.secondary))
                .frame(minHeight: 40)
            }
        }
        .padding(24)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .accessibilityElement(children: .contain)
    }
}
