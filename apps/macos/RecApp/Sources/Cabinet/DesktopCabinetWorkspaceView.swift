import AppKit
import SwiftUI

public struct DesktopCabinetWorkspaceView: View {
    public static let workspaceTitle = "Встречи"
    public static let workspaceAccessibilityLabel = "Встречи и обзор записей"
    public static let embeddedSurfaceHeight: CGFloat = 420
    public static let shellEmbeddedSurfaceMinHeight: CGFloat = 520
    public static let embeddedWorkspaceMaxWidth: CGFloat = 1120

    private let configuration: DesktopCabinetConfiguration?
    private let initialRoute: URL?
    private let presentation: DesktopCabinetWorkspacePresentation
    private let workspaceZoom: WorkspaceZoomPreference
    private let navigationEventLogger: EmbeddedCabinetWebView.NavigationEventLogger?
    private let showsAppUpdateBadge: Bool
    private let onCheckForUpdates: EmbeddedCabinetWebView.CheckForUpdatesAction
    private let supportIncidentBridge: EmbeddedCabinetSupportIncidentBridge?
    private let externalCabinetState: Binding<DesktopCabinetState>?
    @StateObject private var navigationController = EmbeddedCabinetNavigationController()
    @State private var internalCabinetState: DesktopCabinetState
    @Binding private var currentRoute: URL?

    public init(
        configuration: DesktopCabinetConfiguration? = DesktopCabinetConfiguration.configuredFromEnvironment(),
        initialRoute: URL? = nil,
        currentRoute: Binding<URL?> = .constant(nil),
        cabinetState: Binding<DesktopCabinetState>? = nil,
        presentation: DesktopCabinetWorkspacePresentation = .card,
        workspaceZoom: WorkspaceZoomPreference = .default,
        navigationEventLogger: EmbeddedCabinetWebView.NavigationEventLogger? = nil,
        showsAppUpdateBadge: Bool = false,
        onCheckForUpdates: @escaping EmbeddedCabinetWebView.CheckForUpdatesAction = {},
        supportIncidentBridge: EmbeddedCabinetSupportIncidentBridge? = nil,
        initialState: DesktopCabinetState? = nil
    ) {
        let resolvedInitialState = initialState ?? (configuration == nil ? .notConfigured : .loading)
        self.configuration = configuration
        self.initialRoute = initialRoute
        self.presentation = presentation
        self.workspaceZoom = workspaceZoom
        self.navigationEventLogger = navigationEventLogger
        self.showsAppUpdateBadge = showsAppUpdateBadge
        self.onCheckForUpdates = onCheckForUpdates
        self.supportIncidentBridge = supportIncidentBridge
        self.externalCabinetState = cabinetState
        _internalCabinetState = State(initialValue: cabinetState?.wrappedValue ?? resolvedInitialState)
        _currentRoute = currentRoute
    }

