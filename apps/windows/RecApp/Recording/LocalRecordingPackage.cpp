#include "LocalRecordingPackage.h"

#include "../Storage/AtomicFileStore.h"
#include "../Storage/Sha256.h"

#include <array>
#include <charconv>
#include <cstring>
#include <fstream>
#include <regex>

#ifdef _WIN32
#include <mfapi.h>
#include <mfidl.h>
#include <mfreadwrite.h>
#include <propvarutil.h>
#include <wrl/client.h>
#endif

namespace graf::windows {
namespace {

bool confinedFile(const std::filesystem::path& directory, const std::filesystem::path& path) {
    std::error_code error;
    const auto status = std::filesystem::symlink_status(path, error);
    return !error && std::filesystem::is_regular_file(status) &&
        AtomicFileStore::isWithinRoot(directory, path);
}

bool parseNumber(const std::string& text, std::uint64_t& value) {
    const auto parsed = std::from_chars(text.data(), text.data() + text.size(), value);
    return parsed.ec == std::errc{} && parsed.ptr == text.data() + text.size();
}

bool matchesArtifact(const std::filesystem::path& directory, const std::filesystem::path& path,
                     std::uint64_t bytes, const std::string& hash) {
    if (bytes == 0 || !confinedFile(directory, path)) return false;
    std::error_code error;
    const auto size = std::filesystem::file_size(path, error);
    return !error && size == bytes && sha256File(path) == hash;
}

bool canonicalWav(const std::filesystem::path& path, std::uint64_t bytes, std::uint64_t durationMs) {
    std::array<unsigned char, 44> header{};
    std::ifstream input(path, std::ios::binary);
    if (!input.read(reinterpret_cast<char*>(header.data()), static_cast<std::streamsize>(header.size()))) return false;
    const auto u32 = [&](std::size_t offset) {
        return std::uint32_t(header[offset]) | (std::uint32_t(header[offset + 1]) << 8) |
            (std::uint32_t(header[offset + 2]) << 16) | (std::uint32_t(header[offset + 3]) << 24);
    };
    return std::memcmp(header.data(), "RIFF", 4) == 0 &&
        std::memcmp(header.data() + 8, "WAVEfmt ", 8) == 0 &&
        std::memcmp(header.data() + 36, "data", 4) == 0 &&
        u32(16) == 16 && u32(20) == 0x00010001 && u32(24) == 16'000 &&
        u32(28) == 32'000 && u32(32) == 0x00100002 &&
        bytes >= 44 && u32(4) == bytes - 8 && u32(40) == bytes - 44 &&
        (bytes - 44) % 32 == 0 && (bytes - 44) / 32 == durationMs;
}

bool canonicalPlayback(const std::filesystem::path& path, std::uint64_t durationMs) {
#ifndef _WIN32
    (void)path;
    (void)durationMs;
    return false; // The portable lane cannot attest to an AAC decoder.
#else
    const auto com = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    if (FAILED(com) && com != RPC_E_CHANGED_MODE) return false;
    const bool started = SUCCEEDED(MFStartup(MF_VERSION));
    bool valid = false;
    if (started) {
        Microsoft::WRL::ComPtr<IMFSourceReader> reader;
        Microsoft::WRL::ComPtr<IMFMediaType> type;
        GUID subtype{};
        UINT32 rate = 0, channels = 0;
        PROPVARIANT duration;
        PropVariantInit(&duration);
        if (SUCCEEDED(MFCreateSourceReaderFromURL(path.c_str(), nullptr, &reader)) &&
            SUCCEEDED(reader->GetNativeMediaType(static_cast<DWORD>(MF_SOURCE_READER_FIRST_AUDIO_STREAM), 0, &type)) &&
            SUCCEEDED(type->GetGUID(MF_MT_SUBTYPE, &subtype)) && subtype == MFAudioFormat_AAC &&
            SUCCEEDED(type->GetUINT32(MF_MT_AUDIO_SAMPLES_PER_SECOND, &rate)) && rate == 48'000 &&
            SUCCEEDED(type->GetUINT32(MF_MT_AUDIO_NUM_CHANNELS, &channels)) && channels == 1 &&
            SUCCEEDED(reader->GetPresentationAttribute(static_cast<DWORD>(MF_SOURCE_READER_MEDIASOURCE), MF_PD_DURATION, &duration)) &&
            duration.vt == VT_UI8) {
            const auto actualMs = duration.uhVal.QuadPart / 10'000;
            valid = actualMs > 0 && (actualMs > durationMs ? actualMs - durationMs : durationMs - actualMs) <= 100;
        }
        PropVariantClear(&duration);
    } // Release reader/type before MFShutdown.
    if (started) MFShutdown();
    if (SUCCEEDED(com)) CoUninitialize();
    return valid;
#endif
}

} // namespace

LocalRecordingPackageSnapshot LocalRecordingPackage::inspect(
    const std::filesystem::path& directory, const std::filesystem::path& custodyRoot) {
    LocalRecordingPackageSnapshot result;
    result.directory = directory;
    const auto root = custodyRoot.empty() ? directory.parent_path() : custodyRoot;
    if (!AtomicFileStore::isWithinRoot(root, directory)) {
        result.integrity = PackageIntegrity::malformed;
        return result;
    }
    result.recordingId = directory.filename().string();
    const auto manifest = directory / "manifest.json";
    const auto wav = directory / "meeting-transcription.wav";
    const auto playback = directory / "meeting-review.m4a";
    const bool retained = confinedFile(directory, directory / "capture-recovery.json") ||
        confinedFile(directory, directory / ".canonical-mix.f32.tmp");
    if (retained) result.integrity = PackageIntegrity::degraded;
    if (!confinedFile(directory, manifest)) return result;
    std::error_code error;
    const auto size = std::filesystem::file_size(manifest, error);
    if (error || size == 0 || size > 4096) { result.integrity = PackageIntegrity::malformed; return result; }
    std::string json(static_cast<std::size_t>(size), '\0');
    std::ifstream input(manifest, std::ios::binary);
    if (!input.read(json.data(), static_cast<std::streamsize>(json.size()))) return result;

    // Exact bounded serialization emitted by the Windows writer, including its
    // pre-capture-status form. Do not infer validity from matching substrings.
    static const std::regex shape(
        R"manifest(\{"schema_version":"local-recording-manifest\.v5","canonical_mix_profile":"canonical-mix\.v1","source_kind":"initial_mixed_recording","media_scribe_source_mode":"single_wav_v1"(?:,"capture_status":"(normal|degraded)","capture_reason_code":"([a-z_]+)")?,"duration_ms":([0-9]+),"artifacts":\{"media":\{"bytes":([0-9]+),"sha256":"([0-9a-f]{64})"\},"playback":\{"bytes":([0-9]+),"sha256":"([0-9a-f]{64})"\}\}\})manifest");
    std::smatch fields;
    std::uint64_t durationMs = 0, wavBytes = 0, playbackBytes = 0;
    if (!std::regex_match(json, fields, shape) ||
        !parseNumber(fields[3].str(), durationMs) || durationMs == 0 ||
        !parseNumber(fields[4].str(), wavBytes) ||
        !parseNumber(fields[6].str(), playbackBytes)) {
        result.integrity = PackageIntegrity::malformed;
        return result;
    }
    const bool mediaValid = matchesArtifact(directory, wav, wavBytes, fields[5].str()) &&
        canonicalWav(wav, wavBytes, durationMs);
    const bool playbackMatches = matchesArtifact(directory, playback, playbackBytes, fields[7].str());
    const bool degraded = retained || fields[1].str() == "degraded" ||
        (fields[2].matched && fields[2].str() != "none");
    result.integrity = mediaValid && playbackMatches
        ? (degraded ? PackageIntegrity::degraded : PackageIntegrity::valid)
        : PackageIntegrity::malformed;
    // Playback eligibility is independent of upload eligibility. Require an
    // explicit custody root for UI file access; old metadata-only callers keep
    // their signature and cannot accidentally authorize opening an arbitrary path.
    result.playbackAvailable = !custodyRoot.empty() && playbackMatches && canonicalPlayback(playback, durationMs);
    if (mediaValid || result.playbackAvailable) result.durationMs = durationMs;
    return result;
}

} // namespace graf::windows
