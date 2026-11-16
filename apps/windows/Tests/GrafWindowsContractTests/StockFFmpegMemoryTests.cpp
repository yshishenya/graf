#ifdef NDEBUG
#undef NDEBUG
#endif
#include "../../RecApp/Storage/ProtectedCustodyMemory.h"
#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <string_view>

namespace {
using Clock = std::chrono::steady_clock;
using graf::windows::CustodyOwnedMemory;
constexpr double pi = 3.14159265358979323846;
constexpr unsigned sampleRate = 48000, blockSamples = 480, pollMs = 5;
struct Variant { unsigned minutes; bool paced; };
bool variant(std::string_view argument, Variant& result) {
    if (argument == "--synthetic-10min-accelerated") result = {10,false};
    else if (argument == "--synthetic-60min-accelerated") result = {60,false};
    else if (argument == "--synthetic-10min-paced") result = {10,true};
    else if (argument == "--synthetic-60min-paced") result = {60,true};
    else return false;
    return true;
}
float sourceValue(unsigned at) {
    return static_cast<float>(0.15*std::sin(2*pi*1000*at/sampleRate) +
                              0.10*std::sin(2*pi*2000*at/sampleRate));
}
struct Tones {
    const std::array<double,2> coefficients{2*std::cos(2*pi*1000/sampleRate),2*std::cos(2*pi*2000/sampleRate)};
    std::array<double,2> previous{}, older{};
    std::uint64_t frames = 0;
    bool finite = true;
    void add(double value) {
        finite = finite && std::isfinite(value);
        for (std::size_t i=0; i<2; ++i) {
            const auto next = value+coefficients[i]*previous[i]-older[i];
            older[i] = previous[i]; previous[i] = next;
        }
        ++frames;
    }
    double amplitude(std::size_t i) const {
        return frames ? 2*std::sqrt((std::max)(0.0,previous[i]*previous[i]+older[i]*older[i]-
            coefficients[i]*previous[i]*older[i]))/static_cast<double>(frames) : 0;
    }
};
bool durationMatches(std::uint64_t actual, std::uint64_t expected) {
    return (actual > expected ? actual-expected : expected-actual) <= 1000000; // Existing 100 ms bound, in 100 ns.
}
void selfcheck() {
    static_assert(pollMs<=10);
    Variant v{};
    for (const auto argument : {"--synthetic-10min-accelerated","--synthetic-60min-accelerated",
                               "--synthetic-10min-paced","--synthetic-60min-paced"}) assert(variant(argument,v));
    assert(!variant("",v) && !variant("--synthetic-1min-paced",v));
    assert(!variant("--synthetic-60min-paced-extra",v));
    assert(variant("--synthetic-10min-accelerated",v) && v.minutes==10 && !v.paced);
    assert(variant("--synthetic-60min-paced",v) && v.minutes==60 && v.paced);
    assert(std::uint64_t{10}*6000*blockSamples==28800000 && std::uint64_t{60}*6000*blockSamples==172800000);
    assert(Tones{}.amplitude(0)==0);
    Tones tones;
    for (unsigned i=0; i<sampleRate; ++i) tones.add(sourceValue(i%blockSamples));
    assert(tones.finite && std::abs(tones.amplitude(0)-0.15)<1e-6 && std::abs(tones.amplitude(1)-0.10)<1e-6);
    assert(durationMatches(6000000000ULL,6000000000ULL));
    assert(durationMatches(6001000000ULL,6000000000ULL));
    assert(!durationMatches(6001000001ULL,6000000000ULL));
    assert(!durationMatches(0,36000000000ULL));
    const auto before = CustodyOwnedMemory::usedBytes(); assert(before == 0);
    assert(CustodyOwnedMemory::tryReserve(CustodyOwnedMemory::limit));
    assert(!CustodyOwnedMemory::tryReserve(1));
    assert(!CustodyOwnedMemory::tryReserve(CustodyOwnedMemory::limit+1));
    CustodyOwnedMemory::release(CustodyOwnedMemory::limit);
    assert(CustodyOwnedMemory::usedBytes() == before);
    assert(CustodyOwnedMemory::peakBytes() == CustodyOwnedMemory::limit);
    std::fputs("SOURCE_SELFCHECK PASS pure_variants_signal_duration_admission windows_execution=0\n",stderr);
}
}

#ifdef _WIN32
#include "../GeneratedRecordingFixtures.h"
#include <mfapi.h>
#include <mfidl.h>
#include <mfreadwrite.h>
#include <psapi.h>
#include <condition_variable>
#include <mutex>
#include <thread>