    public var body: some View {
        Group {
            switch presentation {
            case .card:
                let stack = VStack(alignment: .leading, spacing: 12) {
                    header
                    content
                }
                .accessibilityElement(children: .contain)
                .accessibilityLabel(Self.workspaceAccessibilityLabel)
                .accessibilityIdentifier(DesktopCabinetAccessibilityIdentifier.workspace)

                stack
                    .padding(16)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(DesktopMeetingShellChrome.shellSurfaceColor)
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(DesktopMeetingShellChrome.shellStrokeColor, lineWidth: 1)
                    )
            case .shell:
                content
                    .accessibilityElement(children: .contain)
                    .accessibilityLabel(Self.workspaceAccessibilityLabel)
                    .accessibilityIdentifier(DesktopCabinetAccessibilityIdentifier.workspace)
                    .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            }
        }
        .background {
            DesktopCabinetNavigationTitlebarAccessory(
                controller: navigationController,
                isVisible: configuration != nil && shouldShowEmbeddedSurface
            )
            .frame(width: 0, height: 0)
        }
    }

    private var header: some View {
        HStack(alignment: .firstTextBaseline, spacing: 10) {
            Label(Self.workspaceTitle, systemImage: "rectangle.stack.fill")
                .font(.headline)
                .lineLimit(1)
                .minimumScaleFactor(0.85)
            Spacer()
            Text(statusText)
                .font(.caption)
                .foregroundStyle(statusColor)
                .lineLimit(1)
                .minimumScaleFactor(0.8)
        }
    }

    @ViewBuilder
    private var content: some View {
        if let configuration, shouldShowEmbeddedSurface {
            let route = currentRoute ?? initialRoute ?? configuration.meetingsURL()
            let webView = EmbeddedCabinetWebView(
                request: configuration.urlRequest(for: route),
                routePolicy: DesktopCabinetRoutePolicy(baseURL: configuration.baseURL),
                cabinetState: activeCabinetStateBinding,
                workspaceZoom: workspaceZoom,
                currentRoute: $currentRoute,
                navigationEventLogger: navigationEventLogger,
                showsAppUpdateBadge: showsAppUpdateBadge,
                onCheckForUpdates: onCheckForUpdates,
                supportIncidentBridge: supportIncidentBridge,
                fallbackRequest: configuration.urlRequest(for: configuration.meetingsURL()),
                navigationController: navigationController
            )
            .id(navigationController.sessionBoundaryID)
            .accessibilityIdentifier(DesktopCabinetAccessibilityIdentifier.embeddedSurface)

            switch presentation {
            case .card:
                webView
                    .frame(
                        maxWidth: .infinity,
                        minHeight: Self.embeddedSurfaceHeight,
                        maxHeight: Self.embeddedSurfaceHeight
                    )
            case .shell:
                webView
                    .frame(
                        maxWidth: .infinity,
                        minHeight: Self.shellEmbeddedSurfaceMinHeight,
                        maxHeight: .infinity
                    )
            }
        } else {
            unavailableState
        }
    }

    private var unavailableState: some View {
        VStack(alignment: .center, spacing: DesktopMeetingShellChrome.spacingMedium) {
            Label(activeCabinetState.unavailableTitle, systemImage: activeCabinetState.unavailableSystemImage)
                .font(.headline)
            Text(activeCabinetState.userMessage)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)
                .frame(maxWidth: 520)
            if let recoveryActionTitle, let recoveryTarget {
                HStack(spacing: DesktopMeetingShellChrome.spacingSmall) {
                    recoveryButton(
                        target: recoveryTarget,
                        title: recoveryActionTitle,
                        systemImage: activeCabinetState.recoverySystemImage,
                        prominent: true
                    )
                    if let homeRecoveryTarget {
                        recoveryButton(
                            target: homeRecoveryTarget,
                            title: "К списку встреч",
                            systemImage: "house",
                            prominent: false
                        )
                    }
                }
            }
        }
        .frame(
            maxWidth: .infinity,
            minHeight: presentation == .shell ? 360 : 160,
            maxHeight: presentation == .shell ? .infinity : nil,
            alignment: .center
        )
        .padding(presentation == .shell ? DesktopMeetingShellChrome.spacingXLarge : 14)
        .background(Color.secondary.opacity(presentation == .shell ? 0 : 0.08))
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .accessibilityElement(children: recoveryTarget == nil ? .combine : .contain)
        .accessibilityIdentifier(DesktopCabinetAccessibilityIdentifier.unavailableState)
    }

    private var recoveryTarget: DesktopCabinetRecoveryTarget? {
        guard let configuration else { return nil }
        return DesktopCabinetWorkspace.recoveryTarget(
            for: activeCabinetState,
            currentRoute: currentRoute,
            initialRoute: initialRoute,
            configuration: configuration
        )
    }

    private var recoveryActionTitle: String? {
        guard recoveryTarget != nil else { return nil }
        guard activeCabinetState == .blockedRoute else {
            return activeCabinetState.recoveryActionTitle
        }
        guard let configuration,
              let route = recoveryURL,
              route.path != configuration.meetingsURL().path
        else {
            return activeCabinetState.recoveryActionTitle
        }
        return "Вернуться"
    }

    private var recoveryURL: URL? {
        guard case let .embedded(url)? = recoveryTarget else { return nil }
        return url
    }

    private var shouldShowHomeRecovery: Bool {
        guard let configuration,
              let route = recoveryURL,
              route.path != configuration.meetingsURL().path
        else { return false }
        return [.offline, .timeout, .malformedResponse, .blockedRoute].contains(activeCabinetState)
    }

    private var homeRecoveryTarget: DesktopCabinetRecoveryTarget? {
        guard shouldShowHomeRecovery, let configuration else { return nil }
        return .embedded(configuration.meetingsURL())
    }

    private struct RecoveryButtonModifier: ViewModifier {
        let title: String
        let prominent: Bool

        func body(content: Content) -> some View {
            Group {
                if prominent {
                    content.buttonStyle(.borderedProminent)
                } else {
                    content.buttonStyle(.bordered)
                }
            }
            .controlSize(.regular)
            .frame(minHeight: DesktopMeetingShellChrome.minimumInteractiveTarget)
            .help(title)
            .accessibilityLabel(title)
        }
    }

    @ViewBuilder
    private func recoveryButton(
        target: DesktopCabinetRecoveryTarget,
        title: String,
        systemImage: String,
        prominent: Bool
    ) -> some View {
        switch target {
        case let .embedded(url):
            Button {
                currentRoute = url
                activeCabinetStateBinding.wrappedValue = .loading
            } label: {
                Label(title, systemImage: systemImage)
            }
            .modifier(RecoveryButtonModifier(title: title, prominent: prominent))
        case let .external(url):
            Link(destination: url) {
                Label(title, systemImage: "arrow.up.right.square")
            }
            .modifier(RecoveryButtonModifier(title: title, prominent: prominent))
        }
    }

    private var shouldShowEmbeddedSurface: Bool {
        DesktopCabinetWorkspace.shouldShowEmbeddedSurface(
            for: activeCabinetState,
            currentRoute: currentRoute,
            initialRoute: initialRoute,
            configuration: configuration
        )
    }

    private var statusText: String {
        switch activeCabinetState {
        case .ready:
            return "Готово"
        case .loading:
            return "Загрузка"
        case .notConfigured:
            return "Не подключено"
        case .expiredSession:
            return "Нужен вход"
        case .workspaceReselectionRequired:
            return "Выберите пространство"
        case .accessDenied:
            return "Нет доступа"
        case .notFound:
            return "Не найдено"
        case .offline, .timeout:
            return "Нет связи"
        case .blockedRoute:
            return "Ограничено"
        default:
            return "Требуется внимание"
        }
    }

    private var statusColor: Color {
        switch activeCabinetState {
        case .ready:
            return .green
        case .loading:
            return .secondary
        case .notConfigured:
            return .orange
        default:
            return .orange
        }
    }

    private var activeCabinetState: DesktopCabinetState {
        externalCabinetState?.wrappedValue ?? internalCabinetState
    }

    private var activeCabinetStateBinding: Binding<DesktopCabinetState> {
        externalCabinetState ?? $internalCabinetState
    }
}

