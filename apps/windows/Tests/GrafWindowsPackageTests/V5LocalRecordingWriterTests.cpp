#include "../../RecApp/Recording/LocalRecordingPackage.h"
#include "../../RecApp/Storage/AtomicFileStore.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <fstream>
#include <limits>

#ifdef _WIN32
#include <mfapi.h>
#include <mfidl.h>
#include <mfreadwrite.h>
#include <propvarutil.h>
#include <wrl/client.h>
#endif

int main() {
    using namespace graf::windows;
    const auto directory = std::filesystem::temp_directory_path() / "graf-feature-200-writer";
    const auto custodyRoot = directory / "custody";
    const auto escape = directory.parent_path() / "graf-feature-200-writer-escape";
    std::filesystem::remove_all(directory);
    std::filesystem::remove_all(escape);
    std::filesystem::create_directories(custodyRoot);
    assert(!AtomicFileStore::isWithinRoot(custodyRoot, escape));
    V5LocalRecordingWriter escapedWriter(custodyRoot, escape, [](const auto& path, const auto&, std::uint64_t) {
        std::ofstream output(path, std::ios::binary); output << "must-not-write"; return output.good();
    });
    CanonicalAudioFrame escapedFrame; escapedFrame.mixed.fill(0.25F);
    assert(!escapedWriter.append(escapedFrame));
    assert(!std::filesystem::exists(escape));

    V5LocalRecordingWriter writer(directory, [](const auto& path, const auto&, std::uint64_t) {
        std::ofstream output(path, std::ios::binary); output << "m4a-fixture"; return output.good();
    });
    CanonicalAudioFrame frame; frame.mixed.fill(0.25F);
    assert(writer.append(frame));
    const auto result = writer.finalize();
    assert(result.ok() && result.durationMs == 10 && result.wavBytes > 44 && !result.wavSha256.empty());
    assert(result.normalPackage());
    assert(writer.finalize().wavSha256 == result.wavSha256);
    assert(!writer.append(frame));
    const auto package = LocalRecordingPackage::inspect(directory);
    assert(package.integrity == PackageIntegrity::valid && package.durationMs == 10);
    assert(!package.playbackAvailable); // No explicit custody root / no real AAC fixture.
    assert(!LocalRecordingPackage::inspect(directory, custodyRoot).playbackAvailable);
    {
        // Existing Windows packages predate explicit capture status. Their
        // verified WAV still supplies duration; a conflicting duration cannot.
        std::ifstream input(result.manifestPath);
        std::string manifest((std::istreambuf_iterator<char>(input)), {});
        input.close();
        const std::string status = ",\"capture_status\":\"normal\",\"capture_reason_code\":\"none\"";
        const auto offset = manifest.find(status);
        assert(offset != std::string::npos);
        manifest.erase(offset, status.size());
        { std::ofstream output(result.manifestPath); output << manifest; }
        const auto legacy = LocalRecordingPackage::inspect(directory, directory.parent_path());
        assert(legacy.integrity == PackageIntegrity::valid && legacy.durationMs == 10);
        const auto durationOffset = manifest.find("\"duration_ms\":10");
        assert(durationOffset != std::string::npos);
        manifest.replace(durationOffset, std::string("\"duration_ms\":10").size(), "\"duration_ms\":9999");
        { std::ofstream output(result.manifestPath); output << manifest; }
        const auto inconsistent = LocalRecordingPackage::inspect(directory, directory.parent_path());
        assert(inconsistent.integrity == PackageIntegrity::malformed);
        assert(inconsistent.durationMs == 0 && !inconsistent.playbackAvailable);
    }
    const auto failedDirectory = custodyRoot / "failed";
    V5LocalRecordingWriter failedWriter(custodyRoot, failedDirectory,
        [](const auto& path, const auto&, std::uint64_t) {
            std::ofstream output(path, std::ios::binary);
            output << "partial-m4a";
            return false;
        });
    assert(failedWriter.append(frame));
    const auto failed = failedWriter.finalize();
    assert(!failed.ok());
    assert(!std::filesystem::exists(failed.wavPath));
    assert(!std::filesystem::exists(failed.playbackPath));
    assert(failed.trustedPrefixRetained && !failed.normalPackage());
    assert(LocalRecordingPackage::inspect(failedDirectory).integrity == PackageIntegrity::degraded);
    assert(failedWriter.finalize().error == failed.error);

    const auto prefixDirectory = custodyRoot / "prefix";
    {
        V5LocalRecordingWriter prefix(custodyRoot, prefixDirectory,
            [](const auto& path, const auto&, std::uint64_t frames) {
                assert(path.extension() == ".m4a" && frames == 1);
                std::ofstream output(path, std::ios::binary);
                output << "synthetic-playback";
                return output.good();
            });
        assert(prefix.append(frame));
        const auto retained = prefix.finalize(ReasonCode::endpointInvalidated);
        assert(retained.ok() && !retained.normalPackage() && retained.trustedPrefixRetained);
        assert(retained.captureFailure == ReasonCode::endpointInvalidated);
        const auto snapshot = LocalRecordingPackage::inspect(prefixDirectory, custodyRoot);
        assert(snapshot.integrity == PackageIntegrity::degraded && snapshot.durationMs == 10);
        assert(!snapshot.playbackAvailable); // A fixture string is not playable AAC.
        std::ifstream input(retained.manifestPath);
        const std::string manifest((std::istreambuf_iterator<char>(input)), {});
        assert(manifest.find("\"capture_status\":\"degraded\"") != std::string::npos);
        assert(manifest.find("endpoint_invalidated") != std::string::npos);
        assert(!prefix.finalize().normalPackage());
    }
    // Session replacement/destruction must keep the trusted prefix and its reason.
    const auto canonical = prefixDirectory / ".canonical-mix.f32.tmp";
    assert(std::filesystem::file_size(canonical) == 480 * sizeof(float));
    {
        V5LocalRecordingWriter replacement(custodyRoot, prefixDirectory);
        assert(!replacement.append(frame));
    }
    assert(std::filesystem::file_size(canonical) == 480 * sizeof(float));

    const auto interruptedDirectory = custodyRoot / "interrupted";
    {
        V5LocalRecordingWriter interrupted(custodyRoot, interruptedDirectory);
        assert(interrupted.append(frame));
    }
    assert(std::filesystem::file_size(interruptedDirectory / ".canonical-mix.f32.tmp") == 480 * sizeof(float));
    assert(std::filesystem::exists(interruptedDirectory / "capture-recovery.json"));
    assert(LocalRecordingPackage::inspect(interruptedDirectory).integrity == PackageIntegrity::degraded);
    const auto interrupted = LocalRecordingPackage::inspect(interruptedDirectory, custodyRoot);
    assert(!interrupted.playbackAvailable && interrupted.durationMs == 0);

    const auto invalidDirectory = custodyRoot / "invalid";
    {
        V5LocalRecordingWriter invalid(custodyRoot, invalidDirectory);
        assert(invalid.append(frame));
        auto bad = frame;
        bad.mixed[0] = std::numeric_limits<float>::quiet_NaN();
        assert(!invalid.append(bad));
        assert(!invalid.append(frame));
        const auto retained = invalid.finalize(ReasonCode::aecUnavailable);
        assert(!retained.normalPackage() && retained.trustedPrefixRetained);
    }
    assert(std::filesystem::file_size(invalidDirectory / ".canonical-mix.f32.tmp") == 480 * sizeof(float));
#ifdef _WIN32
    // Guest/Windows runner exercises the real AAC encoder and container, not the
    // portable synthetic encoder. No input or output device/hardware is involved.
    assert(SUCCEEDED(CoInitializeEx(nullptr, COINIT_MULTITHREADED)));
    assert(SUCCEEDED(MFStartup(MF_VERSION)));
    {
        V5LocalRecordingWriter native(custodyRoot, custodyRoot / "native-aac");
        for (int index = 0; index < 100; ++index) assert(native.append(frame));
        const auto encoded = native.finalize();
        assert(encoded.normalPackage() && encoded.durationMs == 1000);
        Microsoft::WRL::ComPtr<IMFSourceReader> reader;
        assert(SUCCEEDED(MFCreateSourceReaderFromURL(encoded.playbackPath.c_str(), nullptr, &reader)));
        PROPVARIANT duration;
        PropVariantInit(&duration);
        assert(SUCCEEDED(reader->GetPresentationAttribute(static_cast<DWORD>(MF_SOURCE_READER_MEDIASOURCE), MF_PD_DURATION, &duration)));
        assert(duration.vt == VT_UI8);
        const auto durationMs = duration.uhVal.QuadPart / 10'000;
        assert(durationMs >= 900 && durationMs <= 1100);
        PropVariantClear(&duration);
        const auto snapshot = LocalRecordingPackage::inspect(encoded.packageDirectory, custodyRoot);
        assert(snapshot.integrity == PackageIntegrity::valid && snapshot.playbackAvailable && snapshot.durationMs == 1000);
        assert(!LocalRecordingPackage::inspect(encoded.packageDirectory).playbackAvailable);
        assert(!LocalRecordingPackage::inspect(encoded.packageDirectory, custodyRoot / "unrelated").playbackAvailable);
        reader.Reset();
    }
    {
        V5LocalRecordingWriter native(custodyRoot, custodyRoot / "native-degraded");
        for (int index = 0; index < 100; ++index) assert(native.append(frame));
        const auto encoded = native.finalize(ReasonCode::endpointInvalidated);
        assert(!encoded.normalPackage() && encoded.trustedPrefixRetained);
        const auto snapshot = LocalRecordingPackage::inspect(encoded.packageDirectory, custodyRoot);
        assert(snapshot.integrity == PackageIntegrity::degraded && snapshot.playbackAvailable && snapshot.durationMs == 1000);
        {
            std::ofstream corrupt(encoded.playbackPath, std::ios::binary | std::ios::app);
            corrupt << "synthetic-corruption";
        }
        assert(!LocalRecordingPackage::inspect(encoded.packageDirectory, custodyRoot).playbackAvailable);
    }
    MFShutdown();
    CoUninitialize();
#endif
    {
        std::ofstream corrupt(prefixDirectory / "meeting-review.m4a", std::ios::binary | std::ios::app);
        corrupt << "synthetic-corruption";
    }
    const auto corrupted = LocalRecordingPackage::inspect(prefixDirectory, custodyRoot);
    assert(corrupted.integrity == PackageIntegrity::malformed && !corrupted.playbackAvailable);
    assert(corrupted.durationMs == 10); // The independent canonical WAV still verifies.
    assert(LocalRecordingPackage::inspect(prefixDirectory, escape).integrity == PackageIntegrity::malformed);
#ifndef _WIN32
    // No path escape through an artifact symlink, even with unchanged digest.
    const auto movedPlayback = custodyRoot / "outside-package.m4a";
    std::filesystem::rename(prefixDirectory / "meeting-review.m4a", movedPlayback);
    std::filesystem::create_symlink(movedPlayback, prefixDirectory / "meeting-review.m4a");
    assert(!LocalRecordingPackage::inspect(prefixDirectory, custodyRoot).playbackAvailable);
    // Exercise confinement independently of both AAC decoding and a bad digest.
    const auto movedWav = custodyRoot / "outside-package.wav";
    std::filesystem::rename(prefixDirectory / "meeting-transcription.wav", movedWav);
    std::filesystem::create_symlink(movedWav, prefixDirectory / "meeting-transcription.wav");
    const auto escapedMedia = LocalRecordingPackage::inspect(prefixDirectory, custodyRoot);
    assert(escapedMedia.integrity == PackageIntegrity::malformed && escapedMedia.durationMs == 0);
#endif
    std::filesystem::remove_all(directory);
    std::filesystem::remove_all(escape);
    return 0;
}
