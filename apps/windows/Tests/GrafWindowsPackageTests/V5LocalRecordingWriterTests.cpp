#include "../../RecApp/Recording/LocalRecordingPackage.h"
#include "../../RecApp/Storage/AtomicFileStore.h"
#include "../../RecApp/Upload/DesktopApiClient.h"
#include "../../RecApp/Upload/DesktopHttpTransport.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include "../GeneratedRecordingFixtures.h"
#include <cstdlib>
#include <ctime>
#include <fstream>
#include <limits>
#include <map>
#include <type_traits>

#ifdef _WIN32
#include <mfapi.h>
#include <mfidl.h>
#include <mfreadwrite.h>
#include <propvarutil.h>
#include <wrl/client.h>
#if defined(_MSC_VER) && defined(_DEBUG)
#include <crtdbg.h>
namespace {
thread_local std::size_t resultAllocation = 0, denyResultAllocation = 0;
int resultAllocationHook(int kind, void*, std::size_t, int, long, const unsigned char*, int) {
    return kind != _HOOK_ALLOC || !denyResultAllocation || ++resultAllocation != denyResultAllocation;
}
void resultAllocationCuts() {
    static_assert(!std::is_nothrow_default_constructible_v<graf::windows::V5WriterResult>);
    const auto previous = _CrtSetAllocHook(resultAllocationHook);
    for (std::size_t cut = 1; cut != 33; ++cut) {
        resultAllocation = 0; denyResultAllocation = cut;
        try {
            graf::windows::V5WriterResult result;
            result.packageDirectory = L"generated-only";
            result.wavSha256.assign(64, 'a'); result.playbackSha256.assign(64, 'b');
            std::optional<graf::windows::V5WriterResult> completion;
            completion.emplace(std::move(result)); // Must remain catchable in Debug.
        } catch (const std::bad_alloc&) {}
        denyResultAllocation = 0;
    }
    _CrtSetAllocHook(previous);
}
}
#endif
#endif

