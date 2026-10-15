#include "V5LocalRecordingWriter.h"

#include "LocalRecordingPackage.h"
#include "../Storage/ProtectedCustodyWriter.h"
#include "../Storage/ProtectedPackedCustodyTree.h"
#include "../Storage/Sha256.h"

#include <algorithm>
#include <array>
#include <charconv>
#include <chrono>
#include <cmath>
#include <cstring>
#include <ctime>
#include <limits>
#include <stdexcept>

#ifdef _WIN32
#include "../Storage/ProtectedCustodyReader.h"
#include <mfapi.h>
#include <mfidl.h>
#include <mfreadwrite.h>
#include <windows.h>
#include <wrl/client.h>
#endif

namespace graf::windows {
namespace {
constexpr std::uint64_t lastPrivacyWallMs = 253402300799999; // ISO8601, year 9999.
constexpr auto lastPrivacyMonotonicMs = static_cast<std::uint64_t>((std::numeric_limits<std::int64_t>::max)());
std::uint64_t wallClockMs() {
    return static_cast<std::uint64_t>(std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count());
}
int displayOffsetMinutes(std::uint64_t epochMs) {
    const auto seconds = static_cast<std::time_t>(epochMs / 1000);
    std::tm local{}, utc{};
#ifdef _WIN32
    if (localtime_s(&local,&seconds) || gmtime_s(&utc,&seconds)) return 0;
    const auto asUtc = [](std::tm value) { return _mkgmtime(&value); };
#else
    if (!localtime_r(&seconds,&local) || !gmtime_r(&seconds,&utc)) return 0;
    const auto asUtc = [](std::tm value) { return timegm(&value); };
#endif
    const auto minutes = static_cast<long long>(std::difftime(asUtc(local),asUtc(utc))) / 60;
    return minutes < -840 || minutes > 840 ? 0 : static_cast<int>(minutes);
}
#ifdef _WIN32
std::string hexHash(const std::array<std::uint8_t,32>& bytes) {
    std::string out(64,'0');
    for (std::size_t i = 0; i < bytes.size(); ++i) {
        out[2*i] = "0123456789abcdef"[bytes[i] >> 4];
        out[2*i+1] = "0123456789abcdef"[bytes[i] & 15];
    }
    return std::string(static_cast<const std::string&>(out));
}
// Bounded metadata only. Audio uses the incremental exact-length stream hash.
std::optional<std::array<std::uint8_t,32>> metadataHash(const CustodyBytes& bytes) {
    const auto hash = sha256({reinterpret_cast<const char*>(bytes.data()),bytes.size()});
    if (hash.size() != 64) return std::nullopt;
    std::array<std::uint8_t,32> out{};
    const auto digit = [](char c) { return c >= '0' && c <= '9' ? c-'0' : c >= 'a' && c <= 'f' ? c-'a'+10 : -1; };
    for (std::size_t i = 0; i < out.size(); ++i) {
        const auto a = digit(hash[2*i]), b = digit(hash[2*i+1]);
        if (a < 0 || b < 0) return std::nullopt;
        out[i] = static_cast<std::uint8_t>(a*16+b);
    }
    return out;
}
#endif
class MetadataJson final {
public:
    MetadataJson() { bytes.reserve(65536); }
    void text(std::string_view s) {
        if (s.size() > 65536-bytes.size()) throw std::length_error("recording metadata limit");
        bytes.insert(bytes.end(),s.begin(),s.end());
    }
    void number(std::uint64_t n) {
        char value[20]; const auto result = std::to_chars(value,value+sizeof(value),n);
        text({value,static_cast<std::size_t>(result.ptr-value)});
    }
    void date(std::uint64_t epochMs) {
        if (epochMs > lastPrivacyWallMs) throw std::length_error("recording date limit");
        std::tm utc{};
#ifdef _WIN32
        // The Windows CRT's gmtime_s stops at year3000. Use the native UTC
        // conversion for the known ISO8601 four-digit range, without locale IO.
        const auto ticks = (epochMs+11644473600000ULL)*10000;
        const FILETIME fileTime{static_cast<DWORD>(ticks),static_cast<DWORD>(ticks >> 32)};
        SYSTEMTIME time{};
        if (!FileTimeToSystemTime(&fileTime,&time)) throw std::length_error("recording date limit");
        utc.tm_year = time.wYear-1900; utc.tm_mon = time.wMonth-1; utc.tm_mday = time.wDay;
        utc.tm_hour = time.wHour; utc.tm_min = time.wMinute; utc.tm_sec = time.wSecond;
#else
        const auto seconds = static_cast<std::time_t>(epochMs/1000);
        if (!gmtime_r(&seconds,&utc)) throw std::length_error("recording date limit");
#endif
        char date[21]{};
        if (std::strftime(date,sizeof(date),"%Y-%m-%dT%H:%M:%SZ",&utc) != 20)
            throw std::length_error("recording date limit");
        text("\""); text({date,20}); text("\"");
    }
    CustodyBytes bytes;
};
#ifdef _WIN32
struct MediaRuntime final {
    HRESULT com = CoInitializeEx(nullptr,COINIT_MULTITHREADED);
    bool started = false;
    ~MediaRuntime() { if (started) MFShutdown(); if (SUCCEEDED(com)) CoUninitialize(); }
};
#endif
} // namespace

struct V5LocalRecordingWriter::State {
    struct PrivacySegment {
        std::uint64_t startedAt = 0, startMonotonic = 0, endedAt = 0, endMonotonic = 0;
        bool closed = false;
    };
    std::shared_ptr<ProtectedCustodyRecordingPackage> package;
    std::shared_ptr<const std::atomic<bool>> cancellation;
    std::array<std::shared_ptr<ProtectedCustodyWriter>,3> writers{};
    std::array<std::optional<CustodyPackageReference>,5> refs{};
    std::array<char,301> session{};
    std::size_t sessionLength = 0;
    bool shortIntent = false;
    CustodyVector<PrivacySegment> privacy;
#ifdef _WIN32
    // These proofs and native objects never travel in V5WriterResult to the UI.
    std::array<std::shared_ptr<const ProtectedPackedCustodyTree>,3> snapshots{};
    std::shared_ptr<const LocalRecordingPackage::ProtectedInspection> inspection;
#endif
    ~State() {
        volatile auto* bytes = reinterpret_cast<volatile unsigned char*>(session.data());
        for (std::size_t i = 0; i < session.size(); ++i) bytes[i] = 0;
    }
};

V5LocalRecordingWriter::V5LocalRecordingWriter(std::shared_ptr<State> state) : state_(std::move(state)) {}
V5LocalRecordingWriter::~V5LocalRecordingWriter() = default; // No flush, encoding, recovery or deletion IO.

CustodyFileResult<std::shared_ptr<V5LocalRecordingWriter>> V5LocalRecordingWriter::open(
    std::shared_ptr<ProtectedCustodyStoreOwner> owner, std::string_view session,
    std::shared_ptr<const std::atomic<bool>> cancellation) try {
#ifndef _WIN32
    (void)owner; (void)session; (void)cancellation;
    return {std::nullopt,CustodyFileError::unsupportedPlatform,0};
#else
    if (!owner || !cancellation || session.empty() || session.size() > 300)
        return {std::nullopt,CustodyFileError::invalidInput,0};
    if (cancellation->load()) return {std::nullopt,CustodyFileError::ioFailed,ERROR_OPERATION_ABORTED};
    // Allocate the charged wrapper/state before performing an irreversible birth.
    auto state = std::allocate_shared<State>(CustodyAllocator<State>{});
    state->cancellation = std::move(cancellation);
    std::copy(session.begin(),session.end(),state->session.begin()); state->sessionLength = session.size();
    std::shared_ptr<V5LocalRecordingWriter> writer{new V5LocalRecordingWriter(state),
        std::default_delete<V5LocalRecordingWriter>{},CustodyAllocator<V5LocalRecordingWriter>{}};
    auto package = owner->createPackage(session,state->cancellation);
    if (!package.ok()) return {std::nullopt,package.error,package.nativeError};
    state->package = std::move(*package.value);
    const auto& birth = state->package->current();
    if (birth.phase != CustodyPackagePhase::capturing || birth.generation != 1)
        return {std::nullopt,CustodyFileError::invalidContent,0};
    auto canonical = state->package->createWriter(CustodyRole::canonical);
    if (!canonical.ok()) return {std::nullopt,canonical.error,canonical.nativeError};
    state->writers[0] = std::move(*canonical.value);
    writer->result_.packageDirectory = state->package->path();
    writer->result_.packageContext = state->package->context();
    writer->result_.packageGeneration = birth.generation;
    return {std::move(writer),CustodyFileError::none,0};
#endif
} catch (const std::bad_alloc&) { return {std::nullopt,CustodyFileError::allocationFailed,0}; }

CustodyContext V5LocalRecordingWriter::packageContext() const noexcept {
    return state_->package ? state_->package->context() : CustodyContext{};
}

std::shared_ptr<ProtectedCustodyRecordingPackage> V5LocalRecordingWriter::package() const noexcept {
    return state_->package;
}

void V5LocalRecordingWriter::fail(V5WriterError error, CustodyFileError storage, std::uint32_t native) noexcept {
    if (result_.error == V5WriterError::none) {
        result_.error = error; result_.storageError = storage; result_.nativeError = native;
    }
}

bool V5LocalRecordingWriter::append(const CanonicalAudioFrame& frame) {
    if (finalized_ || result_.error != V5WriterError::none || !state_->writers[0]) return false;
    if (state_->cancellation->load()) { fail(V5WriterError::storageUnavailable,CustodyFileError::ioFailed); return false; }
    if (frameCount_ >= ProtectedPackedCustodyFormat::logicalLimit/1920 ||
        std::any_of(frame.mixed.begin(),frame.mixed.end(),[](float v) { return !std::isfinite(v); })) {
        fail(V5WriterError::integrityFailed,CustodyFileError::invalidContent); return false;
    }
    static_assert(sizeof(float) == 4);
    const auto wrote = state_->writers[0]->writeAt(frameCount_*1920,frame.mixed.data(),1920);
    if (!wrote.ok() || *wrote.value != 1920) {
        fail(V5WriterError::storageUnavailable,wrote.ok() ? CustodyFileError::ioFailed : wrote.error,wrote.nativeError); return false;
    }
    if (!startedAtMs_) startedAtMs_ = wallClockMs();
    ++frameCount_;
    return true;
}

CustodyFileResult<bool> V5LocalRecordingWriter::pausePrivacy(std::uint64_t wallMs, std::uint64_t monotonicMs) {
    if (finalized_ || result_.error != V5WriterError::none ||
        state_->package->current().phase != CustodyPackagePhase::capturing)
        return {std::nullopt,CustodyFileError::writerFailed,0};
    if (wallMs > lastPrivacyWallMs || monotonicMs > lastPrivacyMonotonicMs ||
        (!state_->privacy.empty() && monotonicMs < state_->privacy.back().endMonotonic))
        return {std::nullopt,CustodyFileError::invalidInput,0};
    if (!state_->privacy.empty() && !state_->privacy.back().closed) return {false,CustodyFileError::none,0};
    bool added = false;
    try {
        state_->privacy.push_back({wallMs,monotonicMs,0,0,false}); added = true;
        // Serialize the ENTIRE worst-case final shape before OPEN: future end
        // fields, audio digests/lengths and time bounds, not a segment-count cap.
        (void)manifestJson(true);
        const auto bytes = manifestJson();
        if (sealMetadata(CustodyRole::manifest,bytes)) return {true,CustodyFileError::none,0};
        state_->privacy.pop_back();
        return {std::nullopt,result_.storageError,result_.nativeError};
    } catch (const std::bad_alloc&) {
        if (added) state_->privacy.pop_back();
        return {std::nullopt,CustodyFileError::allocationFailed,0};
    } catch (const std::length_error&) {
        if (added) state_->privacy.pop_back();
        return {std::nullopt,CustodyFileError::invalidInput,0};
    }
}

CustodyFileResult<bool> V5LocalRecordingWriter::closePrivacy(std::uint64_t wallMs, std::uint64_t monotonicMs) {
    if (finalized_ || result_.error != V5WriterError::none ||
        state_->package->current().phase != CustodyPackagePhase::capturing)
        return {std::nullopt,CustodyFileError::writerFailed,0};
    if (wallMs > lastPrivacyWallMs || monotonicMs > lastPrivacyMonotonicMs ||
        (!state_->privacy.empty() && monotonicMs < state_->privacy.back().startMonotonic))
        return {std::nullopt,CustodyFileError::invalidInput,0};
    if (state_->privacy.empty() || state_->privacy.back().closed) return {false,CustodyFileError::none,0};
    auto& segment = state_->privacy.back();
    segment.endedAt = wallMs; segment.endMonotonic = monotonicMs; segment.closed = true;
    // The caller already accepted the boundary. Never reopen the in-memory
    // segment on allocation/commit failure or cancel an accepted Resume.
    try {
        const auto bytes = manifestJson();
        if (sealMetadata(CustodyRole::manifest,bytes)) return {true,CustodyFileError::none,0};
        return {std::nullopt,result_.storageError,result_.nativeError};
    } catch (const std::bad_alloc&) { return {std::nullopt,CustodyFileError::allocationFailed,0}; }
      catch (const std::length_error&) { return {std::nullopt,CustodyFileError::invalidInput,0}; }
}

std::int16_t V5LocalRecordingWriter::toPcm16(float value) noexcept {
    return static_cast<std::int16_t>(std::clamp(value,-1.0F,1.0F)*32767.0F);
}

bool V5LocalRecordingWriter::writeWav() {
#ifdef _WIN32
    const auto dataBytes = frameCount_*320;
    if (dataBytes > (std::numeric_limits<std::uint32_t>::max)()-36) {
        fail(V5WriterError::integrityFailed,CustodyFileError::invalidInput); return false;
    }
    auto opened = state_->package->createWriter(CustodyRole::media);
    if (!opened.ok()) { fail(V5WriterError::storageUnavailable,opened.error,opened.nativeError); return false; }
    state_->writers[1] = std::move(*opened.value);
    auto canonical = openProtectedCustodyReader(state_->snapshots[0],state_->cancellation);
    if (!canonical.ok()) { fail(V5WriterError::integrityFailed,canonical.error,canonical.nativeError); return false; }
    std::array<std::uint8_t,44> header{};
    const auto u16 = [&](std::size_t at, std::uint16_t n) {
        header[at] = static_cast<std::uint8_t>(n); header[at+1] = static_cast<std::uint8_t>(n >> 8);
    };
    const auto u32 = [&](std::size_t at, std::uint32_t n) { for (unsigned i = 0; i < 4; ++i) header[at+i] = static_cast<std::uint8_t>(n >> (8*i)); };
    std::memcpy(header.data(),"RIFF",4); u32(4,static_cast<std::uint32_t>(36+dataBytes));
    std::memcpy(header.data()+8,"WAVEfmt ",8); u32(16,16); u16(20,1); u16(22,1);
    u32(24,16000); u32(28,32000); u16(32,2); u16(34,16);
    std::memcpy(header.data()+36,"data",4); u32(40,static_cast<std::uint32_t>(dataBytes));
    const auto first = state_->writers[1]->writeAt(0,header.data(),header.size());
    if (!first.ok() || *first.value != header.size()) {
        fail(V5WriterError::storageUnavailable,first.ok() ? CustodyFileError::ioFailed : first.error,first.nativeError); return false;
    }
    // Charged/wiped plaintext staging; no temporary audio file.
    CustodyBytes input(1920), pcm(320);
    for (std::uint64_t index = 0; index < frameCount_; ++index) {
        ULONG got = 0;
        auto status = state_->cancellation->load() ? HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED) :
            canonical.value->stream->Read(input.data(),static_cast<ULONG>(input.size()),&got);
        if (SUCCEEDED(status) && state_->cancellation->load()) status = HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED);
        if (FAILED(status) || got != input.size()) {
            fail(V5WriterError::integrityFailed,FAILED(status) ? CustodyFileError::ioFailed : CustodyFileError::invalidContent,
                FAILED(status) ? static_cast<std::uint32_t>(status) : 0); return false;
        }
        for (std::size_t at = 0; at < 160; ++at) {
            std::array<float,3> samples{}; std::memcpy(samples.data(),input.data()+at*12,12);
            const auto sample = static_cast<std::uint16_t>(toPcm16((samples[0]+samples[1]+samples[2])/3.0F));
            pcm[2*at] = static_cast<std::uint8_t>(sample); pcm[2*at+1] = static_cast<std::uint8_t>(sample >> 8);
        }
        const auto wrote = state_->writers[1]->writeAt(44+index*320,pcm.data(),pcm.size());
        if (!wrote.ok() || *wrote.value != pcm.size()) {
            fail(V5WriterError::storageUnavailable,wrote.ok() ? CustodyFileError::ioFailed : wrote.error,wrote.nativeError); return false;
        }
    }
    return sealAudio(CustodyRole::media);
