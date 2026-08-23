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
        "Разрешает автоматический запуск после 8-секундного таймера, если действуют политика и разрешения workspace."
    public static let autoRecordSectionTitle = "Приложения"
    public static let applyToAllTitle = "Для всех приложений"
    public static let technicalHintIcon = "info.circle"
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
                        technicalToggle(
                            title: Self.assistedAutoStartTitle,
                            detail: "\(Self.assistedAutoStartDetail)\n\n\(assistedAutoStartPolicyStatus)",
                            binding: assistedAutoStartBinding,
                            isDisabled: currentPolicy?.isActive() != true
                        )
                        .toggleStyle(.switch)

                        technicalToggle(
                            title: Self.promptToggleTitle,
                            detail: Self.promptToggleDetail,
                            binding: recordingPromptBinding
                        )
                        .toggleStyle(.switch)
                        .accessibilityIdentifier(SystemAudioAccessibilityIdentifier.meetingDetectionRecordingToggle)
                    }

                    Section(header: Text(Self.autoRecordSectionTitle).fontWeight(.medium)) {
                        AutomaticRecordingRulePicker(
                            title: Self.applyToAllTitle,
                            selection: bulkRuleBinding,
                            isDisabled: promptCapableTargets.isEmpty
                        )

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

    private func technicalToggle(
        title: String,
        detail: String,
        binding: Binding<Bool>,
        isDisabled: Bool = false
    ) -> some View {
        HStack(spacing: 8) {
            Toggle(title, isOn: binding)
                .fontWeight(.medium)
                .disabled(isDisabled)
                .accessibilityLabel(title)
            TechnicalHintView(detail: detail)
                .frame(width: 20, height: 20)
                .accessibilityLabel("Подробнее о настройке")
                .accessibilityHint(detail)
        }
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

private struct TechnicalHintView: NSViewRepresentable {
    let detail: String

    func makeNSView(context: Context) -> TechnicalHintNSView {
        let view = TechnicalHintNSView(detail: detail)
        return view
    }

    func updateNSView(_ nsView: TechnicalHintNSView, context: Context) {
        nsView.detail = detail
    }
}

@MainActor
private final class TechnicalHintNSView: NSImageView {
    var detail: String {
        didSet { updatePopoverContent() }
    }

    private var hintPopover: NSPopover?
    private var showHintWorkItem: DispatchWorkItem?

    init(detail: String) {
        self.detail = detail
        super.init(frame: .zero)
        image = NSImage(
            systemSymbolName: MeetingDetectionSettingsView.technicalHintIcon,
            accessibilityDescription: "Подробнее о настройке"
        )
        imageScaling = .scaleProportionallyUpOrDown
        contentTintColor = .secondaryLabelColor
        setAccessibilityLabel("Подробнее о настройке")
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    override func updateTrackingAreas() {
        trackingAreas.forEach(removeTrackingArea)
        addTrackingArea(
            NSTrackingArea(
                rect: bounds,
                options: [.mouseEnteredAndExited, .activeAlways, .inVisibleRect],
                owner: self,
                userInfo: nil
            )
        )
        super.updateTrackingAreas()
    }

    override func mouseEntered(with event: NSEvent) {
        super.mouseEntered(with: event)
        showHintWorkItem?.cancel()
        let workItem = DispatchWorkItem { [weak self] in
            self?.presentHintPopover()
        }
        showHintWorkItem = workItem
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.35, execute: workItem)
    }

    override func hitTest(_ point: NSPoint) -> NSView? {
        bounds.contains(point) ? self : nil
    }

    override func mouseExited(with event: NSEvent) {
        super.mouseExited(with: event)
        showHintWorkItem?.cancel()
        hintPopover?.performClose(nil)
        hintPopover = nil
    }

    private func presentHintPopover() {
        guard window != nil, hintPopover == nil else { return }

        let font = NSFont.systemFont(ofSize: NSFont.smallSystemFontSize)
        let textBounds = (detail as NSString).boundingRect(
            with: NSSize(width: 280, height: CGFloat.greatestFiniteMagnitude),
            options: [.usesLineFragmentOrigin, .usesFontLeading],
            attributes: [.font: font]
        )
        let contentSize = NSSize(
            width: 304,
            height: max(44, ceil(textBounds.height) + 24)
        )

        let label = NSTextField(wrappingLabelWithString: detail)
        label.font = font
        label.textColor = .labelColor
        label.translatesAutoresizingMaskIntoConstraints = false

        let container = NSView()
        container.addSubview(label)
        NSLayoutConstraint.activate([
            label.leadingAnchor.constraint(equalTo: container.leadingAnchor, constant: 12),
            label.trailingAnchor.constraint(equalTo: container.trailingAnchor, constant: -12),
            label.topAnchor.constraint(equalTo: container.topAnchor, constant: 12),
            label.bottomAnchor.constraint(equalTo: container.bottomAnchor, constant: -12)
        ])

        let controller = NSViewController()
        controller.view = container
        controller.preferredContentSize = contentSize

        let popover = NSPopover()
        popover.behavior = .transient
        popover.animates = false
        popover.contentViewController = controller
        hintPopover = popover
        popover.show(relativeTo: bounds, of: self, preferredEdge: .minX)
    }

    private func updatePopoverContent() {
        hintPopover?.performClose(nil)
        hintPopover = nil
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
        HStack(spacing: 6) {
            ForEach(AutomaticRecordingRule.allCases, id: \.self) { rule in
                Button {
                    selection = rule
                } label: {
                    HStack(spacing: 5) {
                        Image(systemName: selection == rule ? "largecircle.fill.circle" : "circle")
                            .imageScale(.small)
                        Text(rule.displayName)
                            .lineLimit(1)
                            .minimumScaleFactor(0.8)
                    }
                    .font(.callout)
                    .frame(width: 112)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 7)
                    .background(
                        selection == rule
                            ? Color.accentColor.opacity(0.16)
                            : Color.clear,
                        in: RoundedRectangle(cornerRadius: 7)
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 7)
                            .stroke(
                                selection == rule ? Color.accentColor : Color.secondary.opacity(0.25),
                                lineWidth: 1
                            )
                    )
                }
                .buttonStyle(.plain)
                .disabled(isDisabled)
                .accessibilityAddTraits(selection == rule ? .isSelected : [])
            }
        }
        .accessibilityLabel(title)
        .accessibilityValue(selection?.displayName ?? "Разные")
        .accessibilityHint(isDisabled ? "Недоступно" : "Выберите состояние автозаписи")
    }
}
