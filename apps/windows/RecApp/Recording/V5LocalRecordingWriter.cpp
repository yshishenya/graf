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
#ifdef GRAF_WINDOWS_TEST_FINALIZE_PHASES
#include <type_traits>
#endif

#ifdef _WIN32
#include "FfmpegApi.h"
#include "../Storage/ProtectedCustodyReader.h"
#include <cerrno>
#include <cstdio>
#include <windows.h>
#endif

namespace graf::windows {
#ifdef GRAF_WINDOWS_TEST_FINALIZE_PHASES
// Only the native integration executable defines these allocation-free observers.
void beginFinalizePhase(unsigned stage) noexcept;
void observeStartBeforeCanonical(const ProtectedCustodyRecordingPackage&) noexcept;
#define GRAF_WINDOWS_TEST_START_BEFORE_CANONICAL(package) observeStartBeforeCanonical(package)
void endFinalizePhase(unsigned stage, bool returned) noexcept;
HRESULT playbackReadForTest(IStream*, void*, ULONG, ULONG*);
HRESULT playbackWriteForTest(IStream*, const void*, ULONG, ULONG*);
HRESULT playbackSampleForTest(const float*, unsigned, std::uint64_t, HRESULT);
#define GRAF_PLAYBACK_READ(stream, data, size, got) playbackReadForTest(stream,data,size,got)
#define GRAF_PLAYBACK_WRITE(stream, data, size, written) playbackWriteForTest(stream,data,size,written)
#define GRAF_PLAYBACK_SAMPLE(data, count, offset, status) playbackSampleForTest(data,count,offset,status)
namespace {
template<class Operation> auto measuredFinalize(unsigned stage, Operation operation) {
    struct Scope {
        unsigned stage;
        bool returned = false;
        ~Scope() { endFinalizePhase(stage,returned); }
    } scope{stage};
    beginFinalizePhase(stage);
    auto result = operation();
    static_assert(std::is_nothrow_move_constructible_v<decltype(result)>);
    scope.returned = true;
    return result;
}
}
bool finalizePhaseAdapterForTest(bool (*operation)()) { return measuredFinalize(0,operation); }
#define GRAF_FINALIZE_PHASE(stage, ...) measuredFinalize(stage,[&] { return (__VA_ARGS__); })
#else
#define GRAF_FINALIZE_PHASE(stage, ...) (__VA_ARGS__)
#define GRAF_PLAYBACK_READ(stream, data, size, got) (stream)->Read(data,size,got)
#define GRAF_PLAYBACK_WRITE(stream, data, size, written) (stream)->Write(data,size,written)
#define GRAF_PLAYBACK_SAMPLE(data, count, offset, status) (status)
#endif
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
HRESULT playbackAvError(int status) noexcept {
    return status >= 0 ? S_OK : status == AVERROR(ENOMEM) ? E_OUTOFMEMORY : E_FAIL;
}
struct PlaybackAvio final {
    ProtectedCustodyWriteStream& adapter;
    const std::atomic<bool>& cancellation;
    HRESULT failure = S_OK;
    int reject(HRESULT hr) noexcept {
        if (SUCCEEDED(failure)) failure = hr;
        return AVERROR(EIO);
    }
    bool ready() noexcept {
        if (FAILED(failure)) return false;
        const auto hr = adapter.observedFailure();
        if (FAILED(hr)) { reject(hr); return false; }
        if (cancellation.load()) { reject(HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED)); return false; }
        return true;
    }
    static int write(void* opaque, const std::uint8_t* data, int count) noexcept {
        auto& out = *static_cast<PlaybackAvio*>(opaque);
        if (!out.ready()) return AVERROR(EIO);
        if (!data || count <= 0) return out.reject(STG_E_INVALIDPOINTER);
        ULONG written = 0;
        const auto hr = GRAF_PLAYBACK_WRITE(out.adapter.stream(),data,static_cast<ULONG>(count),&written);
        if (FAILED(hr) || written != static_cast<ULONG>(count))
            return out.reject(FAILED(hr) ? hr : STG_E_WRITEFAULT);
        return out.ready() ? count : AVERROR(EIO);
    }
    static std::int64_t seek(void* opaque, std::int64_t offset, int whence) noexcept {
        auto& out = *static_cast<PlaybackAvio*>(opaque);
        if (!out.ready()) return AVERROR(EIO);
        whence &= ~AVSEEK_FORCE;
        constexpr auto limit = ProtectedPackedCustodyFormat::logicalLimit;
        if (whence == AVSEEK_SIZE) {
            STATSTG stat{};
            const auto hr = out.adapter.stream()->Stat(&stat,STATFLAG_NONAME);
            if (FAILED(hr) || stat.cbSize.QuadPart > limit)
                return out.reject(FAILED(hr) ? hr : STG_E_MEDIUMFULL);
            return out.ready() ? static_cast<std::int64_t>(stat.cbSize.QuadPart) : AVERROR(EIO);
        }
        if (whence != SEEK_SET && whence != SEEK_CUR && whence != SEEK_END)
            return out.reject(STG_E_INVALIDFUNCTION);
        LARGE_INTEGER zero{}; ULARGE_INTEGER position{};
        std::uint64_t base = 0;
        if (whence == SEEK_CUR) {
            const auto hr = out.adapter.stream()->Seek(zero,STREAM_SEEK_CUR,&position);
            if (FAILED(hr)) return out.reject(hr);
            base = position.QuadPart;
        } else if (whence == SEEK_END) {
            STATSTG stat{};
            const auto hr = out.adapter.stream()->Stat(&stat,STATFLAG_NONAME);
            if (FAILED(hr)) return out.reject(hr);
            base = stat.cbSize.QuadPart;
        }
        if (base > limit) return out.reject(STG_E_MEDIUMFULL);
        std::uint64_t target = 0;
        if (offset < 0) {
            const auto magnitude = static_cast<std::uint64_t>(-(offset+1))+1;
            if (magnitude > base) return out.reject(STG_E_INVALIDFUNCTION);
            target = base-magnitude;
        } else {
            if (static_cast<std::uint64_t>(offset) > limit-base) return out.reject(STG_E_MEDIUMFULL);
            target = base+static_cast<std::uint64_t>(offset);
        }
        LARGE_INTEGER to{}; to.QuadPart = static_cast<LONGLONG>(target);
        const auto hr = out.adapter.stream()->Seek(to,STREAM_SEEK_SET,&position);
        if (FAILED(hr) || position.QuadPart != target) return out.reject(FAILED(hr) ? hr : STG_E_SEEKERROR);
        return out.ready() ? static_cast<std::int64_t>(target) : AVERROR(EIO);
    }
    static int denyOpen(AVFormatContext* format, AVIOContext**, const char*, int, AVDictionary**) noexcept {
        return static_cast<PlaybackAvio*>(format->opaque)->reject(E_ACCESSDENIED);
    }
    static int denyClose(AVFormatContext* format, AVIOContext*) noexcept {
        return static_cast<PlaybackAvio*>(format->opaque)->reject(E_ACCESSDENIED);
    }
};
struct PlaybackAvResources final {
    static constexpr int ioCapacity = 32768;
    const FfmpegApi& api;
    HRESULT& result;
    PlaybackAvio& output;
    AVFormatContext* format = nullptr;
    AVCodecContext* codec = nullptr;
    AVIOContext* io = nullptr;
    AVFrame* frame = nullptr;
    AVPacket* packet = nullptr;
    unsigned char* supplied = nullptr; // Owning only until io is constructed.
    bool charged = false;
    bool fixedBuffer() const noexcept {
        return !io || (io->buffer == supplied && io->buffer_size == ioCapacity);
    }
    ~PlaybackAvResources() {
        api.av_packet_free(&packet); api.av_frame_free(&frame); api.avcodec_free_context(&codec);
        // Muxer deinit still has a live bridge, custom pb and protected adapter.
        if (format) api.avformat_free_context(format);
        if (SUCCEEDED(result) && !output.ready()) result = output.failure;
        if (!fixedBuffer() && SUCCEEDED(result)) result = E_UNEXPECTED;
        if (io) {
            // Never dereference a stale original if the pinned write-only route
            // unexpectedly replaced it. Such a route can never publish normal.
            if (io->buffer && io->buffer_size > 0) wipeCustodyMemory(io->buffer,static_cast<std::size_t>(io->buffer_size));
            api.av_freep(&io->buffer); api.avio_context_free(&io);
        } else if (supplied) {
            wipeCustodyMemory(supplied,ioCapacity); api.av_free(supplied);
        }
        if (charged) CustodyOwnedMemory::release(ioCapacity);
    }
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
    CustodyBytes recoveredPrivacy; // Exact validated history; empty only for live capture.
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

CustodyFileResult<std::shared_ptr<V5LocalRecordingWriter>> V5LocalRecordingWriter::recover(
    std::shared_ptr<ProtectedCustodyStoreOwner> owner,std::string_view session,
    std::shared_ptr<const std::atomic<bool>> cancellation) {
    auto prepared=prepareRecovery(std::move(owner),session,std::move(cancellation));
    if (!prepared.ok()) return prepared;
    return finishRecovery(std::move(*prepared.value));
}

CustodyFileResult<std::shared_ptr<V5LocalRecordingWriter>> V5LocalRecordingWriter::prepareRecovery(
    std::shared_ptr<ProtectedCustodyStoreOwner> owner,std::string_view session,
    std::shared_ptr<const std::atomic<bool>> cancellation) try {
#ifndef _WIN32
    (void)owner; (void)session; (void)cancellation;
    return {std::nullopt,CustodyFileError::unsupportedPlatform,0};
#else
    if (!owner || !cancellation || session.empty() || session.size()>300)
        return {std::nullopt,CustodyFileError::invalidInput,0};
    auto state=std::allocate_shared<State>(CustodyAllocator<State>{});
    state->cancellation=cancellation;
    std::copy(session.begin(),session.end(),state->session.begin()); state->sessionLength=session.size();
    std::shared_ptr<V5LocalRecordingWriter> writer{new V5LocalRecordingWriter(state),
        std::default_delete<V5LocalRecordingWriter>{},CustodyAllocator<V5LocalRecordingWriter>{}};
    writer->finalized_=true; // This object can never admit new capture or privacy events.
    const auto reason=owner->recoveryReason(session,cancellation);
    if (!reason.ok()) return {std::nullopt,reason.error,reason.nativeError};
    const bool terminal=*reason.value!=ReasonCode::none;
    auto acquired=owner->openUnfinished(session,cancellation,terminal ? CustodyRecoveryLayout::completed : CustodyRecoveryLayout::unused);
    if (terminal) {
        if (!acquired.ok() && acquired.error==CustodyFileError::recoveryRequired)
            acquired=owner->openUnfinished(session,cancellation,CustodyRecoveryLayout::terminalRecoveryUnused);
        if (!acquired.ok()) return {std::nullopt,acquired.error,acquired.nativeError};
    }
    if (!terminal && !acquired.ok() && acquired.error==CustodyFileError::recoveryRequired)
        acquired=owner->openUnfinished(session,cancellation,CustodyRecoveryLayout::completed);
    if (!terminal && !acquired.ok() && acquired.error==CustodyFileError::recoveryRequired)
        acquired=owner->openUnfinished(session,cancellation,CustodyRecoveryLayout::wavReady);
    if (!terminal && !acquired.ok() && acquired.error==CustodyFileError::recoveryRequired)
        acquired=owner->openUnfinished(session,cancellation,CustodyRecoveryLayout::playbackStarted);
    // Each attempt freshly acquires all leases; refused ownership/proof never transfers.
    if (!acquired.ok()) return {std::nullopt,acquired.error,acquired.nativeError};
    state->package=std::move(*acquired.value);
    writer->recoveryPending_=true;
    return {std::move(writer),CustodyFileError::none,0};
#endif
} catch (const std::bad_alloc&) { return {std::nullopt,CustodyFileError::allocationFailed,0}; }
  catch (const std::length_error&) { return {std::nullopt,CustodyFileError::invalidContent,0}; }
  catch (const std::system_error& e) { return {std::nullopt,CustodyFileError::ioFailed,static_cast<std::uint32_t>(e.code().value())}; }

CustodyFileResult<std::shared_ptr<V5LocalRecordingWriter>> V5LocalRecordingWriter::finishRecovery(
    std::shared_ptr<V5LocalRecordingWriter> writer) try {
#ifndef _WIN32
    (void)writer;
    return {std::nullopt,CustodyFileError::unsupportedPlatform,0};
#else
    if (!writer || !writer->recoveryPending_) return {std::nullopt,CustodyFileError::invalidInput,0};
    writer->recoveryPending_=false; // An effectful attempt is never retried on this object.
    const auto& state=writer->state_;
    const auto& cancellation=state->cancellation;
    const std::string_view session(state->session.data(),state->sessionLength);
    if (state->package->recoveryLayout_==CustodyRecoveryLayout::terminalRecoveryUnused) {
        auto prefix=LocalRecordingPackage::inspectUnfinished(state->package,cancellation);
        if (!prefix.ok()) return {std::nullopt,prefix.error,prefix.nativeError};
        writer->frameCount_=(*prefix.value)->completeFrames();
        for (unsigned i=0;i<3;++i) {
            auto proof=ProtectedPackedCustodyTree::verifyImpl(state->package->packed_[i],nullptr,nullptr,i!=0);
            if (!proof.ok()) return {std::nullopt,proof.error,proof.nativeError};
            state->snapshots[i]=std::move(*proof.value);
        }
        if (state->snapshots[0]->logicalBytes()/1920!=writer->frameCount_)
            return {std::nullopt,CustodyFileError::conflict,0};
        if (!writer->writeWav())
            return {std::nullopt,writer->result_.storageError,writer->result_.nativeError};
        prefix.value.reset(); state->snapshots={}; // Native owners stay; no output writer/encoder was created.
    }
    if (state->package->recoveryLayout_==CustodyRecoveryLayout::completed ||
        state->package->recoveryLayout_==CustodyRecoveryLayout::terminalRecoveryUnused) {
        auto inspection=LocalRecordingPackage::completeUnfinished(state->package,session,cancellation);
        if (!inspection.ok()) return {std::nullopt,inspection.error,inspection.nativeError};
        const auto& evidence=(*inspection.value)->evidence();
        auto& result=writer->result_;
        result.packageDirectory=state->package->path(); result.packageContext=state->package->context();
        result.packageGeneration=state->package->current().generation; result.packagePhase=state->package->current().phase;
        result.captureFailure=state->package->current().reason;
        result.durationMs=evidence.durationMs; result.startedAtMs=evidence.startedAtMs; result.stoppedAtMs=evidence.stoppedAtMs;
        result.displayTimezoneOffsetMinutes=evidence.displayTimezoneOffsetMinutes;
        for (std::size_t i=0;i<state->package->current().refCount;++i) {
            const auto& ref=state->package->current().refs[i];
            if (ref.role==CustodyRole::media) { result.wavBytes=*ref.length; result.wavSha256=hexHash(*ref.sha256); }
            if (ref.role==CustodyRole::playback) { result.playbackBytes=*ref.length; result.playbackSha256=hexHash(*ref.sha256); }
        }
        state->inspection=std::move(*inspection.value);
        result.semanticVerified=true; result.trustedPrefixRetained=true;
        return {std::move(writer),CustodyFileError::none,0};
    }
    auto prefix=LocalRecordingPackage::inspectUnfinished(state->package,cancellation);
    if (!prefix.ok()) return {std::nullopt,prefix.error,prefix.nativeError};
    auto history=LocalRecordingPackage::unfinishedHistory(**prefix.value,session);
    if (!history.ok()) return {std::nullopt,history.error,history.nativeError};
    auto canonical=ProtectedPackedCustodyTree::verify(state->package->packed_[0]);
    if (!canonical.ok()) return {std::nullopt,canonical.error,canonical.nativeError};
    writer->frameCount_=(*prefix.value)->completeFrames();
    if ((*canonical.value)->logicalBytes()/1920!=writer->frameCount_)
        return {std::nullopt,CustodyFileError::conflict,0};
    state->snapshots[0]=std::move(*canonical.value);
    if (state->package->recoveryLayout_==CustodyRecoveryLayout::wavReady ||
        state->package->recoveryLayout_==CustodyRecoveryLayout::playbackStarted) {
        auto media=ProtectedPackedCustodyTree::verifyImpl(state->package->packed_[1],nullptr,nullptr,true);
        if (!media.ok()) return {std::nullopt,media.error,media.nativeError};
        state->snapshots[1]=std::move(*media.value);
    }
    if (state->package->recoveryLayout_==CustodyRecoveryLayout::playbackStarted) {
        auto playback=ProtectedPackedCustodyTree::verify(state->package->packed_[2]);
        if (!playback.ok()) return {std::nullopt,playback.error,playback.nativeError};
        state->snapshots[2]=std::move(*playback.value);
    }
    state->recoveredPrivacy=std::move(history.value->privacy);
    auto& result=writer->result_;
    result.packageDirectory=state->package->path(); result.packageContext=state->package->context();
    result.packageGeneration=state->package->current().generation; result.packagePhase=state->package->current().phase;
    result.captureFailure=state->package->current().reason==ReasonCode::none ? ReasonCode::finalizationFailed : state->package->current().reason;
    result.startedAtMs=history.value->evidence.startedAtMs; writer->startedAtMs_=result.startedAtMs;
    result.stoppedAtMs=history.value->evidence.stoppedAtMs;
    result.displayTimezoneOffsetMinutes=history.value->evidence.displayTimezoneOffsetMinutes;
    result.durationMs=writer->frameCount_*10;
    prefix.value.reset(); history.value.reset(); // Retire temporary readers, not native package/role/root leases.
    (void)writer->manifestJson(true); // Reserve room for final artifacts BEFORE the first publication.
    if (!writer->retainPrefix(result.captureFailure,true))
        return {std::nullopt,result.storageError==CustodyFileError::none ? CustodyFileError::invalidContent : result.storageError,result.nativeError};
    return {std::move(writer),CustodyFileError::none,0};
#endif
} catch (const std::bad_alloc&) { return {std::nullopt,CustodyFileError::allocationFailed,0}; }
  catch (const std::length_error&) { return {std::nullopt,CustodyFileError::invalidContent,0}; }
  catch (const std::system_error& e) { return {std::nullopt,CustodyFileError::ioFailed,static_cast<std::uint32_t>(e.code().value())}; }

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
#ifdef GRAF_WINDOWS_TEST_START_BEFORE_CANONICAL
    GRAF_WINDOWS_TEST_START_BEFORE_CANONICAL(*state->package);
#endif
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
    std::optional<CustodyReader> existing;
    if (state_->snapshots[1]) {
        if (state_->snapshots[1]->logicalBytes()!=44+dataBytes) {
            fail(V5WriterError::integrityFailed,CustodyFileError::invalidContent); return false;
        }
        auto opened=openProtectedCustodyReader(state_->snapshots[1],state_->cancellation);
        if (!opened.ok()) { fail(V5WriterError::integrityFailed,opened.error,opened.nativeError); return false; }
        existing.emplace(std::move(*opened.value));
    } else {
        auto opened = state_->package->createWriter(CustodyRole::media);
        if (!opened.ok()) { fail(V5WriterError::storageUnavailable,opened.error,opened.nativeError); return false; }
        state_->writers[1] = std::move(*opened.value);
    }
    auto canonical = openProtectedCustodyReader(state_->snapshots[0],state_->cancellation);
    if (!canonical.ok()) { fail(V5WriterError::integrityFailed,canonical.error,canonical.nativeError); return false; }
    // Bound staging to 32 frames. Convert the entire batch before reusing input
    // for comparison, avoiding per-frame eviction of the shared reader cache.
    constexpr std::uint64_t batchFrames=32;
    CustodyBytes input(1920*batchFrames), pcm(320*batchFrames);
    const auto emit=[&](std::uint64_t offset,const void* bytes,std::size_t count)->CustodyFileResult<std::uint64_t> {
        if (state_->cancellation->load()) return {std::nullopt,CustodyFileError::ioFailed,ERROR_OPERATION_ABORTED};
        if (!existing) return state_->writers[1]->writeAt(offset,bytes,count);
        ULONG got=0;
        const auto hr=existing->stream->Read(input.data(),static_cast<ULONG>(count),&got);
        if (FAILED(hr)) return {std::nullopt,CustodyFileError::ioFailed,static_cast<std::uint32_t>(hr)};
        if (hr!=S_OK || got!=count || std::memcmp(input.data(),bytes,count))
            return {std::nullopt,CustodyFileError::invalidContent,0};
        return {static_cast<std::uint64_t>(count),CustodyFileError::none,0};
    };
    std::array<std::uint8_t,44> header{};
    const auto u16 = [&](std::size_t at, std::uint16_t n) {
        header[at] = static_cast<std::uint8_t>(n); header[at+1] = static_cast<std::uint8_t>(n >> 8);
    };
    const auto u32 = [&](std::size_t at, std::uint32_t n) { for (unsigned i = 0; i < 4; ++i) header[at+i] = static_cast<std::uint8_t>(n >> (8*i)); };
    std::memcpy(header.data(),"RIFF",4); u32(4,static_cast<std::uint32_t>(36+dataBytes));
    std::memcpy(header.data()+8,"WAVEfmt ",8); u32(16,16); u16(20,1); u16(22,1);
    u32(24,16000); u32(28,32000); u16(32,2); u16(34,16);
    std::memcpy(header.data()+36,"data",4); u32(40,static_cast<std::uint32_t>(dataBytes));
    const auto first = emit(0,header.data(),header.size());
    if (!first.ok() || *first.value != header.size()) {
        fail(V5WriterError::storageUnavailable,first.ok() ? CustodyFileError::ioFailed : first.error,first.nativeError); return false;
    }
    // Charged/wiped plaintext staging; no temporary audio file.
    for (std::uint64_t index = 0; index < frameCount_; index+=batchFrames) {
        const auto frames=(std::min)(batchFrames,frameCount_-index);
        const auto inputBytes=static_cast<ULONG>(frames*1920);
        const auto pcmBytes=static_cast<std::size_t>(frames*320);
        ULONG got = 0;
        auto status = state_->cancellation->load() ? HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED) :
            canonical.value->stream->Read(input.data(),inputBytes,&got);
        if (SUCCEEDED(status) && state_->cancellation->load()) status = HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED);
        if (FAILED(status) || got != inputBytes) {
            fail(V5WriterError::integrityFailed,FAILED(status) ? CustodyFileError::ioFailed : CustodyFileError::invalidContent,
                FAILED(status) ? static_cast<std::uint32_t>(status) : 0); return false;
        }
        for (std::size_t at = 0; at < pcmBytes/2; ++at) {
            if (at%160==0 && state_->cancellation->load()) {
                fail(V5WriterError::integrityFailed,CustodyFileError::ioFailed,ERROR_OPERATION_ABORTED); return false;
            }
            std::array<float,3> samples{}; std::memcpy(samples.data(),input.data()+at*12,12);
            const auto sample = static_cast<std::uint16_t>(toPcm16((samples[0]+samples[1]+samples[2])/3.0F));
            pcm[2*at] = static_cast<std::uint8_t>(sample); pcm[2*at+1] = static_cast<std::uint8_t>(sample >> 8);
        }
        const auto wrote = emit(44+index*320,pcm.data(),pcmBytes);
        if (!wrote.ok() || *wrote.value != pcmBytes) {
            fail(V5WriterError::storageUnavailable,wrote.ok() ? CustodyFileError::ioFailed : wrote.error,wrote.nativeError); return false;
        }
    }
    if (existing) {
        ULONG got=9;
        auto hr=existing->stream->Read(input.data(),1,&got);
        if (FAILED(hr) || hr!=S_FALSE || got) {
            fail(V5WriterError::integrityFailed,CustodyFileError::invalidContent,static_cast<std::uint32_t>(hr)); return false;
        }
        got=9; hr=canonical.value->stream->Read(input.data(),0,&got);
        if (hr!=S_OK || got || state_->cancellation->load()) {
            fail(V5WriterError::integrityFailed,CustodyFileError::ioFailed,
                FAILED(hr) ? static_cast<std::uint32_t>(hr) : ERROR_OPERATION_ABORTED); return false;
        }
    }
    return sealAudio(CustodyRole::media,!existing);
