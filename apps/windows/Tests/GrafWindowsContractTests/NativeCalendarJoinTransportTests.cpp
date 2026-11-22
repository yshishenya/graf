#include <windows.h>
#include <winhttp.h>
#include "../../RecApp/Upload/DesktopHttpTransport.h"
#include "../../RecApp/Storage/ProtectedCustodyCodec.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <algorithm>
#include <array>
#include <cstring>
#include <cstdio>
#include <map>
#include <new>
#include <vector>
#ifdef _MSC_VER
#include <crtdbg.h>
#endif

namespace {
using Clock = std::chrono::steady_clock;
std::string responseBody;
std::size_t wireCursor = 0, chunk = 4096;
std::size_t prematureZeroAt = std::string::npos;
DWORD wireStatus = 200;
std::wstring wireVerb, wirePath, wireHeaders;
std::function<void()> setupCalendarRequest;
std::function<void(std::wstring_view, std::string_view)> checkCalendarPost;
std::optional<std::uint64_t> calendarUtc, advanceUtcAtPostOption;
void WINAPI testSystemTime(LPFILETIME time) {
    if (!calendarUtc) return GetSystemTimePreciseAsFileTime(time);
    const std::uint64_t ticks = 116444736000000000ULL + *calendarUtc * 10'000;
    time->dwLowDateTime = static_cast<DWORD>(ticks);
    time->dwHighDateTime = static_cast<DWORD>(ticks >> 32);
}
unsigned opens = 0, sends = 0, receives = 0, queries = 0, reads = 0;
unsigned timeouts = 0, options = 0;
std::vector<std::array<int, 4>> budgets;
std::map<HINTERNET, unsigned> closes;
Clock::time_point instant;
Clock::time_point fakeNow() { return instant; }
std::shared_ptr<std::atomic_bool> cancel;
std::string interruptAt, failAt, throwAt;
DWORD wireError = ERROR_WINHTTP_CONNECTION_ERROR;
bool expire = false, pretendNoData = false;
std::chrono::milliseconds readAdvance{0};
std::weak_ptr<const graf::windows::CustodyBytes> uploadOwner;
std::shared_ptr<const graf::windows::CustodyBytes>* callerBody = nullptr;
const void* uploadData = nullptr;
std::size_t uploadLength = 0;
bool exhaustAtOption = false;
const wchar_t* retryHeader = nullptr;
const wchar_t* expiryHeader = nullptr;
const wchar_t* cacheHeader = nullptr;
unsigned cacheProbes = 0, cacheCopies = 0;
bool exhaustAtHeader = false;
bool exhaustAtAvailable = false;
struct QuotaPressure {
    graf::windows::CustodyAllocator<std::uint8_t> allocator;
    std::uint8_t* bytes = nullptr;
    std::size_t count = 0;
    bool installed = false;
    void fill() {
        assert(!bytes && !installed);
        count = graf::windows::CustodyOwnedMemory::limit - graf::windows::CustodyOwnedMemory::usedBytes();
        bytes = allocator.allocate(count);
        assert(graf::windows::CustodyOwnedMemory::usedBytes() == graf::windows::CustodyOwnedMemory::limit);
        installed = true;
    }
    void release() noexcept {
        if (bytes) allocator.deallocate(bytes, count);
        bytes = nullptr; count = 0; installed = false;
    }
    ~QuotaPressure() { release(); }
} quotaPressure;
void requireUploadOwner() {
    if (!uploadData) return;
    const auto held = uploadOwner.lock();
    assert(held && held->data() == uploadData && held->size() == uploadLength);
    assert(std::all_of(held->begin(), held->end(), [](auto byte) { return byte == 0x5a; }));
}
HINTERNET session() { return reinterpret_cast<HINTERNET>(1); }
HINTERNET connection() { return reinterpret_cast<HINTERNET>(2); }
HINTERNET handle() { return reinterpret_cast<HINTERNET>(3); }
bool boundary(const char* phase) {
    if (throwAt == phase) throw std::bad_alloc{};
    if (interruptAt == phase) {
        if (expire) instant += std::chrono::seconds(16);
        else cancel->store(true);
    }
    if (failAt == phase) { SetLastError(wireError); return false; }
    return true;
}
HINTERNET WINAPI testOpen(LPCWSTR, DWORD access, LPCWSTR, LPCWSTR, DWORD flags) {
    ++opens; assert(access == WINHTTP_ACCESS_TYPE_AUTOMATIC_PROXY && flags == 0);
    return boundary("open") ? session() : nullptr;
}
BOOL WINAPI testTimeouts(HINTERNET, int resolve, int connect, int send, int receive) {
    ++timeouts; budgets.push_back({resolve, connect, send, receive});
    assert(resolve > 0 && connect > 0 && send > 0 && receive > 0);
    return boundary("timeouts");
}
HINTERNET WINAPI testConnect(HINTERNET s, LPCWSTR host, INTERNET_PORT port, DWORD flags) {
    assert(s == session() && std::wstring(host) == L"example.org" && port == 443 && flags == 0);
    return boundary("connect") ? connection() : nullptr;
}
HINTERNET WINAPI testRequest(HINTERNET c, LPCWSTR verb, LPCWSTR object, LPCWSTR,
    LPCWSTR referer, LPCWSTR*, DWORD flags) {
    assert(c == connection() && !referer && flags == WINHTTP_FLAG_SECURE);
    wireVerb = verb; wirePath = object;
    if (setupCalendarRequest) setupCalendarRequest();
    return boundary("request") ? handle() : nullptr;
}
BOOL WINAPI testOption(HINTERNET h, DWORD option, LPVOID buffer, DWORD size) {
    ++options;
    assert(h == handle() && option == WINHTTP_OPTION_DISABLE_FEATURE && size == sizeof(DWORD));
    const DWORD disabled = WINHTTP_DISABLE_REDIRECTS | WINHTTP_DISABLE_COOKIES |
        (setupCalendarRequest && wireVerb == L"POST" ? WINHTTP_DISABLE_AUTHENTICATION : 0);
    assert(*static_cast<DWORD*>(buffer) == disabled);
    if (advanceUtcAtPostOption && wireVerb == L"POST") calendarUtc = *advanceUtcAtPostOption;
    if (exhaustAtOption) {
        requireUploadOwner();
        callerBody->reset();
        quotaPressure.fill();
    }
    return boundary("option");
}
BOOL WINAPI testSend(HINTERNET h, LPCWSTR text, DWORD length, LPVOID body, DWORD size, DWORD total, DWORD_PTR context) {
    ++sends;
    assert(h == handle() && !context);
    if (uploadData) {
        assert(body == uploadData && size == uploadLength && total == size);
        requireUploadOwner();
        callerBody->reset(); // Native wrapper must retain its own strong owner.
        requireUploadOwner();
    } else if (checkCalendarPost && wireVerb == L"POST") {
        assert(body && size && total == size);
        checkCalendarPost({text, length}, {static_cast<const char*>(body), size});
    } else assert(!body && !size && !total);
    wireHeaders.assign(text, length);
    return boundary("send");
}
BOOL WINAPI testReceive(HINTERNET h, LPVOID reserved) {
    ++receives; assert(h == handle() && !reserved); requireUploadOwner(); return boundary("receive");
}
BOOL WINAPI testHeaders(HINTERNET h, DWORD level, LPCWSTR name, LPVOID buffer, LPDWORD size, LPDWORD) {
    ++queries; assert(h == handle());
    if (!boundary("headers")) return FALSE;
    if (level == (WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER)) {
        assert(buffer && *size == sizeof(DWORD)); *static_cast<DWORD*>(buffer) = wireStatus; return TRUE;
    }
    assert(level == WINHTTP_QUERY_CUSTOM);
    const auto header = std::wstring_view(name);
    const wchar_t* value = nullptr;
    if (header == L"Retry-After") value = retryHeader;
    else if (header == L"X-GRAF-Auth-Expires-At") value = expiryHeader;
    else {
        assert(header == L"Cache-Control");
        value = cacheHeader;
        if (buffer) ++cacheCopies; else ++cacheProbes;
        if (!boundary(buffer ? "cache_read" : "cache_probe")) return FALSE;
    }
    if (value) {
        const auto bytes = static_cast<DWORD>((std::char_traits<wchar_t>::length(value) + 1) * sizeof(wchar_t));
        if (!buffer) {
            if (exhaustAtHeader) quotaPressure.fill();
            *size = bytes; SetLastError(ERROR_INSUFFICIENT_BUFFER); return FALSE;
        }
        assert(*size >= bytes); std::memcpy(buffer, value, bytes); *size = bytes - sizeof(wchar_t); return TRUE;
    }
    *size = 0; SetLastError(ERROR_WINHTTP_HEADER_NOT_FOUND); return FALSE;
}
BOOL WINAPI testAvailable(HINTERNET h, LPDWORD count) {
    assert(h == handle());
    *count = pretendNoData ? 0 : static_cast<DWORD>(std::min(chunk, responseBody.size() - wireCursor));
    if (exhaustAtAvailable && !quotaPressure.installed) quotaPressure.fill();
    return boundary("available");
}
BOOL WINAPI testRead(HINTERNET h, LPVOID buffer, DWORD size, LPDWORD count) {
    ++reads; assert(h == handle());
    if (wireCursor == prematureZeroAt) { *count = 0; return TRUE; }
    *count = static_cast<DWORD>(std::min<std::size_t>(size, responseBody.size() - wireCursor));
    std::memcpy(buffer, responseBody.data() + wireCursor, *count);
    wireCursor += *count;
    instant += readAdvance;
    if (wireCursor == responseBody.size()) boundary("last_read");
    if (*count == 0 && !boundary("eof")) return FALSE;
    return boundary("read");
}
BOOL WINAPI testClose(HINTERNET h) {
    requireUploadOwner();
    assert(++closes[h] == 1);
    SetLastError(ERROR_INVALID_HANDLE); // Cleanup must not replace the actual network failure.
    return TRUE;
}
void reset(std::string body) {
    assert(!quotaPressure.bytes && !quotaPressure.installed); exhaustAtOption = false;
    retryHeader = expiryHeader = cacheHeader = nullptr; exhaustAtHeader = exhaustAtAvailable = false;
    cacheProbes = cacheCopies = 0;
    responseBody = std::move(body); wireCursor = 0; chunk = 4096; wireStatus = 200;
    prematureZeroAt = std::string::npos;
    opens = sends = receives = queries = reads = timeouts = options = 0;
    budgets.clear(); closes.clear(); wireHeaders.clear(); wireVerb.clear(); wirePath.clear();
    interruptAt.clear(); failAt.clear(); throwAt.clear(); expire = pretendNoData = false;
    wireError = ERROR_WINHTTP_CONNECTION_ERROR;
    readAdvance = std::chrono::milliseconds(0);
    uploadOwner.reset(); callerBody = nullptr; uploadData = nullptr; uploadLength = 0;
    instant = Clock::now(); cancel = std::make_shared<std::atomic_bool>(false);
}
} // namespace

