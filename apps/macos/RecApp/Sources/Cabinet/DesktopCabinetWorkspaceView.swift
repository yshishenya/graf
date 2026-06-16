import SwiftUI

public struct DesktopCabinetWorkspaceView: View {
    public static let workspaceTitle = "Встречи"
    public static let workspaceAccessibilityLabel = "Встречи и обзор записей"
    public static let unavailableTitle = "Кабинет встреч недоступен"
    public static let embeddedSurfaceHeight: CGFloat = 420

    private let configuration: DesktopCabinetConfiguration?
    private let initialRoute: URL?
    @State private var cabinetState: DesktopCabinetState

    public init(
        configuration: DesktopCabinetConfiguration? = DesktopCabinetConfiguration.configuredFromEnvironment(),
        initialRoute: URL? = nil,
        initialState: DesktopCabinetState? = nil
    ) {
        self.configuration = configuration
        self.initialRoute = initialRoute
        _cabinetState = State(initialValue: initialState ?? (configuration == nil ? .notConfigured : .loading))
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            header
            content
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(Color(nsColor: .controlBackgroundColor))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(Color.secondary.opacity(0.18), lineWidth: 1)
        )
        .accessibilityElement(children: .contain)
        .accessibilityLabel(Self.workspaceAccessibilityLabel)
        .accessibilityIdentifier(DesktopCabinetAccessibilityIdentifier.workspace)
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
        if let configuration {
            EmbeddedCabinetWebView(
                request: configuration.urlRequest(for: initialRoute ?? configuration.meetingsURL()),
                routePolicy: DesktopCabinetRoutePolicy(baseURL: configuration.baseURL),
                cabinetState: $cabinetState
            )
            .frame(
                maxWidth: .infinity,
                minHeight: Self.embeddedSurfaceHeight,
                maxHeight: Self.embeddedSurfaceHeight
            )
            .accessibilityIdentifier(DesktopCabinetAccessibilityIdentifier.embeddedSurface)
        } else {
            unavailableState
        }
    }

    private var unavailableState: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label(Self.unavailableTitle, systemImage: "wifi.slash")
                .font(.subheadline)
                .fontWeight(.semibold)
            Text(cabinetState.userMessage)
                .font(.caption)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, minHeight: 160, alignment: .leading)
        .padding(14)
        .background(Color.secondary.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier(DesktopCabinetAccessibilityIdentifier.unavailableState)
    }

    private var statusText: String {
        switch cabinetState {
        case .ready:
            return "Готово"
        case .loading:
            return "Загрузка"
        case .notConfigured:
            return "Не подключено"
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
