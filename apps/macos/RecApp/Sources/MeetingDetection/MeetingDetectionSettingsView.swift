import AppKit
import SwiftUI
import TwoBrainRecShared

public struct MeetingDetectionSettingsView: View {
    public static let windowTitle = "Настройки"
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
            VStack(alignment: .leading, spacing: 28) {
                Label(Self.pageTitle, systemImage: "dot.radiowaves.left.and.right")
                    .font(.headline)

                Form {
                    Section(header: Text(Self.autoRecordSectionTitle).fontWeight(.medium)) {
                        VStack(alignment: .leading, spacing: 6) {
                            Text(Self.applyToAllTitle)
                                .font(.subheadline)
                                .fontWeight(.medium)
                            AutomaticRecordingRulePicker(
                                title: Self.applyToAllTitle,
                                selection: bulkRuleBinding,
                                isDisabled: promptCapableTargets.isEmpty
                            )
                        }

                        if promptCapableTargets.isEmpty {
                            Text("Список появится после загрузки реестра.")
                                .font(.callout)
                                .foregroundStyle(.secondary)
                        } else {
                            ForEach(promptCapableTargets, id: \.id) { target in
                                HStack(spacing: 12) {
                                    Image(systemName: "app.dashed")
                                        .foregroundStyle(.secondary)
                                        .frame(width: 20)
                                    Text(target.displayName)
                                        .fontWeight(.medium)
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
                        Image(systemName: rule.symbolName)
                        Text(rule.displayName)
                            .lineLimit(1)
                            .minimumScaleFactor(0.8)
                    }
                    .font(.callout)
                    .frame(width: 112, height: 38)
                    .foregroundStyle(selection == rule ? .white : .primary)
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
                .accessibilityAddTraits(selection == rule ? .isSelected : [])
            }
        }
        .accessibilityLabel(title)
        .accessibilityValue(selection?.displayName ?? "Разные")
        .accessibilityHint(isDisabled ? "Недоступно" : "Выберите состояние автозаписи")
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
