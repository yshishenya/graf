#include "MetadataSafeDiagnostics.h"

#include <iomanip>
#include <sstream>

namespace graf::windows {
namespace {

std::string escapeJson(std::string_view value) {
    std::string escaped;
    escaped.reserve(value.size() + 2);
    for (const unsigned char character : value) {
        switch (character) {
        case '"': escaped += "\\\""; break;
        case '\\': escaped += "\\\\"; break;
        case '\n': escaped += "\\n"; break;
        case '\r': escaped += "\\r"; break;
        case '\t': escaped += "\\t"; break;
        default:
            if (character < 0x20) {
                escaped += "?";
            } else {
                escaped += static_cast<char>(character);
            }
        }
    }
    return escaped;
}

std::string hex(std::uint64_t value) {
    std::ostringstream stream;
    stream << std::hex << std::setfill('0') << std::setw(16) << value;
    return stream.str();
}

} // namespace

std::string MetadataSafeDiagnostics::redactedEndpointFingerprint(std::string_view stableEndpointIdentity) {
    // FNV-1a is only a bounded redaction, not an authenticity or secrecy proof.
    std::uint64_t hash = 14695981039346656037ull;
    for (const unsigned char character : stableEndpointIdentity) {
        hash ^= character;
        hash *= 1099511628211ull;
    }
    return "ep_" + hex(hash);
}

std::string MetadataSafeDiagnostics::serialize(const MetadataSnapshot& snapshot) {
    const auto endpointFingerprint = snapshot.endpointFingerprint.rfind("ep_", 0) == 0
        ? snapshot.endpointFingerprint
        : redactedEndpointFingerprint(snapshot.endpointFingerprint);
    std::ostringstream json;
    json << "{"
         << "\"app_version\":\"" << escapeJson(snapshot.appVersion) << "\","
         << "\"os_build\":\"" << escapeJson(snapshot.osBuild) << "\","
         << "\"architecture\":\"" << escapeJson(snapshot.architecture) << "\","
         << "\"state\":\"" << toString(snapshot.state) << "\","
         << "\"reason_code\":\"" << toString(snapshot.reason) << "\","
         << "\"dropped_frames\":" << snapshot.droppedFrames << ","
         << "\"overflow_count\":" << snapshot.overflowCount << ","
         << "\"duration_ms\":" << snapshot.durationMs << ","
         << "\"endpoint_fingerprint\":\"" << escapeJson(endpointFingerprint) << "\""
         << "}";
    return json.str();
}

} // namespace graf::windows
