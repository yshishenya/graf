#ifdef NDEBUG
#undef NDEBUG
#endif
#include "../../RecApp/Audio/RecordingAudioTimeline.h"
#include "../../RecApp/Capture/WindowsCaptureSessionController.h"
#include "../../RecApp/Audio/AudioNormalizer.h"
#include "../../RecApp/Audio/ClockMapper.h"
#include "../GrafWindowsCoreTests/AutomaticRecordingTestSupport.h"
#ifdef _WIN32
#include "../GeneratedRecordingFixtures.h"
#include "../../RecApp/Upload/DesktopUploadQueueService.h"
#include <mfapi.h>
#include <mfidl.h>
#include <mfreadwrite.h>
#include <shlwapi.h>
#endif

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <cstdio>
#include <future>

using namespace graf::windows;

namespace graf::windows {
// Replace only devices/clock. Admission, worker mailbox, FIFO, privacy epochs,
// dispatcher, Stop and finalizer are the production implementations.
struct CaptureSessionTestPeer {
    using ClockSample = WasapiCaptureWorker::ResumeClockSample;
    static ClockSample clockSample() {
        return {0, 479 * 8, 384'000, 48'000, 997, 1000, 1000, 10'000'000,
            std::chrono::system_clock::now(), std::chrono::steady_clock::now()};
    }
    static void devices(WindowsCaptureSessionController& c, bool selected = true,
                        std::function<ClockSample()> clock = clockSample) {
        c.setEndpoints({"render", "Generated render", WasapiDataFlow::render, 48000, 1, true, false, 1},
                       {"mic", "Generated microphone", WasapiDataFlow::capture, 48000, 1, true, true, 1}, selected);
        c.renderWorker_->deviceRunForTesting_ = [](const auto& running, auto& ready, const auto&) {
            ready.store(true);
            while (running.load()) std::this_thread::yield();
        };
        auto& mic = *c.microphoneWorker_;
        mic.deviceRunForTesting_ = [&mic, clock](const auto& running, auto&, const auto&) {
            ClockMapper mapper; AudioNormalizer normalizer;
            const std::array<float, 480> data{};
            assert(mic.consumePacket(mapper, normalizer,
                {0, 0, 48000, 0, 480, 479 * 8, 384000, 0}, data.data(), 1, true,
                [](std::uint32_t) { return CaptureReleaseResult{true, 0}; }, mic.capturePrivacyEpoch()));
            while (running.load()) { mic.servicePrivacyResume(clock); std::this_thread::yield(); }
        };
    }
    static bool enqueue(WindowsCaptureSessionController& c, AudioBatch batch) { return c.enqueueBatch(std::move(batch)); }
    static void loss(WindowsCaptureSessionController& c, std::string_view id = "mic",
                     std::optional<std::uint32_t> state = 8, bool removed = false, bool render = false) {
        (render ? c.renderWorker_ : c.microphoneWorker_)->observeEndpointLoss(id, state, removed);
    }
    static void foreignGeneration(WindowsCaptureSessionController& c) {
        WasapiCaptureWorker old({"mic", "Old generation", WasapiDataFlow::capture, 48000, 1, true, true, 1}, false);
        c.selectedMicrophoneLost(&old);
    }
    static bool lost(const WindowsCaptureSessionController& c) { return c.microphoneLost_.load(); }
    static unsigned ends(const WindowsCaptureSessionController& c) { return c.sourceEndsProcessed_.load(); }
    static void fault(WindowsCaptureSessionController& c, ReasonCode reason) { c.latchFault(reason); }
    static void renderFailure(WindowsCaptureSessionController& c) { c.renderWorker_->completeNativeStop(-1); }
    static auto holdSink(WindowsCaptureSessionController& c) { return std::unique_lock<std::mutex>(c.captureMutex_); }
    static auto epoch(const WindowsCaptureSessionController& c) { return c.microphonePrivacyEpoch_.load(); }
    static auto recordingStart(const WindowsCaptureSessionController& c) { return c.recordingClockStart_; }
    static bool readyResume(WindowsCaptureSessionController& c, std::atomic_bool& entered, std::atomic_bool& release) {
        return c.microphoneWorker_->resumeMicrophone([&](const auto& receipt, auto deadline) {
            entered.store(true); // The real mailbox invokes apply only for READY.
            while (!release.load()) std::this_thread::yield();
            return c.applyPrivacyBoundary(false, receipt.expectedEpoch, deadline);
        }).has_value();
    }
};
}