#else
    return false;
#endif
}

bool V5LocalRecordingWriter::writePlayback() {
#ifdef _WIN32
    using Microsoft::WRL::ComPtr;
    auto opened = state_->package->createWriter(CustodyRole::playback);
    if (!opened.ok()) { fail(V5WriterError::storageUnavailable,opened.error,opened.nativeError); return false; }
    state_->writers[2] = std::move(*opened.value);
    auto canonical = openProtectedCustodyReader(state_->snapshots[0],state_->cancellation);
    if (!canonical.ok()) { fail(V5WriterError::integrityFailed,canonical.error,canonical.nativeError); return false; }
    auto adapter = ProtectedCustodyWriteStream::open(state_->writers[2],state_->cancellation);
    if (!adapter.ok()) { fail(V5WriterError::storageUnavailable,adapter.error,adapter.nativeError); return false; }
    {
        // Canonical reads and MF output callbacks admit their actual IO through
        // separate Guards; an aggregate slot would double-charge their overlap.
        MediaRuntime runtime;
        HRESULT hr = runtime.com;
        const auto call = [&](auto operation) {
            if (FAILED(hr)) return hr;
            hr = (*adapter.value)->observedFailure();
            if (FAILED(hr)) return hr;
            if (state_->cancellation->load()) return hr = HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED);
            hr = operation();
            if (SUCCEEDED(hr)) hr = (*adapter.value)->observedFailure();
            if (SUCCEEDED(hr) && state_->cancellation->load()) hr = HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED);
            return hr;
        };
        ComPtr<IMFByteStream> bytes;
        ComPtr<IMFSinkWriter> sink;
        ComPtr<IMFAttributes> attributes;
        ComPtr<IMFMediaType> output, input;
        try {
            call([&] { const auto start = MFStartup(MF_VERSION); runtime.started = SUCCEEDED(start); return start; });
            call([&] { return MFCreateMFByteStreamOnStream((*adapter.value)->stream(),&bytes); });
            call([&] { return MFCreateAttributes(&attributes,1); });
            call([&] { return attributes->SetGUID(MF_TRANSCODE_CONTAINERTYPE,MFTranscodeContainerType_MPEG4); });
            call([&] { return MFCreateSinkWriterFromURL(nullptr,bytes.Get(),attributes.Get(),&sink); });
            call([&] { return MFCreateMediaType(&output); });
            call([&] { return output->SetGUID(MF_MT_MAJOR_TYPE,MFMediaType_Audio); });
            call([&] { return output->SetGUID(MF_MT_SUBTYPE,MFAudioFormat_AAC); });
            call([&] { return output->SetUINT32(MF_MT_AUDIO_NUM_CHANNELS,1); });
            call([&] { return output->SetUINT32(MF_MT_AUDIO_SAMPLES_PER_SECOND,48000); });
            call([&] { return output->SetUINT32(MF_MT_AUDIO_BITS_PER_SAMPLE,16); });
            call([&] { return output->SetUINT32(MF_MT_AUDIO_AVG_BYTES_PER_SECOND,12000); });
            call([&] { return output->SetUINT32(MF_MT_AAC_PAYLOAD_TYPE,0); });
            call([&] { return output->SetUINT32(MF_MT_AAC_AUDIO_PROFILE_LEVEL_INDICATION,0x29); });
            DWORD index = 0;
            call([&] { return sink->AddStream(output.Get(),&index); });
            call([&] { return MFCreateMediaType(&input); });
            call([&] { return input->SetGUID(MF_MT_MAJOR_TYPE,MFMediaType_Audio); });
            call([&] { return input->SetGUID(MF_MT_SUBTYPE,MFAudioFormat_PCM); });
            call([&] { return input->SetUINT32(MF_MT_AUDIO_NUM_CHANNELS,1); });
            call([&] { return input->SetUINT32(MF_MT_AUDIO_SAMPLES_PER_SECOND,48000); });
            call([&] { return input->SetUINT32(MF_MT_AUDIO_BITS_PER_SAMPLE,16); });
            call([&] { return input->SetUINT32(MF_MT_AUDIO_BLOCK_ALIGNMENT,2); });
            call([&] { return input->SetUINT32(MF_MT_AUDIO_AVG_BYTES_PER_SECOND,96000); });
            call([&] { return sink->SetInputMediaType(index,input.Get(),nullptr); });
            call([&] { return sink->BeginWriting(); });
            CustodyBytes frame(1920);
            for (std::uint64_t n = 0; SUCCEEDED(hr) && n < frameCount_; ++n) {
                ULONG got = 0;
                HRESULT read = S_OK; bool attempted = false;
                call([&] {
                    attempted = true;
                    return read = canonical.value->stream->Read(frame.data(),static_cast<ULONG>(frame.size()),&got);
                });
                if (attempted && (FAILED(read) || got != frame.size())) {
                    hr = FAILED(read) ? read : STG_E_READFAULT;
                    fail(V5WriterError::integrityFailed,CustodyFileError::ioFailed,static_cast<std::uint32_t>(hr)); break;
                }
                if (FAILED(hr)) break; // Output failure is not canonical corruption.
                ComPtr<IMFMediaBuffer> buffer; ComPtr<IMFSample> sample;
                call([&] { return MFCreateMemoryBuffer(960,&buffer); });
                call([&] { return MFCreateSample(&sample); });
                BYTE* destination = nullptr; DWORD maximum = 0, length = 0;
                bool locked = false;
                call([&] { const auto status = buffer->Lock(&destination,&maximum,&length); locked = SUCCEEDED(status); return status; });
                if (locked) {
                    if (SUCCEEDED(hr) && maximum < 960) hr = E_UNEXPECTED;
                    if (SUCCEEDED(hr)) for (std::size_t at = 0; at < 480; ++at) {
                        float value = 0; std::memcpy(&value,frame.data()+at*4,4);
                        const auto pcm = static_cast<std::uint16_t>(toPcm16(value));
                        destination[2*at] = static_cast<BYTE>(pcm); destination[2*at+1] = static_cast<BYTE>(pcm >> 8);
                    }
                    const auto unlock = buffer->Unlock(); if (SUCCEEDED(hr)) hr = unlock;
                }
                call([&] { return buffer->SetCurrentLength(960); });
                call([&] { return sample->AddBuffer(buffer.Get()); });
                call([&] { return sample->SetSampleTime(static_cast<LONGLONG>(n*100000)); });
                call([&] { return sample->SetSampleDuration(100000); });
                // Never hold the adapter lock around an MF call; callbacks use it.
                call([&] { return sink->WriteSample(index,sample.Get()); });
            }
            call([&] { return sink->Finalize(); });
        } catch (const std::bad_alloc&) { hr = E_OUTOFMEMORY; }
          catch (...) { hr = E_FAIL; }
        // Serialized close drains active stream calls. Late COM references see a
        // closed stream; the worker separately retains the actual writer/state.
        const auto closed = (*adapter.value)->close();
        if (SUCCEEDED(hr) && FAILED(closed)) hr = closed;
        sink.Reset(); bytes.Reset(); output.Reset(); input.Reset(); attributes.Reset();
        adapter.value.reset(); // Worker-only wrapper release, before runtime shutdown.
        if (runtime.started) {
            const auto shutdown = MFShutdown(); runtime.started = false;
            if (SUCCEEDED(hr)) hr = shutdown;
        }
        canonical.value.reset();
        if (FAILED(hr)) {
            fail(V5WriterError::encodeFailed,hr == E_OUTOFMEMORY ? CustodyFileError::allocationFailed : CustodyFileError::ioFailed,
                static_cast<std::uint32_t>(hr)); return false;
        }
    } // Runtime/COM release precedes independent checkpoint/decode.
    if (!sealAudio(CustodyRole::playback)) return false;
    // Decode actual AAC payload/EOF/duration before publishing a sealed state;
    // encoder success and a container header are not semantic acceptance.
    auto decoded = LocalRecordingPackage::readProtectedPlayback(state_->snapshots[2],frameCount_*10,state_->cancellation);
    if (!decoded.ok()) { fail(V5WriterError::integrityFailed,decoded.error,decoded.nativeError); return false; }
    return decoded.value->decodedFrames != 0;
