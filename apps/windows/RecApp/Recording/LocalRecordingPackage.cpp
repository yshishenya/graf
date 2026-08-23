#include "LocalRecordingPackage.h"

#include "../Storage/AtomicFileStore.h"

#include <fstream>
#include <iterator>

namespace graf::windows {

LocalRecordingPackageSnapshot LocalRecordingPackage::inspect(const std::filesystem::path& directory) {
    LocalRecordingPackageSnapshot result;
    result.directory = directory;
    const auto manifest = directory / "manifest.json";
    const auto wav = directory / "meeting-transcription.wav";
    const auto playback = directory / "meeting-review.m4a";
    result.localPurgeRegistered = std::filesystem::exists(directory / ".local-purge-registered");
    std::ifstream input(manifest, std::ios::binary);
    if (!input || !std::filesystem::exists(wav) || !std::filesystem::exists(playback)) return result;
    const std::string json((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    if (json.find("local-recording-manifest.v5") == std::string::npos ||
        json.find("canonical-mix.v1") == std::string::npos || json.find("\"media\"") == std::string::npos ||
        json.find("\"playback\"") == std::string::npos) {
        result.integrity = PackageIntegrity::malformed;
        return result;
    }
    result.integrity = PackageIntegrity::valid;
    const auto duration = json.find("\"duration_ms\":");
    if (duration != std::string::npos) {
        try { result.durationMs = std::stoull(json.substr(duration + 14)); }
        catch (...) { result.integrity = PackageIntegrity::malformed; return result; }
    }
    result.recordingId = directory.filename().string();
    return result;
}

bool LocalRecordingPackage::registerLocalPurge(
    const std::filesystem::path& directory,
    const std::filesystem::path& custodyRoot) {
    if (directory.empty() || !std::filesystem::is_directory(directory)) return false;
    const auto root = custodyRoot.empty() ? directory.parent_path() : custodyRoot;
    if (!AtomicFileStore::isWithinRoot(root, directory)) return false;
    const auto tombstone = directory / ".local-purge-registered";
    return AtomicFileStore::writeWithinRoot(root, tombstone, "local_purge_registered", 128).ok();
}

} // namespace graf::windows
