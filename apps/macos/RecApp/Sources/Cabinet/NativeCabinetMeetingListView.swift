import Foundation
import SwiftUI

public struct NativeCabinetMeetingListView: View {
    private let configuration: DesktopCabinetConfiguration
    private let onOpenMeeting: (URL) -> Void
    @State private var loadState: NativeCabinetMeetingListLoadState = .loading

    public init(
        configuration: DesktopCabinetConfiguration,
        onOpenMeeting: @escaping (URL) -> Void = { _ in }
    ) {
        self.configuration = configuration
        self.onOpenMeeting = onOpenMeeting
    }

    public var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            header
            content
        }
        .padding(24)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .task(id: configuration.baseURL.absoluteString) {
            await loadMeetings()
        }
    }

    private var header: some View {
        HStack(alignment: .firstTextBaseline, spacing: 10) {
            Text("Мои встречи")
                .font(.system(size: 16, weight: .semibold))
            Text("Сначала новые")
                .font(.system(size: 13, weight: .medium))
                .foregroundStyle(.secondary)
            Spacer()
            Button {
                Task { await loadMeetings() }
            } label: {
                Image(systemName: "arrow.clockwise")
                    .frame(width: 28, height: 28)
            }
            .buttonStyle(.plain)
            .help("Обновить встречи")
        }
    }

    @ViewBuilder
    private var content: some View {
        switch loadState {
        case .loading:
            loadingState
        case let .loaded(items):
            if items.isEmpty {
                emptyState
            } else {
                meetingList(items)
            }
        case let .failed(message):
            failedState(message)
        }
    }

    private var loadingState: some View {
        ProgressView()
            .frame(maxWidth: .infinity, minHeight: 220, alignment: .center)
    }

    private var emptyState: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Записей пока нет", systemImage: "waveform")
                .font(.system(size: 14, weight: .semibold))
            Text("Новая запись появится здесь после отправки на сервер.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(16)
        .frame(maxWidth: .infinity, minHeight: 220, alignment: .topLeading)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(DesktopMeetingShellChrome.shellSurfaceColor)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(DesktopMeetingShellChrome.shellStrokeColor, lineWidth: 1)
        )
    }

    private func failedState(_ message: String) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Label("Нужна проверка кабинета", systemImage: "exclamationmark.triangle")
                .font(.system(size: 14, weight: .semibold))
            Text(message)
                .font(.caption)
                .foregroundStyle(.secondary)
            Link(destination: DesktopCabinetWorkspace.loginRoute(configuration: configuration)) {
                Label("Войти в кабинет", systemImage: "person.crop.circle.badge.checkmark")
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.small)
        }
        .padding(16)
        .frame(maxWidth: .infinity, minHeight: 220, alignment: .topLeading)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(DesktopMeetingShellChrome.shellSurfaceColor)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(DesktopMeetingShellChrome.shellStrokeColor, lineWidth: 1)
        )
    }

    private func meetingList(_ items: [NativeCabinetMeetingItem]) -> some View {
        VStack(spacing: 0) {
            ForEach(items) { item in
                Button {
                    onOpenMeeting(configuration.meetingDetailURL(meetingId: item.meetingId))
                } label: {
                    meetingRow(item)
                }
                .buttonStyle(.plain)
                if item.id != items.last?.id {
                    Divider()
                        .padding(.leading, 42)
                }
            }
        }
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(DesktopMeetingShellChrome.shellSurfaceColor)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(DesktopMeetingShellChrome.shellStrokeColor, lineWidth: 1)
        )
    }

    private func meetingRow(_ item: NativeCabinetMeetingItem) -> some View {
        HStack(spacing: 12) {
            Image(systemName: item.transcriptAvailable ? "doc.text.magnifyingglass" : "speaker.wave.2")
                .frame(width: 18)
                .foregroundStyle(item.transcriptAvailable ? DesktopMeetingShellChrome.shellAccentColor : .secondary)
            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 6) {
                    Text(item.title)
                        .font(.system(size: 13, weight: .semibold))
                        .lineLimit(1)
                    Text(NativeCabinetMeetingListClient.durationText(seconds: item.durationSeconds))
                        .font(.caption2.monospacedDigit())
                        .foregroundStyle(.secondary)
                }
                HStack(spacing: 8) {
                    Text(item.statusLabel)
                    Text(item.startedAt == nil ? "Без даты" : item.startedAtDisplay)
                }
                .font(.caption)
                .foregroundStyle(.secondary)
            }
            Spacer()
            Text(item.primaryAction.label)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 11)
        .frame(maxWidth: .infinity, alignment: .leading)
        .contentShape(Rectangle())
    }

    @MainActor
    private func loadMeetings() async {
        loadState = .loading
        do {
            let items = try await NativeCabinetMeetingListClient(configuration: configuration).listMeetings()
            loadState = .loaded(items)
        } catch {
            loadState = .failed(NativeCabinetMeetingListClient.userMessage(for: error))
        }
    }
}