#else
    fail(V5WriterError::aacEncoderUnavailable,CustodyFileError::unsupportedPlatform);
    return false;
#endif
}

bool V5LocalRecordingWriter::sealAudio(CustodyRole role, bool checkpoint) {
#ifdef _WIN32
    const auto index = static_cast<unsigned>(role)-1;
    if (index >= state_->writers.size() || !state_->writers[index]) return false;
    auto writer = state_->writers[index];
    if (checkpoint) {
        const auto commit = writer->checkpoint();
        if (commit.state != CustodyCommitState::committed) {
            fail(V5WriterError::storageUnavailable,commit.error,commit.nativeError); return false;
        }
    }
    auto snapshot = writer->committedPackedSnapshot();
    if (!snapshot.ok()) { fail(V5WriterError::integrityFailed,snapshot.error,snapshot.nativeError); return false; }
    auto identity = state_->package->reference(role);
    if (!identity.ok() || !identity.value->packed || !identity.value->containerId) {
        fail(V5WriterError::integrityFailed,identity.ok() ? CustodyFileError::invalidContent : identity.error,identity.nativeError); return false;
    }
    auto reader = openProtectedCustodyReader(*snapshot.value,state_->cancellation);
    if (!reader.ok()) { fail(V5WriterError::integrityFailed,reader.error,reader.nativeError); return false; }
    auto hash = sha256ProtectedStream(reader.value->stream.Get(),(*snapshot.value)->logicalBytes(),state_->cancellation);
    if (!hash.ok()) { fail(V5WriterError::integrityFailed,hash.error,hash.nativeError); return false; }
    auto reference = *identity.value;
    const auto& descriptor = (*snapshot.value)->descriptor();
    reference.sealed = true; reference.generation = descriptor.generation;
    reference.length = descriptor.logicalBytes; reference.sha256 = *hash.value;
    reference.committedExtent = descriptor.committedExtent;
    reference.rootRef = ProtectedPackedCustodyFormat::encodeReference(descriptor.root);
    if (!reference.rootRef) { fail(V5WriterError::integrityFailed,CustodyFileError::invalidContent); return false; }
    state_->snapshots[index] = std::move(*snapshot.value);
    state_->refs[index] = reference;
    if (role == CustodyRole::media) { result_.wavBytes = *reference.length; result_.wavSha256 = hexHash(*reference.sha256); }
    if (role == CustodyRole::playback) { result_.playbackBytes = *reference.length; result_.playbackSha256 = hexHash(*reference.sha256); }
    return true;
#else
    (void)role; (void)checkpoint; return false;
#endif
}

