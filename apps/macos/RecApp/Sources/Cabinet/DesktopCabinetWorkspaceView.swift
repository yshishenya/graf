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
                supportIncidentBridge: supportIncidentBridge
            )
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
            if let recoveryActionTitle = activeCabinetState.recoveryActionTitle,
               let recoveryTarget {
                switch recoveryTarget {
                case let .embedded(url):
                    Button {
                        currentRoute = url
                        activeCabinetStateBinding.wrappedValue = .loading
                    } label: {
                        Label(recoveryActionTitle, systemImage: activeCabinetState.recoverySystemImage)
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.regular)
                    .frame(minHeight: DesktopMeetingShellChrome.minimumInteractiveTarget)
                    .help(recoveryActionTitle)
                    .accessibilityLabel(recoveryActionTitle)
                case let .external(url):
                    Link(destination: url) {
                        Label(recoveryActionTitle, systemImage: "arrow.up.right.square")
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.regular)
                    .frame(minHeight: DesktopMeetingShellChrome.minimumInteractiveTarget)
                    .help(recoveryActionTitle)
                    .accessibilityLabel(recoveryActionTitle)
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
        if let route = currentRoute ?? initialRoute {
            let decision = DesktopCabinetRoutePolicy(baseURL: configuration.baseURL).decision(for: route)
            if decision.route.kind == .calendarSettings {
                return DesktopCabinetWorkspace.calendarSettingsRecoveryTarget(
                    for: activeCabinetState,
                    configuration: configuration
                )
            }
        }
        return DesktopCabinetWorkspace.recoveryTarget(for: activeCabinetState, configuration: configuration)
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