public enum DesktopCabinetWorkspacePresentation: Equatable, Sendable {
    case card
    case shell
}

private struct DesktopCabinetNavigationTitlebarAccessory: NSViewRepresentable {
    @ObservedObject var controller: EmbeddedCabinetNavigationController
    let isVisible: Bool

    func makeNSView(context _: Context) -> DesktopCabinetNavigationTitlebarAccessoryAnchor {
        let anchor = DesktopCabinetNavigationTitlebarAccessoryAnchor()
        anchor.update(controller: controller, isVisible: isVisible)
        return anchor
    }

    func updateNSView(_ nsView: DesktopCabinetNavigationTitlebarAccessoryAnchor, context _: Context) {
        nsView.update(controller: controller, isVisible: isVisible)
    }

    static func dismantleNSView(
        _ nsView: DesktopCabinetNavigationTitlebarAccessoryAnchor,
        coordinator _: ()
    ) {
        nsView.removeAccessory()
    }
}

private final class DesktopCabinetNavigationTitlebarAccessoryAnchor: NSView {
    private weak var installedWindow: NSWindow?
    private var accessoryController: NSTitlebarAccessoryViewController?
    private var hostingView: NSHostingView<DesktopCabinetNavigationControls>?
    private var controller: EmbeddedCabinetNavigationController?
    private var isVisible = false