public enum NativeCabinetMeetingListLoadState: Equatable {
    case loading
    case loaded([NativeCabinetMeetingItem])
    case failed(String)
}

public struct NativeCabinetMeetingListClient {
    public let configuration: DesktopCabinetConfiguration
    private let session: URLSession
    private let decoder: JSONDecoder

    public init(configuration: DesktopCabinetConfiguration, session: URLSession = .shared) {
        self.configuration = configuration
        self.session = session
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        self.decoder = decoder
    }

    public func listMeetings(limit: Int = 50) async throws -> [NativeCabinetMeetingItem] {
        var request = URLRequest(url: Self.listURL(configuration: configuration, limit: limit))
        request.httpMethod = "GET"
        request.timeoutInterval = configuration.loadTimeoutSeconds
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        for (header, value) in configuration.headers {
            request.setValue(value, forHTTPHeaderField: header)
        }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw NativeCabinetMeetingListError.network
        }
        guard let httpResponse = response as? HTTPURLResponse else {
            throw NativeCabinetMeetingListError.invalidResponse
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            throw NativeCabinetMeetingListError.httpStatus(httpResponse.statusCode)
        }
        return try decoder.decode(NativeCabinetMeetingListResponse.self, from: data).items
    }

    public static func listURL(configuration: DesktopCabinetConfiguration, limit: Int = 50) -> URL {
        var components = URLComponents(url: configuration.baseURL, resolvingAgainstBaseURL: false)
        components?.path = "/api/v1/cabinet/meetings"
        components?.queryItems = [
            URLQueryItem(name: "sort", value: "updated_desc"),
            URLQueryItem(name: "limit", value: "\(limit)")
        ]
        return components?.url ?? configuration.baseURL.appending(path: "api/v1/cabinet/meetings")
    }

    public static func durationText(seconds: Int) -> String {
        if seconds < 60 {
            return "\(max(0, seconds))s"
        }
        let minutes = seconds / 60
        if minutes < 60 {
            return "\(minutes)m"
        }
        return "\(minutes / 60)h \(minutes % 60)m"
    }

    public static func userMessage(for error: Error) -> String {
        switch error as? NativeCabinetMeetingListError {
        case .httpStatus(401):
            return "Нужен вход, чтобы открыть список встреч."
        case .httpStatus(403):
            return "Текущая сессия не подтверждает доступ к этому кабинету."
        case .httpStatus:
            return "Кабинет встреч вернул неожиданный ответ. Локальная запись не меняется."
        case .network:
            return "Кабинет встреч недоступен. Проверьте соединение с сервером Rec."
        case .invalidResponse:
            return "Кабинет встреч вернул ответ, который приложение не смогло прочитать."
        case .none:
            return "Кабинет встреч временно недоступен."
        }
    }
}

public enum NativeCabinetMeetingListError: Error, Equatable, Sendable {
    case network
    case invalidResponse
    case httpStatus(Int)
}

public struct NativeCabinetMeetingListResponse: Decodable, Equatable, Sendable {
    public let items: [NativeCabinetMeetingItem]
}

public struct NativeCabinetMeetingItem: Decodable, Equatable, Identifiable, Sendable {
    public let meetingId: String
    public let title: String
    public let startedAt: String?
    public let durationSeconds: Int
    public let status: String
    public let statusLabel: String
    public let primaryAction: NativeCabinetPrimaryAction
    public let transcriptAvailable: Bool

    public var id: String { meetingId }

    public var startedAtDisplay: String {
        guard let startedAt else { return "Без даты" }
        return String(startedAt.prefix(10))
    }
}

public enum NativeCabinetPrimaryAction: String, Decodable, Equatable, Sendable {
    case open
    case wait
    case retryFuture = "retry_future"
    case openStatus = "open_status"
    case unavailable

    public var label: String {
        switch self {
        case .open:
            return "Открыть"
        case .wait:
            return "В обработке"
        case .retryFuture:
            return "Повтор позже"
        case .openStatus:
            return "Статус"
        case .unavailable:
            return "Недоступно"
        }
    }
}