#else
    return false;
#endif
}

bool V5LocalRecordingWriter::writePlayback() {
#ifdef _WIN32
    if (state_->snapshots[2]) {
        auto opened=ProtectedCustodyWriter::open(state_->snapshots[2],state_->cancellation);
        if (!opened.ok()) { fail(V5WriterError::storageUnavailable,opened.error,opened.nativeError); return false; }
        state_->writers[2]=std::shared_ptr<ProtectedCustodyWriter>(opened.value->release(),
            [](ProtectedCustodyWriter* p) { delete p; },CustodyAllocator<ProtectedCustodyWriter>{});
        // Full history/BOTH trees and bytewise WAV proof precede this effect.
        // Logical reset only: retain container identity, generations, all old
        // records/orphans and actual physical EOF; the AAC path rebuilds.
        const auto reset=state_->writers[2]->setSize(0);
        if (!reset.ok()) { fail(V5WriterError::storageUnavailable,reset.error,reset.nativeError); return false; }
    } else {
        auto opened = state_->package->createWriter(CustodyRole::playback);
        if (!opened.ok()) { fail(V5WriterError::storageUnavailable,opened.error,opened.nativeError); return false; }
        state_->writers[2] = std::move(*opened.value);
    }
    auto canonical = openProtectedCustodyReader(state_->snapshots[0],state_->cancellation);
    if (!canonical.ok()) { fail(V5WriterError::integrityFailed,canonical.error,canonical.nativeError); return false; }
    auto adapter = ProtectedCustodyWriteStream::open(state_->writers[2],state_->cancellation);
    if (!adapter.ok()) { fail(V5WriterError::storageUnavailable,adapter.error,adapter.nativeError); return false; }
    {
        // Canonical reads and AVIO callbacks admit their actual IO through
        // separate Guards; an aggregate slot would double-charge their overlap.
        std::optional<FfmpegApi> library; // Unloaded last, after resource/adapter drain.
        HRESULT hr = S_OK;
        try {
            auto& api = library.emplace();
            PlaybackAvio out{**adapter.value,*state_->cancellation};
            constexpr std::uint64_t batchFrames = 32;
            CustodyBytes canonicalBytes(1920*batchFrames);
            // Non-refcounted input: send_frame makes its own library-owned copy.
            // This caller-owned PCM allocation remains charged and fully wiped.
            CustodyVector<float> pcm(1024+AV_INPUT_BUFFER_PADDING_SIZE/sizeof(float));
            PlaybackAvResources resources{api,hr,out};
            const auto check = [&](int status = 0) {
                if (!out.ready()) hr = out.failure;
                else if (!resources.fixedBuffer()) hr = E_UNEXPECTED;
                else if (resources.io && resources.io->error < 0) hr = playbackAvError(resources.io->error);
                else hr = playbackAvError(status);
                if (FAILED(hr)) throw hr;
            };
            check();
            check(api.avformat_alloc_output_context2(&resources.format,nullptr,"ipod",nullptr));
            if (!resources.format || !resources.format->oformat ||
                std::strcmp(resources.format->oformat->name,"ipod") != 0) throw E_UNEXPECTED;
            // Retain the charged AVIO buffer instead of flushing each encoded packet.
            resources.format->flush_packets = 0;
            resources.format->opaque = &out;
            resources.format->io_open = PlaybackAvio::denyOpen;
            resources.format->io_close2 = PlaybackAvio::denyClose;
            const auto encoder = api.avcodec_find_encoder_by_name("aac");
            if (!encoder || !(encoder->capabilities & AV_CODEC_CAP_SMALL_LAST_FRAME)) throw E_UNEXPECTED;
            resources.codec = api.avcodec_alloc_context3(encoder);
            if (!resources.codec) throw E_OUTOFMEMORY;
            auto* codec = resources.codec;
            codec->sample_rate = 48000; codec->sample_fmt = AV_SAMPLE_FMT_FLTP;
            codec->bit_rate = 96000; codec->profile = AV_PROFILE_AAC_LOW;
            codec->time_base = AVRational{1,48000}; codec->thread_count = 1;
            api.av_channel_layout_default(&codec->ch_layout,1);
            if (resources.format->oformat->flags & AVFMT_GLOBALHEADER) codec->flags |= AV_CODEC_FLAG_GLOBAL_HEADER;
            check(api.avcodec_open2(codec,encoder,nullptr));
            if (codec->frame_size != 1024) throw E_UNEXPECTED;
            auto* stream = api.avformat_new_stream(resources.format,nullptr);
            if (!stream) throw E_OUTOFMEMORY;
            stream->time_base = codec->time_base;
            check(api.avcodec_parameters_from_context(stream->codecpar,codec));
            if (!CustodyOwnedMemory::tryReserve(PlaybackAvResources::ioCapacity)) throw std::bad_alloc();
            resources.charged = true;
            resources.supplied = static_cast<unsigned char*>(api.av_malloc(PlaybackAvResources::ioCapacity));
            if (!resources.supplied) throw E_OUTOFMEMORY;
            resources.io = api.avio_alloc_context(resources.supplied,PlaybackAvResources::ioCapacity,1,&out,
                nullptr,PlaybackAvio::write,PlaybackAvio::seek);
            if (!resources.io) throw E_OUTOFMEMORY;
            resources.io->seekable = AVIO_SEEKABLE_NORMAL;
            resources.format->pb = resources.io; resources.format->flags |= AVFMT_FLAG_CUSTOM_IO;
            check(api.avformat_write_header(resources.format,nullptr));
            resources.frame = api.av_frame_alloc(); resources.packet = api.av_packet_alloc();
            if (!resources.frame || !resources.packet) throw E_OUTOFMEMORY;
            auto* frame = resources.frame;
            frame->format = codec->sample_fmt; frame->sample_rate = codec->sample_rate;
            check(api.av_channel_layout_copy(&frame->ch_layout,&codec->ch_layout));
            frame->data[0] = reinterpret_cast<std::uint8_t*>(pcm.data());
            frame->linesize[0] = 1024*sizeof(float);
            const auto receive = [&](bool draining) {
                for (;;) {
                    check();
                    const auto received = api.avcodec_receive_packet(codec,resources.packet);
                    check();
                    if (received == AVERROR_EOF) { if (!draining) throw E_UNEXPECTED; return; }
                    if (received == AVERROR(EAGAIN)) { if (draining) throw E_UNEXPECTED; return; }
                    check(received);
                    if (resources.packet->size <= 0) throw E_UNEXPECTED;
                    api.av_packet_rescale_ts(resources.packet,codec->time_base,stream->time_base);
                    resources.packet->stream_index = stream->index;
                    const auto muxed = api.av_interleaved_write_frame(resources.format,resources.packet);
                    api.av_packet_unref(resources.packet);
                    check(muxed);
                }
            };
            std::uint64_t submitted = 0;
            const auto submit = [&](unsigned count) {
                check();
                frame->nb_samples = static_cast<int>(count); frame->pts = static_cast<std::int64_t>(submitted);
                const auto sent = api.avcodec_send_frame(codec,frame);
                check(sent);
                const auto observed = GRAF_PLAYBACK_SAMPLE(reinterpret_cast<const float*>(frame->data[0]),
                    static_cast<unsigned>(frame->nb_samples),static_cast<std::uint64_t>(frame->pts),playbackAvError(sent));
                if (FAILED(observed)) throw observed;
                check(); // A genuine successful submit may trigger the test cancellation.
                receive(false); submitted += count;
            };
            unsigned filled = 0;
            for (std::uint64_t n = 0; n < frameCount_; ++n) {
                check();
                if (n%batchFrames == 0) {
                    const auto count = static_cast<ULONG>((std::min)(batchFrames,frameCount_-n)*1920);
                    ULONG got = 0;
                    const auto read = GRAF_PLAYBACK_READ(canonical.value->stream.Get(),canonicalBytes.data(),count,&got);
                    if (FAILED(read) || got != count) {
                        hr = FAILED(read) ? read : STG_E_READFAULT;
                        fail(V5WriterError::integrityFailed,CustodyFileError::ioFailed,static_cast<std::uint32_t>(hr));
                        throw hr;
                    }
                    check();
                }
                for (std::size_t at = 0; at < 480; ++at) {
                    float value = 0;
                    std::memcpy(&value,canonicalBytes.data()+static_cast<std::size_t>(n%batchFrames)*1920+at*4,4);
                    pcm[filled++] = static_cast<float>(toPcm16(value))/32768.0F;
                    if (filled == 1024) { submit(filled); filled = 0; }
                }
            }
            if (filled) submit(filled); // Actual small_last_frame; no padding or cropping.
            check(api.avcodec_send_frame(codec,nullptr)); receive(true);
            check(api.av_write_trailer(resources.format));
            api.avio_flush(resources.io); check(); // flush is void: inspect sticky IO state.
        } catch (const std::bad_alloc&) { hr = E_OUTOFMEMORY; }
          catch (HRESULT error) { hr = error; }
          catch (...) { hr = E_FAIL; }
        // Serialized close drains actual stream calls before checkpoint/decode.
        const auto closed = (*adapter.value)->close();
        if (SUCCEEDED(hr) && FAILED(closed)) hr = closed;
        adapter.value.reset(); canonical.value.reset();
        library.reset(); // Every FFmpeg free/callback has already returned.
        if (FAILED(hr)) {
            fail(V5WriterError::encodeFailed,hr == E_OUTOFMEMORY ? CustodyFileError::allocationFailed : CustodyFileError::ioFailed,
                static_cast<std::uint32_t>(hr)); return false;
        }
    }
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
    if (index >= state_->writers.size() || (!state_->writers[index] && (checkpoint || !state_->snapshots[index]))) return false;
    auto writer = state_->writers[index];
    if (checkpoint) {
        const auto commit = writer->checkpoint();
        if (commit.state != CustodyCommitState::committed) {
            fail(V5WriterError::storageUnavailable,commit.error,commit.nativeError); return false;
        }
    }
    auto snapshot = writer ? writer->committedPackedSnapshot() :
        CustodyFileResult<std::shared_ptr<const ProtectedPackedCustodyTree>>{state_->snapshots[index],CustodyFileError::none,0};
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
    if (state_->recoveredPrivacy.empty() || capacityCheck || startedAtMs_) {
        json.text(",\"started_at_ms\":"); json.number(capacityCheck ? maximum : startedAtMs_);
        json.text(",\"stopped_at_ms\":"); json.number(capacityCheck ? maximum : finalized_ ? result_.stoppedAtMs : std::max(startedAtMs_,wallClockMs()));
        json.text(",\"display_timezone_offset_minutes\":");
        if (capacityCheck || result_.displayTimezoneOffsetMinutes < 0) json.text("-");
        json.number(capacityCheck ? 840 : static_cast<std::uint64_t>(std::abs(result_.displayTimezoneOffsetMinutes)));
    }
    json.text(",\"sessionId\":\""); json.text({state_->session.data(),state_->sessionLength}); json.text("\"");
    if (capacityCheck || state_->shortIntent) { json.text(",\""); json.text(kShortRecordingDiscardedField); json.text("\":true"); }
    json.text(",\"privacySegments\":");
    if (!state_->recoveredPrivacy.empty()) json.text({reinterpret_cast<const char*>(state_->recoveredPrivacy.data()),state_->recoveredPrivacy.size()});
    else {
    json.text("[");
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
    }
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

#ifdef _WIN32
CustodyBytes V5LocalRecordingWriter::recoveryJson(ReasonCode reason,std::uint64_t complete,const CustodyPackageReference& canonical) {
    MetadataJson recovery;
    recovery.text("{\"capture_status\":\"degraded\",\"capture_reason_code\":\""); recovery.text(toString(reason));
    recovery.text("\",\"trusted_prefix_frames\":"); recovery.number(complete);
    recovery.text(",\"canonical_bytes\":"); recovery.number(*canonical.length);
    recovery.text(",\"canonical_sha256\":\""); recovery.text(hexHash(*canonical.sha256)); recovery.text("\"}");
    return std::move(recovery.bytes);
}
#endif

bool V5LocalRecordingWriter::retainPrefix(ReasonCode reason,bool playable) {
#ifdef _WIN32
    if (state_->package->current().phase == CustodyPackagePhase::capturing &&
        !commitState(CustodyPackagePhase::finalizing,reason)) return false;
    if (state_->package->current().phase != CustodyPackagePhase::finalizing) return false;
    // Only a genuine committed snapshot; never frameCount or physical file size.
    auto proof = state_->writers[0] ? state_->writers[0]->committedPackedSnapshot() :
        CustodyFileResult<std::shared_ptr<const ProtectedPackedCustodyTree>>{state_->snapshots[0],CustodyFileError::none,0};
    if (!proof.ok()) { fail(V5WriterError::integrityFailed,proof.error,proof.nativeError); return false; }
    const auto complete = (*proof.value)->logicalBytes()/1920;
    if (!complete || !sealAudio(CustodyRole::canonical,false)) return false;
    const auto& canonical = *state_->refs[0];
    const auto recovery=recoveryJson(reason,complete,canonical);
    // Keep history in its existing protected manifest, not in a new recovery
    // shape. Live failures discard derived refs; cold recovery includes only
    // its freshly encoded and independently verified outputs.
    if (playable) { if (!writeWav() || !writePlayback()) return false; }
    else { state_->refs[1].reset(); state_->refs[2].reset(); }
    state_->refs[4].reset();
    result_.durationMs = complete*10;
    const auto manifest = manifestJson();
    if (!sealMetadata(CustodyRole::manifest,manifest) ||
        !sealMetadata(CustodyRole::recovery,recovery) ||
        !commitState(CustodyPackagePhase::sealedDegraded,reason)) return false;
    state_->writers = {}; state_->snapshots = {}; // Sealed: retire write-only resources before the full read closure.
    auto inspected = LocalRecordingPackage::inspectProtected(state_->package,
        {state_->session.data(),state_->sessionLength},state_->cancellation);
    if (!inspected.ok()) { fail(V5WriterError::integrityFailed,inspected.error,inspected.nativeError); return false; }
    if ((*inspected.value)->evidence().integrity != PackageIntegrity::degraded) {
        fail(V5WriterError::integrityFailed,CustodyFileError::invalidContent); return false;
    }
    if (playable && (!(*inspected.value)->evidence().manifestSessionMatched ||
        (*inspected.value)->evidence().durationMs!=complete*10 || !(*inspected.value)->evidence().playback.decodedFrames)) {
        fail(V5WriterError::integrityFailed,CustodyFileError::invalidContent); return false;
    }
    state_->inspection = std::move(*inspected.value);
    result_.semanticVerified = true; result_.trustedPrefixRetained = true; result_.durationMs = complete*10;
    return true;
#else
    (void)reason; (void)playable; return false;
#endif
}

V5WriterResult V5LocalRecordingWriter::finalize(ReasonCode failure, RecordingStopReason stopReason,
    bool confirmedSelectedMicrophoneLoss) try {
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
        const bool microphoneLoss = confirmedSelectedMicrophoneLoss && failure == ReasonCode::microphoneEndpointUnavailable &&
            result_.error == V5WriterError::none;
        if (result_.captureFailure == ReasonCode::none ||
            (confirmedSelectedMicrophoneLoss && failure == ReasonCode::microphoneEndpointUnavailable &&
                result_.error != V5WriterError::none))
            result_.captureFailure = ReasonCode::storageUnavailable;
        // T126 completes a checked system-only stream, using the same protected
        // degraded codec/inspection path as cold recovery. It grants no upload.
        if (!retainPrefix(result_.captureFailure, microphoneLoss) && microphoneLoss)
            result_.captureFailure = ReasonCode::storageUnavailable;
        return result_;
    }
    if (!commitState(CustodyPackagePhase::finalizing,ReasonCode::none) ||
        !GRAF_FINALIZE_PHASE(0,sealAudio(CustodyRole::canonical)) || *state_->refs[0]->length != frameCount_*1920 ||
        !GRAF_FINALIZE_PHASE(1,writeWav()) || !GRAF_FINALIZE_PHASE(2,writePlayback())) {
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
    state_->writers = {}; state_->snapshots = {}; // Package leases/identity stay held; no reopen or relaxed inspection.
    auto inspected = GRAF_FINALIZE_PHASE(3,LocalRecordingPackage::inspectProtected(state_->package,
        {state_->session.data(),state_->sessionLength},state_->cancellation));
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
    if (confirmedSelectedMicrophoneLoss && result_.captureFailure == ReasonCode::microphoneEndpointUnavailable)
        result_.captureFailure = ReasonCode::storageUnavailable;
    fail(V5WriterError::storageUnavailable,CustodyFileError::allocationFailed); return result_;
} catch (...) {
    if (confirmedSelectedMicrophoneLoss && result_.captureFailure == ReasonCode::microphoneEndpointUnavailable)
        result_.captureFailure = ReasonCode::storageUnavailable;
    fail(V5WriterError::integrityFailed,CustodyFileError::invalidContent); return result_;
}

} // namespace graf::windows