    func update(controller: EmbeddedCabinetNavigationController, isVisible: Bool) {
        self.controller = controller
        self.isVisible = isVisible
        syncAccessory()
    }

    override func viewDidMoveToWindow() {
        super.viewDidMoveToWindow()
        syncAccessory()
    }

    func removeAccessory() {
        guard let accessoryController else { return }
        if let installedWindow,
           let index = installedWindow.titlebarAccessoryViewControllers.firstIndex(where: { $0 === accessoryController }) {
            installedWindow.removeTitlebarAccessoryViewController(at: index)
        }
        self.accessoryController = nil
        hostingView = nil
        installedWindow = nil
    }

    private func syncAccessory() {
        guard isVisible, let window, let controller else {
            removeAccessory()
            return
        }
        if installedWindow !== window {
            removeAccessory()
        }

        let rootView = DesktopCabinetNavigationControls(controller: controller)
        let host = hostingView ?? NSHostingView(rootView: rootView)
        host.rootView = rootView
        host.frame = NSRect(
            x: 0,
            y: 0,
            width: DesktopCabinetNavigationControls.preferredWidth,
            height: DesktopCabinetNavigationControls.preferredHeight
        )
        hostingView = host

        if accessoryController == nil {
            let accessory = NSTitlebarAccessoryViewController()
            accessory.layoutAttribute = .left
            accessory.view = host
            accessoryController = accessory
            installedWindow = window
            window.addTitlebarAccessoryViewController(accessory)
        }
    }
}

private struct DesktopCabinetNavigationControls: View {
    static let preferredWidth: CGFloat = 136
    static let preferredHeight: CGFloat = 40

    @ObservedObject var controller: EmbeddedCabinetNavigationController

    var body: some View {
        HStack(spacing: 0) {
            navigationButton(
                title: "Назад",
                hint: "Вернуться к предыдущему экрану",
                symbol: "chevron.left",
                enabled: controller.canGoBack && !controller.isLoading,
                shortcut: "[",
                action: controller.goBack
            )
            navigationButton(
                title: "Вперёд",
                hint: "Перейти к следующему экрану",
                symbol: "chevron.right",
                enabled: controller.canGoForward && !controller.isLoading,
                shortcut: "]",
                action: controller.goForward
            )
            navigationButton(
                title: "Обновить",
                hint: "Обновить текущий экран",
                symbol: "arrow.clockwise",
                enabled: controller.canReload && !controller.isLoading,
                shortcut: "r",
                action: controller.reload
            )
        }
        .padding(.horizontal, 4)
        .frame(width: Self.preferredWidth, height: Self.preferredHeight)
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("desktop-cabinet-navigation-controls")
    }

    private func navigationButton(
        title: String,
        hint: String,
        symbol: String,
        enabled: Bool,
        shortcut: KeyEquivalent,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            Image(systemName: symbol)
                .font(.system(size: 15, weight: .semibold))
                .frame(
                    width: DesktopMeetingShellChrome.minimumInteractiveTarget,
                    height: DesktopMeetingShellChrome.minimumInteractiveTarget
                )
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .foregroundStyle(enabled ? Color.primary : Color.secondary.opacity(0.35))
        .disabled(!enabled)
        .keyboardShortcut(shortcut, modifiers: .command)
        .help(
            controller.isLoading
                ? "Загрузка…"
                : "\(title) (⌘\(String(describing: shortcut)))"
        )
        .accessibilityLabel(title)
        .accessibilityHint(controller.isLoading ? "Загрузка выполняется" : hint)
        .accessibilityValue(controller.isLoading ? "Загрузка" : enabled ? "Доступно" : "Недоступно")
        .accessibilityIdentifier(accessibilityIdentifier(for: title))
    }

    private func accessibilityIdentifier(for title: String) -> String {
        switch title {
        case "Назад":
            return DesktopCabinetAccessibilityIdentifier.navigationBack
        case "Вперёд":
            return DesktopCabinetAccessibilityIdentifier.navigationForward
        default:
            return DesktopCabinetAccessibilityIdentifier.navigationReload
        }
    }
}
