#include "MetadataSafeDiagnostics.h"

#include <iomanip>
#include <locale>
#include <sstream>
#include <string_view>

namespace graf::windows {
namespace {

std::string_view clockFault(ClockFault fault) {
    switch (fault) {
    case ClockFault::none: return "none";
    case ClockFault::invalidPacket: return "invalid_packet";
    case ClockFault::timestampError: return "timestamp_error";
    case ClockFault::discontinuity: return "discontinuity";
    case ClockFault::nonMonotonic: return "non_monotonic";
    case ClockFault::sampleCountMismatch: return "sample_count_mismatch";
    case ClockFault::clockDrift: return "clock_drift";
    }
    return "unknown";
}

bool numericVersion(std::string_view value) {
    if (value.empty() || value.size() > 32) return false;
    bool needsDigit = true;
    for (const char character : value) {
        if (character >= '0' && character <= '9') needsDigit = false;
        else if (character == '.' && !needsDigit) needsDigit = true;
        else return false;
    }
    return !needsDigit;
}

std::string redactedEndpointFingerprint(std::string_view stableEndpointIdentity) {
    // FNV-1a is only a bounded redaction, not an authenticity or secrecy proof.
    std::uint64_t hash = 14695981039346656037ull;
    for (const unsigned char character : stableEndpointIdentity) {
        hash ^= character;
        hash *= 1099511628211ull;
    }
    std::ostringstream stream;
    stream.imbue(std::locale::classic());
    stream << "ep_" << std::hex << std::setfill('0') << std::setw(16) << hash;
    return stream.str();
}

} // namespace

std::string MetadataSafeDiagnostics::serialize(const MetadataSnapshot& snapshot) {
    const auto appVersion = numericVersion(snapshot.appVersion) || snapshot.appVersion == "development"
        ? std::string_view(snapshot.appVersion) : "development";
    const auto osBuild = numericVersion(snapshot.osBuild) || snapshot.osBuild == "unknown"
        ? std::string_view(snapshot.osBuild) : "unknown";
    const auto architecture = snapshot.architecture == "x64" || snapshot.architecture == "ARM64" ||
        snapshot.architecture == "x86" || snapshot.architecture == "unknown"
        ? std::string_view(snapshot.architecture) : "unknown";
    std::ostringstream json;
    json.imbue(std::locale::classic());
    json << "{"
         << "\"app_version\":\"" << appVersion << "\","
         << "\"os_build\":\"" << osBuild << "\","
         << "\"architecture\":\"" << architecture << "\","
         << "\"state\":\"" << toString(snapshot.state) << "\","
         << "\"reason_code\":\"" << toString(snapshot.reason) << "\","
         << "\"processed_blocks\":" << snapshot.processedBlocks << ","
         << "\"written_blocks\":" << snapshot.writtenBlocks << ","
         << "\"duration_ms\":" << snapshot.durationMs << ","
         << "\"endpoint_fingerprint\":\"" << redactedEndpointFingerprint(snapshot.endpointIdentity) << "\","
         << "\"trusted_prefix_retained\":" << (snapshot.trustedPrefixRetained ? "true" : "false") << ","
         << "\"render_startup_discarded_frames\":" <<
            (snapshot.renderClock.startupDiscardedFrames <= 4'800 ? snapshot.renderClock.startupDiscardedFrames : 0) << ","
         << "\"microphone_startup_discarded_frames\":" <<
            (snapshot.microphoneClock.startupDiscardedFrames <= 4'800 ? snapshot.microphoneClock.startupDiscardedFrames : 0) << ","
         << "\"render_clock_fault\":\"" << clockFault(snapshot.renderClock.fault) << "\","
         << "\"microphone_clock_fault\":\"" << clockFault(snapshot.microphoneClock.fault) << "\""
         << "}";
    return json.str();
}

} // namespace graf::windows