bool V5LocalRecordingWriter::sealMetadata(CustodyRole role, const CustodyBytes& bytes) {
#ifdef _WIN32
    if (role != CustodyRole::manifest && role != CustodyRole::recovery) return false;
    const auto hash = metadataHash(bytes);
    if (!hash) { fail(V5WriterError::integrityFailed,CustodyFileError::hashFailed); return false; }
    const auto commit = state_->package->commitMetadata(role,bytes);
    if (commit.state != CustodyCommitState::committed || !commit.snapshot ||
        commit.snapshot->state != CustodySnapshotState::verified || commit.snapshot->index.logicalLength != bytes.size()) {
        fail(V5WriterError::storageUnavailable,commit.error,commit.nativeError); return false;
    }
    CustodyPackageReference reference;
    reference.role = role; reference.objectId = commit.context.objectId; reference.sealed = true;
    reference.generation = commit.targetGeneration; reference.length = bytes.size(); reference.sha256 = *hash;
    state_->refs[static_cast<unsigned>(role)-1] = reference;
    return true;
#else
    (void)role; (void)bytes; return false;
#endif
}

bool V5LocalRecordingWriter::commitState(CustodyPackagePhase phase, ReasonCode reason, bool shortIntent) {
#ifdef _WIN32
    auto value = state_->package->current();
    if (value.generation == (std::numeric_limits<std::uint64_t>::max)()) return false;
    ++value.generation; value.phase = phase; value.reason = reason; value.shortRecordingDiscarded = shortIntent;
    // Live canonical remains only in the intermediate finalizing state.
    if (phase != CustodyPackagePhase::finalizing) {
        value.refCount = 0;
        for (const auto& reference : state_->refs) if (reference) value.refs[value.refCount++] = *reference;
    }
    const auto commit = state_->package->commit(value);
    if (commit.state != CustodyCommitState::committed) {
        fail(V5WriterError::storageUnavailable,commit.error,commit.nativeError); return false;
    }
    result_.packagePhase = phase; result_.packageGeneration = commit.targetGeneration;
    result_.shortRecordingDiscarded = shortIntent; // Only after the actual durable state ACK.
    return true;
#else
    (void)phase; (void)reason; (void)shortIntent; return false;
#endif
}