int main() {
    using namespace graf::windows;
#ifdef _MSC_VER
    _set_error_mode(_OUT_TO_STDERR);
    _set_abort_behavior(0, _WRITE_ABORT_MSG | _CALL_REPORTFAULT);
#endif
#if defined(_MSC_VER) && defined(_DEBUG)
    _CrtSetReportMode(_CRT_ASSERT, _CRTDBG_MODE_FILE);
    _CrtSetReportFile(_CRT_ASSERT, _CRTDBG_FILE_STDERR);
    resultAllocationCuts();
#endif
    const auto directory = std::filesystem::temp_directory_path() / "graf-feature-200-writer";
    const auto custodyRoot = directory / "custody";
    const auto escape = directory.parent_path() / "graf-feature-200-writer-escape";
    std::filesystem::remove_all(directory);
    std::filesystem::remove_all(escape);
    std::filesystem::create_directories(custodyRoot);
    assert(!AtomicFileStore::isWithinRoot(custodyRoot, escape));
#ifdef _WIN32
    {
        testing::GeneratedProtectedRecording capture("actual-native-aac");
        // Caller path strings cannot create storage authority or escape root.
        assert(!V5LocalRecordingWriter::open(capture.store, "../escape", capture.cancel).ok());
        assert(!std::filesystem::exists(capture.paths.parent/"escape"));
        capture.append(100);
        const auto result = capture.writer->finalize();
        assert(result.normalPackage() && result.durationMs == 1000);
        assert(result.wavBytes == 32044 && result.playbackBytes && result.semanticVerified);
        assert(result.startedAtMs && result.stoppedAtMs >= result.startedAtMs);
        assert(result.displayTimezoneOffsetMinutes >= -840 && result.displayTimezoneOffsetMinutes <= 840);
        const auto seconds = static_cast<std::time_t>(result.startedAtMs/1000);
        std::tm local{}; assert(localtime_s(&local,&seconds) == 0);
        char minute[32]{}; assert(std::strftime(minute,sizeof(minute),"%Y-%m-%d %H:%M",&local));
        assert(DesktopApiClient::formatDisplayMinute(result.startedAtMs,result.displayTimezoneOffsetMinutes) == minute);
        assert(!capture.writer->append(CanonicalAudioFrame{}));
        const auto repeated = capture.writer->finalize();
        assert(repeated.packageGeneration == result.packageGeneration && repeated.wavSha256 == result.wavSha256);
        auto pair = capture.coldPair(); assert(pair.ok());
        auto inspection = LocalRecordingPackage::inspectProtected(capture.paths.root,*pair.value,capture.session,capture.cancel);
        assert(inspection.ok() && (*inspection.value)->evidence().integrity == PackageIntegrity::valid);
        assert((*inspection.value)->evidence().durationMs == result.durationMs);
        assert((*inspection.value)->evidence().manifestSessionMatched);
        inspection.value.reset();
        const auto& package = (*pair.value)->current();
        const auto playback = std::find_if(package.refs.begin(), package.refs.begin()+package.refCount,
            [](const auto& ref) { return ref.role == CustodyRole::playback; });
        assert(playback != package.refs.begin()+package.refCount && playback->packed && playback->sealed &&
            playback->length && *playback->length && playback->generation && *playback->generation &&
            playback->containerId && playback->rootRef && playback->sha256);
        for (const bool busy : {false, true}) {
            std::optional<std::array<CustodyNativeJob, 2>> jobs;
            if (busy) { jobs.emplace(); for (const auto& job : *jobs) assert(job); }
            const auto decoded = LocalRecordingPackage::readProtectedPlayback(
                capture.paths.root, *pair.value, result.durationMs, capture.cancel);
            jobs.reset();
            std::fprintf(stderr, "PROTECTED_PLAYBACK held_jobs=%u ok=%u error=%u native=%u frames=%llu\n",
                busy ? 2U : 0U, decoded.ok() ? 1U : 0U, static_cast<unsigned>(decoded.error), decoded.nativeError,
                static_cast<unsigned long long>(decoded.ok() ? decoded.value->decodedFrames : 0));
            std::fflush(stderr);
            assert(decoded.ok() && decoded.value->decodedFrames > 0 &&
                "protected_pair_playback_must_fit_two_available_native_jobs");
        }
        for (const auto& entry : std::filesystem::recursive_directory_iterator(capture.paths.root)) {
            const auto name = entry.path().filename().string();
            assert(name != ".canonical-mix.f32.tmp" && name != "meeting-transcription.wav" &&
                name != "meeting-review.m4a" && name != "manifest.json" && name != "capture-recovery.json");
        }
    }
    {
        testing::GeneratedProtectedRecording capture("invalid-cleaned-frame");
        capture.append(1);
        CanonicalAudioFrame bad; bad.mixed[0] = std::numeric_limits<float>::quiet_NaN();
        assert(!capture.writer->append(bad) && !capture.writer->append(CanonicalAudioFrame{}));
        const auto retained = capture.writer->finalize(ReasonCode::aecUnavailable);
        assert(!retained.normalPackage() && retained.trustedPrefixRetained && retained.durationMs == 10);
        auto pair = capture.coldPair(); assert(pair.ok());
        auto inspected = LocalRecordingPackage::inspectProtected(capture.paths.root,*pair.value,capture.session,capture.cancel);
        assert(inspected.ok() && (*inspected.value)->evidence().trustedPrefixFrames == 1);
    }
    {
        testing::GeneratedProtectedRecording capture("interrupted-owner");
        capture.append(140); // Cross the full canonical block checkpoint.
        const auto context = capture.writer->packageContext();
        const auto snapshot = [&] {
            std::map<std::filesystem::path,std::string> result;
            for (const auto& entry : std::filesystem::recursive_directory_iterator(capture.paths.root))
                if (entry.is_regular_file()) {
                    const auto hash = sha256File(entry.path()); assert(!hash.empty());
                    result.emplace(entry.path(),hash);
                }
            return result;
        };
        const auto before = snapshot();
        assert(!V5LocalRecordingWriter::open(capture.store,capture.session,capture.cancel).ok());
        capture.writer.reset(); capture.store.reset();
        assert(snapshot() == before); // Destructor does no flush/recovery/IO.
        auto pair = ProtectedCustodyPackagePair::read(capture.paths.root,capture.session,context,capture.cancel);
        assert(pair.ok() && (*pair.value)->current().phase == CustodyPackagePhase::capturing);
        assert(snapshot() == before);
    }
#else
    assert(!V5LocalRecordingWriter::open({}, "portable", {}).ok());
#endif
    // Compatibility parser inputs below are generated data, not production
    // writer outputs or encoder success evidence.
    const auto result = testing::makeGeneratedLegacyPackage(directory, 1,
        ReasonCode::none, RecordingStopReason::interruption, "m4a-fixture");
    assert(result.durationMs == 10 && result.wavBytes > 44 && !result.wavSha256.empty());
    const auto package = LocalRecordingPackage::inspect(directory);
    // A matching digest proves bytes, not a usable AAC container.
    assert(package.integrity == PackageIntegrity::malformed && package.durationMs == 10);
    assert(LocalRecordingPackage::inspect(directory, directory.parent_path()).integrity == PackageIntegrity::malformed);
    UploadCustodyItem uploadItem;
    uploadItem.localRecordingId = uploadItem.directoryId = uploadItem.sessionId = "synthetic-recording";
    uploadItem.packageDirectory = directory;
    uploadItem.ownerUserId = "11111111-1111-4111-8111-111111111111";
    uploadItem.ownerWorkspaceId = "22222222-2222-4222-8222-222222222222";
    DesktopHttpConfig uploadConfig;
    uploadConfig.sessionToken = "synthetic-token-not-a-credential";
    uploadConfig.workspaceId = uploadItem.ownerWorkspaceId;
    uploadConfig.confirmedIdentity = DesktopAccountIdentity{uploadItem.ownerUserId, uploadItem.ownerWorkspaceId};
    unsigned sends = 0;
    const DesktopHttpTransport::UploadSend send = [&](const auto&, const auto&) {
        ++sends;
        return DesktopHttpTransport::UploadResponse{503, ""};
    };
    assert(DesktopHttpTransport(uploadConfig).upload(uploadItem, send).status == DesktopTransportStatus::invalidPackage);
    assert(sends == 0 && std::filesystem::exists(result.wavPath) && std::filesystem::exists(result.playbackPath));
    // The first accepted frame carries the start; finalization closes the bounds.
    // Ten milliseconds of audio cannot outlive the recording that produced it.
    assert(result.startedAtMs != 0 && result.stoppedAtMs >= result.startedAtMs);
    assert(result.stoppedAtMs - result.startedAtMs < 60'000);
    assert(result.displayTimezoneOffsetMinutes >= -14 * 60 && result.displayTimezoneOffsetMinutes <= 14 * 60);
    assert(package.startedAtMs == result.startedAtMs && package.stoppedAtMs == result.stoppedAtMs);
    assert(package.displayTimezoneOffsetMinutes == result.displayTimezoneOffsetMinutes);
    {
        // The stored offset has to agree with the operating system for the same
        // instant. This is an independent path: localtime plus strftime, not the
        // arithmetic that produced the offset or the label.
        const auto seconds = static_cast<std::time_t>(result.startedAtMs / 1000);
        std::tm local{};
#ifdef _WIN32
        assert(localtime_s(&local, &seconds) == 0);
#else
        assert(localtime_r(&seconds, &local) != nullptr);
#endif
        char buffer[32] = {};
        assert(std::strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M", &local) > 0);
        assert(DesktopApiClient::formatDisplayMinute(result.startedAtMs, result.displayTimezoneOffsetMinutes) == buffer);
    }
    {
        // A package written before the bounds existed stays readable and simply
        // reports no time instead of a guessed one.
        std::ifstream input(result.manifestPath);
        const std::string original((std::istreambuf_iterator<char>(input)), {});
        input.close();
        const auto bounds = original.find(",\"started_at_ms\":");
        assert(bounds != std::string::npos);
        const auto artifacts = original.find(",\"artifacts\":", bounds);
        assert(artifacts != std::string::npos);
        auto legacyManifest = original;
        legacyManifest.erase(bounds, artifacts - bounds);
        { std::ofstream output(result.manifestPath); output << legacyManifest; }
        const auto legacy = LocalRecordingPackage::inspect(directory, directory.parent_path());
        assert(legacy.integrity == PackageIntegrity::malformed && legacy.durationMs == 10);
        assert(legacy.startedAtMs == 0 && legacy.stoppedAtMs == 0 && legacy.displayTimezoneOffsetMinutes == 0);
        // An impossible pair is dropped; a recording never ends before it starts.
        const auto stoppedAt = original.find("\"stopped_at_ms\":");
        assert(stoppedAt != std::string::npos);
        const auto stoppedEnd = original.find(',', stoppedAt);
        assert(stoppedEnd != std::string::npos);
        auto corrupted = original;
        corrupted.replace(stoppedAt, stoppedEnd - stoppedAt,
            "\"stopped_at_ms\":" + std::to_string(result.startedAtMs - 1));
        { std::ofstream output(result.manifestPath); output << corrupted; }
        const auto rejected = LocalRecordingPackage::inspect(directory, directory.parent_path());
        assert(rejected.integrity == PackageIntegrity::malformed);
        assert(rejected.startedAtMs == 0 && rejected.stoppedAtMs == 0);
        { std::ofstream output(result.manifestPath); output << original; }
        const auto restored = LocalRecordingPackage::inspect(directory, directory.parent_path());
        assert(restored.startedAtMs == result.startedAtMs && restored.stoppedAtMs == result.stoppedAtMs);
    }
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
        assert(legacy.integrity == PackageIntegrity::malformed && legacy.durationMs == 10);
        const auto durationOffset = manifest.find("\"duration_ms\":10");
        assert(durationOffset != std::string::npos);
        manifest.replace(durationOffset, std::string("\"duration_ms\":10").size(), "\"duration_ms\":9999");
        { std::ofstream output(result.manifestPath); output << manifest; }
        const auto inconsistent = LocalRecordingPackage::inspect(directory, directory.parent_path());
        assert(inconsistent.integrity == PackageIntegrity::malformed);
        assert(inconsistent.durationMs == 0 && !inconsistent.playbackAvailable);
    }
    const auto failedDirectory = custodyRoot / "failed";
    testing::writeGeneratedPrefix(failedDirectory, 1, ReasonCode::finalizationFailed);
    assert(!std::filesystem::exists(failedDirectory/"meeting-transcription.wav"));
    assert(!std::filesystem::exists(failedDirectory/"meeting-review.m4a"));
    assert(LocalRecordingPackage::inspect(failedDirectory).integrity == PackageIntegrity::degraded);

    const auto prefixDirectory = custodyRoot / "prefix";
    const auto retained = testing::makeGeneratedLegacyPackage(prefixDirectory, 1,
        ReasonCode::endpointInvalidated, RecordingStopReason::interruption, "synthetic-playback");
    const auto prefixSnapshot = LocalRecordingPackage::inspect(prefixDirectory, custodyRoot);
    assert(prefixSnapshot.integrity == PackageIntegrity::degraded && prefixSnapshot.durationMs == 10);
    assert(!prefixSnapshot.playbackAvailable); // Literal is deliberately not AAC.
    {
        std::ifstream input(retained.manifestPath);
        const std::string manifest((std::istreambuf_iterator<char>(input)), {});
        assert(manifest.find("\"capture_status\":\"degraded\"") != std::string::npos);
        assert(manifest.find("endpoint_invalidated") != std::string::npos);
    }
    assert(std::filesystem::file_size(prefixDirectory/".canonical-mix.f32.tmp") == 480*sizeof(float));
    const auto interruptedDirectory = custodyRoot / "interrupted";
    testing::writeGeneratedPrefix(interruptedDirectory, 1, ReasonCode::finalizationFailed);
    assert(std::filesystem::file_size(interruptedDirectory/".canonical-mix.f32.tmp") == 480*sizeof(float));
    assert(std::filesystem::exists(interruptedDirectory/"capture-recovery.json"));
    assert(LocalRecordingPackage::inspect(interruptedDirectory).integrity == PackageIntegrity::degraded);
    const auto interrupted = LocalRecordingPackage::inspect(interruptedDirectory, custodyRoot);
    assert(!interrupted.playbackAvailable && interrupted.durationMs == 0);
#ifdef _WIN32
    // Guest/Windows runner exercises the real AAC encoder and container, not the
    // portable synthetic encoder. No input or output device/hardware is involved.
    assert(SUCCEEDED(CoInitializeEx(nullptr, COINIT_MULTITHREADED)));
    assert(SUCCEEDED(MFStartup(MF_VERSION)));
    {
        const auto encoded = testing::makeGeneratedLegacyPackage(custodyRoot/"native-aac", 100);
        assert(encoded.durationMs == 1000);
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
        assert((snapshot.trackBytes == std::array<std::uint64_t, 3>{
            std::filesystem::file_size(encoded.manifestPath), encoded.wavBytes, encoded.playbackBytes}));
        const auto metadataOnly = LocalRecordingPackage::inspect(encoded.packageDirectory);
        assert(metadataOnly.integrity == PackageIntegrity::valid && !metadataOnly.playbackAvailable);
        assert(!LocalRecordingPackage::inspect(encoded.packageDirectory, custodyRoot / "unrelated").playbackAvailable);
        reader.Reset();
        std::ifstream input(encoded.manifestPath);
        const std::string original((std::istreambuf_iterator<char>(input)), {});
        input.close();
        const auto bounds = original.find(",\"started_at_ms\":");
        const auto artifacts = original.find(",\"artifacts\":", bounds);
        assert(bounds != std::string::npos && artifacts != std::string::npos);
        auto legacy = original;
        legacy.erase(bounds, artifacts - bounds);
        { std::ofstream output(encoded.manifestPath); output << legacy; }
        const auto timeless = LocalRecordingPackage::inspect(encoded.packageDirectory, custodyRoot);
        assert(timeless.integrity == PackageIntegrity::valid && timeless.playbackAvailable && timeless.durationMs == 1000);
        assert(timeless.startedAtMs == 0 && timeless.stoppedAtMs == 0 && timeless.displayTimezoneOffsetMinutes == 0);
        const std::string status = ",\"capture_status\":\"normal\",\"capture_reason_code\":\"none\"";
        const auto statusOffset = legacy.find(status);
        assert(statusOffset != std::string::npos);
        legacy.erase(statusOffset, status.size());
        { std::ofstream output(encoded.manifestPath); output << legacy; }
        assert(LocalRecordingPackage::inspect(encoded.packageDirectory).integrity == PackageIntegrity::valid);
        auto impossible = original;
        const auto stopped = impossible.find("\"stopped_at_ms\":");
        const auto stoppedEnd = impossible.find(',', stopped);
        assert(stopped != std::string::npos && stoppedEnd != std::string::npos);
        impossible.replace(stopped, stoppedEnd - stopped, "\"stopped_at_ms\":" + std::to_string(encoded.startedAtMs - 1));
        { std::ofstream output(encoded.manifestPath); output << impossible; }
        const auto invalidTime = LocalRecordingPackage::inspect(encoded.packageDirectory);
        assert(invalidTime.integrity == PackageIntegrity::valid && invalidTime.startedAtMs == 0 && invalidTime.stoppedAtMs == 0);
        auto invalidOffset = original;
        const auto offset = invalidOffset.find("\"display_timezone_offset_minutes\":");
        const auto offsetEnd = invalidOffset.find(',', offset);
        assert(offset != std::string::npos && offsetEnd != std::string::npos);
        invalidOffset.replace(offset, offsetEnd - offset, "\"display_timezone_offset_minutes\":9999");
        { std::ofstream output(encoded.manifestPath); output << invalidOffset; }
        const auto invalidZone = LocalRecordingPackage::inspect(encoded.packageDirectory);
        assert(invalidZone.integrity == PackageIntegrity::valid && invalidZone.startedAtMs == 0 && invalidZone.stoppedAtMs == 0);
        { std::ofstream output(encoded.manifestPath); output << original; }
        assert(LocalRecordingPackage::inspect(encoded.packageDirectory).startedAtMs == encoded.startedAtMs);
    }
    {
        const auto source = testing::makeGeneratedLegacyPackage(custodyRoot/"longer-aac", 200);
        assert(LocalRecordingPackage::inspect(source.packageDirectory).integrity == PackageIntegrity::valid);
        std::ifstream sourceBytes(source.playbackPath, std::ios::binary);
        const std::string wrongDuration((std::istreambuf_iterator<char>(sourceBytes)), {});
        const auto encoded = testing::makeGeneratedLegacyPackage(custodyRoot/"duration-mismatch", 100,
            ReasonCode::none, RecordingStopReason::interruption, wrongDuration);
        assert(encoded.durationMs == 1000 && encoded.playbackSha256 == source.playbackSha256);
        for (const auto& root : {std::filesystem::path{}, custodyRoot}) {
            const auto snapshot = LocalRecordingPackage::inspect(encoded.packageDirectory, root);
            assert(snapshot.integrity == PackageIntegrity::malformed && snapshot.durationMs == 1000 && !snapshot.playbackAvailable);
        }
        uploadItem.packageDirectory = encoded.packageDirectory;
        assert(DesktopHttpTransport(uploadConfig).upload(uploadItem, send).status == DesktopTransportStatus::invalidPackage);
        assert(sends == 0 && std::filesystem::exists(encoded.wavPath) && std::filesystem::exists(encoded.playbackPath));
    }
    {
        const auto encoded = testing::makeGeneratedLegacyPackage(custodyRoot/"native-degraded", 100,
            ReasonCode::endpointInvalidated);
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
