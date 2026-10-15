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
DWORD wireStatus = 200;
std::wstring wireVerb, wirePath, wireHeaders;
unsigned opens = 0, sends = 0, receives = 0, queries = 0, reads = 0;
unsigned timeouts = 0, options = 0;
std::vector<std::array<int, 4>> budgets;
std::map<HINTERNET, unsigned> closes;
Clock::time_point instant;
Clock::time_point fakeNow() { return instant; }
std::shared_ptr<std::atomic_bool> cancel;
std::string interruptAt, failAt, throwAt;
bool expire = false, pretendNoData = false;
std::chrono::milliseconds readAdvance{0};
std::weak_ptr<const graf::windows::CustodyBytes> uploadOwner;
std::shared_ptr<const graf::windows::CustodyBytes>* callerBody = nullptr;
const void* uploadData = nullptr;
std::size_t uploadLength = 0;
bool exhaustAtOption = false;
const wchar_t* retryHeader = nullptr;
const wchar_t* expiryHeader = nullptr;
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
    return failAt != phase;
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
    return boundary("request") ? handle() : nullptr;
}
BOOL WINAPI testOption(HINTERNET h, DWORD option, LPVOID buffer, DWORD size) {
    ++options;
    assert(h == handle() && option == WINHTTP_OPTION_DISABLE_FEATURE && size == sizeof(DWORD));
    assert(*static_cast<DWORD*>(buffer) == (WINHTTP_DISABLE_REDIRECTS | WINHTTP_DISABLE_COOKIES));
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
    const auto value = std::wstring_view(name) == L"Retry-After" ? retryHeader : expiryHeader;
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
    *count = static_cast<DWORD>(std::min<std::size_t>(size, responseBody.size() - wireCursor));
    std::memcpy(buffer, responseBody.data() + wireCursor, *count);
    wireCursor += *count;
    instant += readAdvance;
    if (wireCursor == responseBody.size()) boundary("last_read");
    if (*count == 0) boundary("eof");
    return boundary("read");
}
BOOL WINAPI testClose(HINTERNET h) {
    requireUploadOwner();
    assert(++closes[h] == 1); return TRUE;
}
void reset(std::string body) {
    assert(!quotaPressure.bytes && !quotaPressure.installed); exhaustAtOption = false;
    retryHeader = expiryHeader = nullptr; exhaustAtHeader = exhaustAtAvailable = false;
    responseBody = std::move(body); wireCursor = 0; chunk = 4096; wireStatus = 200;
    opens = sends = receives = queries = reads = timeouts = options = 0;
    budgets.clear(); closes.clear(); wireHeaders.clear(); wireVerb.clear(); wirePath.clear();
    interruptAt.clear(); failAt.clear(); throwAt.clear(); expire = pretendNoData = false;
    readAdvance = std::chrono::milliseconds(0);
    uploadOwner.reset(); callerBody = nullptr; uploadData = nullptr; uploadLength = 0;
    instant = Clock::now(); cancel = std::make_shared<std::atomic_bool>(false);
}
} // namespace

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
