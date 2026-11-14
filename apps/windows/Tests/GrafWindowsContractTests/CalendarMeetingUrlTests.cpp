#include "../../RecApp/Shell/CalendarMeetingOpener.h"
#include "../../RecApp/Shell/MeetingReminderModel.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>
#ifdef _WIN32
#include <winrt/Windows.Data.Json.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <icu.h>
#pragma comment(lib, "windowsapp.lib")
#pragma comment(lib, "icu.lib")
#endif

using graf::windows::CalendarMeetingOpener;
using graf::windows::MeetingReminderModel;

void asciiBoundaries() {
    for (const auto* url : {
        "http://example.org/join", "https://", "https://@example.org/join",
        "https://user:pass@example.org/join", "https://example.org\\@localhost/join",
        "https://%40example.org/join", "https://example.org%2fprivate/join",
        "https://example.org%5cprivate/join", "https://%256cocalhost/join",
        "https://%G0example.org/join", "https://example.org%/join",
        "https://example.org:/join", "https://example.org:-1/join",
        "https://example.org:65536/join", "https://example.org:999999999999/join",
        "https://[2001:::1]/join", "https://[2606:4700::1111]extra/join",
        "https://[.2606:4700::1111]/join", "https://[2606:4700::1111.]/join",
        "https://[.2606:4700::1111.]/join", "https://[%322606:4700::1111]/join",
        "https://[2606%3A4700::1111]/join", "https://[%2e2606:4700::1111]/join",
        "https://[2606:4700::1111%2e]/join",
        "https://example%00.org/join", "https://example%7f.org/join",
        "https://localhost/join", "https://%6cocalhost/join", "https://127.1/join",
        "https://0x7f000001/join", "https://[::ffff:127.0.0.1]/join",
        "https://192.0.2.1/join", "https://[2001:db8::1]/join"}) {
        assert(!CalendarMeetingOpener::validatedHTTPS(url));
        assert(!MeetingReminderModel::safeMeetingUrl(url));
    }
    for (const auto* url : {
        "https://conference/join", "https://meeting.local/join",
        "https://example.org:0/join", "https://example.org:65535/join",
        "https://8.8.8.8/join", "https://0x08080808/join", "https://134744072/join",
        "https://010.010.010.010/join", "https://%38.%38.%38.%38/join",
        "https://192.0.0.9/join", "https://[2001:1::1]/join",
        "https://[::ffff:8.8.8.8]/join", "https://256.0.2.1/join"}) {
        assert(CalendarMeetingOpener::validatedHTTPS(url));
        assert(MeetingReminderModel::safeMeetingUrl(url));
    }
    const std::string preserved = "https://zoom.us/j/12345678901?pwd=%2B%26%23%25+abc&x=1#Room%2FName";
    assert(CalendarMeetingOpener::validatedHTTPS(preserved) == preserved);
    std::string longest = "https://example.org/";
    longest.append(8192 - longest.size(), 'a');
    assert(CalendarMeetingOpener::validatedHTTPS(longest));
    longest += 'a';
    assert(!CalendarMeetingOpener::validatedHTTPS(longest));
    for (const unsigned control : {0u, 1u, 31u, 127u}) {
        auto url = preserved; url.push_back(static_cast<char>(control));
        assert(!CalendarMeetingOpener::validatedHTTPS(url));
    }
    assert(!CalendarMeetingOpener::validatedHTTPS(std::string("https://example.org/?x=") + '\xff'));
    for (const auto* bytes : {"\x80", "\xc0\xaf", "\xed\xa0\x80", "\xf4\x90\x80\x80"})
        assert(!CalendarMeetingOpener::validatedHTTPS(std::string("https://example.org/?x=") + bytes));
}

#ifdef _WIN32
void nativeUnicodeAndRepresentation() {
    // Native Win32 validation works on a cold thread: no apartment side effect.
    assert(CalendarMeetingOpener::validatedHTTPS("HTTPS://ＬＯＣＡＬＨＯＳＴ/join") == std::nullopt);
    assert(CalendarMeetingOpener::validatedHTTPS("https://ｃｏｎｆｅｒｅｎｃｅ/join?x=%2f#room") ==
        "https://conference/join?x=%2f#room");
    assert(CalendarMeetingOpener::validatedHTTPS("https://会议.example/join") == "https://xn--6oqu09l.example/join");
    assert(CalendarMeetingOpener::validatedHTTPS("https://0x08080808:0/join?x=%2f#room") ==
        "https://8.8.8.8:0/join?x=%2f#room");
    for (const auto* scalar : {u8"\u0085", u8"\u00ad", u8"\u200b", u8"\U000e0001", u8"\U000e0020",
        u8"\U000e007f", u8"\U00013430", u8"\U0001bca0", u8"\U0001d173"}) {
        for (const auto* prefix : {"https://example.org/path", "https://example.org/?x=", "https://example.org/#"})
            assert(!CalendarMeetingOpener::validatedHTTPS(std::string(prefix) + scalar));
        std::string encoded;
        constexpr char hex[] = "0123456789ABCDEF";
        for (const auto c : std::string(scalar)) {
            const auto byte = static_cast<unsigned char>(c);
            encoded += '%'; encoded += hex[byte >> 4]; encoded += hex[byte & 15];
        }
        assert(!CalendarMeetingOpener::validatedHTTPS("https://a" + encoded + ".example/join"));
    }
    // Known Foundation false positives in Plane14 are not copied (gate H1).
    for (const auto* scalar : {u8"\U0001f600", u8"\U000e0100", u8"\U000e0101", u8"\U000e0120", u8"\U00013440"}) {
        const auto url = std::string("https://example.org/?x=") + scalar;
        const auto safe = CalendarMeetingOpener::validatedHTTPS(url);
        assert(safe == url);
        assert(CalendarMeetingOpener::validatedHTTPS(*safe) == safe);
    }
}

void unchangedCorpus() {
    winrt::init_apartment(); // only the test fixture JSON reader needs this
    const auto path = std::filesystem::path(__FILE__).parent_path() / "Fixtures/calendar_join_host_policy.json";
    std::ifstream input(path, std::ios::binary);
    assert(input);
    const std::string bytes{std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
    const auto cases = winrt::Windows::Data::Json::JsonArray::Parse(winrt::to_hstring(bytes));
    assert(cases.Size() == 141);
    for (std::uint32_t i = 0; i < cases.Size(); ++i) {
        const auto row = cases.GetObjectAt(i);
        const auto url = winrt::to_string(row.GetNamedString(L"url"));
        const bool expected = row.GetNamedBoolean(L"allowed");
        const auto safe = CalendarMeetingOpener::validatedHTTPS(url);
        if (safe.has_value() != expected) std::fprintf(stderr, "Shared corpus mismatch at index %u\n", i);
        assert(safe.has_value() == expected);
        if (safe) assert(CalendarMeetingOpener::validatedHTTPS(*safe) == safe);
    }
    UVersionInfo version{}; u_getUnicodeVersion(version);
    std::printf("Native shared corpus: 141/141; system ICU Unicode %u.%u\n", static_cast<unsigned>(version[0]), static_cast<unsigned>(version[1]));
}
#endif

int main() {
    asciiBoundaries();
#ifdef _WIN32
    nativeUnicodeAndRepresentation();
    unchangedCorpus();
#else
    std::puts("Portable ASCII policy only; native IDNA/URI/corpus proof requires Windows.");
#endif
    std::puts("CalendarMeetingUrlTests passed");
}
