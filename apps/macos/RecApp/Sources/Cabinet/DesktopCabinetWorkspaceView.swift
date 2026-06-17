import SwiftUI

public struct DesktopCabinetWorkspaceView: View {
    public static let workspaceTitle = "Встречи"
    public static let workspaceAccessibilityLabel = "Встречи и обзор записей"
    public static let unavailableTitle = "Кабинет встреч"
    public static let embeddedSurfaceHeight: CGFloat = 420
    public static let shellEmbeddedSurfaceMinHeight: CGFloat = 520

    private let configuration: DesktopCabinetConfiguration?
    private let initialRoute: URL?
    private let presentation: DesktopCabinetWorkspacePresentation
    @State private var cabinetState: DesktopCabinetState

    public init(
        configuration: DesktopCabinetConfiguration? = DesktopCabinetConfiguration.configuredFromEnvironment(),
        initialRoute: URL? = nil,
        presentation: DesktopCabinetWorkspacePresentation = .card,
        initialState: DesktopCabinetState? = nil
    ) {
        self.configuration = configuration
        self.initialRoute = initialRoute
        self.presentation = presentation
        _cabinetState = State(initialValue: initialState ?? (configuration == nil ? .notConfigured : .loading))
    }

    public var body: some View {
        let stack = VStack(alignment: .leading, spacing: 12) {
            header
            content
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel(Self.workspaceAccessibilityLabel)
        .accessibilityIdentifier(DesktopCabinetAccessibilityIdentifier.workspace)

        switch presentation {
        case .card:
            stack
                .padding(16)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(Color(nsColor: .controlBackgroundColor))
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(Color.secondary.opacity(0.18), lineWidth: 1)
                )
        case .shell:
            stack
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
        if let configuration, cabinetState.shouldShowEmbeddedSurface {
            let webView = EmbeddedCabinetWebView(
                request: configuration.urlRequest(for: initialRoute ?? configuration.meetingsURL()),
                routePolicy: DesktopCabinetRoutePolicy(baseURL: configuration.baseURL),
                cabinetState: $cabinetState
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
        VStack(alignment: .leading, spacing: 8) {
            Label(cabinetState.unavailableTitle, systemImage: cabinetState.unavailableSystemImage)
                .font(.subheadline)
                .fontWeight(.semibold)
            Text(cabinetState.userMessage)
                .font(.caption)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            if let recoveryActionTitle = cabinetState.recoveryActionTitle,
               let recoveryURL {
                Link(destination: recoveryURL) {
                    Label(recoveryActionTitle, systemImage: "arrow.up.right.square")
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.small)
                .padding(.top, 4)
                .help(recoveryActionTitle)
            }
        }
        .frame(maxWidth: .infinity, minHeight: presentation == .shell ? 360 : 160, alignment: .leading)
        .padding(14)
        .background(Color.secondary.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier(DesktopCabinetAccessibilityIdentifier.unavailableState)
    }

    private var recoveryURL: URL? {
        guard let configuration else { return nil }
        switch cabinetState {
        case .expiredSession:
            return configuration.baseURL.appending(path: "meetings")
        case .offline, .timeout:
            return configuration.baseURL
        default:
            return nil
        }
    }

    private var statusText: String {
        switch cabinetState {
        case .ready:
            return "Готово"
        case .loading:
            return "Загрузка"
        case .notConfigured:
            return "Не подключено"
        case .expiredSession:
            return "Нужен вход"
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
        switch cabinetState {
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
}

public enum DesktopCabinetWorkspacePresentation: Equatable, Sendable {
    case card
    case shell
}
