#include "../../RecApp/Shell/CalendarMeetingOpener.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <cstdio>
using graf::windows::CalendarMeetingOpener;
int main() {
    const auto native = CalendarMeetingOpener::nativeTarget;
    assert(native("HTTPS://US02WEB.ZOOM.US./j/12345678901?pwd=synthetic%2Bpass#fragment") ==
        "zoommtg://us02web.zoom.us/join?action=join&confno=12345678901&pwd=synthetic+pass#fragment");
    assert(native("https://zoom.com:443//j///123456789/?action=x&%63onfno=y&flag&&empty=&bad=%FF") ==
        "zoommtg://zoom.com:443/join?action=join&confno=123456789&flag&&empty=&bad");
    assert(native("https://zoom.us/j/%31%32%33%34%35%36%37%38%39?a=a%20b&b=%2f&c=%3a&d=%00") ==
        "zoommtg://zoom.us/join?action=join&confno=123456789&a=a%20b&b=/&c=:&d=%00");
    assert(native("https://zoom.us/j/123456789?x=%xx&%FF=x&a=b=c&p=[x]&x=%C0%AF") ==
        "zoommtg://zoom.us/join?action=join&confno=123456789&x=%25xx&=x&a=b%3Dc&p=%5Bx%5D&x");
    assert(native("https://teams.microsoft.com/l/%6deetup-join/synthetic?context=x#fragment") ==
        "msteams://teams.microsoft.com/l/%6deetup-join/synthetic?context=x#fragment");
    assert(native("https://telemost.yandex.ru/j/synthetic?x=%2f#fragment") ==
        "https://telemost.yandex.ru/j/synthetic?x=%2f#fragment");
    assert(native("https://zoom.us/j/123456789?&a&action=x&") ==
        "zoommtg://zoom.us/join?action=join&confno=123456789&&a&");
#ifdef _WIN32
    assert(native("https://zoom.us/j/123456789?x=%D0%AF&bad=%ED%A0%80") ==
        "zoommtg://zoom.us/join?action=join&confno=123456789&x=%D0%AF&bad");
#endif
    for (const auto* url : {"https://zoom.us.evil.test/j/123456789", "https://zoom.us:444/j/123456789",
            "https://zoom.us/j/12345678", "https://zoom.us/j/123456789012", "https://zoom.us/j/123456789/more",
            "https://teams.microsoft.com/l/other/synthetic", "https://telemost.yandex.ru:0/j/synthetic",
            "https://teams.microsoft.com/l/meetup-join/%FF", "https://telemost.yandex.ru/j/%FF",
            "https://example.org/meeting", "https://127.0.0.1/j/123456789", "zoommtg://zoom.us/join",
            "https://user@zoom.us/j/123456789"}) assert(!native(url));
    std::puts("CalendarMeetingNativeTargetTests passed; conversion only, no OS launch");
}