CustodyBytes V5LocalRecordingWriter::manifestJson(bool capacityCheck) const {
    MetadataJson json;
    json.text("{\"schema_version\":\""); json.text(kManifestSchemaVersion);
    json.text("\",\"canonical_mix_profile\":\""); json.text(kCanonicalMixProfile);
    json.text("\",\"source_kind\":\""); json.text(kV5SourceKind);
    json.text("\",\"media_scribe_source_mode\":\""); json.text(kV5MediaScribeSourceMode);
    json.text("\",\"capture_status\":\""); json.text(capacityCheck || state_->shortIntent ? "blocked" :
        result_.captureFailure == ReasonCode::none ? "normal" : "degraded");
    const auto maximum = (std::numeric_limits<std::uint64_t>::max)();
    json.text("\",\"capture_reason_code\":\""); json.text(capacityCheck ? "none" : toString(result_.captureFailure));
    json.text("\",\"duration_ms\":"); json.number(capacityCheck ? maximum : finalized_ ? result_.durationMs : frameCount_*10);
    json.text(",\"started_at_ms\":"); json.number(capacityCheck ? maximum : startedAtMs_);
    json.text(",\"stopped_at_ms\":"); json.number(capacityCheck ? maximum : finalized_ ? result_.stoppedAtMs : std::max(startedAtMs_,wallClockMs()));
    json.text(",\"display_timezone_offset_minutes\":");
    if (capacityCheck || result_.displayTimezoneOffsetMinutes < 0) json.text("-");
    json.number(capacityCheck ? 840 : static_cast<std::uint64_t>(std::abs(result_.displayTimezoneOffsetMinutes)));
    json.text(",\"sessionId\":\""); json.text({state_->session.data(),state_->sessionLength}); json.text("\"");
    if (capacityCheck || state_->shortIntent) { json.text(",\""); json.text(kShortRecordingDiscardedField); json.text("\":true"); }
    json.text(",\"privacySegments\":[");
    for (std::size_t i = 0; i < state_->privacy.size(); ++i) {
        const auto& segment = state_->privacy[i];
        const bool closed = segment.closed || capacityCheck;
        const auto end = segment.closed ? segment.endMonotonic : lastPrivacyMonotonicMs;
        if (i) json.text(",");
        json.text("{\"segmentId\":\""); json.text({state_->session.data(),state_->sessionLength});
        json.text("-privacy-"); json.number(i+1);
        json.text("\",\"sessionId\":\""); json.text({state_->session.data(),state_->sessionLength});
        json.text("\",\"control\":\"pause\",\"startedAt\":"); json.date(segment.startedAt);
        json.text(",\"startMonotonicMs\":"); json.number(segment.startMonotonic);
        if (closed) {
            json.text(",\"endedAt\":"); json.date(segment.closed ? segment.endedAt : lastPrivacyWallMs);
            json.text(",\"endMonotonicMs\":"); json.number(end);
        }
        json.text(",\"durationMs\":"); json.number(closed ? end-segment.startMonotonic : 0);
        json.text(",\"localMicTreatment\":\"silenced\",\"initiator\":\"user\",\"diagnosticSafe\":true}");
    }
    json.text("]");
    if (capacityCheck || (state_->refs[1] && state_->refs[2])) {
        // Capacity-only placeholders are NEVER persisted as artifact evidence.
        constexpr std::string_view capacityHash = "0000000000000000000000000000000000000000000000000000000000000000";
        json.text(",\"artifacts\":{\"media\":{\"bytes\":"); json.number(capacityCheck ? maximum : result_.wavBytes);
        json.text(",\"sha256\":\""); json.text(capacityCheck ? capacityHash : result_.wavSha256);
        json.text("\"},\"playback\":{\"bytes\":"); json.number(capacityCheck ? maximum : result_.playbackBytes);
        json.text(",\"sha256\":\""); json.text(capacityCheck ? capacityHash : result_.playbackSha256); json.text("\"}}");
    }
    json.text("}");
    return std::move(json.bytes);
}