#define GetSystemTimePreciseAsFileTime testSystemTime
#define WinHttpOpen testOpen
#define WinHttpSetTimeouts testTimeouts
#define WinHttpConnect testConnect
#define WinHttpOpenRequest testRequest
#define WinHttpSetOption testOption
#define WinHttpSendRequest testSend
#define WinHttpReceiveResponse testReceive
#define WinHttpQueryHeaders testHeaders
#define WinHttpQueryDataAvailable testAvailable
#define WinHttpReadData testRead
#define WinHttpCloseHandle testClose
#include "../../RecApp/Upload/DesktopHttpTransport.cpp"
#include "../../RecApp/Upload/DesktopApiClient.cpp"
#undef WinHttpOpen
#undef WinHttpSetTimeouts
#undef WinHttpConnect
#undef WinHttpOpenRequest
#undef WinHttpSetOption
#undef WinHttpSendRequest
#undef WinHttpReceiveResponse
#undef WinHttpQueryHeaders
#undef WinHttpQueryDataAvailable
#undef WinHttpReadData
#undef WinHttpCloseHandle

int main() {
#ifdef _MSC_VER
    _set_error_mode(_OUT_TO_STDERR);
    _set_abort_behavior(0, _WRITE_ABORT_MSG | _CALL_REPORTFAULT);
#ifdef _DEBUG
    _CrtSetReportMode(_CRT_ASSERT, _CRTDBG_MODE_FILE);
    _CrtSetReportFile(_CRT_ASSERT, _CRTDBG_FILE_STDERR);
#endif
#endif
    using namespace graf::windows;
    // Preserve the numeric token contract without an uncharged temporary string.
    for (const auto token : {"", "-1", "1.0", "1e2", "1x", "18446744073709551616", " 1"}) {
        const auto json = std::string("{\"value\":") + token + "}";
        assert(!jsonNumberField(json, "value") && !jsonNumberField<CustodyString>(json, "value"));
    }
    for (const auto token : {"0", "18446744073709551615", "1 \t"}) {
        const auto json = std::string("{\"value\":") + token + "}";
        const auto ordinary = jsonNumberField(json, "value");
        assert(ordinary && ordinary == jsonNumberField<CustodyString>(json, "value"));
    }
    assert(jsonNumberField("\"value\":18446744073709551615", "value") == UINT64_MAX);
    static_assert(std::is_same_v<decltype(ProtectedDesktopTransportResult::safeReason)::allocator_type, CustodyAllocator<char>>);
    static_assert(std::is_same_v<decltype(BasicUploadServerTruth<CustodyString>::meetingId)::allocator_type, CustodyAllocator<char>>);
    const std::string event = "abcdefab-1234-4567-89ab-abcdefabcdef";
    const auto target = std::string("{\"event_id\":\"") + event +
        "\",\"provider_family\":\"calendar\",\"https_url\":\"https://example.org/join\"}";
    DesktopHttpConfig config;
    config.baseOrigin = "https://example.org";
    config.workspaceId = "22222222-2222-4222-8222-222222222222";
    config.sessionToken = "synthetic-session";
    config.confirmedIdentity = DesktopAccountIdentity{"11111111-1111-4111-8111-111111111111", config.workspaceId};
    config.deviceId = "must-not-travel";
    config.scopedAccount = DeletionScope{"foreign", "foreign"};
    for (const auto phase : {"send", "receive", "available", "read"}) {
        for (const DWORD error : {ERROR_WINHTTP_TIMEOUT, ERROR_WINHTTP_NAME_NOT_RESOLVED,
            ERROR_WINHTTP_CANNOT_CONNECT, ERROR_WINHTTP_CONNECTION_ERROR, ERROR_WINHTTP_SECURE_FAILURE}) {
            reset("{}"); failAt = phase; wireError = error;
            const auto failed = DesktopHttpTransport(config).notificationContext(
                {config.confirmedIdentity->userId, config.workspaceId});
            assert(failed.transportFailed && failed.nativeError == error);
            CalendarReminderResponse classified{failed.status, std::nullopt, std::nullopt, failed.nativeError, failed.transportFailed};
            assert(classified.temporarilyUnavailable() == (error == ERROR_WINHTTP_TIMEOUT ||
                error == ERROR_WINHTTP_NAME_NOT_RESOLVED || error == ERROR_WINHTTP_CANNOT_CONNECT));
            if (std::string_view(phase) != "available") { // This reader uses ReadData directly.
                reset("{}"); failAt = phase; wireError = error;
                const auto calendar = DesktopApiClient::calendarReminders(config);
                assert(calendar.transportFailed && calendar.nativeError == error);
                assert(calendar.temporarilyUnavailable() == classified.temporarilyUnavailable());
            }
        }
    }
    for (const DWORD status : {301, 400, 401, 403, 404, 408, 429, 503}) {
        reset("{}"); wireStatus = status; failAt = "read"; wireError = ERROR_WINHTTP_TIMEOUT;
        const auto failed = DesktopHttpTransport(config).notificationContext(
            {config.confirmedIdentity->userId, config.workspaceId});
        assert(failed.status == status && failed.transportFailed && failed.nativeError == ERROR_WINHTTP_TIMEOUT);
        CalendarReminderResponse classified{failed.status, std::nullopt, std::nullopt, failed.nativeError, failed.transportFailed};
        assert(classified.temporarilyUnavailable() == (status == 408 || status == 429 || status == 503));
    }
    // Exercise the actual protected request with the WinHTTP calls above replaced.
    const CalendarMatchReceiptQuery receiptQuery{
        "https://example.org", "11111111-1111-4111-8111-111111111111", config.workspaceId,
        "33333333-3333-4333-8333-333333333333", "44444444-4444-4444-8444-444444444444",
        "revision--initial", "55555555-5555-4555-8555-555555555555", CalendarMatchIntent::userSelected, {}};
    ProtectedDesktopHttpConfig receiptConfig;
    receiptConfig.baseOrigin = receiptQuery.origin;
    receiptConfig.workspaceId = receiptQuery.workspaceId;
    receiptConfig.deviceId = receiptQuery.deviceId;
    receiptConfig.sessionToken = "synthetic-session";
    receiptConfig.confirmedIdentity = BasicDesktopAccountIdentity<CustodyString>{
        CustodyString(receiptQuery.userId), receiptConfig.workspaceId, receiptConfig.deviceId};
    using ReceiptState = CalendarMatchReceiptState;
    const auto receipt = [&] {
        receiptConfig.cancellation = cancel;
        const auto result = DesktopHttpTransport::calendarMatchReceipt(
            receiptConfig, receiptQuery, Clock::now() + std::chrono::seconds(15));
        assert(opens == 1 && sends == 1 && receives == 1 && options == 1 && closes.size() == 3);
        assert(wireVerb == L"GET" && wirePath ==
            L"/api/v1/desktop/recordings/44444444-4444-4444-8444-444444444444/"
            L"sync-state?local_media_revision_id=revision--initial&include_calendar_match_receipt=true");
        for (const auto* header : {
            L"X-Workspace-Id: 22222222-2222-4222-8222-222222222222\r\n",
            L"X-Device-Id: 33333333-3333-4333-8333-333333333333\r\n",
            L"X-Auth-Session: synthetic-session\r\n",
            L"X-Graf-Expected-Actor: 11111111-1111-4111-8111-111111111111\r\n",
            L"X-Graf-Expected-Workspace: 22222222-2222-4222-8222-222222222222\r\n",
            L"Cache-Control: no-cache, no-store\r\n"}) assert(wireHeaders.find(header) != std::wstring::npos);
        assert(wireHeaders.find(L"Idempotency-Key:") == std::wstring::npos);
        return result.state;
    };
    const std::string proof = R"({
        "local_recording_id":"44444444-4444-4444-8444-444444444444",
        "local_media_revision_id":"revision--initial",
        "meeting":{"meeting_id":"66666666-6666-4666-8666-666666666666","access_state":"owner","deletion_state":"none"},
        "media_revision":{"local_media_revision_id":"revision--initial","status":"pending_upload"},
        "conflict":{"state":"none"},
        "calendar_match_receipt":{"attempt_id":"55555555-5555-4555-8555-555555555555","state":"matched_user"}
    })";
    const std::string absence = R"({"code":"recording_not_found"})";
    for (const auto* body : {&proof, &absence}) {
        const DWORD status = body == &proof ? 200 : 404;
        const auto accepted = status == 200 ? ReceiptState::proved : ReceiptState::recordingNotFound;
        for (const std::size_t size : {65537U, 2U * 1024U * 1024U, 2U * 1024U * 1024U + 1U}) {
            reset(*body + std::string(size - body->size(), ' ')); wireStatus = status;
            assert(receipt() == (size > 2U * 1024U * 1024U ? ReceiptState::unproved : accepted));
            if (size <= 2U * 1024U * 1024U) assert(wireCursor == size && reads == (size + chunk - 1) / chunk + 1);
        }
        reset(*body); wireStatus = status; failAt = "eof";
        assert(receipt() == ReceiptState::unproved && wireCursor == body->size());
        reset(*body + ' '); wireStatus = status; chunk = body->size(); prematureZeroAt = body->size();
        assert(receipt() == ReceiptState::unproved && wireCursor == body->size());
    }
    reset(absence); wireStatus = 302;
    assert(receipt() == ReceiptState::unproved);

    auto strictQuery = receiptQuery;
    strictQuery.revisionId = "44444444-4444-4444-8444-444444444444--initial";
    auto strictProof = proof;
    constexpr std::string_view oldRevision = "revision--initial";
    for (std::size_t at = 0; (at = strictProof.find(oldRevision, at)) != std::string::npos;
         at += strictQuery.revisionId.size()) strictProof.replace(at, oldRevision.size(), strictQuery.revisionId);
    const auto create = DesktopApiClient::createMeetingRequest<CustodyString>(strictQuery.recordingId,
        strictQuery.revisionId, 60, 1'750'000'000'000, 1'750'000'060'000, 0, strictQuery.attemptId);
    assert(create);
    const CalendarMatchReplay frozen{CustodyString(strictQuery.attemptId),
        DesktopApiClient::idempotencyKey<CustodyString>("calendar-meeting", strictQuery.recordingId, strictQuery.attemptId),
        DesktopApiClient::createMeetingBody(*create), 1'750'000'300'000};
    enum class StrictFault { loseResponse, expireBeforeSend, resendRequested };
    for (const auto fault : {StrictFault::loseResponse, StrictFault::expireBeforeSend, StrictFault::resendRequested}) {
        const bool expireBeforeSend = fault == StrictFault::expireBeforeSend;
        reset(absence);
        receiptConfig.cancellation = cancel;
        calendarUtc = frozen.expiresAtMs - 1;
        if (expireBeforeSend) advanceUtcAtPostOption = frozen.expiresAtMs;
        std::string prepared;
        unsigned posted = 0;
        setupCalendarRequest = [&] {
            if (!prepared.empty()) {
                assert(closes.size() == 3);
                closes.clear(); // The shim reuses fake handles across sequential requests.
            }
            prepared += wireVerb == L"POST" ? 'P' : 'G';
            wireCursor = 0;
            if (wireVerb == L"POST") {
                assert(wirePath == L"/api/v1/desktop/meetings/with-calendar-context");
                failAt = fault == StrictFault::resendRequested ? "send" : "receive";
                if (fault == StrictFault::resendRequested) wireError = ERROR_WINHTTP_RESEND_REQUEST;
            } else {
                assert(wireVerb == L"GET" && wirePath ==
                    L"/api/v1/desktop/recordings/44444444-4444-4444-8444-444444444444/"
                    L"sync-state?local_media_revision_id=44444444-4444-4444-8444-444444444444--initial&include_calendar_match_receipt=true");
                responseBody = posted ? strictProof : absence;
                wireStatus = posted ? 200 : 404;
                failAt.clear();
            }
        };
        checkCalendarPost = [&](std::wstring_view headers, std::string_view body) {
            ++posted;
            assert(body == frozen.body);
            auto key = utf8ToWide(frozen.idempotencyKey);
            assert(headers.find(L"Idempotency-Key: " + key + L"\r\n") != std::wstring_view::npos);
            for (const auto* header : {
                L"X-Workspace-Id: 22222222-2222-4222-8222-222222222222\r\n",
                L"X-Device-Id: 33333333-3333-4333-8333-333333333333\r\n",
                L"X-Auth-Session: synthetic-session\r\n",
                L"X-Graf-Expected-Actor: 11111111-1111-4111-8111-111111111111\r\n",
                L"X-Graf-Expected-Workspace: 22222222-2222-4222-8222-222222222222\r\n"})
                assert(headers.find(header) != std::wstring_view::npos);
            calendarUtc = frozen.expiresAtMs;
        };
        const auto replay = DesktopHttpTransport::replayCalendarMeeting(
            receiptConfig, strictQuery, frozen, Clock::now() + std::chrono::seconds(15));
        assert(prepared == "GPG" && closes.size() == 3 && options == 3);
        assert(posted == (expireBeforeSend ? 0U : 1U) && sends == (expireBeforeSend ? 2U : 3U));
        assert(replay.state == (expireBeforeSend ? ReceiptState::unproved : ReceiptState::proved));
        if (posted) assert(replay.meetingId && *replay.meetingId == "66666666-6666-4666-8666-666666666666");
        setupCalendarRequest = {};
        checkCalendarPost = {};
        calendarUtc.reset();
        advanceUtcAtPostOption.reset();
    }

    // T128: no ready-response callback. Only WinHTTP is replaced; the real
    // response-header reader must propagate no-store into proof eligibility.
    {
        const LocalCacheProofQuery query{receiptQuery.origin, receiptQuery.userId, receiptQuery.workspaceId,
            receiptQuery.deviceId, receiptQuery.recordingId, strictQuery.revisionId,
            "66666666-6666-4666-8666-666666666666"};
        const std::string body = R"({
            "local_recording_id":"44444444-4444-4444-8444-444444444444",
            "local_media_revision_id":"44444444-4444-4444-8444-444444444444--initial",
            "meeting":{"meeting_id":"66666666-6666-4666-8666-666666666666","access_state":"owner",
                "deletion_state":"none","retention":{"policy_state":"active","delete_after":"2025-12-17T00:00:00Z"}},
            "conflict":{"state":"none"},
            "playback":{"state":"available","can_play":true,"reason_code":"canonical_ready","object_verified":true,
                "media_revision_id":"77777777-7777-4777-8777-777777777777",
                "local_media_revision_id":"44444444-4444-4444-8444-444444444444--initial","verified_at":"2025-11-17T00:00:00Z"},
            "finalized_upload":{"session_id":"88888888-8888-4888-8888-888888888888","status":"finalized","archive_audio":true,
                "media_revision_id":"77777777-7777-4777-8777-777777777777",
                "local_media_revision_id":"44444444-4444-4444-8444-444444444444--initial","finalized_at":"2025-11-10T00:00:00Z"}
        })";
        const auto check = [&](bool eligible, unsigned copies) {
            receiptConfig.cancellation = cancel;
            const auto baseline = CustodyOwnedMemory::usedBytes();
            {
                const auto result = DesktopHttpTransport::localCacheProof(receiptConfig, query,
                    Clock::now() + std::chrono::seconds(5), {}, [] { return 1'763'337'600'000ULL; });
                assert(DesktopHttpTransport::localCacheProofEligibility(receiptConfig, query, result, 1'763'337'600'000ULL) ==
                    (eligible ? "potentially_eligible" : "proof_missing"));
                assert(result.serverMediaRevisionId() == (eligible ? "77777777-7777-4777-8777-777777777777" : ""));
                assert(result.finalizedUploadSessionId() == (eligible ? "88888888-8888-4888-8888-888888888888" : ""));
            }
            assert(CustodyOwnedMemory::usedBytes() == baseline);
            assert(cacheProbes == 1 && cacheCopies == copies);
            assert(opens == 1 && sends == 1 && receives == 1 && options == 1 && closes.size() == 3);
            for (const auto& entry : closes) assert(entry.second == 1);
            assert(wireVerb == L"GET" && wirePath ==
                L"/api/v1/desktop/recordings/44444444-4444-4444-8444-444444444444/"
                L"sync-state?local_media_revision_id=44444444-4444-4444-8444-444444444444--initial");
            assert(wireHeaders.find(L"Cache-Control: no-cache, no-store\r\n") != std::wstring::npos);
            assert(wireHeaders.find(L"X-Graf-Expected-Actor: 11111111-1111-4111-8111-111111111111\r\n") != std::wstring::npos);
            assert(wireHeaders.find(L"X-Graf-Expected-Workspace: 22222222-2222-4222-8222-222222222222\r\n") != std::wstring::npos);
            assert(wireHeaders.find(L"Idempotency-Key:") == std::wstring::npos &&
                wireHeaders.find(L"X-Byte-Offset:") == std::wstring::npos && !uploadData && !callerBody);
        };
        for (const auto* value : {L"no-store", L"private, no-store", L"PRIVATE, NO-STORE"}) {
            reset(body); cacheHeader = value; check(true, 1);
        }
        reset(body); check(false, 0); // Missing header cannot inherit request no-store.
        reset(body); cacheHeader = L""; check(false, 0);
        for (const auto* value : {L"no-cache", L"no-store=1", L"xno-store", L"no-store\r\n", L"no-store,\u00e9"}) {
            reset(body); cacheHeader = value; check(false, 1);
        }
        const std::wstring limit = std::wstring(248, L' ') + L"no-store";
        assert(limit.size() == 256 && (limit.size() + 1) * sizeof(wchar_t) == 514);
        reset(body); cacheHeader = limit.c_str(); check(true, 1);
        const auto oversized = L" " + limit;
        reset(body); cacheHeader = oversized.c_str(); check(false, 0); // 516 UTF-16 bytes: no copy.
        for (const auto* point : {"cache_probe", "cache_read"}) {
            reset(body); cacheHeader = L"no-store"; failAt = point;
            check(false, std::string_view(point) == "cache_read" ? 1U : 0U);
        }
        reset(body); cacheHeader = L"no-store"; interruptAt = "cache_read";
        check(false, 1); assert(cancel->load() && reads == 0);
        reset(body); cacheHeader = L"no-store"; throwAt = "cache_read";
        check(false, 1); assert(reads == 0);
        // The header option stays off for existing callers, even if supplied.
        reset("{}"); cacheHeader = L"no-store"; receiptConfig.cancellation = cancel;
        const auto baseline = CustodyOwnedMemory::usedBytes();
        {
            const auto response = request<DesktopHttpTransport::ProtectedUploadResponse>(receiptConfig, L"GET", L"/synthetic", {}, true);
            assert(!response.transportFailed && response.cacheControl.empty() && cacheProbes == 0 && cacheCopies == 0);
        }
        assert(CustodyOwnedMemory::usedBytes() == baseline);
        std::fputs("local_cache_winhttp_header_stub=pass real_https_fixture=open\n", stderr);
    }

    reset(target);
    const auto resolved = DesktopHttpTransport(config).calendarJoinTarget(event, Clock::now() + std::chrono::seconds(15));
    assert(resolved.target && opens == 1 && sends == 1 && receives == 1 && closes.size() == 3);
    {
        const auto expectedPath = utf8ToWide(DesktopApiClient::calendarJoinTargetPath(event));
        assert(wireVerb == L"GET" && std::wstring_view(wirePath) == std::wstring_view(expectedPath.data(), expectedPath.size()));
        const auto unicode = utf8ToWide("GRAF \xd0\x92\xd1\x81\xd1\x82\xd1\x80\xd0\xb5\xd1\x87\xd0\xb0 \xf0\x9f\x8e\x99");
        assert(std::wstring_view(unicode.data(), unicode.size()) == L"GRAF \u0412\u0441\u0442\u0440\u0435\u0447\u0430 \U0001f399");
        assert(utf8ToWide({}).empty() && utf8ToWide("\xff").empty());
    }
    assert(wireHeaders.find(L"X-Device-Id") == std::wstring::npos && wireHeaders.find(L"foreign") == std::wstring::npos);
    assert(wireHeaders.find(L"X-Auth-Session: synthetic-session\r\n") != std::wstring::npos);
    assert(wireHeaders.find(L"X-Graf-Expected-Actor: 11111111-1111-4111-8111-111111111111\r\n") != std::wstring::npos);
    assert(wireHeaders.find(L"X-Graf-Expected-Workspace: 22222222-2222-4222-8222-222222222222\r\n") != std::wstring::npos);
    assert(options == 1);

    const auto call = [&](Clock::duration budget = std::chrono::seconds(15), bool limited = true) {
        config.cancellation = cancel;
        return request(config, L"GET", L"/synthetic", {}, true, {}, {}, {},
            limited ? std::optional<Clock::time_point>(instant + budget) : std::nullopt, fakeNow);
    };
    for (const auto* point : {"open", "timeouts", "connect", "request", "option", "send", "receive", "headers", "available", "read", "last_read", "eof"}) {
        for (const bool timeout : {false, true}) {
            reset(target); interruptAt = point; expire = timeout;
            const auto result = call();
            assert(result.transportFailed && opens == 1 && !closes.empty());
            if (std::string(point) == "send") assert(receives == 0 && reads == 0);
            if (std::string(point) == "receive" || std::string(point) == "headers") assert(reads == 0);
            if (std::string(point) == "available") assert(reads == 0);
            if (std::string(point) == "read" || std::string(point) == "last_read" || std::string(point) == "eof") assert(reads >= 1);
        }
    }
    for (const auto* point : {"open", "timeouts", "connect", "request", "option", "send", "receive", "headers", "available", "read"}) {
        reset(target); failAt = point;
        assert(call().transportFailed);
        if (std::string(point) == "timeouts" || std::string(point) == "option") assert(sends == 0);
    }
    for (const auto* point : {"send", "receive", "headers", "available", "read"}) {
        reset(target); throwAt = point; config.cancellation = cancel;
        const auto result = DesktopHttpTransport(config).calendarJoinTarget(event, Clock::now() + std::chrono::seconds(15));
        assert(result.state == CalendarJoinResolutionState::dependencyUnavailable && !result.target);
        assert(closes.size() == 3); // Exception cleanup runs on the same worker.
    }
    for (const std::size_t size : {65535U, 65536U, 65537U}) {
        reset(target + std::string(size - target.size(), ' '));
        const auto result = call();
        assert(result.transportFailed == (size > 65536) && result.body.size() <= 65536);
        assert(closes.size() == 3);
        if (!result.transportFailed) assert(result.body == responseBody && wireCursor == size);
    }
    reset(std::string(65537, ' ')); pretendNoData = true;
    assert(call().transportFailed && wireCursor == 65537); // EOF probe catches a hidden trailing byte.
    reset(target); readAdvance = std::chrono::milliseconds(5); chunk = 1;
    assert(call(std::chrono::milliseconds(12)).transportFailed && reads == 3);
    assert(budgets.front()[3] == 12 && budgets.back()[3] <= 2);
    reset(target);
    assert(!call(std::chrono::microseconds(500)).transportFailed);
    assert(std::all_of(budgets.begin(), budgets.end(), [](const auto& b) { return b[3] == 1; }));
    reset(target);
    assert(call(Clock::duration::zero()).transportFailed && opens == 0);
    reset(target);
    assert(!call(std::chrono::seconds(1), false).transportFailed && timeouts == 1);
    assert((budgets.front() == std::array<int, 4>{5000, 5000, 10000, 10000}));
    reset(std::string(2 * 1024 * 1024, ' '));
    assert(call(std::chrono::seconds(1), false).transportFailed); // Preserve legacy equal-cap refusal.
    reset(std::string(2 * 1024 * 1024 - 1, ' '));
    assert(!call(std::chrono::seconds(1), false).transportFailed);
    reset("{}"); retryHeader = L"17"; expiryHeader = L"1800000000";
    const auto withHeaders = request(config, L"PUT", L"/synthetic", {}, false, "synthetic-key",
        std::numeric_limits<std::uint64_t>::max(), "synthetic-hash");
    assert(!withHeaders.transportFailed && withHeaders.retryAfter == "17" && withHeaders.authExpiresAt == "1800000000");
    assert(wireHeaders.find(L"Idempotency-Key: synthetic-key\r\n") != std::wstring::npos);
    assert(wireHeaders.find(L"X-Byte-Offset: 18446744073709551615\r\n") != std::wstring::npos);
    assert(wireHeaders.find(L"X-Content-SHA256: synthetic-hash\r\n") != std::wstring::npos);
    reset(std::string(4096, ' ')); retryHeader = L"17"; expiryHeader = L"1800000000";
    {
        using Response = DesktopHttpTransport::ProtectedUploadResponse;
        static_assert(std::is_same_v<decltype(Response::body)::allocator_type, CustodyAllocator<char>>);
        const auto baseline = CustodyOwnedMemory::usedBytes();
        std::size_t proxies = 0;
        { Response empty; proxies = CustodyOwnedMemory::usedBytes() - baseline; }
        {
            const auto response = request<Response>(config, L"GET", L"/synthetic", {}, true);
            assert(!response.transportFailed && std::string_view(response.body) == responseBody);
            assert(response.retryAfter == "17" && response.authExpiresAt == "1800000000");
            assert(CustodyOwnedMemory::usedBytes() == baseline + proxies + response.body.capacity() + 1);
        }
        assert(CustodyOwnedMemory::usedBytes() == baseline);
    }
    // The body is already alive before quota pressure. Exercise both parser
    // construction and node allocation in an already-constructed reader, so
    // proxy/constructor termination cannot masquerade as catchable refusal.
    using AccountReader = json_detail::JsonReader<CustodyAllocator, CustodyString>;
    const std::string_view spaces = R"({"spaces":[{"id":"22222222-2222-4222-8222-222222222222","active":true}]})";
    for (const bool prebuilt : {false, true}) {
        const auto baseline = CustodyOwnedMemory::usedBytes();
        {
            DesktopHttpTransport::ProtectedUploadResponse live{200, spaces.data()};
            std::optional<AccountReader> reader;
            if (prebuilt) reader.emplace(std::string_view(live.body));
            quotaPressure.fill();
            bool caught = false;
            try {
                if (prebuilt) (void)reader->read();
                else (void)decodeActiveWorkspaceUsing<AccountReader>(live.body);
            } catch (const std::bad_alloc&) { caught = true; }
            assert(caught && quotaPressure.installed && std::string_view(live.body) == spaces);
            quotaPressure.release();
        }
        assert(CustodyOwnedMemory::usedBytes() == baseline);
    }
    std::fputs("account_parser_zero_quota_constructor=pass account_parser_zero_quota_read=pass\n", stderr);

    // Same native upload wrapper as production; fake WinHTTP only. Body must
    // outlive SendRequest, ReceiveResponse and request-handle close on failure.
    for (const auto* point : {"none", "send", "receive", "headers", "available", "read"}) {
        for (unsigned fault = 0; fault != 3; ++fault) {
            reset("{}"); config.cancellation = cancel;
            const auto baseline = CustodyOwnedMemory::usedBytes();
            DesktopHttpTransport::UploadRequest upload{"PUT", "/synthetic", "", false};
            upload.protectedBody = std::allocate_shared<CustodyBytes>(CustodyAllocator<CustodyBytes>{}, 65536, std::uint8_t{0x5a});
            callerBody = &upload.protectedBody; uploadOwner = upload.protectedBody;
            uploadData = upload.protectedBody->data(); uploadLength = upload.protectedBody->size();
            if (fault == 0) interruptAt = point;
            if (fault == 1) failAt = point;
            if (fault == 2) throwAt = point;
            bool threw = false;
            {
                DesktopHttpTransport::ProtectedUploadResponse response;
                try { response = sendUploadRequest<DesktopHttpTransport::ProtectedUploadResponse>(config, upload); }
                catch (const std::bad_alloc&) { threw = true; }
                assert(sends == 1 && !upload.protectedBody && closes.size() == 3);
                assert(uploadOwner.expired());
                uploadOwner.reset(); // The charged weak control block is released too.
                if (std::string_view(point) == "none") assert(!threw && !response.transportFailed);
                else assert(threw || response.transportFailed);
            }
            assert(CustodyOwnedMemory::usedBytes() == baseline);
        }
    }
    for (const auto* point : {"option", "retry", "expiry", "body"}) {
        const bool bodyCut = std::string_view(point) == "body";
        reset(bodyCut ? std::string(4096, ' ') : "{}");
        config.cancellation = cancel;
        const auto baseline = CustodyOwnedMemory::usedBytes();
        DesktopHttpTransport::UploadRequest upload{"PUT", "/synthetic", "", false};
        upload.protectedBody = std::allocate_shared<CustodyBytes>(CustodyAllocator<CustodyBytes>{}, 65536, std::uint8_t{0x5a});
        callerBody = &upload.protectedBody; uploadOwner = upload.protectedBody;
        uploadData = upload.protectedBody->data(); uploadLength = upload.protectedBody->size();
        const bool beforeSend = std::string_view(point) == "option";
        exhaustAtOption = beforeSend;
        exhaustAtHeader = !beforeSend && !bodyCut;
        exhaustAtAvailable = bodyCut;
        if (std::string_view(point) == "retry") retryHeader = L"11111111111111111111111111111111";
        if (std::string_view(point) == "expiry") expiryHeader = L"1800000000";
        bool caught = false;
        try { (void)sendUploadRequest<DesktopHttpTransport::ProtectedUploadResponse>(config, upload); } catch (const std::bad_alloc&) { caught = true; }
        if (bodyCut) std::fprintf(stderr, "RESPONSE_QUOTA installed=%u caught=%u sends=%u receives=%u reads=%u closes=%zu\n",
            quotaPressure.installed ? 1U : 0U, caught ? 1U : 0U, sends, receives, reads, closes.size());
        assert(caught && quotaPressure.installed && opens == 1 && options == 1 && sends == (beforeSend ? 0U : 1U) && receives == sends && reads == 0 && closes.size() == 3);
        assert(!upload.protectedBody && uploadOwner.expired());
        uploadOwner.reset(); quotaPressure.release();
        assert(CustodyOwnedMemory::usedBytes() == baseline);
    }
    std::fputs("winhttp_wide_quota_before_send=pass headers_quota_after_receive=pass handles_closed_before_body_release=pass\n", stderr);
    std::fputs("protected_response_quota_before_read=pass\n", stderr);
    reset("{}");
    DesktopHttpTransport::UploadRequest mixed{"PUT", "/synthetic", "ordinary", false};
    mixed.protectedBody = std::allocate_shared<CustodyBytes>(CustodyAllocator<CustodyBytes>{}, 1, std::uint8_t{});
    assert(!mixed.bodyView() && sendUploadRequest(config, mixed).transportFailed && opens == 0);
}
