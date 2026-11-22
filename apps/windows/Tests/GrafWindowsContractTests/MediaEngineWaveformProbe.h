#pragma once
// Test TU only, included INSIDE its anonymous namespace after aacAlignmentPrint.
// Requires global SDK <mftransform.h>. Forward-declare mediaEngineWaveformCoCreateInstance
// in this same anonymous namespace; redirect CoCreateInstance only around the
// existing ProtectedLocalRecordingPlayback.cpp include, then immediately undef it.
// No PCM copies/files, acceptance policy, public API, or production instrumentation.

struct MediaEngineWaveformModel {
    std::array<AacAlignmentStats,6> windows{};
    AacAlignmentStats prefix, tail;
    void add(std::int64_t position, std::uint64_t frames, double value) noexcept {
        if (position < 0) { prefix.add(prefix.count,0,value); return; }
        const auto at = static_cast<std::uint64_t>(position);
        if (at >= frames) { tail.add(tail.count,0,value); return; }
        const std::array<std::array<std::uint64_t,2>,6> ranges{{
            {0,frames},{0,frames/2},{frames/2,frames},{0,(std::min)(frames,std::uint64_t{240})},
            {(std::min)(frames,std::uint64_t{480}),(std::min)(frames,std::uint64_t{960})},
            {frames-(std::min)(frames,std::uint64_t{240}),frames}}};
        for (std::size_t i = 0; i < ranges.size(); ++i)
            if (at >= ranges[i][0] && at < ranges[i][1]) windows[i].add(at,aacAlignmentReference(at),value);
    }
};

std::int64_t mediaEngineWaveformFrame(LONGLONG ticks) noexcept {
    // Quotient/remainder avoids overflow even for INT64_MIN; round to nearest frame.
    const auto remainder = ticks%10'000'000;
    return ticks/10'000'000*48000 + (remainder*48000+(remainder < 0 ? -5'000'000 : 5'000'000))/10'000'000;
}

struct MediaEngineWaveformState {
    std::mutex mutex;
    const std::uint64_t frames, rawBound;
    std::uint64_t inspectorRaw = 0;
    AacAlignmentTiming timing{};
    AacAlignmentStats raw;
    std::array<MediaEngineWaveformModel,3> models{}; // no-offset, metadata, sample timestamps
    HRESULT failure = S_OK;
    unsigned factories = 0, insertions = 0, samples = 0, outputs = 0, flushes = 0, drains = 0, starts = 0, ends = 0;
    unsigned liveFactories = 0, liveTransforms = 0;
    unsigned typeRejections = 0;
    bool discontinuous = false, timelineContiguous = true;
    LONGLONG firstTime = 0, lastTime = 0, lastSpan = 0;
    std::int64_t nextFrame = 0;
    explicit MediaEngineWaveformState(std::uint64_t count) : frames(count), rawBound(count+4800) {}
    void fail(HRESULT hr) noexcept { if (SUCCEEDED(failure)) failure = hr; }
};