bool V5LocalRecordingWriter::retainPrefix(ReasonCode reason) {
#ifdef _WIN32
    if (state_->package->current().phase == CustodyPackagePhase::capturing &&
        !commitState(CustodyPackagePhase::finalizing,reason)) return false;
    if (state_->package->current().phase != CustodyPackagePhase::finalizing) return false;
    // Only a genuine committed snapshot; never frameCount or physical file size.
    auto proof = state_->writers[0]->committedPackedSnapshot();
    if (!proof.ok()) return false;
    const auto complete = (*proof.value)->logicalBytes()/1920;
    if (!complete || !sealAudio(CustodyRole::canonical,false)) return false;
    const auto& canonical = *state_->refs[0];
    MetadataJson recovery;
    recovery.text("{\"capture_status\":\"degraded\",\"capture_reason_code\":\""); recovery.text(toString(reason));
    recovery.text("\",\"trusted_prefix_frames\":"); recovery.number(complete);
    recovery.text(",\"canonical_bytes\":"); recovery.number(*canonical.length);
    recovery.text(",\"canonical_sha256\":\""); recovery.text(hexHash(*canonical.sha256)); recovery.text("\"}");
    // Keep history in its existing protected manifest, not in a new recovery
    // shape. Derived outputs remain owned artifacts, but cannot become refs.
    state_->refs[1].reset(); state_->refs[2].reset(); state_->refs[4].reset();
    result_.durationMs = complete*10;
    const auto manifest = manifestJson();
    if (!sealMetadata(CustodyRole::manifest,manifest) ||
        !sealMetadata(CustodyRole::recovery,recovery.bytes) ||
        !commitState(CustodyPackagePhase::sealedDegraded,reason)) return false;
    auto inspected = LocalRecordingPackage::inspectProtected(state_->package,
        {state_->session.data(),state_->sessionLength},state_->cancellation);
    if (!inspected.ok() || inspected.value.value()->evidence().integrity != PackageIntegrity::degraded) return false;
    state_->inspection = std::move(*inspected.value);
    result_.semanticVerified = true; result_.trustedPrefixRetained = true; result_.durationMs = complete*10;
    return true;
#else
    (void)reason; return false;
#endif
}

