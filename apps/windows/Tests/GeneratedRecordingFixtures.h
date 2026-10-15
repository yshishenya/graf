#pragma once

// Generated compatibility inputs only. This is not a writer, capture fallback,
// migration implementation or persistence ACK. All paths belong to test roots.
#include "../RecApp/Recording/LocalRecordingPackage.h"
#include "../RecApp/Recording/V5LocalRecordingWriter.h"
#include "../RecApp/Storage/Sha256.h"
#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <cstdio>
#include <ctime>
#include <fstream>
#include <optional>

namespace graf::windows::testing {

struct GeneratedRecordingRoot {
    std::filesystem::path parent, root;
    GeneratedRecordingRoot() {
        const auto name = "graf-generated-recording-" +
            std::to_string(std::chrono::steady_clock::now().time_since_epoch().count());
        parent = std::filesystem::temp_directory_path() / name;
        assert(std::filesystem::create_directory(parent));
#ifdef _WIN32
        // Native confinement compares long names; TEMP may contain an 8.3 alias.
        std::wstring longName(32768, L'\0');
        const auto n = GetLongPathNameW(parent.c_str(), longName.data(), static_cast<DWORD>(longName.size()));
        assert(n && n < longName.size()); longName.resize(n); parent = longName;
#endif
        root = parent / "recordings"; // The genuine StoreOwner births this child.
    }
    ~GeneratedRecordingRoot() { std::filesystem::remove_all(parent); }
    GeneratedRecordingRoot(const GeneratedRecordingRoot&) = delete;
};

#ifdef _WIN32
struct GeneratedProtectedRecording {
    GeneratedRecordingRoot paths; // Dies after native references, on this worker.
    std::shared_ptr<std::atomic<bool>> cancel = std::make_shared<std::atomic<bool>>(false);
    std::shared_ptr<ProtectedCustodyStoreOwner> store;
    std::shared_ptr<V5LocalRecordingWriter> writer;
    std::string session;
    explicit GeneratedProtectedRecording(std::string name) : session(std::move(name)) {
        auto opened = ProtectedCustodyStoreOwner::open(paths.root, cancel); assert(opened.ok());
        store = std::move(*opened.value);
        auto capture = V5LocalRecordingWriter::open(store, session, cancel); assert(capture.ok());
        writer = std::move(*capture.value);
        assert(writer->package()->current().phase == CustodyPackagePhase::capturing);
        assert(writer->package()->current().generation == 1);
    }
    void append(std::uint64_t count, float value = 0.25F) {
        CanonicalAudioFrame frame; frame.mixed.fill(value);
        for (std::uint64_t i = 0; i < count; ++i) {
            frame.ptsFrames = static_cast<std::int64_t>(writer->frameCount()*480);
            assert(writer->append(frame));
        }
    }
    auto coldPair() {
        const auto context = writer->packageContext();
        writer.reset(); store.reset();
        return ProtectedCustodyPackagePair::read(paths.root, session, context, cancel);
    }
};

inline void exportGeneratedPlayback(const std::filesystem::path& output, std::uint64_t frames) {
    GeneratedProtectedRecording capture("legacy-fixture-source");
    capture.append(frames);
    const auto sealed = capture.writer->finalize(ReasonCode::none, RecordingStopReason::interruption);
    if (!sealed.normalPackage()) std::fprintf(stderr,
        "GENERATED_AAC frames=%llu error=%u storage=%u native=%u phase=%u\n",
        static_cast<unsigned long long>(frames), static_cast<unsigned>(sealed.error),
        static_cast<unsigned>(sealed.storageError), sealed.nativeError, static_cast<unsigned>(sealed.packagePhase));
    assert(sealed.normalPackage() && sealed.durationMs == frames*10);
    auto pair = capture.coldPair(); assert(pair.ok());
    auto readers = openProtectedCustodyReaders(capture.paths.root, *pair.value, capture.cancel); assert(readers.ok());
    const auto slot = (*pair.value)->selectedSlot();
    const auto& refs = (*pair.value)->current();
    std::size_t index = 0;
    while (index < refs.refCount && refs.refs[index].role != CustodyRole::playback) ++index;
    assert(index < refs.refCount && refs.refs[index].length);
    auto* stream = readers.value->at(slot).at(index).stream.Get(); assert(stream);
    LARGE_INTEGER start{}; assert(stream->Seek(start, STREAM_SEEK_SET, nullptr) == S_OK);
    std::ofstream bytes(output, std::ios::binary); assert(bytes);
    std::array<char, 65536> chunk{};
    std::uint64_t copied = 0;
    while (copied < *refs.refs[index].length) {
        const auto wanted = static_cast<ULONG>(std::min<std::uint64_t>(chunk.size(), *refs.refs[index].length-copied));
        ULONG got = 0; assert(stream->Read(chunk.data(), wanted, &got) == S_OK && got == wanted);
        bytes.write(chunk.data(), got); assert(bytes); copied += got;
    }
    ULONG got = 0; assert(stream->Read(chunk.data(), 1, &got) == S_FALSE && !got);
}
#endif

struct GeneratedLegacyPackage {
    std::filesystem::path packageDirectory, manifestPath, wavPath, playbackPath;
    std::uint64_t durationMs = 0, wavBytes = 0, playbackBytes = 0;
    std::uint64_t startedAtMs = 0, stoppedAtMs = 0;
    int displayTimezoneOffsetMinutes = 0;
    std::string wavSha256, playbackSha256;
    bool shortRecordingDiscarded = false;
};

inline void writeGeneratedPrefix(const std::filesystem::path& directory,
    std::uint64_t frames, ReasonCode reason) {
    assert(frames && frames <= 10000); std::filesystem::create_directories(directory);
    const auto canonical = directory / ".canonical-mix.f32.tmp";
    std::array<float, 480> frame{}; frame.fill(0.25F);
    { std::ofstream out(canonical, std::ios::binary); assert(out);
      for (std::uint64_t i = 0; i < frames; ++i) out.write(reinterpret_cast<const char*>(frame.data()), sizeof(frame));
      assert(out); }
    std::ofstream recovery(directory / "capture-recovery.json"); assert(recovery);
    recovery << "{\"capture_status\":\"degraded\",\"capture_reason_code\":\"" << toString(reason)
        << "\",\"trusted_prefix_frames\":" << frames << ",\"canonical_bytes\":" << frames*1920
        << ",\"canonical_sha256\":\"" << sha256File(canonical) << "\"}";
    assert(recovery);
}

// An optional literal is deliberately invalid AAC for negative/portable cases.
// Windows' default obtains real AAC from the actual protected writer above.
inline GeneratedLegacyPackage makeGeneratedLegacyPackage(const std::filesystem::path& directory,
    std::uint64_t frames, ReasonCode reason = ReasonCode::none,
    RecordingStopReason stop = RecordingStopReason::interruption,
    std::optional<std::string> playback = std::nullopt) {
    assert(frames && frames <= 10000); std::filesystem::create_directories(directory);
    GeneratedLegacyPackage result;
    result.packageDirectory = directory; result.manifestPath = directory/"manifest.json";
    result.wavPath = directory/"meeting-transcription.wav"; result.playbackPath = directory/"meeting-review.m4a";
    result.durationMs = frames*10;
    result.startedAtMs = static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count());
    result.stoppedAtMs = result.startedAtMs;
    const auto seconds = static_cast<std::time_t>(result.startedAtMs/1000);
    std::tm local{}, utc{};
#ifdef _WIN32
    assert(localtime_s(&local,&seconds) == 0 && gmtime_s(&utc,&seconds) == 0);
    result.displayTimezoneOffsetMinutes = static_cast<int>(std::difftime(_mkgmtime(&local),_mkgmtime(&utc))/60);
#else
    assert(localtime_r(&seconds,&local) && gmtime_r(&seconds,&utc));
    result.displayTimezoneOffsetMinutes = static_cast<int>(std::difftime(timegm(&local),timegm(&utc))/60);
#endif
    // Fixed generated PCM fixture: no canonical temporary file or old writer.
    { std::ofstream wav(result.wavPath, std::ios::binary); assert(wav);
      const auto le = [&](std::uint32_t value, unsigned n) { for (unsigned i = 0; i < n; ++i) wav.put(static_cast<char>(value >> (8*i))); };
      wav.write("RIFF",4); le(static_cast<std::uint32_t>(frames*320+36),4); wav.write("WAVEfmt ",8);
      le(16,4); le(1,2); le(1,2); le(16000,4); le(32000,4); le(2,2); le(16,2);
      wav.write("data",4); le(static_cast<std::uint32_t>(frames*320),4);
      for (std::uint64_t i = 0; i < frames*160; ++i) le(8191,2);
      assert(wav); }
#ifdef _WIN32
    if (!playback) exportGeneratedPlayback(result.playbackPath, frames);
#else
    if (!playback) playback = "synthetic-playback";
#endif
    if (playback) { std::ofstream out(result.playbackPath,std::ios::binary); out << *playback; assert(out); }
    result.wavBytes = std::filesystem::file_size(result.wavPath); result.playbackBytes = std::filesystem::file_size(result.playbackPath);
    result.wavSha256 = sha256File(result.wavPath); result.playbackSha256 = sha256File(result.playbackPath);
    assert(!result.wavSha256.empty() && !result.playbackSha256.empty());
    result.shortRecordingDiscarded = isShortRecording(frames,stop,reason != ReasonCode::none);
    if (reason != ReasonCode::none) writeGeneratedPrefix(directory,frames,reason);
    std::ofstream manifest(result.manifestPath); assert(manifest);
    manifest << "{\"schema_version\":\"" << kManifestSchemaVersion << "\",\"canonical_mix_profile\":\"" << kCanonicalMixProfile
        << "\",\"source_kind\":\"" << kV5SourceKind << "\",\"media_scribe_source_mode\":\"" << kV5MediaScribeSourceMode
        << "\",\"capture_status\":\"" << (result.shortRecordingDiscarded ? "blocked" : reason == ReasonCode::none ? "normal" : "degraded")
        << "\",\"capture_reason_code\":\"" << toString(reason) << "\",\"duration_ms\":" << result.durationMs
        << ",\"started_at_ms\":" << result.startedAtMs << ",\"stopped_at_ms\":" << result.stoppedAtMs
        << ",\"display_timezone_offset_minutes\":" << result.displayTimezoneOffsetMinutes;
    if (result.shortRecordingDiscarded) manifest << ",\"short_recording_discarded\":true";
    manifest << ",\"artifacts\":{\"media\":{\"bytes\":" << result.wavBytes << ",\"sha256\":\"" << result.wavSha256
        << "\"},\"playback\":{\"bytes\":" << result.playbackBytes << ",\"sha256\":\"" << result.playbackSha256 << "\"}}}";
    assert(manifest); return result;
}

} // namespace graf::windows::testing