namespace {
template<class Predicate> void waitFor(Predicate predicate) {
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(4);
    while (!predicate()) {
        assert(std::chrono::steady_clock::now() < deadline);
        std::this_thread::yield();
    }
}
void start(WindowsCaptureSessionController& c) {
    assert(c.record(testing::ready().capture).accepted());
    waitFor([&] { return c.pollHealth().state == SessionState::recording; });
}
void finish(WindowsCaptureSessionController& c) {
    (void)c.stop();
    waitFor([&] {
        const auto state = c.pollHealth().state;
        return state == SessionState::failed || state == SessionState::savedLocal;
    });
    assert(CaptureSessionTestPeer::ends(c) == 3);
}
struct TailAec final : IAec3Processor {
    std::vector<std::array<float, 480>> inputs;
    bool fail = false, nonfinite = false;
    bool process(const float*, const float* mic, float* cleaned) noexcept override {
        std::array<float, 480> input{};
        std::copy_n(mic, 480, input.begin()); inputs.push_back(input);
        for (unsigned i = 0; i < 480; ++i)
            cleaned[i] = nonfinite ? std::numeric_limits<float>::quiet_NaN() : mic[i] * 0.5F + 0.125F;
        return !fail;
    }
};

constexpr std::int64_t S = 48'000'000'123;
AudioBatch samples(AudioSource source, std::int64_t offset, std::size_t count) {
    AudioBatch batch{source, 48'000, 1, S + offset, 1, 7, false, {}, static_cast<std::uint64_t>(offset)};
    for (std::size_t i = 0; i < count; ++i)
        batch.samples.push_back(source == AudioSource::microphone ? 0.5F : 0.1F + static_cast<float>(offset + i) / 10'000);
    return batch;
}

void timelineBoundary() {
    for (const auto boundary : {719, 960}) for (const bool renderFirst : {false, true}) {
        TailAec aec;
        RecordingAudioTimeline timeline(aec);
        if (renderFirst) assert(timeline.push(samples(AudioSource::systemRender, 0, 1440)));
        assert(timeline.push(samples(AudioSource::microphone, 0, boundary)));
        if (!renderFirst) assert(timeline.push(samples(AudioSource::systemRender, 0, 480)));
        assert(timeline.endMicrophone());
        assert(timeline.endMicrophone()); // A repeated event never moves B.
        assert(!timeline.push(samples(AudioSource::microphone, boundary, 480)));
        if (!renderFirst) assert(timeline.push(samples(AudioSource::systemRender, 480, 960)));
        assert(timeline.close());
        const auto frames = timeline.takeFrames();
        assert(frames.size() == 3 && aec.inputs.size() == 3);
        for (unsigned f = 0; f < 3; ++f) for (unsigned i = 0; i < 480; ++i) {
            const auto at = f * 480 + i;
            const auto system = 0.1F + static_cast<float>(at) / 10'000;
            assert(frames[f].ptsFrames == S + f * 480);
            assert(frames[f].system[i] == system);
            assert(aec.inputs[f][i] == (at < static_cast<unsigned>(boundary) ? 0.5F : 0));
            const auto cleaned = at < static_cast<unsigned>(boundary) ? 0.375F : 0;
            assert(frames[f].microphone[i] == cleaned);
            assert(std::abs(frames[f].mixed[i] - 0.5F * (system + cleaned)) < 0.000001F);
        }
    }
    for (unsigned fault = 0; fault < 4; ++fault) {
        TailAec aec;
        RecordingAudioTimeline timeline(aec);
        assert(timeline.push(samples(AudioSource::systemRender, 0, 480)));
        assert(timeline.push(samples(AudioSource::microphone, 0, 480)));
        assert(timeline.takeFrames().size() == 1 && timeline.endMicrophone());
        auto next = samples(AudioSource::systemRender, 480, 480);
        if (fault == 0) ++next.routeGeneration;
        if (fault == 1) next.ptsFrames += 49;
        aec.fail = fault == 2; aec.nonfinite = fault == 3;
        assert(!timeline.push(std::move(next)) && !timeline.healthy());
        assert(timeline.takeFrames().empty());
    }
    TailAec aec;
    RecordingAudioTimeline noBoundary(aec);
    assert(!noBoundary.endMicrophone()); // Never invent the missing start/range.
}

void orderedContinuation() {
    for (const unsigned boundary : {719U, 960U}) {
        TailAec aec; RecordingAudioTimeline timeline(aec);
        std::atomic_bool entered{false}, release{false};
        std::atomic<unsigned> ends{0};
        unsigned finalized = 0, microphoneBatches = 0;
        std::vector<CanonicalAudioFrame> frames;
        WindowsCaptureSessionController c("selected-mic-order", [&](AudioBatch batch) {
            if (batch.source == AudioSource::systemRender && !entered.exchange(true))
                waitFor([&] { return release.load(); });
            if (batch.source == AudioSource::microphone) ++microphoneBatches;
            return timeline.push(std::move(batch)) ? ReasonCode::none : ReasonCode::clockDiscontinuity;
        }, [&](ReasonCode reason, RecordingStopReason) {
            ++finalized; assert(timeline.close()); frames = timeline.takeFrames();
            return CaptureFinalization{false, reason, true};
        }, {}, {}, [&] {
            const bool ended = timeline.endMicrophone(); ++ends;
            return ended ? ReasonCode::none : ReasonCode::clockDiscontinuity;
        });
        CaptureSessionTestPeer::devices(c); start(c);
        assert(CaptureSessionTestPeer::enqueue(c, samples(AudioSource::systemRender, 0, 1440)));
        waitFor([&] { return entered.load(); });
        assert(CaptureSessionTestPeer::enqueue(c, samples(AudioSource::microphone, 0, boundary)));
        CaptureSessionTestPeer::loss(c);
        CaptureSessionTestPeer::loss(c); // Exactly one EOS; no reconnection.
        assert(CaptureSessionTestPeer::enqueue(c, samples(AudioSource::microphone, boundary, 480)));
        release.store(true);
        waitFor([&] { return ends.load() == 1; });
        assert(c.pollHealth().state == SessionState::degraded && c.indicator().snapshot().visible);
        assert(!c.resume().accepted());
        finish(c); (void)c.stop(); (void)c.pollHealth();
        assert(finalized == 1 && microphoneBatches == 1 && frames.size() == 3);
        assert(c.finalization().reason == ReasonCode::microphoneEndpointUnavailable && c.finalization().trustedPrefixRetained);
        for (unsigned f = 0; f < 3; ++f) for (unsigned i = 0; i < 480; ++i) {
            const auto at = f * 480 + i;
            assert(frames[f].ptsFrames == S + f * 480);
            assert(frames[f].system[i] == 0.1F + static_cast<float>(at) / 10000);
            assert(frames[f].microphone[i] == (at < boundary ? 0.375F : 0));
        }
    }
}

void proofAndFaults() {
    for (unsigned mode = 0; mode < 8; ++mode) {
        unsigned finalized = 0; std::atomic<unsigned> ends{0};
        WindowsCaptureSessionController c("selected-mic-proof", [](AudioBatch) { return ReasonCode::none; },
            [&](ReasonCode reason, RecordingStopReason) {
                ++finalized;
                return CaptureFinalization{reason == ReasonCode::none,
                    mode == 7 ? ReasonCode::storageUnavailable : reason};
            }, {}, {}, [&] { ++ends; return ReasonCode::none; });
        CaptureSessionTestPeer::devices(c, mode != 0);
        CaptureSessionTestPeer::loss(c); // Idle/startup never authorizes continuation.
        assert(!CaptureSessionTestPeer::lost(c)); start(c);
        CaptureSessionTestPeer::loss(c, "other");
        for (const auto state : {1U, 2U, 4U, 12U}) CaptureSessionTestPeer::loss(c, "mic", state);
        CaptureSessionTestPeer::loss(c, "mic", 1, true); // Fresh contradictory state beats removal.
        CaptureSessionTestPeer::loss(c, "mic", std::nullopt);
        CaptureSessionTestPeer::loss(c, "render", 8, false, true);
        CaptureSessionTestPeer::foreignGeneration(c);
        assert(!CaptureSessionTestPeer::lost(c));
        if (mode == 1) (void)c.stop(); // Stop wins the admission race.
        if (mode == 2) {
            CaptureSessionTestPeer::renderFailure(c);
            (void)c.pollHealth(); // Generic interruption decided before proof.
        }
        CaptureSessionTestPeer::loss(c, "mic", mode == 3 ? std::nullopt : std::optional<std::uint32_t>{8}, mode == 3);
        const bool continued = mode >= 3;
        assert(CaptureSessionTestPeer::lost(c) == continued);
        if (continued) {
            waitFor([&] { return ends.load() == 1; });
            if (mode == 4) CaptureSessionTestPeer::renderFailure(c);
            if (mode == 5) CaptureSessionTestPeer::fault(c, ReasonCode::aecUnavailable);
            if (mode == 6) CaptureSessionTestPeer::fault(c, ReasonCode::clockDiscontinuity);
            (void)c.pollHealth();
        }
        finish(c);
        assert(finalized == 1 && ends.load() == (continued ? 1U : 0U));
        const auto reason = c.finalization().reason;
        if (mode == 0 || mode == 1) assert(reason == ReasonCode::none);
        if (mode == 2 || mode == 4) assert(reason != ReasonCode::none && reason != ReasonCode::microphoneEndpointUnavailable);
        if (mode == 3) assert(reason == ReasonCode::microphoneEndpointUnavailable);
        if (mode == 5) assert(reason == ReasonCode::aecUnavailable);
        if (mode == 6) assert(reason == ReasonCode::clockDiscontinuity);
        if (mode == 7) assert(reason == ReasonCode::storageUnavailable);
    }
}

void privacyRaces() {
    // Pending clock, READY before epoch commit, committed Resume, failed CLOSE.
    for (unsigned mode = 0; mode < 4; ++mode) {
        std::atomic_bool clockEntered{false}, releaseClock{false}, resumed{false}, releaseResume{false};
        std::atomic<unsigned> ends{0}, closes{0};
        std::atomic<std::uint64_t> expectedWall{0}, expectedMonotonic{0};
        WindowsCaptureSessionController c("selected-mic-privacy", [](AudioBatch) { return ReasonCode::none; },
            [](ReasonCode reason, RecordingStopReason) { return CaptureFinalization{false, reason, true}; },
            [&](bool paused) {
                if (!paused) { resumed.store(true); waitFor([&] { return releaseResume.load(); }); }
            }, [&](bool opening, std::uint64_t wall, std::uint64_t monotonic) {
                if (!opening && closes.fetch_add(1) == 0 && mode >= 2)
                    assert(wall == expectedWall.load() && monotonic == expectedMonotonic.load());
                return PrivacyCheckpointResult{opening || mode != 3, false};
            }, [&] { ++ends; return ReasonCode::none; });
        CaptureSessionTestPeer::devices(c, true, [&] {
            clockEntered.store(true);
            if (mode == 0) waitFor([&] { return releaseClock.load(); });
            auto sample = CaptureSessionTestPeer::clockSample();
            expectedWall.store(static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(
                sample.wall.time_since_epoch()).count()));
            expectedMonotonic.store(static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(
                sample.steady - CaptureSessionTestPeer::recordingStart(c)).count()));
            return sample;
        });
        start(c); (void)c.pause();
        waitFor([&] { return c.pollHealth().state == SessionState::paused && !c.privacyPending(); });
        auto held = CaptureSessionTestPeer::holdSink(c);
        if (mode != 1) held.unlock(); // Mode1 holds the real precommit/READY boundary.
        (void)c.resume(); waitFor([&] { return clockEntered.load(); });
        if (mode >= 2) waitFor([&] { return resumed.load(); });
        CaptureSessionTestPeer::loss(c);
        releaseClock.store(true); releaseResume.store(true);
        if (held.owns_lock()) held.unlock();
        waitFor([&] { return ends.load() == 1; });
        (void)c.pollHealth();
        assert(c.session().state() == SessionState::degraded && !c.privacyPending());
        assert(CaptureSessionTestPeer::epoch(c) == (mode >= 2 ? 2U : 1U));
        assert(closes.load() == (mode >= 2 ? 1U : 0U));
        assert(!c.resume().accepted()); finish(c);
        assert(closes.load() == (mode >= 2 ? 2U : 1U)); // OPEN closed only at Stop if loss won.
        assert(c.finalization().reason == ReasonCode::microphoneEndpointUnavailable);
    }
    std::atomic_bool ready{false}, release{false};
    std::atomic<unsigned> closes{0}, ends{0};
    WindowsCaptureSessionController c("selected-mic-ready", [](AudioBatch) { return ReasonCode::none; },
        [](ReasonCode reason, RecordingStopReason) { return CaptureFinalization{false, reason, true}; }, {},
        [&](bool opening, std::uint64_t, std::uint64_t) {
            if (!opening) ++closes;
            return PrivacyCheckpointResult{true, false};
        }, [&] { ++ends; return ReasonCode::none; });
    CaptureSessionTestPeer::devices(c); start(c); (void)c.pause();
    waitFor([&] { return c.pollHealth().state == SessionState::paused && !c.privacyPending(); });
    auto pending = std::async(std::launch::async, [&] { return CaptureSessionTestPeer::readyResume(c, ready, release); });
    waitFor([&] { return ready.load(); });
    CaptureSessionTestPeer::loss(c); release.store(true);
    assert(!pending.get() && CaptureSessionTestPeer::epoch(c) == 1 && closes.load() == 0);
    waitFor([&] { return ends.load() == 1; }); finish(c);
    assert(closes.load() == 1);
}

#ifdef _WIN32
std::vector<float> decodeAac(IStream* stream, unsigned boundary) {
    using Microsoft::WRL::ComPtr;
    LARGE_INTEGER zero{}; assert(stream->Seek(zero, STREAM_SEEK_SET, nullptr) == S_OK);
    ComPtr<IMFByteStream> bytes; ComPtr<IMFSourceReader> reader; ComPtr<IMFMediaType> pcm;
    assert(MFCreateMFByteStreamOnStream(stream, &bytes) == S_OK);
    assert(MFCreateSourceReaderFromByteStream(bytes.Get(), nullptr, &reader) == S_OK);
    assert(MFCreateMediaType(&pcm) == S_OK);
    assert(pcm->SetGUID(MF_MT_MAJOR_TYPE, MFMediaType_Audio) == S_OK);
    assert(pcm->SetGUID(MF_MT_SUBTYPE, MFAudioFormat_PCM) == S_OK);
    assert(reader->SetCurrentMediaType(0, nullptr, pcm.Get()) == S_OK);
    ComPtr<IMFMediaType> actual;
    const auto typeResult = reader->GetCurrentMediaType(0, &actual);
    std::printf("SELECTED_MIC_AAC boundary=%u current_type_hr=%08lx type_present=%u\n",
        boundary, static_cast<unsigned long>(typeResult), actual ? 1U : 0U);
    if (SUCCEEDED(typeResult) && actual) {
        GUID major{}, subtype{};
        const auto majorResult = actual->GetGUID(MF_MT_MAJOR_TYPE, &major);
        const auto subtypeResult = actual->GetGUID(MF_MT_SUBTYPE, &subtype);
        std::printf("SELECTED_MIC_AAC boundary=%u major_hr=%08lx subtype_hr=%08lx",
            boundary, static_cast<unsigned long>(majorResult), static_cast<unsigned long>(subtypeResult));
        if (SUCCEEDED(majorResult)) std::printf(" pcm_audio=%u", major == MFMediaType_Audio ? 1U : 0U);
        if (SUCCEEDED(subtypeResult)) std::printf(" pcm_subtype=%u", subtype == MFAudioFormat_PCM ? 1U : 0U);
        std::puts("");
        const auto printNumber = [&](REFGUID key, const char* name) {
            UINT32 value = 0;
            const auto status = actual->GetUINT32(key, &value);
            std::printf("SELECTED_MIC_AAC boundary=%u field=%s hr=%08lx", boundary, name, static_cast<unsigned long>(status));
            if (SUCCEEDED(status)) std::printf(" value=%u", value);
            std::puts("");
        };
        printNumber(MF_MT_AUDIO_SAMPLES_PER_SECOND, "rate");
        printNumber(MF_MT_AUDIO_NUM_CHANNELS, "channels");
        printNumber(MF_MT_AUDIO_BITS_PER_SAMPLE, "bits");
        printNumber(MF_MT_AUDIO_BLOCK_ALIGNMENT, "alignment");
        printNumber(MF_MT_AUDIO_AVG_BYTES_PER_SECOND, "bytes_per_second");
    }
    std::fflush(stdout);
    unsigned reads = 0;
    std::vector<float> result;
    for (;;) {
        DWORD flags = 0, streamIndex = 0; LONGLONG timestamp = 0;
        ComPtr<IMFSample> sample;
        const auto readResult = reader->ReadSample(0, 0, &streamIndex, &flags, &timestamp, &sample);
        std::printf("SELECTED_MIC_AAC boundary=%u read=%u hr=%08lx stream=%lu flags=%08lx timestamp=%lld sample=%u decoded_before=%zu\n",
            boundary, ++reads, static_cast<unsigned long>(readResult), static_cast<unsigned long>(streamIndex),
            static_cast<unsigned long>(flags), static_cast<long long>(timestamp), sample ? 1U : 0U, result.size());
        std::fflush(stdout);
        assert(readResult == S_OK);
        if (sample) {
            ComPtr<IMFMediaBuffer> buffer; assert(sample->ConvertToContiguousBuffer(&buffer) == S_OK);
            BYTE* data = nullptr; DWORD length = 0;
            assert(buffer->Lock(&data, nullptr, &length) == S_OK && length % 2 == 0);
            for (DWORD i = 0; i < length; i += 2) {
                const auto value = static_cast<std::int16_t>(static_cast<unsigned>(data[i]) |
                    (static_cast<unsigned>(data[i+1]) << 8));
                result.push_back(static_cast<float>(value) / 32768);
            }
            assert(buffer->Unlock() == S_OK);
            LONGLONG sampleTime = 0, sampleDuration = 0;
            const auto timeResult = sample->GetSampleTime(&sampleTime);
            const auto durationResult = sample->GetSampleDuration(&sampleDuration);
            std::printf("SELECTED_MIC_AAC boundary=%u read=%u bytes=%lu time_hr=%08lx duration_hr=%08lx decoded_after=%zu",
                boundary, reads, static_cast<unsigned long>(length), static_cast<unsigned long>(timeResult),
                static_cast<unsigned long>(durationResult), result.size());
            if (SUCCEEDED(timeResult)) std::printf(" time=%lld", static_cast<long long>(sampleTime));
            if (SUCCEEDED(durationResult)) std::printf(" duration=%lld", static_cast<long long>(sampleDuration));
            std::puts("");
            std::fflush(stdout);
        }
        assert(result.size() <= 6240); // Existing 30ms + SC-003 100ms bound.
        if (flags & MF_SOURCE_READERF_ENDOFSTREAM) return result;
    }
}

// Observe the first container-presented native AAC AU, not raw MFT output.
// Optional type/time/duration metadata must not add a new acceptance assertion.
void probeAacBegin(IStream* stream, const char* name) {
    using Microsoft::WRL::ComPtr;
    const auto log = [&](const char* operation, HRESULT status) {
        std::printf("SELECTED_MIC_R6_AU case=%s operation=%s hr=%08lx\n",
            name, operation, static_cast<unsigned long>(status));
        std::fflush(stdout);
        return SUCCEEDED(status);
    };
    LARGE_INTEGER zero{};
    if (!log("Seek", stream->Seek(zero, STREAM_SEEK_SET, nullptr))) return;
    ComPtr<IMFByteStream> bytes; ComPtr<IMFSourceReader> reader; ComPtr<IMFMediaType> native;
    if (!log("ByteStream", MFCreateMFByteStreamOnStream(stream, &bytes)) ||
        !log("SourceReader", MFCreateSourceReaderFromByteStream(bytes.Get(), nullptr, &reader)) ||
        !log("NativeType", reader->GetNativeMediaType(0, 0, &native))) return;
    GUID major{}, subtype{};
    const auto majorResult = native->GetGUID(MF_MT_MAJOR_TYPE, &major);
    const auto subtypeResult = native->GetGUID(MF_MT_SUBTYPE, &subtype);
    const bool aac = SUCCEEDED(majorResult) && SUCCEEDED(subtypeResult) &&
        major == MFMediaType_Audio && subtype == MFAudioFormat_AAC;
    std::printf("SELECTED_MIC_R6_AU case=%s major_hr=%08lx subtype_hr=%08lx native_aac=%u\n",
        name, static_cast<unsigned long>(majorResult), static_cast<unsigned long>(subtypeResult), aac ? 1U : 0U);
    std::fflush(stdout);
    if (!aac || !log("SetNativeType", reader->SetCurrentMediaType(0, nullptr, native.Get()))) return;
    for (unsigned read = 0; read < 8; ++read) {
        DWORD index = 0, flags = 0; LONGLONG timestamp = 0;
        ComPtr<IMFSample> sample;
        const auto status = reader->ReadSample(0, 0, &index, &flags, &timestamp, &sample);
        std::printf("SELECTED_MIC_R6_AU case=%s read=%u hr=%08lx stream=%lu flags=%08lx timestamp=%lld sample=%u\n",
            name, read + 1, static_cast<unsigned long>(status), static_cast<unsigned long>(index),
            static_cast<unsigned long>(flags), static_cast<long long>(timestamp), sample ? 1U : 0U);
        if (SUCCEEDED(status) && sample) {
            DWORD length = 0; LONGLONG time = 0, duration = 0;
            const auto lengthResult = sample->GetTotalLength(&length);
            const auto timeResult = sample->GetSampleTime(&time);
            const auto durationResult = sample->GetSampleDuration(&duration);
            std::printf("SELECTED_MIC_R6_AU case=%s bytes_hr=%08lx time_hr=%08lx duration_hr=%08lx",
                name, static_cast<unsigned long>(lengthResult), static_cast<unsigned long>(timeResult),
                static_cast<unsigned long>(durationResult));
            if (SUCCEEDED(lengthResult)) std::printf(" bytes=%lu", static_cast<unsigned long>(length));
            if (SUCCEEDED(timeResult)) std::printf(" time=%lld", static_cast<long long>(time));
            if (SUCCEEDED(durationResult)) std::printf(" duration=%lld", static_cast<long long>(duration));
            std::puts("");
        }
        std::fflush(stdout);
        if (FAILED(status) || sample || (flags & MF_SOURCE_READERF_ENDOFSTREAM)) return;
    }
    std::printf("SELECTED_MIC_R6_AU case=%s first_au_not_observed reads=8\n", name);
    std::fflush(stdout);
} // Probe reader/byte stream retire before the existing PCM decode opens.

void printAacControlMetrics(const char* name, const std::vector<float>& decoded) {
    constexpr double pi = 3.14159265358979323846;
    // Global and fixed 240-sample windows use the same absolute phase as P480.
    const auto print = [&](const char* range, std::size_t offset, std::size_t count) {
        double sum = 0, squares = 0;
        std::array<std::array<double, 2>, 2> tones{};
        for (std::size_t i = offset; i < offset + count; ++i) {
            const double sample = decoded[i];
            sum += sample; squares += sample * sample;
            for (const auto frequency : {1000, 2000}) {
                const auto phase = 2 * pi * frequency * static_cast<double>(i) / 48000;
                auto& tone = tones[frequency == 1000 ? 0 : 1];
                tone[0] += sample * std::sin(phase); tone[1] += sample * std::cos(phase);
            }
        }
        const auto length = static_cast<double>(count);
        std::printf("SELECTED_MIC_R6_METRIC case=%s range=%s offset=%zu count=%zu mean=%.17g rms=%.17g sin1000=%.17g cos1000=%.17g sin2000=%.17g cos2000=%.17g tone1000=%.17g tone2000=%.17g\n",
            name, range, offset, count, sum / length, std::sqrt(squares / length),
            2 * tones[0][0] / length, 2 * tones[0][1] / length,
            2 * tones[1][0] / length, 2 * tones[1][1] / length,
            2 * std::hypot(tones[0][0], tones[0][1]) / length,
            2 * std::hypot(tones[1][0], tones[1][1]) / length);
    };
    if (!decoded.empty()) print("global", 0, decoded.size());
    for (std::size_t offset = 0; offset < decoded.size(); offset += 240)
        print("window", offset, std::min<std::size_t>(240, decoded.size() - offset));
    std::fflush(stdout);
}

void compareAacControls(const char* leftName, const std::vector<float>& left,
                        const char* rightName, const std::vector<float>& right) {
    std::printf("SELECTED_MIC_R6_DELTA left=%s right=%s left_count=%zu right_count=%zu counts_equal=%u",
        leftName, rightName, left.size(), right.size(), left.size() == right.size() ? 1U : 0U);
    if (left.size() != right.size()) std::printf(" counts_differ=1 delta_not_computed=1");
    else if (left.empty()) std::printf(" empty_diagnostic=1 delta_not_computed=1");
    else {
        double maxError = 0;
        for (std::size_t i = 0; i < left.size(); ++i)
            maxError = std::max(maxError, std::abs(static_cast<double>(left[i]) - right[i]));
        std::printf(" max_abs_pcm_delta=%.17g", maxError);
    } // Never crop to a common prefix.
    std::puts(""); std::fflush(stdout);
}

std::vector<float> memoryAacControl(const char* name, const std::array<std::int16_t, 1440>& pcm,
                                  std::size_t chunkFrames) {
    using Microsoft::WRL::ComPtr;
    assert(chunkFrames == 480 || chunkFrames == 1440);
    std::printf("SELECTED_MIC_R6 case=%s case_begin input_frames=%zu chunk_frames=%zu boundary=719\n",
        name, pcm.size(), chunkFrames);
    std::fflush(stdout);
    const auto check = [&](const char* operation, HRESULT status) {
        std::printf("SELECTED_MIC_R6 case=%s operation=%s hr=%08lx\n",
            name, operation, static_cast<unsigned long>(status));
        std::fflush(stdout);
        assert(SUCCEEDED(status)); // A broken control is not evidence of AAC onset loss.
    };
    ComPtr<IStream> stream; ComPtr<IMFByteStream> bytes; ComPtr<IMFSinkWriter> sink;
    ComPtr<IMFAttributes> attributes; ComPtr<IMFMediaType> output, input;
    // HGlobal Stat reports read-only mode to the MF byte-stream adapter.
    stream.Attach(SHCreateMemStream(nullptr, 0));
    check("MemoryStream", stream ? S_OK : E_OUTOFMEMORY);
    check("ByteStream", MFCreateMFByteStreamOnStream(stream.Get(), &bytes));
    DWORD capabilities = 0;
    check("Capabilities", bytes->GetCapabilities(&capabilities));
    std::printf("SELECTED_MIC_R6 case=%s byte_stream_capabilities=%08lx\n",
        name, static_cast<unsigned long>(capabilities));
    std::fflush(stdout);
    assert((capabilities & (MFBYTESTREAM_IS_WRITABLE | MFBYTESTREAM_IS_SEEKABLE)) ==
        (MFBYTESTREAM_IS_WRITABLE | MFBYTESTREAM_IS_SEEKABLE));
    // Match V5LocalRecordingWriter::writePlayback, including offline throttling.
    check("Attributes", MFCreateAttributes(&attributes, 1));
    check("Container", attributes->SetGUID(MF_TRANSCODE_CONTAINERTYPE, MFTranscodeContainerType_MPEG4));
    check("DisableThrottling", attributes->SetUINT32(MF_SINK_WRITER_DISABLE_THROTTLING, TRUE));
    check("SinkWriter", MFCreateSinkWriterFromURL(nullptr, bytes.Get(), attributes.Get(), &sink));
    check("OutputType", MFCreateMediaType(&output));
    check("OutputMajor", output->SetGUID(MF_MT_MAJOR_TYPE, MFMediaType_Audio));
    check("OutputSubtype", output->SetGUID(MF_MT_SUBTYPE, MFAudioFormat_AAC));
    check("OutputChannels", output->SetUINT32(MF_MT_AUDIO_NUM_CHANNELS, 1));
    check("OutputRate", output->SetUINT32(MF_MT_AUDIO_SAMPLES_PER_SECOND, 48000));
    check("OutputBits", output->SetUINT32(MF_MT_AUDIO_BITS_PER_SAMPLE, 16));
    check("OutputBytesPerSecond", output->SetUINT32(MF_MT_AUDIO_AVG_BYTES_PER_SECOND, 12000));
    check("OutputPayload", output->SetUINT32(MF_MT_AAC_PAYLOAD_TYPE, 0));
    check("OutputProfile", output->SetUINT32(MF_MT_AAC_AUDIO_PROFILE_LEVEL_INDICATION, 0x29));
    DWORD index = 0;
    check("AddStream", sink->AddStream(output.Get(), &index));
    check("InputType", MFCreateMediaType(&input));
    check("InputMajor", input->SetGUID(MF_MT_MAJOR_TYPE, MFMediaType_Audio));
    check("InputSubtype", input->SetGUID(MF_MT_SUBTYPE, MFAudioFormat_PCM));
    check("InputChannels", input->SetUINT32(MF_MT_AUDIO_NUM_CHANNELS, 1));
    check("InputRate", input->SetUINT32(MF_MT_AUDIO_SAMPLES_PER_SECOND, 48000));
    check("InputBits", input->SetUINT32(MF_MT_AUDIO_BITS_PER_SAMPLE, 16));
    check("InputAlignment", input->SetUINT32(MF_MT_AUDIO_BLOCK_ALIGNMENT, 2));
    check("InputBytesPerSecond", input->SetUINT32(MF_MT_AUDIO_AVG_BYTES_PER_SECOND, 96000));
    check("SetInputMediaType", sink->SetInputMediaType(index, input.Get(), nullptr));
    check("BeginWriting", sink->BeginWriting());
    for (std::size_t offset = 0; offset < pcm.size(); offset += chunkFrames) {
        const auto byteCount = static_cast<DWORD>(chunkFrames * 2);
        const auto time = static_cast<LONGLONG>(offset * 10'000'000 / 48000);
        const auto duration = static_cast<LONGLONG>(chunkFrames * 10'000'000 / 48000);
        ComPtr<IMFMediaBuffer> buffer; ComPtr<IMFSample> sample;
        check("Buffer", MFCreateMemoryBuffer(byteCount, &buffer));
        check("Sample", MFCreateSample(&sample));
        BYTE* data = nullptr; DWORD maximum = 0, length = 0;
        check("PackLock", buffer->Lock(&data, &maximum, &length));
        assert(maximum >= byteCount);
        for (std::size_t i = 0; i < chunkFrames; ++i) {
            const auto value = static_cast<std::uint16_t>(pcm[offset + i]);
            data[2*i] = static_cast<BYTE>(value); data[2*i+1] = static_cast<BYTE>(value >> 8);
        }
        check("PackUnlock", buffer->Unlock());
        check("Length", buffer->SetCurrentLength(byteCount));
        check("AddBuffer", sample->AddBuffer(buffer.Get()));
        check("SetSampleTime", sample->SetSampleTime(time));
        check("SetSampleDuration", sample->SetSampleDuration(duration));
        // Inspect the packed sample buffer immediately before WriteSample.
        ComPtr<IMFMediaBuffer> packed;
        check("PackedBuffer", sample->ConvertToContiguousBuffer(&packed));
        check("PackedLock", packed->Lock(&data, nullptr, &length));
        assert(length == byteCount);
        int maxError = 0; std::size_t nonzero = 0; double squares = 0;
        for (std::size_t i = 0; i < chunkFrames; ++i) {
            const auto value = static_cast<std::int16_t>(static_cast<unsigned>(data[2*i]) |
                (static_cast<unsigned>(data[2*i+1]) << 8));
            maxError = std::max(maxError, std::abs(static_cast<int>(value) - pcm[offset + i]));
            if (value) ++nonzero;
            const double normalized = static_cast<double>(value) / 32768;
            squares += normalized * normalized;
        }
        check("PackedUnlock", packed->Unlock());
        std::printf("SELECTED_MIC_R6_PCM case=%s chunk=%zu input_offset=%zu frames=%zu bytes=%lu max_abs_pcm16_error=%d nonzero_count=%zu rms=%.17g pts=%lld duration=%lld\n",
            name, offset / chunkFrames, offset, chunkFrames, static_cast<unsigned long>(length), maxError,
            nonzero, std::sqrt(squares / static_cast<double>(chunkFrames)),
            static_cast<long long>(time), static_cast<long long>(duration));
        std::fflush(stdout);
        assert(maxError == 0);
        check("WriteSample", sink->WriteSample(index, sample.Get()));
    }
    check("Finalize", sink->Finalize());
    sink.Reset(); bytes.Reset(); output.Reset(); input.Reset(); attributes.Reset();
    STATSTG stat{}; check("Stat", stream->Stat(&stat, STATFLAG_NONAME));
    std::printf("SELECTED_MIC_R6 case=%s encoded_bytes=%llu\n", name, static_cast<unsigned long long>(stat.cbSize.QuadPart));
    std::fflush(stdout);
    probeAacBegin(stream.Get(), name);
    // The original decoder performs its own Seek and identical PCM negotiation.
    auto decoded = decodeAac(stream.Get(), 719);
    printAacControlMetrics(name, decoded);
    std::printf("SELECTED_MIC_R6 case=%s case_end decoded=%zu nonempty_decode=%u\n",
        name, decoded.size(), decoded.empty() ? 0U : 1U);
    std::fflush(stdout);
    return decoded;
}

void protectedContinuation() {
    for (const unsigned boundary : {719U, 960U}) std::async(std::launch::async, [boundary] {
        testing::GeneratedRecordingRoot paths;
        auto cancel = std::make_shared<std::atomic_bool>(false);
        constexpr auto session = "33333333-3333-4333-8333-333333333333";
        constexpr double pi = 3.14159265358979323846;
        constexpr auto user = "11111111-1111-4111-8111-111111111111";
        constexpr auto workspace = "22222222-2222-4222-8222-222222222222";
        const auto commit = [&](const auto& store, const auto& value) {
            auto bytes = value.serialize(cancel); assert(bytes.ok());
            assert(commitProtectedCustodyMetadata(store, store->queueContext(), store->queueGeneration(),
                *bytes.value, cancel).state == CustodyCommitState::committed);
        };
        {
            auto opened = ProtectedCustodyStoreOwner::open(paths.root, cancel); assert(opened.ok());
            auto store = *opened.value;
            auto initial = store->readQueueValue(cancel); assert(initial.ok());
            auto candidate = **initial.value;
            auto prepared = store->prepareRecordingReservation(candidate, session, user, workspace, true, 1000, cancel);
            assert(prepared.ok() && *prepared.value); commit(store, candidate);
            auto reservation = store->readQueueValue(cancel); assert(reservation.ok());
            auto capture = V5LocalRecordingWriter::open(store, session, cancel); assert(capture.ok());
            auto writer = *capture.value;
            TailAec aec; RecordingAudioTimeline timeline(aec);
            auto system = samples(AudioSource::systemRender, 0, 1440);
            for (std::size_t i = 0; i < system.samples.size(); ++i)
                system.samples[i] = 0.3F * static_cast<float>(std::sin(2 * pi * (i < 720 ? 1000 : 2000) *
                    static_cast<double>(i) / 48000));
            std::atomic<unsigned> ended{0};
            V5WriterResult sealed;
            const auto writeFrames = [&] {
                for (const auto& frame : timeline.takeFrames()) if (!writer->append(frame)) return ReasonCode::storageUnavailable;
                return ReasonCode::none;
            };
            WindowsCaptureSessionController c(session, [&](AudioBatch batch) {
                if (!timeline.push(std::move(batch))) return ReasonCode::clockDiscontinuity;
                return writeFrames();
            }, [&](ReasonCode reason, RecordingStopReason stop) {
                assert(timeline.close() && writeFrames() == ReasonCode::none);
                sealed = writer->finalize(reason, stop, ended.load() == 1);
                return CaptureFinalization{false, sealed.captureFailure, sealed.trustedPrefixRetained};
            }, {}, {}, [&] {
                assert(timeline.endMicrophone());
                const auto result = writeFrames(); ++ended; return result;
            });
            CaptureSessionTestPeer::devices(c); start(c);
            assert(CaptureSessionTestPeer::enqueue(c, system));
            assert(CaptureSessionTestPeer::enqueue(c, samples(AudioSource::microphone, 0, boundary)));
            CaptureSessionTestPeer::loss(c);
            waitFor([&] { return ended.load() == 1; }); finish(c);
            assert(sealed.ok() && sealed.semanticVerified && sealed.trustedPrefixRetained && !sealed.normalPackage());
            assert(sealed.packagePhase == CustodyPackagePhase::sealedDegraded && sealed.durationMs == 30);
            assert(sealed.captureFailure == ReasonCode::microphoneEndpointUnavailable && sealed.wavBytes == 1004 && sealed.playbackBytes);
            writer.reset(); capture.value->reset(); // Retire all writer leases before queue/cold proof.
            candidate = **reservation.value;
            const auto finished = store->finishRecordingReservation(candidate, **reservation.value, session, sealed, 2000, cancel);
            assert(finished.ok() && *finished.value); commit(store, candidate);
        }
        // Cold store/ledger/package acquisition; no retained writer or proof.
        const auto com = CoInitializeEx(nullptr, COINIT_MULTITHREADED); assert(SUCCEEDED(com));
        assert(MFStartup(MF_VERSION) == S_OK);
        {
            auto opened = ProtectedCustodyStoreOwner::open(paths.root, cancel); assert(opened.ok());
            auto store = *opened.value;
            auto queue = store->readQueueValue(cancel); assert(queue.ok());
            auto candidate = **queue.value;
            assert(candidate.items().size() == 1 && candidate.items().front().status == UploadQueueStatus::quarantined);
            assert(!candidate.canManualSend(0, user, workspace, true));
            assert(!candidate.prepareManualSend(0, user, workspace, true, 3000, cancel.get()));
            assert(candidate.prepareUploads(true, 5, 3000, cancel.get()).empty());
            assert(!hasUploadServerIdentity(candidate.items().front()));
            auto pair = store->readPackage(session, cancel); assert(pair.ok());
            assert((*pair.value)->current().phase == CustodyPackagePhase::sealedDegraded &&
                (*pair.value)->current().reason == ReasonCode::microphoneEndpointUnavailable);
            auto proof = LocalRecordingPackage::inspectProtected(paths.root, *pair.value, session, cancel); assert(proof.ok());
            assert((*proof.value)->evidence().integrity == PackageIntegrity::degraded &&
                (*proof.value)->evidence().durationMs == 30 && (*proof.value)->evidence().trustedPrefixFrames == 3 &&
                (*proof.value)->evidence().playback.decodedFrames);
            proof.value.reset();
            auto readers = openProtectedCustodyReaders(paths.root, *pair.value, cancel); assert(readers.ok());
            const auto& value = (*pair.value)->current();
            std::vector<float> memory480, memory1440;
            {
                std::size_t ref = 0;
                while (ref != value.refCount && value.refs[ref].role != CustodyRole::canonical) ++ref;
                assert(ref != value.refCount);
                auto* stream = readers.value->at((*pair.value)->selectedSlot()).at(ref).stream.Get();
                LARGE_INTEGER zero{}; assert(stream->Seek(zero, STREAM_SEEK_SET, nullptr) == S_OK);
                std::array<float, 1440> canonical{}; ULONG got = 0;
                assert(stream->Read(canonical.data(), sizeof(canonical), &got) == S_OK && got == sizeof(canonical));
                double maxError = 0;
                for (std::size_t i = 0; i < canonical.size(); ++i) {
                    const auto system = 0.3F * static_cast<float>(std::sin(2 * pi * (i < 720 ? 1000 : 2000) *
                        static_cast<double>(i) / 48000));
                    const auto cleaned = i < boundary ? 0.375F : 0.0F;
                    // Match timeline: float source/AEC, double sum/weight/clamp, float result.
                    const auto expected = static_cast<float>(std::clamp(0.5 * (static_cast<double>(system) + cleaned), -1.0, 1.0));
                    maxError = std::max(maxError, std::abs(static_cast<double>(canonical[i]) - expected));
                }
                std::printf("SELECTED_MIC_CANONICAL count=%zu max_error=%.17g\n", canonical.size(), maxError);
                std::fflush(stdout);
                if (boundary == 719) {
                    std::array<std::int16_t, 1440> pcm{};
                    for (std::size_t i = 0; i < canonical.size(); ++i)
                        pcm[i] = static_cast<std::int16_t>(std::clamp(canonical[i], -1.0F, 1.0F) * 32767.0F);
                    memory480 = memoryAacControl("M480", pcm, 480);
                    memory1440 = memoryAacControl("M1440", pcm, 1440);
                    compareAacControls("M480", memory480, "M1440", memory1440);
                }
            }
            for (std::size_t r = 0; r < value.refCount; ++r) {
                auto* stream = readers.value->at((*pair.value)->selectedSlot()).at(r).stream.Get();
                if (value.refs[r].role == CustodyRole::media) {
                    LARGE_INTEGER zero{}; assert(stream->Seek(zero, STREAM_SEEK_SET, nullptr) == S_OK);
                    std::array<unsigned char, 1004> wav{}; ULONG got = 0;
                    assert(stream->Read(wav.data(), static_cast<ULONG>(wav.size()), &got) == S_OK && got == wav.size());
                    for (unsigned i = 0; i < 480; ++i) {
                        float expected = 0;
                        for (unsigned j = 0; j < 3; ++j) {
                            const auto at = i * 3 + j;
                            expected += 0.5F * (0.3F * static_cast<float>(std::sin(2 * pi * (at < 720 ? 1000 : 2000) *
                                static_cast<double>(at) / 48000)) + (at < boundary ? 0.375F : 0)) / 3;
                        }
                        const auto pcm = static_cast<std::int16_t>(static_cast<unsigned>(wav[44+i*2]) |
                            (static_cast<unsigned>(wav[45+i*2]) << 8));
                        assert(std::abs(static_cast<float>(pcm) / 32768 - expected) < 0.0001F);
                    }
                }
                if (value.refs[r].role == CustodyRole::playback) {
                    if (boundary == 719) probeAacBegin(stream, "P480");
                    const auto decoded = decodeAac(stream, boundary);
                    assert(!decoded.empty());
                    // Codec delay changes phase, so compare both known tones by
                    // their sine/cosine magnitude across the decoded samples.
                    std::array<std::array<double, 2>, 2> tones{};
                    for (const auto frequency : {1000, 2000}) {
                        double sine = 0, cosine = 0;
                        for (std::size_t i = 0; i < decoded.size(); ++i) {
                            const auto phase = 2 * pi * frequency * static_cast<double>(i) / 48000;
                            sine += decoded[i] * std::sin(phase); cosine += decoded[i] * std::cos(phase);
                        }
                        tones[frequency == 1000 ? 0 : 1] = {sine, cosine};
                    }
                    std::printf("SELECTED_MIC_AAC boundary=%u decoded=%zu tone1000=%.17g tone2000=%.17g threshold=0.015\n",
                        boundary, decoded.size(), 2 * std::hypot(tones[0][0], tones[0][1]) / static_cast<double>(decoded.size()),
                        2 * std::hypot(tones[1][0], tones[1][1]) / static_cast<double>(decoded.size()));
                    // Fixed 5ms windows, using absolute sample phase and each window's actual count.
                    for (std::size_t offset = 0; offset < decoded.size(); offset += 240) {
                        const auto count = std::min<std::size_t>(240, decoded.size() - offset);
                        double sum = 0, sumSquares = 0;
                        std::array<std::array<double, 2>, 2> components{};
                        for (std::size_t i = offset; i < offset + count; ++i) {
                            const double sample = decoded[i];
                            sum += sample; sumSquares += sample * sample;
                            for (const auto frequency : {1000, 2000}) {
                                const auto phase = 2 * pi * frequency * static_cast<double>(i) / 48000;
                                auto& tone = components[frequency == 1000 ? 0 : 1];
                                tone[0] += sample * std::sin(phase); tone[1] += sample * std::cos(phase);
                            }
                        }
                        const auto length = static_cast<double>(count);
                        std::printf("SELECTED_MIC_AAC_WINDOW boundary=%u offset=%zu count=%zu mean=%.17g rms=%.17g sin1000=%.17g cos1000=%.17g sin2000=%.17g cos2000=%.17g\n",
                            boundary, offset, count, sum / length, std::sqrt(sumSquares / length),
                            2 * components[0][0] / length, 2 * components[0][1] / length,
                            2 * components[1][0] / length, 2 * components[1][1] / length);
                    }
                    std::fflush(stdout);
                    if (boundary == 719) {
                        compareAacControls("P480", decoded, "M480", memory480);
                        compareAacControls("P480", decoded, "M1440", memory1440);
                    }
                    for (const auto& components : tones) {
                        const auto sine = components[0], cosine = components[1];
                        assert(2 * std::hypot(sine, cosine) / static_cast<double>(decoded.size()) > 0.015);
                    }
                }
            }
        }
        assert(MFShutdown() == S_OK); CoUninitialize();
    }).get();
    std::puts("SELECTED_MIC_LOSS protected=2 cold_read=2 manual_auto_upload_refused=2 wav_aac=2");
}

void protectedFaults() {
    for (unsigned mode = 0; mode < 3; ++mode) std::async(std::launch::async, [mode] {
        testing::GeneratedProtectedRecording recording("selected-mic-fault");
        recording.append(3);
        if (mode == 2) {
            recording.cancel->store(true);
            CanonicalAudioFrame next; next.mixed.fill(0.25F); next.ptsFrames = 1440;
            assert(!recording.writer->append(next)); // Actual protected write cancellation.
        }
        const auto result = recording.writer->finalize(mode == 1 ? ReasonCode::clockDiscontinuity :
            ReasonCode::microphoneEndpointUnavailable, RecordingStopReason::userRequested, mode != 0);
        assert(!result.normalPackage() && !result.keepablePackage() && !result.playbackBytes && !result.shortRecordingDiscarded);
        if (mode == 2) assert(!result.ok() && result.captureFailure == ReasonCode::storageUnavailable);
        else assert(result.semanticVerified && result.trustedPrefixRetained &&
            result.captureFailure == (mode == 1 ? ReasonCode::clockDiscontinuity : ReasonCode::microphoneEndpointUnavailable));
    }).get();
    std::puts("SELECTED_MIC_LOSS no_proof_clock_custody_no_playable=3");
}
#endif
} // namespace

int main() {
    timelineBoundary();
    orderedContinuation();
    proofAndFaults();
    privacyRaces();
#ifdef _WIN32
    protectedContinuation();
    protectedFaults();
#endif
    std::puts("SELECTED_MIC_LOSS timeline=4 fifo=2 proof_fault=8 privacy_races=5");
}
