import AppKit
import SwiftUI
import TwoBrainRecShared

public struct MeetingDetectionSettingsView: View {
    public static let windowTitle = "Настройки"
    public static let windowSize = NSSize(width: 820, height: 600)
    public static let pageTitle = "Автозапись"
    public static let autoRecordSectionTitle = "Приложения"
    public static let applyToAllTitle = "Для всех приложений"
    private let store: MeetingDetectionSettingsStore
    private let registryStore: MeetingTargetRegistryStore
    private let notificationCenter: NotificationCenter

    @State private var settings: MeetingDetectionSettings
    @State private var promptCapableTargets: [MeetingTargetRegistryTarget] = []
    @State private var saveError: String?
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
        .alert("Не удалось обновить настройки", isPresented: Binding(
            get: { saveError != nil },
            set: { if !$0 { saveError = nil } }
        )) {
            Button("Понятно", role: .cancel) { saveError = nil }
        } message: {
            Text(saveError ?? "Попробуйте ещё раз.")
        }
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
        promptCapableTargets.filter { search.isEmpty || $0.displayName.localizedStandardContains(search) }
    }

    private var content: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                VStack(alignment: .leading, spacing: 10) {
                    Text(Self.pageTitle)
                        .font(.title2.weight(.semibold))
                        .foregroundStyle(.primary)
                    Text("Выберите, как начинать запись встреч в каждом приложении на этом Mac.")
                    Text("Всегда — без запроса. Спрашивать — показать запрос и начать запись через 8 секунд, если вы не откажетесь. Никогда — не начинать автоматически.")
                    Text("Изменения сохраняются автоматически. Ручная запись остаётся доступна.")
                }
                .font(.callout)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)

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

                    Text("Поддерживаемые приложения на macOS. Общее правило применяется ко всем, включая скрытые поиском.")
                        .font(.callout).foregroundStyle(.secondary)
                    NativeSettingsComboBox(
                        title: "Приложения",
                        options: promptCapableTargets.map { .init(id: $0.id, label: $0.displayName) },
                        placeholder: "Выберите приложение или начните вводить",
                        filter: $search
                    )
                    .frame(height: 32)
                    Divider()
                    if !settingsAvailable {
                        Text("Не удалось прочитать сохранённые правила.").foregroundStyle(.secondary)
                        Button("Повторить загрузку") { reloadSettings() }
                    } else if promptCapableTargets.isEmpty {
                        Text("Список приложений пока недоступен. Попробуйте открыть настройки позже.")
                            .font(.callout)
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                        Button("Повторить загрузку") { reloadRegistryTargets() }
                    } else if filteredTargets.isEmpty {
                        Text("Приложения не найдены. Измените поиск.").foregroundStyle(.secondary)
                    } else {
                        ForEach(filteredTargets, id: \.id) { target in
                            HStack(spacing: 12) {
                                Text(target.displayName)
                                    .fontWeight(.medium)
                                    .fixedSize(horizontal: false, vertical: true)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                AutomaticRecordingRulePicker(
                                    title: target.displayName,
                                    selection: ruleBinding(for: target.id)
                                )
                            }
                            .frame(minHeight: 48)
                            Divider()
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
                let rules = promptCapableTargets.map { settings.recordingRule(for: $0.id) }
                guard let first = rules.first, rules.allSatisfy({ $0 == first }) else { return nil }
                return first
            },
            set: { rule in
                guard let rule else { return }
                updateSettings { draft in
                    for target in promptCapableTargets {
                        draft.setRecordingRule(rule, for: target.id)
                    }
                }
            }
        )
    }

    private func ruleBinding(for targetID: String) -> Binding<AutomaticRecordingRule> {
        Binding(
            get: { settings.recordingRule(for: targetID) },
            set: { rule in
                updateSettings { draft in
                    draft.setRecordingRule(rule, for: targetID)
                }
            }
        )
    }

    private func updateSettings(_ transform: (inout MeetingDetectionSettings) -> Void) {
        do {
            settings = try store.update(transform)
            settingsAvailable = true
            saveError = nil
            notificationCenter.post(name: .twoBrainRecMeetingDetectionSettingsDidChange, object: nil)
        } catch {
            saveError = "Изменения не сохранены. Прежние правила остаются в силе. Попробуйте ещё раз."
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
        saveError = nil
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
        .accessibilityLabel(title)
        .accessibilityValue(selection?.displayName ?? "Разные правила")
    }
}

/// Local controls remain reachable while the cabinet is unavailable.
public struct LocalSettingsFallbackView: View {
    @State private var notifications: Bool
    private let onOpenAll: () -> Void
    public init(notifications: Bool, onOpenAll: @escaping () -> Void) {
        _notifications = State(initialValue: notifications)
        self.onOpenAll = onOpenAll
    }
    public var body: some View {
        HStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 12) {
                Button(action: onOpenAll) { Label("Все настройки GRAF", systemImage: "chevron.left") }
                    .buttonStyle(.plain)
                Text("На этом Mac").font(.caption).foregroundStyle(.secondary).padding(.top, 16)
                ForEach([false, true], id: \.self) { item in
                    Button { notifications = item } label: {
                        Label(item ? "Уведомления" : "Запись", systemImage: item ? "bell" : "record.circle")
                            .frame(maxWidth: .infinity, alignment: .leading).padding(10)
                            .background(notifications == item ? Color.accentColor.opacity(0.15) : .clear, in: RoundedRectangle(cornerRadius: 6))
                    }
                    .buttonStyle(.plain)
                    .accessibilityAddTraits(notifications == item ? .isSelected : [])
                }
                Spacer()
                Text("Кабинет недоступен. Локальные настройки продолжают работать.")
                    .font(.caption).foregroundStyle(.secondary)
            }.padding(16).frame(width: 208).frame(maxHeight: .infinity).background(.bar)
            Divider()
            if notifications { DesktopNotificationsSettingsView() }
            else { MeetingDetectionSettingsView() }
        }
    }
}
