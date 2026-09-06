import AppKit
import SwiftUI
import TwoBrainRecShared

public struct MeetingDetectionSettingsView: View {
    public static let windowTitle = "Настройки"
    public static let windowSize = NSSize(width: 820, height: 600)
    public static let sidebarTitle = "Встречи"
    public static let pageTitle = "Автозапись"
    public static let autoRecordSectionTitle = "Приложения"
    public static let applyToAllTitle = "Для всех приложений"
    private let store: MeetingDetectionSettingsStore
    private let registryStore: MeetingTargetRegistryStore
    private let notificationCenter: NotificationCenter

    @State private var settings: MeetingDetectionSettings
    @State private var promptCapableTargets: [MeetingTargetRegistryTarget] = []
    @State private var saveError: String?

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
        _settings = State(initialValue: (try? store.load()) ?? MeetingDetectionSettings())
        _promptCapableTargets = State(initialValue: Self.loadPromptCapableTargets(from: registryStore))
    }

    public var body: some View {
        HStack(spacing: 0) {
            sidebar
            Divider()
            content
        }
        .frame(width: Self.windowSize.width, height: Self.windowSize.height)
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
                Task { @MainActor in
                    NSApp.keyWindow?.close()
                }
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
                        Text(Self.applyToAllTitle)
                            .fontWeight(.medium)
                        AutomaticRecordingRulePicker(
                            title: Self.applyToAllTitle,
                            selection: bulkRuleBinding,
                            isDisabled: promptCapableTargets.isEmpty
                        )
                        if !promptCapableTargets.isEmpty && bulkRuleBinding.wrappedValue == nil {
                            Text("Для приложений выбраны разные правила.")
                                .font(.callout)
                                .foregroundStyle(.secondary)
                        }
                    }

                    Divider()
                    if promptCapableTargets.isEmpty {
                        Text("Список приложений пока недоступен. Попробуйте открыть настройки позже.")
                            .font(.callout)
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                    } else {
                        ForEach(promptCapableTargets, id: \.id) { target in
                            HStack(spacing: 12) {
                                Image(systemName: "app.dashed")
                                    .foregroundStyle(.secondary)
                                    .frame(width: 20)
                                    .accessibilityHidden(true)
                                Text(target.displayName)
                                    .fontWeight(.medium)
                                    .fixedSize(horizontal: false, vertical: true)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                AutomaticRecordingRulePicker(
                                    title: target.displayName,
                                    selection: ruleBinding(for: target.id)
                                )
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
            saveError = nil
            notificationCenter.post(name: .twoBrainRecMeetingDetectionSettingsDidChange, object: nil)
        } catch {
            saveError = "Изменения не сохранены. Прежние правила остаются в силе. Попробуйте ещё раз."
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
    @State private var hoveredRule: AutomaticRecordingRule?

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
        HStack(spacing: 6) {
            ForEach(AutomaticRecordingRule.allCases, id: \.self) { rule in
                Button {
                    selection = rule
                } label: {
                    HStack(spacing: 5) {
                        Image(systemName: selection == rule ? "checkmark.circle.fill" : rule.symbolName)
                        Text(rule.displayName)
                            .lineLimit(1)
                            .minimumScaleFactor(0.8)
                    }
                    .font(.callout)
                    .frame(width: 104, height: 40)
                    .foregroundStyle(selection == rule ? Color.black : Color.primary)
                    .background(
                        selection == rule
                            ? DesktopMeetingShellChrome.shellAccentColor
                            : hoveredRule == rule ? DesktopMeetingShellChrome.shellAccentColor.opacity(0.12) : Color.clear,
                        in: RoundedRectangle(cornerRadius: 10)
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 10)
                            .stroke(
                                selection == rule
                                    ? DesktopMeetingShellChrome.shellAccentColor
                                    : hoveredRule == rule
                                        ? DesktopMeetingShellChrome.shellAccentColor.opacity(0.55)
                                        : Color.secondary.opacity(0.25),
                                lineWidth: 1
                            )
                    )
                }
                .buttonStyle(.plain)
                .disabled(isDisabled)
                .onHover { isHovering in
                    hoveredRule = isHovering ? rule : nil
                }
                .accessibilityLabel("\(title): \(rule.displayName)")
                .accessibilityHint(isDisabled ? "Недоступно" : "Выберите состояние автозаписи")
                .accessibilityAddTraits(selection == rule ? .isSelected : [])
            }
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel(title)
        .accessibilityValue(selection?.displayName ?? "Разные")
    }
}

private extension AutomaticRecordingRule {
    var symbolName: String {
        switch self {
        case .always: return "record.circle"
        case .ask: return "questionmark.circle"
        case .never: return "nosign"
        }
    }
}