V5WriterResult V5LocalRecordingWriter::finalize(ReasonCode failure, RecordingStopReason stopReason) try {
    if (finalized_) return result_;
    finalized_ = true;
    result_.captureFailure = failure;
    result_.startedAtMs = startedAtMs_;
    result_.stoppedAtMs = std::max(startedAtMs_,wallClockMs());
    result_.displayTimezoneOffsetMinutes = startedAtMs_ ? displayOffsetMinutes(startedAtMs_) : 0;
    result_.durationMs = frameCount_*10;
    if (!frameCount_) { fail(V5WriterError::emptyRecording,CustodyFileError::invalidContent); return result_; }
    const auto canonical = state_->writers[0]->checkpoint();
    if (canonical.state != CustodyCommitState::committed) fail(V5WriterError::storageUnavailable,canonical.error,canonical.nativeError);
    if (result_.error != V5WriterError::none || failure != ReasonCode::none) {
        if (result_.captureFailure == ReasonCode::none) result_.captureFailure = ReasonCode::storageUnavailable;
        (void)retainPrefix(result_.captureFailure); return result_;
    }
    if (!commitState(CustodyPackagePhase::finalizing,ReasonCode::none) ||
        !sealAudio(CustodyRole::canonical) || *state_->refs[0]->length != frameCount_*1920 ||
        !writeWav() || !writePlayback()) {
        if (result_.error == V5WriterError::none) fail(V5WriterError::integrityFailed,CustodyFileError::invalidContent);
        result_.captureFailure = ReasonCode::finalizationFailed;
        (void)retainPrefix(result_.captureFailure); return result_;
    }
    state_->shortIntent = isShortRecording(frameCount_,stopReason,false);
    auto manifest = manifestJson();
    if (!sealMetadata(CustodyRole::manifest,manifest) ||
        !commitState(state_->shortIntent ? CustodyPackagePhase::discardPending : CustodyPackagePhase::sealedNormal,
            ReasonCode::none,state_->shortIntent)) return result_;
#ifdef _WIN32
    auto inspected = LocalRecordingPackage::inspectProtected(state_->package,
        {state_->session.data(),state_->sessionLength},state_->cancellation);
    if (!inspected.ok()) {
        fail(V5WriterError::integrityFailed,inspected.error,inspected.nativeError); return result_;
    }
    const auto& evidence = inspected.value.value()->evidence();
    const auto expected = result_.shortRecordingDiscarded ? PackageIntegrity::discardPending : PackageIntegrity::valid;
    if (evidence.integrity != expected || !evidence.manifestSessionMatched || evidence.durationMs != result_.durationMs ||
        !evidence.playback.decodedFrames) {
        fail(V5WriterError::integrityFailed,CustodyFileError::invalidContent); return result_;
    }
    state_->inspection = std::move(*inspected.value);
    result_.semanticVerified = true;
#endif
    return result_;
} catch (const std::bad_alloc&) {
    fail(V5WriterError::storageUnavailable,CustodyFileError::allocationFailed); return result_;
} catch (...) {
    fail(V5WriterError::integrityFailed,CustodyFileError::invalidContent); return result_;
}

} // namespace graf::windows