// Synchronous one-input/one-output identity MFT. The exact incoming IMFSample is
// returned with its buffers/attributes unchanged; inspection happens on output.
class MediaEngineWaveformTransform final : public IMFTransform {
    using State = MediaEngineWaveformState;
    template<class T> using Ptr = Microsoft::WRL::ComPtr<T>;
    std::atomic<ULONG> references_{1};
    std::shared_ptr<State> state_;
    Ptr<IMFMediaType> input_, output_;
    Ptr<IMFSample> pending_;
    static HRESULT validType(IMFMediaType* type) noexcept {
        if (!type) return S_OK;
        GUID major{}, subtype{}; UINT32 rate = 0, channels = 0, bits = 0, block = 0, average = 0;
        if (FAILED(type->GetGUID(MF_MT_MAJOR_TYPE,&major)) || major != MFMediaType_Audio ||
            FAILED(type->GetGUID(MF_MT_SUBTYPE,&subtype)) ||
            (subtype != MFAudioFormat_PCM && subtype != MFAudioFormat_Float) ||
            FAILED(type->GetUINT32(MF_MT_AUDIO_SAMPLES_PER_SECOND,&rate)) || rate != 48000 ||
            FAILED(type->GetUINT32(MF_MT_AUDIO_NUM_CHANNELS,&channels)) || channels != 1 ||
            FAILED(type->GetUINT32(MF_MT_AUDIO_BITS_PER_SAMPLE,&bits)) ||
            bits != (subtype == MFAudioFormat_PCM ? 16U : 32U) ||
            FAILED(type->GetUINT32(MF_MT_AUDIO_BLOCK_ALIGNMENT,&block)) || block != bits/8 ||
            FAILED(type->GetUINT32(MF_MT_AUDIO_AVG_BYTES_PER_SECOND,&average)) || average != 48000*block)
            return MF_E_INVALIDMEDIATYPE;
        return S_OK;
    }
    HRESULT setType(DWORD id, IMFMediaType* type, DWORD flags, bool input) {
        if (id) return MF_E_INVALIDSTREAMNUMBER;
        if (flags & ~MFT_SET_TYPE_TEST_ONLY) return E_INVALIDARG;
        std::lock_guard<std::mutex> lock(state_->mutex);
        auto hr = validType(type);
        if (FAILED(hr)) { ++state_->typeRejections; return hr; }
        const auto& other = input ? output_ : input_;
        if (type && other) { DWORD equal = 0; hr = type->IsEqual(other.Get(),&equal); if (hr != S_OK) return MF_E_INVALIDMEDIATYPE; }
        if (flags & MFT_SET_TYPE_TEST_ONLY) return S_OK;
        if (pending_) return MF_E_TRANSFORM_CANNOT_CHANGE_MEDIATYPE_WHILE_PROCESSING;
        // Clone metadata so a caller cannot mutate the negotiated type behind us.
        Ptr<IMFMediaType> copy;
        if (type) { hr = MFCreateMediaType(&copy); if (FAILED(hr)) return hr; hr = type->CopyAllItems(copy.Get()); if (FAILED(hr)) return hr; }
        (input ? input_ : output_) = std::move(copy);
        return S_OK;
    }
    HRESULT getType(DWORD id, IMFMediaType** type, bool input, bool available, DWORD index = 0) {
        if (!type) return E_POINTER; *type = nullptr;
        if (id) return MF_E_INVALIDSTREAMNUMBER;
        if (available && index) return MF_E_NO_MORE_TYPES;
        std::lock_guard<std::mutex> lock(state_->mutex);
        const auto& current = input ? input_ : output_;
        const auto& other = input ? output_ : input_;
        if (available && other) return other.CopyTo(type);
        if (!available) return current ? current.CopyTo(type) : MF_E_TRANSFORM_TYPE_NOT_SET;
        // One preferred float32 type; complete PCM16 is also accepted.
        Ptr<IMFMediaType> candidate; auto hr = MFCreateMediaType(&candidate); if (FAILED(hr)) return hr;
        for (const auto result : {candidate->SetGUID(MF_MT_MAJOR_TYPE,MFMediaType_Audio),
            candidate->SetGUID(MF_MT_SUBTYPE,MFAudioFormat_Float),candidate->SetUINT32(MF_MT_AUDIO_NUM_CHANNELS,1),
            candidate->SetUINT32(MF_MT_AUDIO_SAMPLES_PER_SECOND,48000),candidate->SetUINT32(MF_MT_AUDIO_BITS_PER_SAMPLE,32),
            candidate->SetUINT32(MF_MT_AUDIO_BLOCK_ALIGNMENT,4),candidate->SetUINT32(MF_MT_AUDIO_AVG_BYTES_PER_SECOND,192000)})
            if (FAILED(result)) return result;
        return candidate.CopyTo(type);
    }
    HRESULT observe(IMFSample* sample) {
        auto& s = *state_; // Caller holds the state lock. No PCM survives this call.
        DWORD total = 0, buffers = 0; LONGLONG time = 0, span = 0; UINT32 bits = 0;
        auto hr = sample->GetTotalLength(&total); if (FAILED(hr)) return hr;
        if (FAILED(hr = input_->GetUINT32(MF_MT_AUDIO_BITS_PER_SAMPLE,&bits))) return hr;
        const auto block = bits/8;
        if (!total || total > 65536 || total%block || total/block > s.rawBound-s.raw.count || s.samples >= 64)
            return MF_E_INVALIDMEDIATYPE;
        if (FAILED(hr = sample->GetSampleTime(&time)) || FAILED(hr = sample->GetSampleDuration(&span)) || span <= 0) return FAILED(hr) ? hr : MF_E_INVALIDMEDIATYPE;
        const auto begin = mediaEngineWaveformFrame(time);
        const auto count = total/block;
        if (mediaEngineWaveformFrame(span) != static_cast<std::int64_t>(count)) return MF_E_INVALIDMEDIATYPE;
        if (s.samples && begin != s.nextFrame) s.timelineContiguous = false;
        if (!s.samples) s.firstTime = time;
        s.nextFrame = begin+count; s.lastTime = time; s.lastSpan = span;
        UINT32 discontinuity = 0;
        const auto attribute = sample->GetUINT32(MFSampleExtension_Discontinuity,&discontinuity);
        if (FAILED(attribute) && attribute != MF_E_ATTRIBUTENOTFOUND) return attribute;
        s.discontinuous = s.discontinuous || (SUCCEEDED(attribute) && discontinuity != 0);
        if (FAILED(hr = sample->GetBufferCount(&buffers))) return hr;
        if (!buffers || buffers > 32) return MF_E_INVALIDMEDIATYPE;
        std::fprintf(stderr,"DIAGNOSTIC_ONLY strict_acceptance=0 MEDIA_ENGINE_WAVEFORM frames=%llu sample=%u raw_begin=%llu bytes=%lu bits=%u timestamp=%lld span=%lld buffers=%lu discontinuity=%u tap_stage=effect_pre_renderer trim_stage=UNKNOWN\n",
            static_cast<unsigned long long>(s.frames),s.samples,static_cast<unsigned long long>(s.raw.count),total,bits,time,span,buffers,discontinuity);
        std::uint64_t read = 0;
        for (DWORD n = 0; n < buffers; ++n) {
            Ptr<IMFMediaBuffer> buffer; if (FAILED(hr = sample->GetBufferByIndex(n,&buffer))) return hr;
            BYTE* data = nullptr; DWORD capacity = 0, size = 0;
            if (FAILED(hr = buffer->Lock(&data,&capacity,&size))) return hr;
            HRESULT observed = S_OK;
            if (!data || size > capacity || size%block || size > total-read) observed = MF_E_INVALIDMEDIATYPE;
            else for (DWORD at = 0; at < size; at += block) {
                double value = 0;
                if (bits == 16) { std::int16_t pcm = 0; std::memcpy(&pcm,data+at,2); value = static_cast<double>(pcm)/32768; }
                else { float pcm = 0; std::memcpy(&pcm,data+at,4); value = pcm; }
                if (!std::isfinite(value)) { observed = MF_E_INVALIDMEDIATYPE; break; }
                const auto raw = static_cast<std::int64_t>(s.raw.count);
                s.models[0].add(raw,s.frames,value);
                if (s.timing.known) s.models[1].add(raw-static_cast<std::int64_t>(s.timing.offset),s.frames,value);
                s.models[2].add(begin+static_cast<std::int64_t>(read/block+at/block),s.frames,value);
                s.raw.add(s.raw.count,0,value);
            }
            const auto unlocked = buffer->Unlock();
            if (FAILED(observed)) return observed;
            if (FAILED(unlocked)) return unlocked;
            read += size;
        }
        if (read != total) return MF_E_INVALIDMEDIATYPE;
        ++s.samples; return S_OK;
    }
public:
    static void* operator new(std::size_t) { return CustodyAllocator<MediaEngineWaveformTransform>{}.allocate(1); }
    static void operator delete(void* p) noexcept { CustodyAllocator<MediaEngineWaveformTransform>{}.deallocate(static_cast<MediaEngineWaveformTransform*>(p),1); }
    explicit MediaEngineWaveformTransform(std::shared_ptr<State> state) : state_(std::move(state)) {
        std::lock_guard<std::mutex> lock(state_->mutex); ++state_->liveTransforms;
    }
    ~MediaEngineWaveformTransform() { std::lock_guard<std::mutex> lock(state_->mutex); pending_.Reset(); --state_->liveTransforms; }
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID iid, void** out) override {
        if (!out) return E_POINTER; *out = nullptr;
        if (iid != __uuidof(IUnknown) && iid != __uuidof(IMFTransform)) return E_NOINTERFACE;
        *out = static_cast<IMFTransform*>(this); AddRef(); return S_OK;
    }
    ULONG STDMETHODCALLTYPE AddRef() override { return ++references_; }
    ULONG STDMETHODCALLTYPE Release() override { const auto n = --references_; if (!n) delete this; return n; }
    HRESULT STDMETHODCALLTYPE GetStreamLimits(DWORD* a,DWORD* b,DWORD* c,DWORD* d) override { if (!a||!b||!c||!d) return E_POINTER; *a=*b=*c=*d=1; return S_OK; }
    HRESULT STDMETHODCALLTYPE GetStreamCount(DWORD* in,DWORD* out) override { if (!in||!out) return E_POINTER; *in=*out=1; return S_OK; }
    HRESULT STDMETHODCALLTYPE GetStreamIDs(DWORD,DWORD*,DWORD,DWORD*) override { return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE GetInputStreamInfo(DWORD id,MFT_INPUT_STREAM_INFO* info) override {
        if (!info) return E_POINTER; if (id) return MF_E_INVALIDSTREAMNUMBER;
        *info = {}; info->dwFlags=MFT_INPUT_STREAM_WHOLE_SAMPLES; return S_OK;
    }
    HRESULT STDMETHODCALLTYPE GetOutputStreamInfo(DWORD id,MFT_OUTPUT_STREAM_INFO* info) override {
        if (!info) return E_POINTER; if (id) return MF_E_INVALIDSTREAMNUMBER;
        *info = {}; info->dwFlags=MFT_OUTPUT_STREAM_WHOLE_SAMPLES|MFT_OUTPUT_STREAM_PROVIDES_SAMPLES; return S_OK;
    }
    HRESULT STDMETHODCALLTYPE GetAttributes(IMFAttributes** out) override { if (!out) return E_POINTER; *out=nullptr; return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE GetInputStreamAttributes(DWORD id,IMFAttributes** out) override { return id ? MF_E_INVALIDSTREAMNUMBER : GetAttributes(out); }
    HRESULT STDMETHODCALLTYPE GetOutputStreamAttributes(DWORD id,IMFAttributes** out) override { return id ? MF_E_INVALIDSTREAMNUMBER : GetAttributes(out); }
    HRESULT STDMETHODCALLTYPE DeleteInputStream(DWORD) override { return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE AddInputStreams(DWORD,DWORD*) override { return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE GetInputAvailableType(DWORD id,DWORD index,IMFMediaType** out) override { return getType(id,out,true,true,index); }
    HRESULT STDMETHODCALLTYPE GetOutputAvailableType(DWORD id,DWORD index,IMFMediaType** out) override { return getType(id,out,false,true,index); }
    HRESULT STDMETHODCALLTYPE SetInputType(DWORD id,IMFMediaType* type,DWORD flags) override { return setType(id,type,flags,true); }
    HRESULT STDMETHODCALLTYPE SetOutputType(DWORD id,IMFMediaType* type,DWORD flags) override { return setType(id,type,flags,false); }
    HRESULT STDMETHODCALLTYPE GetInputCurrentType(DWORD id,IMFMediaType** out) override { return getType(id,out,true,false); }
    HRESULT STDMETHODCALLTYPE GetOutputCurrentType(DWORD id,IMFMediaType** out) override { return getType(id,out,false,false); }
    HRESULT STDMETHODCALLTYPE GetInputStatus(DWORD id,DWORD* flags) override {
        if (!flags) return E_POINTER; if (id) return MF_E_INVALIDSTREAMNUMBER;
        std::lock_guard<std::mutex> lock(state_->mutex); *flags=input_&&output_&&!pending_ ? MFT_INPUT_STATUS_ACCEPT_DATA : 0; return S_OK;
    }
    HRESULT STDMETHODCALLTYPE GetOutputStatus(DWORD* flags) override { if (!flags) return E_POINTER; std::lock_guard<std::mutex> lock(state_->mutex); *flags=pending_ ? MFT_OUTPUT_STATUS_SAMPLE_READY : 0; return S_OK; }
    HRESULT STDMETHODCALLTYPE SetOutputBounds(LONGLONG,LONGLONG) override { return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE ProcessEvent(DWORD id,IMFMediaEvent*) override { return id ? MF_E_INVALIDSTREAMNUMBER : E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE ProcessMessage(MFT_MESSAGE_TYPE message,ULONG_PTR) override {
        std::lock_guard<std::mutex> lock(state_->mutex);
        if (message == MFT_MESSAGE_COMMAND_FLUSH) { if (pending_) state_->fail(E_UNEXPECTED); pending_.Reset(); ++state_->flushes; }
        else if (message == MFT_MESSAGE_COMMAND_DRAIN) ++state_->drains;
        else if (message == MFT_MESSAGE_NOTIFY_START_OF_STREAM) ++state_->starts;
        else if (message == MFT_MESSAGE_NOTIFY_END_OF_STREAM) ++state_->ends;
        else if (message != MFT_MESSAGE_NOTIFY_BEGIN_STREAMING && message != MFT_MESSAGE_NOTIFY_END_STREAMING &&
            message != MFT_MESSAGE_NOTIFY_RELEASE_RESOURCES && message != MFT_MESSAGE_NOTIFY_REACQUIRE_RESOURCES) return E_NOTIMPL;
        return S_OK;
    }
    HRESULT STDMETHODCALLTYPE ProcessInput(DWORD id,IMFSample* sample,DWORD flags) override {
        if (id) return MF_E_INVALIDSTREAMNUMBER; if (!sample) return E_POINTER; if (flags) return E_INVALIDARG;
        std::lock_guard<std::mutex> lock(state_->mutex);
        if (!input_ || !output_) return MF_E_TRANSFORM_TYPE_NOT_SET;
        if (pending_) return MF_E_NOTACCEPTING;
        if (FAILED(state_->failure)) return state_->failure;
        DWORD size = 0; const auto hr = sample->GetTotalLength(&size); if (FAILED(hr)) return hr;
        if (!size || size > 65536) { state_->fail(MF_E_INVALIDMEDIATYPE); return state_->failure; }
        pending_ = sample; return S_OK;
    }
    HRESULT STDMETHODCALLTYPE ProcessOutput(DWORD flags,DWORD count,MFT_OUTPUT_DATA_BUFFER* out,DWORD* status) override {
        if (!out || !status) return E_POINTER; *status=0;
        if (flags || count != 1 || out[0].dwStreamID || out[0].pSample || out[0].pEvents) return E_INVALIDARG;
        out[0].dwStatus=0;
        std::lock_guard<std::mutex> lock(state_->mutex);
        if (!input_ || !output_) return MF_E_TRANSFORM_TYPE_NOT_SET;
        if (!pending_) return MF_E_TRANSFORM_NEED_MORE_INPUT;
        const auto hr = observe(pending_.Get());
        if (FAILED(hr)) { state_->fail(hr); pending_.Reset(); return hr; }
        out[0].pSample=pending_.Detach(); ++state_->outputs; return S_OK;
    }
};

class MediaEngineWaveformFactory final : public IMFMediaEngineClassFactory {
    std::atomic<ULONG> references_{1};
    Microsoft::WRL::ComPtr<IMFMediaEngineClassFactory> real_;
    std::shared_ptr<MediaEngineWaveformState> state_;
public:
    static void* operator new(std::size_t) { return CustodyAllocator<MediaEngineWaveformFactory>{}.allocate(1); }
    static void operator delete(void* p) noexcept { CustodyAllocator<MediaEngineWaveformFactory>{}.deallocate(static_cast<MediaEngineWaveformFactory*>(p),1); }
    MediaEngineWaveformFactory(IMFMediaEngineClassFactory* real,std::shared_ptr<MediaEngineWaveformState> state) : real_(real),state_(std::move(state)) {
        std::lock_guard<std::mutex> lock(state_->mutex); ++state_->factories; ++state_->liveFactories;
    }
    ~MediaEngineWaveformFactory() { std::lock_guard<std::mutex> lock(state_->mutex); --state_->liveFactories; }
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID iid,void** out) override {
        if (!out) return E_POINTER; *out=nullptr;
        if (iid != __uuidof(IUnknown) && iid != __uuidof(IMFMediaEngineClassFactory)) return E_NOINTERFACE;
        *out=static_cast<IMFMediaEngineClassFactory*>(this); AddRef(); return S_OK;
    }
    ULONG STDMETHODCALLTYPE AddRef() override { return ++references_; }
    ULONG STDMETHODCALLTYPE Release() override { const auto n=--references_; if (!n) delete this; return n; }
    HRESULT STDMETHODCALLTYPE CreateTimeRange(IMFMediaTimeRange** out) override { return real_->CreateTimeRange(out); }
    HRESULT STDMETHODCALLTYPE CreateError(IMFMediaError** out) override { return real_->CreateError(out); }
    HRESULT STDMETHODCALLTYPE CreateInstance(DWORD flags,IMFAttributes* attributes,IMFMediaEngine** out) override {
        const auto hr=real_->CreateInstance(flags,attributes,out); if (FAILED(hr)) return hr;
        if (!out || !*out) return E_UNEXPECTED;
        HRESULT inserted=E_OUTOFMEMORY;
        try {
            Microsoft::WRL::ComPtr<IMFTransform> effect; effect.Attach(new MediaEngineWaveformTransform(state_));
            Microsoft::WRL::ComPtr<IMFMediaEngineEx> extended;
            inserted=(*out)->QueryInterface(IID_PPV_ARGS(&extended));
            if (SUCCEEDED(inserted)) inserted=extended->InsertAudioEffect(effect.Get(),FALSE);
        } catch (const std::bad_alloc&) { inserted=E_OUTOFMEMORY; }
        {
            std::lock_guard<std::mutex> lock(state_->mutex);
            if (SUCCEEDED(inserted)) ++state_->insertions; else state_->fail(inserted);
        }
        // Keep even a failed-insertion engine in the output. Returning its real
        // creation result lets production open own Shutdown/drain; the driver
        // refuses Play, never a false optional-observer success.
        return hr;
    }
};

thread_local std::shared_ptr<MediaEngineWaveformState> mediaEngineWaveformArmed;
HRESULT WINAPI mediaEngineWaveformCoCreateInstance(REFCLSID clsid,LPUNKNOWN outer,DWORD context,REFIID iid,LPVOID* out) {
    if (!mediaEngineWaveformArmed || clsid != CLSID_MFMediaEngineClassFactory ||
        iid != __uuidof(IMFMediaEngineClassFactory) || outer)
        return ::CoCreateInstance(clsid,outer,context,iid,out);
    if (!out) return E_POINTER; *out=nullptr;
    Microsoft::WRL::ComPtr<IMFMediaEngineClassFactory> real;
    auto hr=::CoCreateInstance(clsid,outer,context,iid,reinterpret_cast<void**>(real.GetAddressOf()));
    if (FAILED(hr)) return hr;
    if (!real) return E_UNEXPECTED;
    try { *out=static_cast<IMFMediaEngineClassFactory*>(new MediaEngineWaveformFactory(real.Get(),mediaEngineWaveformArmed)); return hr; }
    catch (const std::bad_alloc&) { return E_OUTOFMEMORY; }
}

// Default playback only: observation may complete, but the final trim/sink stage
// is UNKNOWN. Caller must propagate the return code, not turn it into strict PASS.
[[nodiscard]] int diagnosticMediaEngineWaveform() {
    const auto baseline=CustodyOwnedMemory::usedBytes();
    for (const unsigned blocks : {3U,1U}) {
        const auto state=std::allocate_shared<MediaEngineWaveformState>(CustodyAllocator<MediaEngineWaveformState>{},blocks*480ULL);
        const bool completed=std::async(std::launch::async,[&]() -> bool { try {
            testing::GeneratedProtectedRecording capture("generated-diagnostic-media-engine-waveform");
            for (unsigned n=0;n<blocks;++n) {
                CanonicalAudioFrame frame; frame.ptsFrames=n*480;
                for (unsigned at=0;at<480;++at) frame.mixed[at]=aacAlignmentSource(n*480+at);
                if (!capture.writer->append(frame)) return false;
            }
            const auto sealed=capture.writer->finalize();
            if (!sealed.normalPackage() || sealed.durationMs != blocks*10) return false;
            auto pair=capture.coldPair(); if (!pair.ok()) return false;
            auto inspection=LocalRecordingPackage::inspectProtected(capture.paths.root,*pair.value,capture.session,capture.cancel);
            if (!inspection.ok()) return false;
            const auto evidence=(*inspection.value)->evidence(); inspection.value.reset();
            state->inspectorRaw=evidence.playback.decodedFrames;
            {
                auto readers=openProtectedCustodyReaders(capture.paths.root,*pair.value,capture.cancel); if (!readers.ok()) return false;
                const auto& refs=(*pair.value)->current(); const auto slot=(*pair.value)->selectedSlot();
                std::size_t canonical=refs.refCount,playback=refs.refCount;
                for (std::size_t i=0;i<refs.refCount;++i) {
                    if (refs.refs[i].role == CustodyRole::canonical) canonical=i;
                    if (refs.refs[i].role == CustodyRole::playback) playback=i;
                }
                if (canonical==refs.refCount || playback==refs.refCount || !refs.refs[canonical].length ||
                    *refs.refs[canonical].length != state->frames*sizeof(float) || !refs.refs[playback].length) return false;
                CustodyVector<float> chunk(480);
                for (unsigned n=0;n<blocks;++n) {
                    ULONG got=0; const auto bytes=static_cast<ULONG>(chunk.size()*sizeof(float));
                    if (readers.value->at(slot).at(canonical).stream->Read(chunk.data(),bytes,&got)!=S_OK || got!=bytes) return false;
                    for (unsigned at=0;at<480;++at) if (chunk[at]!=aacAlignmentSource(n*480+at)) return false;
                }
                auto* input=readers.value->at(slot).at(playback).stream.Get(); HRESULT io=S_OK;
                state->timing=aacAlignmentTiming(*refs.refs[playback].length,[&](std::uint64_t at,std::uint8_t* data,unsigned count) {
                    LARGE_INTEGER offset{}; offset.QuadPart=static_cast<LONGLONG>(at); ULARGE_INTEGER actual{}; ULONG got=0;
                    io=input->Seek(offset,STREAM_SEEK_SET,&actual);
                    if (io==S_OK && actual.QuadPart!=at) io=STG_E_SEEKERROR;
                    if (io==S_OK) io=input->Read(data,count,&got);
                    if (SUCCEEDED(io) && (io!=S_OK || got!=count)) io=STG_E_READFAULT;
                    return io==S_OK;
                });
                if (FAILED(io)) return false;
            } // Retire every diagnostic Reader before fresh production inspection.
            std::fprintf(stderr,"DIAGNOSTIC_ONLY strict_acceptance=0 MEDIA_ENGINE_WAVEFORM begin frames=%llu canonical_mismatched=0 raw_inspector=%llu container_100ns=%llu metadata_known=%u media_time=%llu offset=%llu metadata_parser_frames=1440\n",
                static_cast<unsigned long long>(state->frames),static_cast<unsigned long long>(state->inspectorRaw),
                static_cast<unsigned long long>(evidence.playback.containerDuration100ns),unsigned(state->timing.known),
                static_cast<unsigned long long>(state->timing.mediaTime),static_cast<unsigned long long>(state->timing.offset));
            if (!state->timing.known) std::fputs("DIAGNOSTIC_ONLY strict_acceptance=0 MEDIA_ENGINE_WAVEFORM metadata_offset=UNKNOWN no_priming_guess=1\n",stderr);
            else std::fprintf(stderr,"DIAGNOSTIC_ONLY strict_acceptance=0 MEDIA_ENGINE_WAVEFORM movie_scale=%u media_scale=%u movie_duration=%llu media_duration=%llu edit_duration=%llu\n",
                state->timing.movieScale,state->timing.mediaScale,static_cast<unsigned long long>(state->timing.movieDuration),
                static_cast<unsigned long long>(state->timing.mediaDuration),static_cast<unsigned long long>(state->timing.editDuration));
            inspection=LocalRecordingPackage::inspectProtected(capture.paths.root,*pair.value,capture.session,capture.cancel);
            if (!inspection.ok()) return false;
            auto opened=[&] {
                struct Arm {
                    explicit Arm(std::shared_ptr<MediaEngineWaveformState> value) { if (mediaEngineWaveformArmed) throw std::logic_error("waveform_probe_already_armed"); mediaEngineWaveformArmed=std::move(value); }
                    ~Arm() { mediaEngineWaveformArmed.reset(); }
                } armed(state);
                return ProtectedLocalRecordingPlayback::open(std::move(*inspection.value),capture.cancel,true);
            }();
            if (!opened.ok()) {
                std::fprintf(stderr,"DIAGNOSTIC_ONLY strict_acceptance=0 MEDIA_ENGINE_WAVEFORM open=0 error=%u native=%08x\n",unsigned(opened.error),opened.nativeError);
                return false;
            }
            auto player=std::move(*opened.value);
            const bool ready=waitFor([&] { const auto s=player->observe(); return SUCCEEDED(s.error)&&s.ready&&s.muted; },std::chrono::seconds(10));
            bool inserted=false; { std::lock_guard<std::mutex> lock(state->mutex); inserted=state->insertions==1 && SUCCEEDED(state->failure); }
            const auto before=player->observe(); const auto played=ready&&inserted ? player->play() : E_FAIL;
            const bool ended=SUCCEEDED(played)&&waitFor([&] { const auto s=player->observe(); return SUCCEEDED(s.error)&&s.ended; },std::chrono::seconds(10));
            const auto after=player->observe();
            const bool closed=waitFor([&] { return player->startClose()&&player->drained(); },std::chrono::seconds(30));
            player.reset();
            std::fprintf(stderr,"DIAGNOSTIC_ONLY strict_acceptance=0 MEDIA_ENGINE_WAVEFORM ready=%u duration_ms=%.9g start=%.9g ended=%u end=%.9g play_hr=%08lx error=%08lx closed=%u\n",
                unsigned(ready),before.durationSeconds*1000,before.positionSeconds,unsigned(ended),after.positionSeconds,
                static_cast<unsigned long>(played),static_cast<unsigned long>(after.error),unsigned(closed));
            return ready&&inserted&&SUCCEEDED(played)&&ended&&closed&&SUCCEEDED(after.error);
        } catch (const std::bad_alloc&) {
            std::lock_guard<std::mutex> lock(state->mutex); state->fail(E_OUTOFMEMORY); return false;
        } catch (...) {
            std::lock_guard<std::mutex> lock(state->mutex); state->fail(E_FAIL); return false;
        }
        }).get();
        std::lock_guard<std::mutex> lock(state->mutex);
        aacAlignmentPrint("media_engine_raw","all_raw",state->raw);
        constexpr std::array<const char*,6> windows{"all_source","first_half","second_half","first240","transition480_960","last240"};
        for (unsigned model=0;model<3;++model) {
            if (model==1 && !state->timing.known) continue;
            const auto* name=model==0 ? "media_engine_no_offset" : model==1 ? "media_engine_metadata_offset" : "media_engine_timestamp";
            aacAlignmentPrint(name,"prefix",state->models[model].prefix); aacAlignmentPrint(name,"tail",state->models[model].tail);
            for (std::size_t i=0;i<windows.size();++i) aacAlignmentPrint(name,windows[i],state->models[model].windows[i]);
        }
        const bool observed=completed&&SUCCEEDED(state->failure)&&state->samples&&state->samples==state->outputs&&
            !state->liveFactories&&!state->liveTransforms;
        std::fprintf(stderr,"DIAGNOSTIC_ONLY strict_acceptance=0 MEDIA_ENGINE_WAVEFORM frames=%llu execution_complete=%u observed=%u native=%08lx samples=%u outputs=%u raw_frames=%llu inspector_raw=%llu first=%lld last=%lld span=%lld contiguous=%u discontinuity=%u flushes=%u drains=%u starts=%u ends=%u factories=%u insertions=%u live_factories=%u live_mfts=%u rejected_types=%u metadata_known=%u trim_stage=UNKNOWN presentation=UNKNOWN\n",
            static_cast<unsigned long long>(state->frames),unsigned(completed),unsigned(observed),static_cast<unsigned long>(state->failure),state->samples,state->outputs,
            static_cast<unsigned long long>(state->raw.count),static_cast<unsigned long long>(state->inspectorRaw),state->firstTime,state->lastTime,state->lastSpan,
            unsigned(state->timelineContiguous),unsigned(state->discontinuous),state->flushes,state->drains,state->starts,state->ends,state->factories,state->insertions,state->liveFactories,state->liveTransforms,state->typeRejections,unsigned(state->timing.known));
        std::fflush(stderr);
    }
    const bool released=waitFor([&] { return CustodyOwnedMemory::usedBytes()==baseline; });
    std::fprintf(stderr,"DIAGNOSTIC_ONLY strict_acceptance=0 MEDIA_ENGINE_WAVEFORM owned_baseline=%zu owned_final=%zu released=%u result=UNKNOWN strict_acceptance=0\n",baseline,CustodyOwnedMemory::usedBytes(),unsigned(released));
    return 96; // Effect position relative to final renderer trim is not established.
}
