#include "../../RecApp/Diagnostics/MetadataSafeDiagnostics.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <limits>
#include <locale>

namespace {
class GroupedNumbers final : public std::numpunct<char> {
    char do_thousands_sep() const override { return ','; }
    std::string do_grouping() const override { return "\3"; }
};
} // namespace

int main() {
    using namespace graf::windows;
    const MetadataSnapshot sample{"2026.09.06.1", "10.0.26200.9168", "x64", SessionState::failed,
        ReasonCode::clockDiscontinuity, 100, 97, 970, "ep_C:\\private\\endpoint", true,
        {480, ClockFault::clockDrift}, {441, ClockFault::sampleCountMismatch}};
    const auto json = MetadataSafeDiagnostics::serialize(sample);
    assert(json == "{\"app_version\":\"2026.09.06.1\",\"os_build\":\"10.0.26200.9168\","
        "\"architecture\":\"x64\",\"state\":\"failed\",\"reason_code\":\"clock_discontinuity\","
        "\"processed_blocks\":100,\"written_blocks\":97,\"duration_ms\":970,"
        "\"endpoint_fingerprint\":\"ep_22d61c6cfc6f3f20\",\"trusted_prefix_retained\":true,"
        "\"render_startup_discarded_frames\":480,\"microphone_startup_discarded_frames\":441,"
        "\"render_clock_fault\":\"clock_drift\",\"microphone_clock_fault\":\"sample_count_mismatch\"}");
    assert(json.find("dropped_frames") == std::string::npos);
    assert(json.find("overflow_count") == std::string::npos);

    auto snapshot = sample;
    for (const auto* endpoint : {"C:\\private\\endpoint", "ep_C:\\private\\endpoint",
                                "ep_0123456789abcdef", "ep_\"cookie=synthetic\ntranscript", ""}) {
        snapshot.endpointIdentity = endpoint;
        const auto output = MetadataSafeDiagnostics::serialize(snapshot);
        const std::string key = "\"endpoint_fingerprint\":\"ep_";
        const auto start = output.find(key);
        assert(start != std::string::npos);
        const auto fingerprint = output.substr(start + key.size(), 16);
        assert(fingerprint.find_first_not_of("0123456789abcdef") == std::string::npos);
        assert(output[start + key.size() + 16] == '"');
        assert(output.find("private") == std::string::npos);
        assert(output.find("cookie") == std::string::npos);
        assert(output.find("transcript") == std::string::npos);
        if (*endpoint) assert(output.find(endpoint) == std::string::npos);
        assert(output.size() <= 1024);
    }

    for (const auto* invalid : {"", "development ", "unknown ", "1..2", ".1", "1.", "-1", "+1",
                               "1e3", "1/2", "1\n2", "1\"2", "1\\2", "C:\\private", "cookie=synthetic"}) {
        snapshot.appVersion = snapshot.osBuild = snapshot.architecture = invalid;
        const auto output = MetadataSafeDiagnostics::serialize(snapshot);
        assert(output.find("\"app_version\":\"development\"") != std::string::npos);
        assert(output.find("\"os_build\":\"unknown\"") != std::string::npos);
        assert(output.find("\"architecture\":\"unknown\"") != std::string::npos);
    }
    snapshot.appVersion = snapshot.osBuild = std::string("1\0private", 9);
    const auto nul = MetadataSafeDiagnostics::serialize(snapshot);
    assert(nul.find("\"app_version\":\"development\"") != std::string::npos);
    assert(nul.find("\"os_build\":\"unknown\"") != std::string::npos);

    for (const auto* version : {"0", "1", "0.1.0", "2026.09.06.1"}) {
        snapshot.appVersion = snapshot.osBuild = version;
        const auto output = MetadataSafeDiagnostics::serialize(snapshot);
        assert(output.find("\"app_version\":\"" + std::string(version) + "\"") != std::string::npos);
        assert(output.find("\"os_build\":\"" + std::string(version) + "\"") != std::string::npos);
    }
    snapshot.appVersion = "development";
    snapshot.osBuild = "unknown";
    for (const auto* architecture : {"x64", "ARM64", "x86", "unknown"}) {
        snapshot.architecture = architecture;
        const auto output = MetadataSafeDiagnostics::serialize(snapshot);
        assert(output.find("\"architecture\":\"" + std::string(architecture) + "\"") != std::string::npos);
    }
    for (const auto* architecture : {"arm64", "X64", "amd64", "x86_64", "x64 "}) {
        snapshot.architecture = architecture;
        assert(MetadataSafeDiagnostics::serialize(snapshot).find("\"architecture\":\"unknown\"") != std::string::npos);
    }

    snapshot.appVersion = snapshot.osBuild = std::string(32, '9');
    snapshot.processedBlocks = snapshot.writtenBlocks = snapshot.durationMs = std::numeric_limits<std::uint64_t>::max();
    snapshot.state = SessionState::checkingReadiness;
    snapshot.reason = ReasonCode::formatNormalizationUnavailable;
    snapshot.renderClock = snapshot.microphoneClock = {4'800, ClockFault::sampleCountMismatch};
    const auto maximum = MetadataSafeDiagnostics::serialize(snapshot);
    assert(maximum.find("\"app_version\":\"" + std::string(32, '9') + "\"") != std::string::npos);
    assert(maximum.find("\"os_build\":\"" + std::string(32, '9') + "\"") != std::string::npos);
    assert(maximum.find("\"processed_blocks\":18446744073709551615") != std::string::npos);
    assert(maximum.find("\"written_blocks\":18446744073709551615") != std::string::npos);
    assert(maximum.find("\"duration_ms\":18446744073709551615") != std::string::npos);
    assert(maximum.size() <= 1024);
    assert(maximum.find("\"render_startup_discarded_frames\":4800,\"microphone_startup_discarded_frames\":4800") != std::string::npos);
    const auto previousLocale = std::locale::global(std::locale(std::locale::classic(), new GroupedNumbers));
    assert(MetadataSafeDiagnostics::serialize(snapshot) == maximum);
    std::locale::global(previousLocale);

    for (const auto size : {33, 1024 * 1024}) {
        snapshot.appVersion = snapshot.osBuild = snapshot.architecture = std::string(size, '9');
        snapshot.endpointIdentity = "ep_private_" + std::string(size, 'x');
        const auto output = MetadataSafeDiagnostics::serialize(snapshot);
        assert(output.find("\"app_version\":\"development\"") != std::string::npos);
        assert(output.find("\"os_build\":\"unknown\"") != std::string::npos);
        assert(output.find("\"architecture\":\"unknown\"") != std::string::npos);
        assert(output.find("private") == std::string::npos);
        assert(output.size() <= 1024);
    }
    const auto empty = MetadataSafeDiagnostics::serialize({});
    assert(empty.find("\"processed_blocks\":0,\"written_blocks\":0,\"duration_ms\":0") != std::string::npos);
    assert(empty.find("\"trusted_prefix_retained\":false") != std::string::npos);
    assert(empty.find("\"render_startup_discarded_frames\":0,\"microphone_startup_discarded_frames\":0") != std::string::npos);
    assert(empty.find("\"render_clock_fault\":\"none\",\"microphone_clock_fault\":\"none\"") != std::string::npos);
    for (const auto fault : {ClockFault::none, ClockFault::invalidPacket, ClockFault::timestampError,
                            ClockFault::discontinuity, ClockFault::nonMonotonic,
                            ClockFault::sampleCountMismatch, ClockFault::clockDrift}) {
        const char* names[]{"none", "invalid_packet", "timestamp_error", "discontinuity",
                            "non_monotonic", "sample_count_mismatch", "clock_drift"};
        snapshot.renderClock.fault = snapshot.microphoneClock.fault = fault;
        const auto output = MetadataSafeDiagnostics::serialize(snapshot);
        const std::string name = names[static_cast<int>(fault)];
        assert(output.find("\"render_clock_fault\":\"" + name + "\"") != std::string::npos);
        assert(output.find("\"microphone_clock_fault\":\"" + name + "\"") != std::string::npos);
    }
    snapshot.state = static_cast<SessionState>(-1);
    snapshot.reason = static_cast<ReasonCode>(-1);
    snapshot.renderClock = snapshot.microphoneClock = {std::numeric_limits<std::uint32_t>::max(), static_cast<ClockFault>(-1)};
    const auto unknown = MetadataSafeDiagnostics::serialize(snapshot);
    assert(unknown.find("\"state\":\"unknown\",\"reason_code\":\"unknown\"") != std::string::npos);
    assert(unknown.find("\"render_clock_fault\":\"unknown\",\"microphone_clock_fault\":\"unknown\"") != std::string::npos);
    assert(unknown.find("\"render_startup_discarded_frames\":0,\"microphone_startup_discarded_frames\":0") != std::string::npos);
    return 0;
}
