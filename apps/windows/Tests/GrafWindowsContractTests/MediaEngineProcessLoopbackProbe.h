#pragma once
// TEST ONLY: include at GLOBAL scope after the TU's anonymous AAC helper namespace.
// No factory shim, sink/trim claim, alternate playback role, or production hook.
#include "../../RecApp/Recording/ProtectedLocalRecordingPlayback.h"
#include "../GeneratedRecordingFixtures.h"
#include <audioclient.h>
#include <audioclientactivationparams.h>
#include <mmdeviceapi.h>
#include <wrl/implements.h>
#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <limits>
#include <memory>
#include <thread>
#include <utility>
#include <vector>

namespace {
using namespace graf::windows;
// BEGIN PROCESS LOOPBACK ARITHMETIC (also compiled unchanged by host selfcheck).
bool processLoopbackQpc100ns(std::uint64_t ticks, std::uint64_t frequency, std::uint64_t& out) noexcept {
    constexpr auto maximum = (std::numeric_limits<std::uint64_t>::max)();
    if (!frequency) return false;
    const auto q=ticks/frequency, r=ticks%frequency;
    if (q>maximum/10'000'000 || r>maximum/10'000'000) return false;
    const auto whole=q*10'000'000, fraction=r*10'000'000/frequency;
    if (fraction>maximum-whole) return false;
    out=whole+fraction; return true;
}
bool processLoopbackSample(std::uint64_t packet100ns, unsigned frame, std::uint64_t anchor,
    std::uint64_t& time100ns, unsigned& bin) noexcept {
    if (frame>=4800) return false;
    const auto offset=std::uint64_t{frame}*10'000'000/48000;
    if (packet100ns>(std::numeric_limits<std::uint64_t>::max)()-offset) return false;
    time100ns=packet100ns+offset;
    bin=time100ns<anchor ? 201U : time100ns-anchor>=10'000'000 ? 200U : unsigned((time100ns-anchor)/50'000);
    return true; // 201=pre-roll; 200=after the fixed observation bins, never source indices.
}
template<class Client> struct ProcessLoopbackPacketRelease {
    Client* client; unsigned frames; long& failure;
    ProcessLoopbackPacketRelease(Client* c,unsigned n,long& f) : client(c),frames(n),failure(f) {}
    ProcessLoopbackPacketRelease(const ProcessLoopbackPacketRelease&)=delete;
    ProcessLoopbackPacketRelease& operator=(const ProcessLoopbackPacketRelease&)=delete;
    ~ProcessLoopbackPacketRelease() { const auto hr=client->ReleaseBuffer(frames); if (hr<0 && failure>=0) failure=hr; }
};
// END PROCESS LOOPBACK ARITHMETIC
template<class Native, class Release> bool processLoopbackReleaseNative(Native& value, bool& attempted,
    long& failure, const char* kind, Release release) noexcept {
    if (!value) return true;
    if (attempted) return false; // Retain a failed release; never retry an ambiguous native outcome.
    attempted=true;
    const auto released=release(value);
    const DWORD native=released ? ERROR_SUCCESS : GetLastError();
    std::fprintf(stderr,"DIAGNOSTIC_ONLY strict_acceptance=0 PROCESS_LOOPBACK teardown_release=%s returned=%u native=%lu\n",
        kind,unsigned(released!=FALSE),static_cast<unsigned long>(native));
    if (!released) { if (failure>=0) failure=native ? HRESULT_FROM_WIN32(native) : E_FAIL; return false; }
    value=nullptr; return true;
}
struct ProcessLoopbackActivation {
    HANDLE event=CreateEventW(nullptr,TRUE,FALSE,nullptr);
    bool releaseAttempted=false;
    std::atomic<bool> done{false};
    AUDIOCLIENT_ACTIVATION_PARAMS params{};
    PROPVARIANT blob{};
    // The probe explicitly observes event release after callback drain, before dropping this owner.
    bool close(long& failure) noexcept {
        return processLoopbackReleaseNative(event,releaseAttempted,failure,"activation_event",
            [](HANDLE value) { return CloseHandle(value); });
    }
};
class ProcessLoopbackCompletion final : public Microsoft::WRL::RuntimeClass<
    Microsoft::WRL::RuntimeClassFlags<Microsoft::WRL::ClassicCom>,
    IActivateAudioInterfaceCompletionHandler, Microsoft::WRL::FtmBase> {
    std::shared_ptr<ProcessLoopbackActivation> state_;
public:
    static void* operator new(std::size_t) { return CustodyAllocator<ProcessLoopbackCompletion>{}.allocate(1); }
    static void operator delete(void* p) noexcept { CustodyAllocator<ProcessLoopbackCompletion>{}.deallocate(static_cast<ProcessLoopbackCompletion*>(p),1); }
    explicit ProcessLoopbackCompletion(std::shared_ptr<ProcessLoopbackActivation> state) : state_(std::move(state)) {}
    HRESULT STDMETHODCALLTYPE ActivateCompleted(IActivateAudioInterfaceAsyncOperation*) noexcept override {
        const auto held=state_; // System COM reference and this strong state survive the signal.
        SetEvent(held->event); held->done.store(true,std::memory_order_release); return S_OK;
    }
};
struct ProcessLoopbackProbe {
    using Clock=std::chrono::steady_clock;
    template<class T> using Ptr=Microsoft::WRL::ComPtr<T>;
    const Clock::time_point begun=Clock::now(), activeLimit=begun+std::chrono::seconds(45);
    std::unique_ptr<testing::GeneratedProtectedRecording> fixture;
    std::unique_ptr<ProtectedLocalRecordingPlayback> player;
    std::shared_ptr<ProcessLoopbackActivation> activation;
    Ptr<ProcessLoopbackCompletion> handler;
    Ptr<IActivateAudioInterfaceAsyncOperation> operation;
    Ptr<IAudioClient> client; Ptr<IAudioCaptureClient> capture;
    std::vector<std::array<AacAlignmentStats,2>,CustodyAllocator<std::array<AacAlignmentStats,2>>> bins{200};
    std::array<AacAlignmentStats,2> all{}, pre{};
    HMODULE module=nullptr; HANDLE packetEvent=nullptr;
    bool packetReleaseAttempted=false, moduleReleaseAttempted=false;
    bool com=false, pending=false, running=false, stopped=false, cleaned=false, ended=false, truncated=false;
    bool complete=false, gaps=false; long failure=S_OK;
    const char* phase="entry";
    std::uint64_t frequency=0, anchor=0, playBefore=0, playAfter=0, frames=0, packets=0;
    std::uint64_t previousQpc=0, previousEnd=0;
    void check(HRESULT hr) { if (FAILED(hr)) { if (failure>=0) failure=hr; throw hr; } }
    void require(bool ok) { check(ok ? S_OK : E_UNEXPECTED); }
    bool active() const { return !stopped && Clock::now()<activeLimit && (!fixture || !fixture->cancel->load()); }
    std::uint64_t qpc() {
        LARGE_INTEGER value{}; require(QueryPerformanceCounter(&value) && value.QuadPart>=0); return std::uint64_t(value.QuadPart);
    }
    void pump(Clock::time_point limit) {
        for (unsigned burst=0; burst<32 && active() && Clock::now()<limit; ++burst) {
            UINT32 available=0; check(capture->GetNextPacketSize(&available)); if (!available) break;
            BYTE* data=nullptr; UINT32 count=0; DWORD flags=0; UINT64 device=0, qpc100ns=0;
            const auto hr=capture->GetBuffer(&data,&count,&flags,&device,&qpc100ns);
            if (hr==AUDCLNT_S_BUFFER_EMPTY) break;
            check(hr); require(hr==S_OK && count!=0);
            { ProcessLoopbackPacketRelease<IAudioCaptureClient> release{capture.Get(),count,failure};
              require(count<=4800 && frames<=96000 && count<=96000-frames &&
                  device<=(std::numeric_limits<std::uint64_t>::max)()-count);
              require(active()); require((flags&AUDCLNT_BUFFERFLAGS_SILENT) || data);
              require(!(flags&~(AUDCLNT_BUFFERFLAGS_SILENT|AUDCLNT_BUFFERFLAGS_DATA_DISCONTINUITY|AUDCLNT_BUFFERFLAGS_TIMESTAMP_ERROR)));
              if ((flags&AUDCLNT_BUFFERFLAGS_TIMESTAMP_ERROR) ||
                  ((flags&AUDCLNT_BUFFERFLAGS_DATA_DISCONTINUITY) && packets)) gaps=true;
              if (packets && (qpc100ns<previousQpc ||
                  (qpc100ns>previousEnd ? qpc100ns-previousEnd : previousEnd-qpc100ns)>209)) gaps=true;
              std::fprintf(stderr,"DIAGNOSTIC_ONLY strict_acceptance=0 PROCESS_LOOPBACK packet=%llu frames=%u device=%llu qpc100ns=%llu flags=%lu gaps=%u device_semantics=%s\n",
                  static_cast<unsigned long long>(packets),count,static_cast<unsigned long long>(device),
                  static_cast<unsigned long long>(qpc100ns),static_cast<unsigned long>(flags),unsigned(gaps),device ? "unexpected_nonzero" : "virtual_unavailable");
              if (device) {
                  std::fputs("DIAGNOSTIC_ONLY strict_acceptance=0 PROCESS_LOOPBACK reason=unexpected_nonzero_device_position result=UNKNOWN\n",stderr);
                  require(false); // Fixed virtual observer only; never infer endpoint clock semantics.
              }
              require(!gaps); // Never populate timed bins from an untrustworthy capture timeline.
              for (unsigned i=0; i<count; ++i) {
                  std::uint64_t time=0; unsigned bin=0; require(processLoopbackSample(qpc100ns,i,anchor,time,bin));
                  for (unsigned channel=0; channel<2; ++channel) {
                      std::int16_t pcm=0;
                      if (!(flags&AUDCLNT_BUFFERFLAGS_SILENT)) std::memcpy(&pcm,data+(i*2+channel)*2,2);
                      const double value=pcm/32768.0; const auto index=frames+i;
                      all[channel].add(index,0,value);
                      if (!anchor || bin==201) pre[channel].add(index,0,value);
                      else if (bin<200) bins[bin][channel].add(index,0,value);
                  }
              }
              require(qpc100ns<=(std::numeric_limits<std::uint64_t>::max)()-std::uint64_t{count}*10'000'000/48000);
              previousEnd=qpc100ns+std::uint64_t{count}*10'000'000/48000;
              previousQpc=qpc100ns; frames+=count; ++packets;
            } check(static_cast<HRESULT>(failure));
        }
    }
    void run() {
        phase="fixture"; check(CoInitializeEx(nullptr,COINIT_MULTITHREADED)); com=true;
        LARGE_INTEGER f{}; require(QueryPerformanceFrequency(&f) && f.QuadPart>0); frequency=std::uint64_t(f.QuadPart);
        fixture=std::make_unique<testing::GeneratedProtectedRecording>("generated-diagnostic-process-loopback");
        { CustodyVector<CanonicalAudioFrame> scratch(1);
          for (unsigned n=0; n<3; ++n) {
            auto& frame=scratch.front(); frame.ptsFrames=n*480;
            for (unsigned i=0; i<480; ++i) frame.mixed[i]=aacAlignmentSource(n*480+i);
            require(fixture->writer->append(frame));
          }
        }
        const auto sealed=fixture->writer->finalize(); require(sealed.normalPackage() && sealed.durationMs==30);
        auto pair=fixture->coldPair(); require(pair.ok()); AacAlignmentTiming timing{};
        {
            auto readers=openProtectedCustodyReaders(fixture->paths.root,*pair.value,fixture->cancel); require(readers.ok());
            const auto& refs=(*pair.value)->current(); const auto slot=(*pair.value)->selectedSlot();
            std::size_t canonical=refs.refCount, playback=refs.refCount;
            for (std::size_t i=0;i<refs.refCount;++i) {
                if (refs.refs[i].role==CustodyRole::canonical) canonical=i;
                if (refs.refs[i].role==CustodyRole::playback) playback=i;
            }
            require(canonical<refs.refCount && playback<refs.refCount && refs.refs[canonical].length &&
                *refs.refs[canonical].length==1440*sizeof(float) && refs.refs[playback].length);
            CustodyVector<float> chunk(480);
            for (unsigned n=0;n<3;++n) {
                ULONG got=0; const auto bytes=static_cast<ULONG>(chunk.size()*sizeof(float));
                require(readers.value->at(slot).at(canonical).stream->Read(chunk.data(),bytes,&got)==S_OK && got==bytes);
                for (unsigned i=0;i<480;++i) require(chunk[i]==aacAlignmentSource(n*480+i));
            }
            auto* input=readers.value->at(slot).at(playback).stream.Get();
            timing=aacAlignmentTiming(*refs.refs[playback].length,[&](std::uint64_t at,std::uint8_t* data,unsigned count) {
                LARGE_INTEGER offset{}; offset.QuadPart=static_cast<LONGLONG>(at); ULARGE_INTEGER actual{}; ULONG got=0;
                return input->Seek(offset,STREAM_SEEK_SET,&actual)==S_OK && actual.QuadPart==at &&
                    input->Read(data,count,&got)==S_OK && got==count;
            });
        } // Every diagnostic Reader retires before genuine production inspection.
        auto inspection=LocalRecordingPackage::inspectProtected(fixture->paths.root,*pair.value,fixture->session,fixture->cancel);
        require(inspection.ok()); const auto evidence=(*inspection.value)->evidence();
        std::fprintf(stderr,"DIAGNOSTIC_ONLY strict_acceptance=0 PROCESS_LOOPBACK source_frames=1440 canonical_mismatched=0 inspector_raw=%llu container100ns=%llu metadata_known=%u metadata_offset=%llu source_alignment=UNKNOWN\n",
            static_cast<unsigned long long>(evidence.playback.decodedFrames),static_cast<unsigned long long>(evidence.playback.containerDuration100ns),
            unsigned(timing.known),static_cast<unsigned long long>(timing.known ? timing.offset : 0));
        require(Clock::now()<begun+std::chrono::seconds(20) && active()); phase="activation";
        module=LoadLibraryExW(L"MMDevAPI.dll",nullptr,LOAD_LIBRARY_SEARCH_SYSTEM32); require(module!=nullptr);
        using Activate=decltype(&::ActivateAudioInterfaceAsync); // SDK WINAPI signature, no static import reference.
        const auto activate=reinterpret_cast<Activate>(GetProcAddress(module,"ActivateAudioInterfaceAsync")); require(activate!=nullptr);
        activation=std::allocate_shared<ProcessLoopbackActivation>(CustodyAllocator<ProcessLoopbackActivation>{}); require(activation->event!=nullptr);
        activation->params.ActivationType=AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK;
        activation->params.ProcessLoopbackParams.TargetProcessId=GetCurrentProcessId();
        activation->params.ProcessLoopbackParams.ProcessLoopbackMode=PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE;
        activation->blob.vt=VT_BLOB; activation->blob.blob.cbSize=static_cast<ULONG>(sizeof(activation->params));
        activation->blob.blob.pBlobData=reinterpret_cast<BYTE*>(&activation->params);
        handler.Attach(new ProcessLoopbackCompletion(activation));
        const auto activated=activate(VIRTUAL_AUDIO_DEVICE_PROCESS_LOOPBACK,__uuidof(IAudioClient),&activation->blob,handler.Get(),&operation);
        pending=SUCCEEDED(activated) || operation.Get()!=nullptr; check(activated); require(operation.Get()!=nullptr);
        const auto activationLimit=Clock::now()+std::chrono::seconds(5);
        while (!activation->done.load(std::memory_order_acquire) && active() && Clock::now()<activationLimit)
            require(WaitForSingleObject(activation->event,2)!=WAIT_FAILED);
        require(active() && activation->done.load(std::memory_order_acquire));
        HRESULT result=E_UNEXPECTED; Ptr<IUnknown> object;
        check(operation->GetActivateResult(&result,&object)); check(result); require(object.Get()!=nullptr);
        check(object.As(&client)); object.Reset();
        WAVEFORMATEX format{}; format.wFormatTag=WAVE_FORMAT_PCM; format.nChannels=2; format.nSamplesPerSec=48000;
        format.wBitsPerSample=16; format.nBlockAlign=4; format.nAvgBytesPerSec=192000;
        check(client->Initialize(AUDCLNT_SHAREMODE_SHARED,AUDCLNT_STREAMFLAGS_LOOPBACK|AUDCLNT_STREAMFLAGS_EVENTCALLBACK|
            AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM,0,0,&format,nullptr));
        UINT32 buffer=0; check(client->GetBufferSize(&buffer)); require(buffer && buffer<=48000);
        packetEvent=CreateEventW(nullptr,FALSE,FALSE,nullptr); require(packetEvent!=nullptr);
        check(client->GetService(IID_PPV_ARGS(&capture))); require(capture.Get()!=nullptr); check(client->SetEventHandle(packetEvent));
        std::fprintf(stderr,"DIAGNOSTIC_ONLY strict_acceptance=0 PROCESS_LOOPBACK pid=%lu include_tree=1 observer_rate=48000 channels=2 bits=16 autoconvert_observer_only=1 buffer_frames=%u qpc_frequency=%llu\n",
            static_cast<unsigned long>(GetCurrentProcessId()),buffer,static_cast<unsigned long long>(frequency));
        phase="open"; auto opened=ProtectedLocalRecordingPlayback::open(std::move(*inspection.value),fixture->cancel,false);
        if (!opened.ok()) { std::fprintf(stderr,"PROCESS_LOOPBACK open_error=%u native=%08x\n",unsigned(opened.error),opened.nativeError); check(E_FAIL); }
        player=std::move(*opened.value); phase="ready"; const auto readyLimit=Clock::now()+std::chrono::seconds(10);
        while (active() && Clock::now()<readyLimit) { const auto s=player->observe(); check(s.error); if (s.ready && !s.muted) break; Sleep(2); }
        const auto ready=player->observe(); check(ready.error); require(ready.ready && !ready.muted && active());
        check(client->Start()); running=true; phase="pre_roll";
        const auto preLimit=Clock::now()+std::chrono::milliseconds(100);
        while (active() && Clock::now()<preLimit) { pump(preLimit); require(WaitForSingleObject(packetEvent,2)!=WAIT_FAILED); }
        require(active()); phase="play"; playBefore=qpc(); require(processLoopbackQpc100ns(playBefore,frequency,anchor));
        check(player->play()); playAfter=qpc(); const auto playLimit=Clock::now()+std::chrono::seconds(10);
        const auto observationLimit=Clock::now()+std::chrono::seconds(1); auto drainLimit=(Clock::time_point::max)();
        while (active() && Clock::now()<playLimit) {
            const auto s=player->observe(); check(s.error);
            if (s.ended && !ended) { ended=true; drainLimit=Clock::now()+std::chrono::milliseconds(250); }
            if (running && (Clock::now()>=observationLimit || Clock::now()>=drainLimit)) {
                truncated=Clock::now()<drainLimit; check(client->Stop()); running=false;
            }
            if (running) pump((std::min)(observationLimit,drainLimit)); else if (ended) break;
            if (running) require(WaitForSingleObject(packetEvent,2)!=WAIT_FAILED); else Sleep(2);
        }
        require(active() && ended); complete=true;
    }
    bool close() noexcept {
        if (cleaned) return true;
        if ((activation && activation->releaseAttempted && activation->event) ||
            (packetReleaseAttempted && packetEvent) || (moduleReleaseAttempted && module)) return false;
        stopped=true; if (fixture) fixture->cancel->store(true,std::memory_order_release);
        if (running) { const auto hr=client->Stop(); if (FAILED(hr)) { if (failure>=0) failure=hr; return false; } running=false;
            std::fputs("DIAGNOSTIC_ONLY strict_acceptance=0 PROCESS_LOOPBACK teardown=capture_stopped\n",stderr); }
        if (player) { if (!player->startClose() || !player->drained()) return false; player.reset();
            std::fputs("DIAGNOSTIC_ONLY strict_acceptance=0 PROCESS_LOOPBACK teardown=player_drained\n",stderr); }
        if (pending && !activation->done.load(std::memory_order_acquire)) return false;
        capture.Reset(); client.Reset(); operation.Reset(); handler.Reset(); pending=false;
        if (activation && activation.use_count()!=1) return false; // The callback still owns its strong state.
        std::fputs("DIAGNOSTIC_ONLY strict_acceptance=0 PROCESS_LOOPBACK teardown=async_refs_released\n",stderr);
        if (activation && !activation->close(failure)) return false;
        activation.reset();
        if (!processLoopbackReleaseNative(packetEvent,packetReleaseAttempted,failure,"packet_event",
            [](HANDLE value) { return CloseHandle(value); })) return false;
        if (!processLoopbackReleaseNative(module,moduleReleaseAttempted,failure,"module",
            [](HMODULE value) { return FreeLibrary(value); })) return false;
        fixture.reset(); if (com) { CoUninitialize(); com=false; }
        std::fputs("DIAGNOSTIC_ONLY strict_acceptance=0 PROCESS_LOOPBACK teardown=complete\n",stderr);
        cleaned=true; return true;
    }
    void printStats(const char* label,unsigned channel,const AacAlignmentStats& s) const {
        const double n=static_cast<double>(s.count);
        std::fprintf(stderr,"DIAGNOSTIC_ONLY strict_acceptance=0 PROCESS_LOOPBACK window=%s channel=%u count=%llu mean=%.17g rms=%.17g tone1000=%.17g tone2000=%.17g source_alignment=UNKNOWN\n",
            label,channel,static_cast<unsigned long long>(s.count),n ? s.y/n : 0,n ? std::sqrt(s.yy/n) : 0,
            n ? 2*std::hypot(s.real[0],s.imag[0])/n : 0,n ? 2*std::hypot(s.real[1],s.imag[1])/n : 0);
    }
    void finish() {
        const auto until=(std::min)(Clock::now()+std::chrono::seconds(30),begun+std::chrono::seconds(75));
        while (!close() && Clock::now()<until) Sleep(2);
        if (!cleaned) { complete=false; if (failure>=0) failure=HRESULT_FROM_WIN32(ERROR_TIMEOUT); }
        for (unsigned channel=0;channel<2;++channel) { printStats("all_capture",channel,all[channel]); printStats("pre_roll",channel,pre[channel]); }
        for (unsigned bin=0;bin<200;++bin) { char label[32]{}; std::snprintf(label,sizeof(label),"qpc_%u_%u_ms",bin*5,(bin+1)*5);
            for (unsigned channel=0;channel<2;++channel) printStats(label,channel,bins[bin][channel]); }
        if (Clock::now()>=begun+std::chrono::seconds(80)) { complete=false; if (failure>=0) failure=HRESULT_FROM_WIN32(ERROR_TIMEOUT); }
        std::fprintf(stderr,"DIAGNOSTIC_ONLY strict_acceptance=0 PROCESS_LOOPBACK phase=%s execution_complete=%u native=%08lx packets=%llu capture_frames=%llu gaps=%u observation_truncated=%u ended=%u cleaned=%u play_before_ticks=%llu play_after_ticks=%llu anchor100ns=%llu render_signal_observed=%u presentation_trim=UNKNOWN all_source_rendered=UNKNOWN result=UNKNOWN\n",
            phase,unsigned(complete && cleaned && failure>=0),static_cast<unsigned long>(failure),static_cast<unsigned long long>(packets),
            static_cast<unsigned long long>(frames),unsigned(gaps),unsigned(truncated),unsigned(ended),unsigned(cleaned),
            static_cast<unsigned long long>(playBefore),static_cast<unsigned long long>(playAfter),static_cast<unsigned long long>(anchor),
            unsigned(!gaps && packets && (all[0].yy>0 || all[1].yy>0)));
        std::fflush(stderr);
    }
    ~ProcessLoopbackProbe() { while (!cleaned && !close()) Sleep(2); } // External 90s runner owns a hung native process, never detach/release early.
};
[[nodiscard]] int diagnosticMediaEngineProcessLoopback() {
    const auto baseline=CustodyOwnedMemory::usedBytes();
    try {
        ProcessLoopbackProbe owner;
        try { owner.run(); } catch (HRESULT hr) { if (owner.failure>=0) owner.failure=hr; }
        catch (...) { if (owner.failure>=0) owner.failure=E_FAIL; }
        owner.finish();
    } catch (...) { std::fputs("DIAGNOSTIC_ONLY strict_acceptance=0 PROCESS_LOOPBACK construction_error=1 result=UNKNOWN\n",stderr); }
    std::fprintf(stderr,"DIAGNOSTIC_ONLY strict_acceptance=0 PROCESS_LOOPBACK owned_baseline=%zu owned_final=%zu released=%u presentation_trim=UNKNOWN all_source_rendered=UNKNOWN result=UNKNOWN\n",
        baseline,CustodyOwnedMemory::usedBytes(),unsigned(baseline==CustodyOwnedMemory::usedBytes()));
    return 96; // Diagnostic completion, absence, failure and unsupported API never become strict PASS.
}
} // anonymous namespace