namespace {
using namespace graf::windows;
using Microsoft::WRL::ComPtr;
void require(bool ok, const char* operation) {
    if (!ok) throw std::runtime_error(operation);
}
void checked(HRESULT hr, const char* operation) {
    if (FAILED(hr)) {
        std::fprintf(stderr,"MEMORY_ERROR operation=%s hr=%08lx\n",operation,static_cast<unsigned long>(hr));
        throw std::runtime_error(operation);
    }
}
struct MediaRuntime {
    bool& shutdownSucceeded;
    explicit MediaRuntime(bool& shutdown) : shutdownSucceeded(shutdown) {
        checked(CoInitializeEx(nullptr,COINIT_MULTITHREADED),"CoInitializeEx");
        const auto hr = MFStartup(MF_VERSION);
        if (FAILED(hr)) { CoUninitialize(); checked(hr,"MFStartup"); }
    }
    ~MediaRuntime() {
        const auto hr = MFShutdown();
        shutdownSucceeded = SUCCEEDED(hr);
        std::fprintf(stderr,"MEMORY_MF shutdown_hr=%08lx\n",static_cast<unsigned long>(hr));
        CoUninitialize();
    }
};
struct MemoryPoint { std::size_t privateBytes=0, workingSet=0, owned=0; };
MemoryPoint maximum(MemoryPoint a, MemoryPoint b) {
    return {(std::max)(a.privateBytes,b.privateBytes),(std::max)(a.workingSet,b.workingSet),(std::max)(a.owned,b.owned)};
}
// Fixed-size summaries only. Process totals include MF, FFmpeg, the sampler and the fixture.
class MemorySamples {
public:
    std::atomic<unsigned> phase{0}; // 0 warm-up, 1 open/append, 2 finalize/Stop, 3 cold inspect/decode, 4 cleanup.
    std::atomic<std::uint64_t> writtenBlocks{0};
    explicit MemorySamples(Clock::time_point deadline) : deadline_(deadline) {
        std::lock_guard<std::mutex> lock(mutex_);
        initial_ = take();
        thread_ = std::thread([this] {
            std::unique_lock<std::mutex> lock(mutex_);
            while (!cv_.wait_for(lock,std::chrono::milliseconds(pollMs),[this] { return stop_; })) {
                take();
                const auto now = Clock::now();
                expired.store(now >= deadline_,std::memory_order_relaxed);
                if (now-lastLog_ >= std::chrono::seconds(10)) { print("series",current_); lastLog_ = now; }
            }
        });
    }
    ~MemorySamples() { stop(); }
    void warmed() {
        std::lock_guard<std::mutex> lock(mutex_);
        warm_ = take(); afterWarmPeak_ = warm_; warmed_ = true; print("warm",warm_);
    }
    void finish() {
        stop();
        std::lock_guard<std::mutex> lock(mutex_);
        const auto final = take();
        print("initial",initial_); print("final",final); print("sampled_peak",peak_);
        print("sampled_post_warm_peak",afterWarmPeak_);
        for (unsigned i=0; i<phasePeaks_.size(); ++i) {
            std::fprintf(stderr,"MEMORY_PHASE_PEAK phase=%u private_bytes=%zu working_set=%zu owned_sampled=%zu\n",
                i,phasePeaks_[i].privateBytes,phasePeaks_[i].workingSet,phasePeaks_[i].owned);
        }
        const auto growth = afterWarmPeak_.workingSet > warm_.workingSet ? afterWarmPeak_.workingSet-warm_.workingSet : 0;
        std::fprintf(stderr,"MEMORY_SAMPLING requested_ms=%u actual_max_gap_us=%lld samples=%llu failures=%llu first_native_error=%lu "
            "os_lifetime_peak_commit=%zu os_lifetime_peak_ws=%zu warm_valid=%u post_warm_ws_growth=%zu growth_le_128mib=%u "
            "owned_admitted_lifetime_peak=%zu owned_limit=%zu strict_sc003_acceptance=0\n",
            pollMs,static_cast<long long>(maxGapUs_),static_cast<unsigned long long>(samples_),
            static_cast<unsigned long long>(failures_),firstSamplingError_,osPeakCommit_,osPeakWs_,unsigned(warmed_),growth,unsigned(warmed_ && growth<=128ULL*1024*1024),
            CustodyOwnedMemory::peakBytes(),CustodyOwnedMemory::limit);
        std::fflush(stderr);
        require(!failures_ && samples_>1 && warmed_,"process memory sampling incomplete");
        require(CustodyOwnedMemory::peakBytes() <= CustodyOwnedMemory::limit,"owned admission limit");
        require(growth<=128ULL*1024*1024,"sampled post-warm working set growth exceeds 128 MiB");
    }
    std::atomic<bool> expired{false};
private:
    MemoryPoint take() {
        PROCESS_MEMORY_COUNTERS_EX counters{}; counters.cb = sizeof(counters);
        if (!K32GetProcessMemoryInfo(GetCurrentProcess(),reinterpret_cast<PROCESS_MEMORY_COUNTERS*>(&counters),sizeof(counters))) {
            if (!failures_) firstSamplingError_ = GetLastError();
            ++failures_; return current_;
        }
        const auto now = Clock::now();
        if (samples_) maxGapUs_ = (std::max)(maxGapUs_,std::chrono::duration_cast<std::chrono::microseconds>(now-lastSample_).count());
        lastSample_ = now; ++samples_;
        current_ = {counters.PrivateUsage,counters.WorkingSetSize,CustodyOwnedMemory::usedBytes()};
        peak_ = maximum(peak_,current_);
        const auto stage = phase.load(std::memory_order_relaxed);
        phasePeaks_[stage] = maximum(phasePeaks_[stage],current_);
        if (warmed_) afterWarmPeak_ = maximum(afterWarmPeak_,current_);
        osPeakCommit_ = (std::max)(osPeakCommit_,counters.PeakPagefileUsage);
        osPeakWs_ = (std::max)(osPeakWs_,counters.PeakWorkingSetSize);
        return current_;
    }
    void print(const char* kind, MemoryPoint p) const {
        std::fprintf(stderr,"MEMORY_POINT kind=%s elapsed_ms=%lld phase=%u written_blocks=%llu private_bytes=%zu working_set=%zu owned_sampled=%zu\n",
            kind,static_cast<long long>(std::chrono::duration_cast<std::chrono::milliseconds>(Clock::now()-started_).count()),
            phase.load(std::memory_order_relaxed),static_cast<unsigned long long>(writtenBlocks.load(std::memory_order_relaxed)),
            p.privateBytes,p.workingSet,p.owned);
        std::fflush(stderr);
    }
    void stop() noexcept {
        { std::lock_guard<std::mutex> lock(mutex_); stop_ = true; }
        cv_.notify_one(); if (thread_.joinable()) thread_.join();
    }
    const Clock::time_point started_ = Clock::now(), deadline_;
    Clock::time_point lastSample_{}, lastLog_ = started_;
    std::chrono::microseconds::rep maxGapUs_=0;
    std::uint64_t samples_=0, failures_=0;
    DWORD firstSamplingError_=0;
    std::size_t osPeakCommit_=0, osPeakWs_=0;
    bool stop_=false, warmed_=false;
    MemoryPoint initial_{}, current_{}, warm_{}, peak_{}, afterWarmPeak_{};
    std::array<MemoryPoint,5> phasePeaks_{};
    std::mutex mutex_; std::condition_variable cv_; std::thread thread_;
};
struct LockedPcm {
    IMFMediaBuffer* buffer;
    HRESULT& unlockResult;
    BYTE* data=nullptr; DWORD capacity=0, length=0;
    LockedPcm(IMFMediaBuffer* value, HRESULT& result) : buffer(value), unlockResult(result) {
        checked(buffer->Lock(&data,&capacity,&length),"PCM Lock");
    }
    ~LockedPcm() {
        if (data) wipeCustodyMemory(data,(std::min)(length,capacity));
        unlockResult = buffer->Unlock();
    }
};
void checkDeadline(MemorySamples& memory, const std::shared_ptr<std::atomic<bool>>& cancel) {
    if (memory.expired.load(std::memory_order_relaxed)) {
        cancel->store(true,std::memory_order_relaxed); throw std::runtime_error("cooperative case deadline");
    }
}
std::uint64_t decode(IStream* input, std::uint64_t expected, std::uint64_t original, MemorySamples& memory,
                     const std::shared_ptr<std::atomic<bool>>& cancel) {
    LARGE_INTEGER zero{}; checked(input->Seek(zero,STREAM_SEEK_SET,nullptr),"playback seek");
    ComPtr<IMFByteStream> bytes; ComPtr<IMFSourceReader> reader; ComPtr<IMFMediaType> pcm, actual;
    checked(MFCreateMFByteStreamOnStream(input,&bytes),"MF byte stream");
    checked(MFCreateSourceReaderFromByteStream(bytes.Get(),nullptr,&reader),"MF source reader");
    checked(MFCreateMediaType(&pcm),"PCM type");
    checked(pcm->SetGUID(MF_MT_MAJOR_TYPE,MFMediaType_Audio),"PCM major");
    checked(pcm->SetGUID(MF_MT_SUBTYPE,MFAudioFormat_PCM),"PCM subtype");
    checked(pcm->SetUINT32(MF_MT_AUDIO_BITS_PER_SAMPLE,16),"PCM bits");
    checked(pcm->SetUINT32(MF_MT_AUDIO_NUM_CHANNELS,1),"PCM channels");
    checked(pcm->SetUINT32(MF_MT_AUDIO_SAMPLES_PER_SECOND,sampleRate),"PCM rate");
    checked(reader->SetCurrentMediaType(0,nullptr,pcm.Get()),"PCM select");
    checked(reader->GetCurrentMediaType(0,&actual),"PCM actual");
    for (const auto property : {std::pair<GUID,UINT32>{MF_MT_AUDIO_BITS_PER_SAMPLE,16},
                               {MF_MT_AUDIO_NUM_CHANNELS,1},{MF_MT_AUDIO_SAMPLES_PER_SECOND,sampleRate}}) {
        UINT32 value=0; checked(actual->GetUINT32(property.first,&value),"PCM actual property"); require(value==property.second,"PCM actual mismatch");
    }
    Tones tones; bool eos=false;
    for (std::uint64_t calls=0; calls<original+1024 && !eos; ++calls) {
        checkDeadline(memory,cancel);
        DWORD stream=0, flags=0; LONGLONG timestamp=0; ComPtr<IMFSample> sample;
        checked(reader->ReadSample(0,0,&stream,&flags,&timestamp,&sample),"PCM ReadSample");
        require(stream==0 && !(flags & ~MF_SOURCE_READERF_ENDOFSTREAM),"PCM unexpected flags");
        if (sample) {
            ComPtr<IMFMediaBuffer> buffer; checked(sample->ConvertToContiguousBuffer(&buffer),"PCM buffer");
            HRESULT unlocked=S_OK;
            {
                LockedPcm data(buffer.Get(),unlocked);
                require(data.data && data.length && data.length<=data.capacity && !(data.length%2) && data.length<=256*1024,"PCM chunk bound");
                require(tones.frames+data.length/2<=original+4800,"PCM frame bound including AAC delay/tail");
                for (DWORD at=0; at<data.length; at+=2) {
                    std::int16_t value=0; std::memcpy(&value,data.data+at,2); tones.add(static_cast<double>(value)/32768);
                }
            }
            checked(unlocked,"PCM Unlock");
        } else require(flags & MF_SOURCE_READERF_ENDOFSTREAM,"PCM missing sample without EOS");
        eos = (flags & MF_SOURCE_READERF_ENDOFSTREAM)!=0;
    }
    std::fprintf(stderr,"MEMORY_DECODE full_eos=%u raw_frames=%llu inspector_raw_frames=%llu original_frames=%llu "
        "raw_minus_original=%lld tone1000=%.17g tone2000=%.17g threshold=0.015 priming_metadata=NOT_ASSESSED strict_audio_acceptance=0\n",
        unsigned(eos),static_cast<unsigned long long>(tones.frames),static_cast<unsigned long long>(expected),
        static_cast<unsigned long long>(original),static_cast<long long>(tones.frames)-static_cast<long long>(original),
        tones.amplitude(0),tones.amplitude(1)); std::fflush(stderr);
    require(eos && tones.frames==expected && tones.frames>=original,"full decoded frame count");
    require(tones.finite && std::isfinite(tones.amplitude(0)) && std::isfinite(tones.amplitude(1)) &&
            tones.amplitude(0)>0.015 && tones.amplitude(1)>0.015,"full EOF two-tone levels");
    return tones.frames;
}
void recording(std::uint64_t blocks, bool paced, bool warmup, MemorySamples& memory) {
    memory.phase.store(warmup ? 0 : 1);
    testing::GeneratedProtectedRecording capture(warmup ? "generated-memory-warmup" : "generated-memory-long");
    CustodyVector<CanonicalAudioFrame> chunk(1);
    for (unsigned at=0; at<blockSamples; ++at) chunk[0].mixed[at] = sourceValue(at);
    const auto begin = Clock::now();
    long long maximumLatenessUs=0;
    for (std::uint64_t n=0; n<blocks; ++n) {
        if (paced) {
            const auto due = begin+std::chrono::milliseconds((n+1)*10);
            std::this_thread::sleep_until(due);
            maximumLatenessUs = (std::max)(maximumLatenessUs,
                static_cast<long long>(std::chrono::duration_cast<std::chrono::microseconds>(Clock::now()-due).count()));
        }
        checkDeadline(memory,capture.cancel);
        chunk[0].ptsFrames = static_cast<std::int64_t>(n*blockSamples);
        require(capture.writer->append(chunk[0]),"V5 append"); memory.writtenBlocks.store(n+1);
    }
    require(capture.writer->frameCount()==blocks,"writer block count");
    const auto stop = Clock::now(); memory.phase.store(warmup ? 0 : 2);
    const auto sealed = capture.writer->finalize();
    const auto finalized = Clock::now();
    std::fprintf(stderr,"MEMORY_RECORD warmup=%u mode=%s blocks=%llu original_frames=%llu duration_ms=%llu "
        "append_wall_ms=%lld stop_finalize_ms=%lld pacing_max_late_us=%lld error=%u storage=%u native=%08x normal=%u\n",
        unsigned(warmup),paced ? "paced" : "accelerated",static_cast<unsigned long long>(blocks),
        static_cast<unsigned long long>(blocks*blockSamples),static_cast<unsigned long long>(sealed.durationMs),
        static_cast<long long>(std::chrono::duration_cast<std::chrono::milliseconds>(stop-begin).count()),
        static_cast<long long>(std::chrono::duration_cast<std::chrono::milliseconds>(finalized-stop).count()),maximumLatenessUs,
        unsigned(sealed.error),unsigned(sealed.storageError),sealed.nativeError,unsigned(sealed.normalPackage())); std::fflush(stderr);
    checkDeadline(memory,capture.cancel);
    require(sealed.normalPackage() && sealed.durationMs==blocks*10,"V5 finalize/duration");
    memory.phase.store(warmup ? 0 : 3);
    auto pair = capture.coldPair(); require(pair.ok(),"cold package pair");
    auto inspection = LocalRecordingPackage::inspectProtected(capture.paths.root,*pair.value,capture.session,capture.cancel);
    require(inspection.ok(),"cold full inspection");
    const auto evidence = (*inspection.value)->evidence(); inspection.value.reset();
    require(evidence.durationMs==blocks*10,"cold duration");
    const auto duration100ns = evidence.playback.containerDuration100ns;
    std::fprintf(stderr,"MEMORY_DURATION container_100ns=%llu expected_100ns=%llu difference_100ns=%lld\n",
        static_cast<unsigned long long>(duration100ns),static_cast<unsigned long long>(blocks*100000),
        static_cast<long long>(duration100ns)-static_cast<long long>(blocks*100000)); std::fflush(stderr);
    require(durationMatches(duration100ns,blocks*100000),"container duration within 100ms");
    auto readers = openProtectedCustodyReaders(capture.paths.root,*pair.value,capture.cancel); require(readers.ok(),"cold BOTH readers");
    const auto slot = (*pair.value)->selectedSlot(); const auto& refs = (*pair.value)->current();
    std::size_t canonical=refs.refCount, playback=refs.refCount;
    for (std::size_t i=0; i<refs.refCount; ++i) {
        if (refs.refs[i].role==CustodyRole::canonical) canonical=i;
        if (refs.refs[i].role==CustodyRole::playback) playback=i;
    }
    require(canonical<refs.refCount && playback<refs.refCount && refs.refs[canonical].length &&
        *refs.refs[canonical].length==blocks*blockSamples*sizeof(float),"canonical role/length");
    CustodyVector<float> canonicalChunk(32*blockSamples); auto* source = readers.value->at(slot).at(canonical).stream.Get();
    for (std::uint64_t n=0; n<blocks;) {
        checkDeadline(memory,capture.cancel); ULONG got=0;
        const auto count = static_cast<unsigned>((std::min)(blocks-n,std::uint64_t{32}));
        const auto bytes = static_cast<ULONG>(count*blockSamples*sizeof(float));
        checked(source->Read(canonicalChunk.data(),bytes,&got),"canonical read");
        require(got==bytes,"canonical full read");
        for (unsigned i=0; i<count; ++i)
            require(std::memcmp(canonicalChunk.data()+i*blockSamples,chunk[0].mixed.data(),blockSamples*sizeof(float))==0,"canonical full synthetic content");
        n+=count;
    }
    ULONG got=0; const auto end = source->Read(canonicalChunk.data(),sizeof(float),&got);
    require(end==S_FALSE && !got,"canonical EOF");
    decode(readers.value->at(slot).at(playback).stream.Get(),evidence.playback.decodedFrames,blocks*blockSamples,memory,capture.cancel);
    const auto verified = Clock::now();
    std::fprintf(stderr,"MEMORY_VERIFY warmup=%u cold_inspect_decode_ms=%lld stop_to_verified_ms=%lld canonical_checked_frames=%llu\n",
        unsigned(warmup),static_cast<long long>(std::chrono::duration_cast<std::chrono::milliseconds>(verified-finalized).count()),
        static_cast<long long>(std::chrono::duration_cast<std::chrono::milliseconds>(verified-stop).count()),
        static_cast<unsigned long long>(blocks*blockSamples)); std::fflush(stderr);
    memory.phase.store(warmup ? 0 : 4);
}
int run(Variant selected) {
    const auto baseline = CustodyOwnedMemory::usedBytes();
    require(baseline==0,"use a fresh dedicated process without other custody owners");
    // Cooperative cancellation only; the parent must set its hard timeout above this bound.
    const unsigned deadlineSeconds = selected.paced ? selected.minutes*60+1800 : selected.minutes*30+900;
    MemorySamples memory(Clock::now()+std::chrono::seconds(deadlineSeconds));
    std::fprintf(stderr,"MEMORY_PROBE synthetic_only=1 microphone=0 network=0 plaintext_files=0 minutes=%u mode=%s "
        "deadline_seconds=%u sample_requested_ms=%u owned_peak_kind=process_lifetime_admission strict_sc003_acceptance=0\n",
        selected.minutes,selected.paced ? "paced" : "accelerated",deadlineSeconds,pollMs); std::fflush(stderr);
    bool complete=false, mediaShutdown=true;
    try {
        {
            MediaRuntime runtime(mediaShutdown);
            recording(100,false,true,memory); // Same full cycle, fixed one-second synthetic warm-up.
            const auto drain = Clock::now()+std::chrono::seconds(5);
            while (CustodyOwnedMemory::usedBytes()!=baseline && Clock::now()<drain) std::this_thread::sleep_for(std::chrono::milliseconds(5));
            require(CustodyOwnedMemory::usedBytes()==baseline,"warm-up owners not drained");
            memory.warmed();
            recording(static_cast<std::uint64_t>(selected.minutes)*6000,selected.paced,false,memory);
        }
        complete=mediaShutdown;
    } catch (const std::exception& error) { std::fprintf(stderr,"MEMORY_PROBE failure=%s\n",error.what()); }
    memory.phase.store(4);
    const auto drain = Clock::now()+std::chrono::seconds(5);
    while (CustodyOwnedMemory::usedBytes()!=baseline && Clock::now()<drain) std::this_thread::sleep_for(std::chrono::milliseconds(5));
    memory.finish();
    const bool released = CustodyOwnedMemory::usedBytes()==baseline;
    std::fprintf(stderr,"MEMORY_PROBE completed=%u owned_baseline=%zu owned_final=%zu owned_admitted_lifetime_peak=%zu "
        "owners_released=%u strict_sc003_acceptance=0 metadata_priming_acceptance=NOT_ASSESSED\n",
        unsigned(complete),baseline,CustodyOwnedMemory::usedBytes(),CustodyOwnedMemory::peakBytes(),unsigned(released)); std::fflush(stderr);
    return complete && released ? 0 : 1;
}
}
#endif

int main(int argc, char** argv) {
    if (argc==2 && std::string_view(argv[1])=="--selfcheck") { selfcheck(); return 0; }
    Variant selected{};
    if (argc!=2 || !variant(argv[1],selected)) {
        std::fputs("Opt in: --synthetic-{10|60}min-{accelerated|paced}; --selfcheck runs pure source checks only.\n",stderr); return 2;
    }
#ifdef _WIN32
    try { return run(selected); }
    catch (const std::exception& error) { std::fprintf(stderr,"MEMORY_PROBE fatal=%s\n",error.what()); return 1; }
#else
    std::fputs("NOT_RUN Windows process/custody/MF test; this host supports --selfcheck only.\n",stderr); return 3;
#endif
}
