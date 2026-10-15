#include "LocalRecordingPackage.h"

#include "../Storage/AtomicFileStore.h"
#include "../Storage/Sha256.h"
#include "../Contracts/JsonString.h"

#include <array>
#include <charconv>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <limits>
#include <regex>

#ifdef _WIN32
#include <mfapi.h>
#include <mferror.h>
#include <mfidl.h>
#include <mfreadwrite.h>
#include <propvarutil.h>
#include <wrl/client.h>
#include "../Storage/ProtectedCustodyReader.h"
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

bool canonicalWavHeader(const std::array<unsigned char, 44>& header, std::uint64_t bytes, std::uint64_t durationMs) {
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

bool canonicalWav(const std::filesystem::path& path, std::uint64_t bytes, std::uint64_t durationMs) {
    std::array<unsigned char, 44> header{};
    std::ifstream input(path, std::ios::binary);
    return input.read(reinterpret_cast<char*>(header.data()), static_cast<std::streamsize>(header.size())) &&
        canonicalWavHeader(header, bytes, durationMs);
}

#ifdef _WIN32
struct PlaybackRuntime {
    HRESULT com = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    bool started = false;
    ~PlaybackRuntime() { if (started) MFShutdown(); if (SUCCEEDED(com)) CoUninitialize(); }
};
HRESULT decodePlayback(IMFSourceReader*, std::uint64_t,
    const std::shared_ptr<const std::atomic<bool>>&, LocalRecordingPackage::PlaybackEvidence&);
#endif

bool canonicalPlayback(const std::filesystem::path& path, std::uint64_t durationMs) try {
#ifndef _WIN32
    (void)path;
    (void)durationMs;
    return false; // The portable lane cannot attest to an AAC decoder.
#else
    const auto cancellation = std::allocate_shared<std::atomic<bool>>(CustodyAllocator<std::atomic<bool>>{}, false);
    PlaybackRuntime runtime;
    if (FAILED(runtime.com) && runtime.com != RPC_E_CHANGED_MODE) return false;
    runtime.started = SUCCEEDED(MFStartup(MF_VERSION));
    bool valid = false;
    if (runtime.started) {
        Microsoft::WRL::ComPtr<IMFSourceReader> reader;
        LocalRecordingPackage::PlaybackEvidence evidence;
        if (SUCCEEDED(MFCreateSourceReaderFromURL(path.c_str(), nullptr, &reader)) &&
            SUCCEEDED(decodePlayback(reader.Get(), durationMs, cancellation, evidence)))
            valid = evidence.decodedFrames != 0;
    } // Release reader before MFShutdown, including exceptional exits.
    return valid;
#endif
} catch (const std::bad_alloc&) { return false; }

} // namespace

#ifdef _WIN32
namespace {
constexpr std::size_t manifestLimit = 65536;
struct ManifestArtifact { std::uint64_t bytes = 0; std::array<std::uint8_t, 32> sha{}; };
struct ProtectedManifest {
    LocalRecordingPackage::ProtectedEvidence evidence;
    std::array<ManifestArtifact, 2> artifacts{};
    ReasonCode reason = ReasonCode::none;
    bool degraded = false, shortDiscarded = false, hasArtifacts = false;
};
struct PrefixRecovery {
    ReasonCode reason = ReasonCode::none;
    std::uint64_t frames = 0;
    ManifestArtifact canonical;
};
// Same closed object/bitmask pattern as PackageJson. Only the known v5 and
// recovery shapes: no DOM, recursive skipping or extra segment/history cap.
class RecordingJson final {
public:
    RecordingJson(std::string_view input, std::string_view session) : input_(input), session_(session) {
        token_.reserve(input.size()); // Charge capacity before decoded plaintext.
    }
    bool manifest(ProtectedManifest& value) {
        constexpr std::array<std::string_view, 14> keys{"schema_version","canonical_mix_profile","source_kind",
            "media_scribe_source_mode","capture_status","capture_reason_code","duration_ms","started_at_ms",
            "stopped_at_ms","display_timezone_offset_minutes","artifacts",kShortRecordingDiscardedField,"sessionId","privacySegments"};
        unsigned fields = 0;
        if (!object(keys, fields, [&](std::size_t key) {
            switch (key) {
            case 0: return equal(kManifestSchemaVersion);
            case 1: return equal(kCanonicalMixProfile);
            case 2: return equal(kV5SourceKind);
            case 3: return equal(kV5MediaScribeSourceMode);
            case 4: { const auto s = string(); if (!s || (*s != "normal" && *s != "degraded" && *s != "blocked")) return false;
                value.degraded = *s == "degraded"; blocked_ = *s == "blocked"; return true; }
            case 5: return reason(value.reason);
            case 6: return number(value.evidence.durationMs);
            case 7: return number(value.evidence.startedAtMs);
            case 8: return number(value.evidence.stoppedAtMs);
            case 9: {
                whitespace(); const auto start = cursor_; if (cursor_ < input_.size() && input_[cursor_] == '-') ++cursor_;
                if (cursor_ == input_.size() || input_[cursor_] < '0' || input_[cursor_] > '9') return false;
                std::uint64_t magnitude = 0; if (!number(magnitude) || magnitude > 840) return false;
                value.evidence.displayTimezoneOffsetMinutes = input_[start] == '-' ? -static_cast<int>(magnitude) : static_cast<int>(magnitude);
                return true;
            }
            case 10: {
                value.hasArtifacts = true;
                constexpr std::array<std::string_view, 2> roles{"media","playback"}; unsigned rolesRead = 0;
                return object(roles, rolesRead, [&](std::size_t role) { return artifact(value.artifacts[role]); }) && rolesRead == 3;
            }
            case 11: return boolean(value.shortDiscarded);
            case 12: value.evidence.manifestSessionMatched = equal(session_); return value.evidence.manifestSessionMatched;
            case 13: return privacy();
            }
            return false;
        }) || !finished() || (fields & 0x4fU) != 0x4fU ||
            // Only the known canonical-only degraded shape omits artifacts;
            // it must bind this session and carry its complete privacy history.
            (!value.hasArtifacts && (!value.degraded || (fields & 0x3000U) != 0x3000U)) ||
            ((fields & 0x30U) != 0 && (fields & 0x30U) != 0x30U) ||
            ((fields & 0x380U) != 0 && (fields & 0x380U) != 0x380U) || blocked_ != value.shortDiscarded ||
            value.degraded != (value.reason != ReasonCode::none)) return false;
        return !(fields & 0x380U) || (value.evidence.startedAtMs > 0 && value.evidence.stoppedAtMs >= value.evidence.startedAtMs);
    }
    bool recovery(PrefixRecovery& value) {
        constexpr std::array<std::string_view, 5> keys{"capture_status","capture_reason_code","trusted_prefix_frames","canonical_bytes","canonical_sha256"};
        unsigned fields = 0;
        return object(keys, fields, [&](std::size_t key) {
            switch (key) {
            case 0: return equal("degraded");
            case 1: return reason(value.reason);
            case 2: return number(value.frames);
            case 3: return number(value.canonical.bytes);
            case 4: return hash(value.canonical.sha);
            }
            return false;
        }) && fields == 31 && finished() && value.reason != ReasonCode::none;
    }
private:
    void whitespace() { while (cursor_ < input_.size() && std::string_view(" \r\n\t").find(input_[cursor_]) != std::string_view::npos) ++cursor_; }
    bool finished() { whitespace(); return cursor_ == input_.size(); }
    bool take(char c) { whitespace(); if (cursor_ == input_.size() || input_[cursor_] != c) return false; ++cursor_; return true; }
    bool literal(std::string_view text) { whitespace(); if (input_.substr(cursor_, text.size()) != text) return false; cursor_ += text.size(); return true; }
    bool boolean(bool& value) { if (literal("true")) { value = true; return true; } if (!literal("false")) return false; value = false; return true; }
    std::optional<std::string_view> string() {
        whitespace(); const auto start = cursor_;
        if (!take('"')) return std::nullopt;
        while (cursor_ < input_.size()) {
            const auto c = input_[cursor_++];
            if (c == '\\') { if (cursor_ == input_.size()) return std::nullopt; ++cursor_; continue; }
            if (c != '"') continue;
            if (!token_.empty()) SecureZeroMemory(token_.data(), token_.size());
            token_.clear();
            if (!json_detail::decodeString(input_.substr(start, cursor_-start), input_.size(), false,
                [&](char byte) { token_.push_back(static_cast<std::uint8_t>(byte)); })) return std::nullopt;
            return std::string_view(reinterpret_cast<const char*>(token_.data()), token_.size());
        }
        return std::nullopt;
    }
    bool equal(std::string_view expected) { const auto s = string(); return s && *s == expected; }
    bool number(std::uint64_t& out) {
        whitespace(); const auto start = cursor_;
        while (cursor_ < input_.size() && input_[cursor_] >= '0' && input_[cursor_] <= '9') ++cursor_;
        if (start == cursor_ || (cursor_-start > 1 && input_[start] == '0')) return false;
        const auto parsed = std::from_chars(input_.data()+start, input_.data()+cursor_, out);
        return parsed.ec == std::errc{} && parsed.ptr == input_.data()+cursor_;
    }
    bool monotonic(std::uint64_t& out) { return number(out) && out <= static_cast<std::uint64_t>((std::numeric_limits<std::int64_t>::max)()); }
    bool reason(ReasonCode& value) {
        const auto s = string(); if (!s) return false;
        for (unsigned i = 0; i <= static_cast<unsigned>(ReasonCode::localPurgeUnverified); ++i)
            if (*s == toString(static_cast<ReasonCode>(i))) { value = static_cast<ReasonCode>(i); return true; }
        return false;
    }
    bool hash(std::array<std::uint8_t, 32>& out) {
        const auto s = string(); if (!s || s->size() != 64) return false;
        const auto digit = [](char c) { return c >= '0' && c <= '9' ? c-'0' : c >= 'a' && c <= 'f' ? c-'a'+10 : -1; };
        for (std::size_t i = 0; i < out.size(); ++i) { const auto a = digit((*s)[2*i]), b = digit((*s)[2*i+1]); if (a < 0 || b < 0) return false; out[i] = static_cast<std::uint8_t>(16*a+b); }
        return true;
    }
    template<std::size_t N, class Field> bool object(const std::array<std::string_view, N>& keys, unsigned& fields, Field field) {
        if (!take('{')) return false;
        if (!take('}')) {
            do {
                const auto s = string(); if (!s) return false;
                const auto at = std::find(keys.begin(), keys.end(), *s); if (at == keys.end()) return false;
                const auto index = static_cast<std::size_t>(at-keys.begin()); const auto bit = 1U << index;
                if ((fields & bit) || !take(':')) return false;
                fields |= bit; if (!field(index)) return false;
            } while (take(','));
            if (!take('}')) return false;
        }
        return true;
    }
    bool artifact(ManifestArtifact& value) {
        constexpr std::array<std::string_view, 2> keys{"bytes","sha256"}; unsigned fields = 0;
        return object(keys, fields, [&](std::size_t key) { return key ? hash(value.sha) : number(value.bytes); }) && fields == 3;
    }
    bool date() {
        const auto s = string(); if (!s || s->size() != 20 || (*s)[4] != '-' || (*s)[7] != '-' || (*s)[10] != 'T' ||
            (*s)[13] != ':' || (*s)[16] != ':' || (*s)[19] != 'Z') return false;
        const auto part = [&](std::size_t at, std::size_t count) {
            unsigned n = 0;
            for (std::size_t i = at; i < at+count; ++i) { const auto c = (*s)[i]; if (c < '0' || c > '9') return 10000U; n = n*10+static_cast<unsigned>(c-'0'); }
            return n;
        };
        const auto y = part(0,4), m = part(5,2), d = part(8,2);
        constexpr std::array<unsigned,12> days{31,28,31,30,31,30,31,31,30,31,30,31};
        return y > 0 && y < 10000 && m > 0 && m <= 12 && d > 0 &&
            d <= days[m-1]+(m == 2 && y%4 == 0 && (y%100 != 0 || y%400 == 0) ? 1U : 0U) &&
            part(11,2) < 24 && part(14,2) < 60 && part(17,2) < 60;
    }
    template<std::size_t N> bool oneOf(const std::array<std::string_view, N>& values) {
        const auto s = string(); return s && std::find(values.begin(), values.end(), *s) != values.end();
    }
    bool privacy() {
        if (!take('[')) return false;
        CustodyVector<CustodyBytes> ids;
        if (!take(']')) {
            do {
                constexpr std::array<std::string_view,11> keys{"segmentId","sessionId","control","startedAt","endedAt",
                    "startMonotonicMs","endMonotonicMs","durationMs","localMicTreatment","initiator","diagnosticSafe"};
                unsigned fields = 0; std::uint64_t start = 0, end = 0, duration = 0;
                if (!object(keys, fields, [&](std::size_t key) {
                    switch (key) {
                    case 0: {
                        const auto s = string(); if (!s || s->empty()) return false;
                        // ponytail: quadratic uniqueness within the entire 64KiB
                        // manifest cap; replace with a charged set if that cap grows.
                        for (const auto& id : ids) if (std::string_view(reinterpret_cast<const char*>(id.data()),id.size()) == *s) return false;
                        ids.emplace_back(token_.begin(),token_.end()); return true;
                    }
                    case 1: return equal(session_);
                    case 2: return oneOf(std::array<std::string_view,3>{"pause","resume","stop"});
                    case 3: case 4: return date();
                    case 5: return monotonic(start);
                    case 6: return monotonic(end);
                    case 7: return monotonic(duration);
                    case 8: return oneOf(std::array<std::string_view,3>{"silenced","redacted","ended"});
                    case 9: return oneOf(std::array<std::string_view,5>{"user","assisted_automation","system_fail_closed","recovery","validation"});
                    case 10: { bool safe = false; return boolean(safe); }
                    }
                    return false;
                }) || ((fields != 0x7afU || duration != 0) &&
                    (fields != 0x7ffU || end < start || duration != end-start))) return false;
            } while (take(','));
            if (!take(']')) return false;
        }
        return true;
    }
    std::string_view input_, session_; std::size_t cursor_ = 0;
    bool blocked_ = false;
    CustodyBytes token_;
};

CustodyFileError nativeFileError(HRESULT hr) {
    return hr == E_OUTOFMEMORY || hr == HRESULT_FROM_WIN32(ERROR_NOT_ENOUGH_MEMORY) || hr == HRESULT_FROM_WIN32(ERROR_NOT_ENOUGH_QUOTA)
        ? CustodyFileError::allocationFailed : CustodyFileError::ioFailed;
}
std::uint32_t nativeCode(HRESULT hr) { return hr == HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED) ? ERROR_OPERATION_ABORTED : static_cast<std::uint32_t>(hr); }
HRESULT protectedRead(IStream* stream, void* bytes, ULONG count, const std::shared_ptr<const std::atomic<bool>>& cancel) {
    if (cancel->load()) return HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED);
    ULONG got = 0; const auto hr = stream->Read(bytes, count, &got);
    if (FAILED(hr)) return hr;
    if (cancel->load()) return HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED);
    return got == count ? S_OK : STG_E_READFAULT;
}
CustodyFileResult<CustodyBytes> protectedMetadata(IStream* stream, std::uint64_t length,
    const std::shared_ptr<const std::atomic<bool>>& cancel) {
    if (!length || length > manifestLimit) return {std::nullopt, CustodyFileError::invalidContent, 0};
    CustodyBytes bytes(static_cast<std::size_t>(length));
    auto hr = protectedRead(stream, bytes.data(), static_cast<ULONG>(bytes.size()), cancel);
    if (FAILED(hr)) return {std::nullopt, nativeFileError(hr), nativeCode(hr)};
    std::uint8_t extra = 0; ULONG got = 0;
    if (cancel->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
    hr = stream->Read(&extra, 1, &got);
    if (FAILED(hr)) return {std::nullopt, nativeFileError(hr), nativeCode(hr)};
    if (cancel->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
    if (got || hr != S_FALSE) return {std::nullopt, CustodyFileError::invalidContent, 0};
    return {std::move(bytes), CustodyFileError::none, 0};
}

HRESULT decodePlayback(IMFSourceReader* reader, std::uint64_t durationMs,
    const std::shared_ptr<const std::atomic<bool>>& cancellation, LocalRecordingPackage::PlaybackEvidence& evidence) {
    using Microsoft::WRL::ComPtr;
    constexpr auto maximum = static_cast<std::uint64_t>((std::numeric_limits<LONGLONG>::max)());
    if (!durationMs || durationMs > maximum/10'000-100) return MF_E_INVALIDMEDIATYPE;
    const auto call = [&](auto action) {
        if (cancellation->load()) return HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED);
        const HRESULT hr = action();
        return FAILED(hr) ? hr : cancellation->load() ? HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED) : hr;
    };
        ComPtr<IMFMediaType> native, pcm, actual, extra;
        HRESULT status = call([&] { return reader->GetNativeMediaType(0, 0, &native); }); if (FAILED(status)) return status;
        status = call([&] { return reader->GetNativeMediaType(1, 0, &extra); });
        if (status != MF_E_INVALIDSTREAMNUMBER) return FAILED(status) ? status : MF_E_INVALIDMEDIATYPE;
        const auto guid = [&](IMFMediaType* type, REFGUID key, REFGUID expected) -> HRESULT {
            GUID value{}; const auto got = call([&] { return type->GetGUID(key, &value); });
            return FAILED(got) ? got : value == expected ? S_OK : MF_E_INVALIDMEDIATYPE;
        };
        const auto number = [&](IMFMediaType* type, REFGUID key, UINT32 expected, bool optional = false) -> HRESULT {
            UINT32 value = 0; const auto got = call([&] { return type->GetUINT32(key, &value); });
            if (optional && got == MF_E_ATTRIBUTENOTFOUND) return S_OK;
            return FAILED(got) ? got : value == expected ? S_OK : MF_E_INVALIDMEDIATYPE;
        };
        for (const auto check : {guid(native.Get(), MF_MT_MAJOR_TYPE, MFMediaType_Audio),
            guid(native.Get(), MF_MT_SUBTYPE, MFAudioFormat_AAC),
            number(native.Get(), MF_MT_AUDIO_SAMPLES_PER_SECOND, 48'000),
            number(native.Get(), MF_MT_AUDIO_NUM_CHANNELS, 1), number(native.Get(), MF_MT_AAC_PAYLOAD_TYPE, 0, true)})
            if (FAILED(check)) return check;
        UINT32 configSize = 0;
        status = call([&] { return native->GetBlobSize(MF_MT_USER_DATA, &configSize); }); if (FAILED(status)) return status;
        if (configSize != 14) return MF_E_INVALIDMEDIATYPE;
        std::array<UINT8, 14> config{};
        status = call([&] { return native->GetBlob(MF_MT_USER_DATA, config.data(), static_cast<UINT32>(config.size()), &configSize); });
        if (FAILED(status)) return status;
        const auto profile = static_cast<UINT32>(config[2]) | (static_cast<UINT32>(config[3]) << 8);
        if (configSize != config.size() || config[0] || config[1] ||
            (profile != 0 && profile != 0xfe && profile != 0x29 && profile != 0x2a && profile != 0x2b) ||
            std::any_of(config.begin()+4, config.begin()+12, [](UINT8 byte) { return byte != 0; }) ||
            config[12] != 0x11 || config[13] != 0x88) return MF_E_INVALIDMEDIATYPE;
        status = number(native.Get(), MF_MT_AAC_AUDIO_PROFILE_LEVEL_INDICATION, profile, true); if (FAILED(status)) return status;
        PROPVARIANT duration; PropVariantInit(&duration);
        status = call([&] { return reader->GetPresentationAttribute(static_cast<DWORD>(MF_SOURCE_READER_MEDIASOURCE), MF_PD_DURATION, &duration); });
        if (SUCCEEDED(status) && duration.vt == VT_UI8) evidence.containerDuration100ns = duration.uhVal.QuadPart;
        else if (SUCCEEDED(status)) status = MF_E_INVALIDMEDIATYPE;
        PropVariantClear(&duration); if (FAILED(status)) return status;
        const auto expected = durationMs * 10'000;
        const auto close = [expected](std::uint64_t value) { return value > 0 && (value > expected ? value-expected : expected-value) <= 1'000'000; };
        if (!close(evidence.containerDuration100ns)) return MF_E_INVALIDMEDIATYPE;
        status = call([&] { return MFCreateMediaType(&pcm); }); if (FAILED(status)) return status;
        status = call([&] { return pcm->SetGUID(MF_MT_MAJOR_TYPE, MFMediaType_Audio); }); if (FAILED(status)) return status;
        status = call([&] { return pcm->SetGUID(MF_MT_SUBTYPE, MFAudioFormat_PCM); }); if (FAILED(status)) return status;
        status = call([&] { return reader->SetCurrentMediaType(0, nullptr, pcm.Get()); }); if (FAILED(status)) return status;
        status = call([&] { return reader->GetCurrentMediaType(0, &actual); }); if (FAILED(status)) return status;
        for (const auto check : {guid(actual.Get(), MF_MT_MAJOR_TYPE, MFMediaType_Audio), guid(actual.Get(), MF_MT_SUBTYPE, MFAudioFormat_PCM),
            number(actual.Get(), MF_MT_AUDIO_SAMPLES_PER_SECOND, 48'000), number(actual.Get(), MF_MT_AUDIO_NUM_CHANNELS, 1),
            number(actual.Get(), MF_MT_AUDIO_BITS_PER_SAMPLE, 16), number(actual.Get(), MF_MT_AUDIO_BLOCK_ALIGNMENT, 2),
            number(actual.Get(), MF_MT_AUDIO_AVG_BYTES_PER_SECOND, 96'000)}) if (FAILED(check)) return check;
        const auto bound = (durationMs+100)*48;
        const auto ticks = [](std::uint64_t frames) { return frames/48'000*10'000'000 + frames%48'000*10'000'000/48'000; };
        LONGLONG previousTime = -1;
        for (;;) {
            DWORD stream = 0, flags = 0; LONGLONG timestamp = 0;
            ComPtr<IMFSample> sample;
            status = call([&] { return reader->ReadSample(0, 0, &stream, &flags, &timestamp, &sample); }); if (FAILED(status)) return status;
            if (stream || (flags & ~MF_SOURCE_READERF_ENDOFSTREAM) || timestamp < 0) return MF_E_INVALIDMEDIATYPE;
            if (sample) {
                DWORD length = 0; LONGLONG time = 0, span = 0;
                status = call([&] { return sample->GetTotalLength(&length); }); if (FAILED(status)) return status;
                if (!length || length%2 || length/2 > bound-evidence.decodedFrames) return MF_E_INVALIDMEDIATYPE;
                status = call([&] { return sample->GetSampleTime(&time); }); if (FAILED(status)) return status;
                status = call([&] { return sample->GetSampleDuration(&span); }); if (FAILED(status)) return status;
                const auto position = ticks(evidence.decodedFrames), sampleTicks = ticks(length/2);
                const auto distance = [](std::uint64_t a, std::uint64_t b) { return a > b ? a-b : b-a; };
                if (time != timestamp || time < previousTime || span <= 0 || distance(static_cast<std::uint64_t>(time), position) > 209 ||
                    distance(static_cast<std::uint64_t>(span), sampleTicks) > 209) return MF_E_INVALIDMEDIATYPE;
                previousTime = time;
                evidence.decodedFrames += length/2;
            } else if (!(flags & MF_SOURCE_READERF_ENDOFSTREAM)) return MF_E_INVALIDMEDIATYPE;
            if (flags & MF_SOURCE_READERF_ENDOFSTREAM) return close(ticks(evidence.decodedFrames)) ? S_OK : MF_E_INVALIDMEDIATYPE;
        }
}

CustodyFileResult<LocalRecordingPackage::PlaybackEvidence> decodeProtectedPlayback(
    IStream* input, std::uint64_t durationMs, const std::shared_ptr<const std::atomic<bool>>& cancellation) try {
    using Microsoft::WRL::ComPtr;
    constexpr auto maximum = static_cast<std::uint64_t>((std::numeric_limits<LONGLONG>::max)());
    if (!durationMs || durationMs > maximum/10'000-100) return {std::nullopt, CustodyFileError::invalidContent, 0};
    const auto call = [&](auto action) {
        if (cancellation->load()) return HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED);
        const HRESULT hr = action();
        return FAILED(hr) ? hr : cancellation->load() ? HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED) : hr;
    };
    PlaybackRuntime runtime;
    HRESULT hr = runtime.com;
    if (FAILED(hr)) return {std::nullopt, CustodyFileError::ioFailed, static_cast<std::uint32_t>(hr)};
    LocalRecordingPackage::PlaybackEvidence evidence;
    hr = call([&] { const auto start = MFStartup(MF_VERSION); runtime.started = SUCCEEDED(start); return start; });
    if (SUCCEEDED(hr)) hr = [&]() -> HRESULT {
        ComPtr<IMFByteStream> bytes;
        ComPtr<IMFSourceReader> reader;
        auto status = call([&] { return MFCreateMFByteStreamOnStream(input, &bytes); });
        if (SUCCEEDED(status)) status = call([&] { return MFCreateSourceReaderFromByteStream(bytes.Get(), nullptr, &reader); });
        if (SUCCEEDED(status)) status = decodePlayback(reader.Get(), durationMs, cancellation, evidence);
        return status;
    }(); // All MF readers/samples/types/byte streams release before shutdown.
    if (runtime.started) { const auto shutdown = MFShutdown(); runtime.started = false; if (SUCCEEDED(hr)) hr = shutdown; }
    if (FAILED(hr)) return {std::nullopt, hr == E_OUTOFMEMORY ? CustodyFileError::allocationFailed :
        hr == MF_E_INVALIDMEDIATYPE ? CustodyFileError::invalidContent : CustodyFileError::ioFailed,
        hr == HRESULT_FROM_WIN32(ERROR_OPERATION_ABORTED) ? ERROR_OPERATION_ABORTED : static_cast<std::uint32_t>(hr)};
    CoUninitialize(); runtime.com = E_FAIL;
    if (cancellation->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
    return {evidence, CustodyFileError::none, 0};
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_MEMORY}; }
} // namespace
LocalRecordingPackage::ProtectedInspection::ProtectedInspection(std::shared_ptr<const ProtectedCustodyPackagePair> pair,
    CustodyPackageReaders&& readers, CustodyBytes&& manifest, CustodyBytes&& session, const ProtectedEvidence& evidence,
    std::shared_ptr<const std::atomic<bool>> cancellation)
    : pair_(std::move(pair)), readers_(std::move(readers)), manifest_(std::move(manifest)),
      session_(std::move(session)), evidence_(evidence), cancellation_(std::move(cancellation)) {}
LocalRecordingPackage::ProtectedInspection::~ProtectedInspection() { SecureZeroMemory(&evidence_, sizeof(evidence_)); }

CustodyFileResult<std::shared_ptr<const LocalRecordingPackage::ProtectedInspection>> LocalRecordingPackage::inspectProtected(
    const std::filesystem::path& root, std::shared_ptr<const ProtectedCustodyPackagePair> pair,
    std::string_view expectedSession, std::shared_ptr<const std::atomic<bool>> cancellation) try {
    if (!pair || !cancellation || expectedSession.empty() || expectedSession.size() > manifestLimit)
        return {std::nullopt,CustodyFileError::invalidInput,0};
    if (pair->current().phase != CustodyPackagePhase::sealedNormal &&
        pair->current().phase != CustodyPackagePhase::sealedDegraded && pair->current().phase != CustodyPackagePhase::discardPending)
        return {std::nullopt,CustodyFileError::invalidInput,0};
    auto readers = openProtectedCustodyReaders(root,pair,cancellation);
    if (!readers.ok()) return {std::nullopt,readers.error,readers.nativeError};
    return inspectProtectedImpl(std::move(pair),std::move(*readers.value),expectedSession,std::move(cancellation));
} catch (const std::bad_alloc&) { return {std::nullopt,CustodyFileError::allocationFailed,ERROR_NOT_ENOUGH_MEMORY}; }

CustodyFileResult<std::shared_ptr<const LocalRecordingPackage::ProtectedInspection>> LocalRecordingPackage::inspectProtected(
    std::shared_ptr<ProtectedCustodyRecordingPackage> package, std::string_view expectedSession,
    std::shared_ptr<const std::atomic<bool>> cancellation) try {
    if (!package || !cancellation || expectedSession.empty() || expectedSession.size() > manifestLimit)
        return {std::nullopt,CustodyFileError::invalidInput,0};
    if (package->current().phase != CustodyPackagePhase::sealedNormal &&
        package->current().phase != CustodyPackagePhase::sealedDegraded && package->current().phase != CustodyPackagePhase::discardPending)
        return {std::nullopt,CustodyFileError::invalidInput,0};
    auto pair = package->readPair();
    if (!pair.ok()) return {std::nullopt,pair.error,pair.nativeError};
    auto readers = openProtectedCustodyReaders(package,*pair.value,cancellation);
    if (!readers.ok()) return {std::nullopt,readers.error,readers.nativeError};
    return inspectProtectedImpl(std::move(*pair.value),std::move(*readers.value),expectedSession,std::move(cancellation));
} catch (const std::bad_alloc&) { return {std::nullopt,CustodyFileError::allocationFailed,ERROR_NOT_ENOUGH_MEMORY}; }

CustodyFileResult<std::shared_ptr<const LocalRecordingPackage::ProtectedInspection>> LocalRecordingPackage::inspectProtectedImpl(
    std::shared_ptr<const ProtectedCustodyPackagePair> pair, CustodyPackageReaders&& heldReaders,
    std::string_view expectedSession, std::shared_ptr<const std::atomic<bool>> cancellation) try {
    using Proof = std::shared_ptr<const ProtectedInspection>;
    const auto reject = [](CustodyFileError error = CustodyFileError::invalidContent, std::uint32_t native = 0) -> CustodyFileResult<Proof> {
        return {std::nullopt, error, native};
    };
    if (!pair || !cancellation || expectedSession.empty() || expectedSession.size() > manifestLimit) return reject(CustodyFileError::invalidInput);
    if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    const auto& package = pair->current();
    if (package.phase != CustodyPackagePhase::sealedNormal && package.phase != CustodyPackagePhase::sealedDegraded &&
        package.phase != CustodyPackagePhase::discardPending)
        return reject(CustodyFileError::invalidInput);
    CustodyNativeJob job; // Through parser, codec, actual shutdown and result/error adoption.
    if (!job) return reject(CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA);
    CustodyBytes session(expectedSession.begin(),expectedSession.end()); // Own before native waits, not an untrusted manifest/directory guess.
    const std::string_view ownSession(reinterpret_cast<const char*>(session.data()),session.size());
    auto held = std::move(pair);
    auto readers = std::move(heldReaders);
    std::array<std::size_t,5> roles{}; roles.fill(package.refCount);
    for (std::size_t i = 0; i < package.refCount; ++i) roles[static_cast<unsigned>(package.refs[i].role)-1] = i;
    const auto ref = [&](CustodyRole role) -> const CustodyPackageReference* {
        const auto i = roles[static_cast<unsigned>(role)-1]; return i < package.refCount ? &package.refs[i] : nullptr;
    };
    const auto stream = [&](CustodyRole role) { return readers[held->selectedSlot()][roles[static_cast<unsigned>(role)-1]].stream.Get(); };
    const auto matches = [&](CustodyRole role, const ManifestArtifact& value) {
        const auto r = ref(role); return r && r->sealed && r->length && r->sha256 && value.bytes == *r->length && value.sha == *r->sha256;
    };
    ProtectedManifest manifest;
    CustodyBytes manifestBytes;
    if (const auto r = ref(CustodyRole::manifest)) {
        auto bytes = protectedMetadata(stream(CustodyRole::manifest),*r->length,cancellation);
        if (!bytes.ok()) return reject(bytes.error,bytes.nativeError);
        manifestBytes = std::move(*bytes.value);
        if (!RecordingJson({reinterpret_cast<const char*>(manifestBytes.data()),manifestBytes.size()},ownSession).manifest(manifest) ||
            manifest.reason != package.reason || manifest.degraded != (package.phase == CustodyPackagePhase::sealedDegraded) ||
            manifest.shortDiscarded != (package.phase == CustodyPackagePhase::discardPending)) return reject();
    } else if (package.phase != CustodyPackagePhase::sealedDegraded) return reject();
    ProtectedEvidence evidence = manifest.evidence;
    if (package.phase == CustodyPackagePhase::sealedDegraded) {
        const auto canonical = ref(CustodyRole::canonical), recovery = ref(CustodyRole::recovery);
        if (!canonical || !recovery || !canonical->sealed || !recovery->sealed) return reject();
        auto bytes = protectedMetadata(stream(CustodyRole::recovery),*recovery->length,cancellation);
        if (!bytes.ok()) return reject(bytes.error,bytes.nativeError);
        PrefixRecovery prefix;
        if (!RecordingJson({reinterpret_cast<const char*>(bytes.value->data()),bytes.value->size()},ownSession).recovery(prefix) ||
            prefix.reason != package.reason || !matches(CustodyRole::canonical,prefix.canonical) || !prefix.frames ||
            prefix.frames > prefix.canonical.bytes/1920) return reject();
        // The entire object SHA was checked by the retained group. Only these
        // proven complete cleaned frames are inspected; the tail is not audio.
        const auto prefixBytes = prefix.frames*1920; // Bounded above by checked logical length.
        evidence.trustedPrefixFrames = prefix.frames;
        evidence.durationMs = prefix.frames*10;
        if (!manifestBytes.empty() && manifest.evidence.durationMs != evidence.durationMs) return reject();
        CustodyBytes buffer(static_cast<std::size_t>(std::min<std::uint64_t>(prefixBytes,65536)));
        for (std::uint64_t at = 0; at < prefixBytes;) {
            const auto count = static_cast<ULONG>(std::min<std::uint64_t>(buffer.size(),prefixBytes-at));
            const auto hr = protectedRead(stream(CustodyRole::canonical),buffer.data(),count,cancellation);
            if (FAILED(hr)) return reject(nativeFileError(hr),nativeCode(hr));
            for (ULONG offset = 0; offset < count; offset += 4) {
                float value = 0; static_assert(sizeof(value) == 4);
                std::memcpy(&value,buffer.data()+offset,4); if (!std::isfinite(value)) return reject();
            }
            at += count;
        }
        evidence.integrity = PackageIntegrity::degraded;
    } else if (package.phase == CustodyPackagePhase::discardPending) {
        if (!package.shortRecordingDiscarded || !evidence.durationMs || evidence.durationMs >= kShortRecordingMinimumSeconds*1000)
            return reject();
        evidence.integrity = PackageIntegrity::discardPending;
    } else evidence.integrity = PackageIntegrity::valid;
    if (!evidence.durationMs) return reject();
    if (!manifestBytes.empty()) {
        if (manifest.hasArtifacts) {
            if (!matches(CustodyRole::media,manifest.artifacts[0]) || !matches(CustodyRole::playback,manifest.artifacts[1])) return reject();
        } else if (ref(CustodyRole::media) || ref(CustodyRole::playback)) return reject();
    }
    if (const auto media = ref(CustodyRole::media)) {
        std::array<unsigned char,44> header{};
        const auto hr = protectedRead(stream(CustodyRole::media),header.data(),static_cast<ULONG>(header.size()),cancellation);
        if (FAILED(hr)) return reject(nativeFileError(hr),nativeCode(hr));
        if (!canonicalWavHeader(header,*media->length,evidence.durationMs)) return reject();
    }
    if (ref(CustodyRole::playback)) {
        const auto playback = decodeProtectedPlayback(stream(CustodyRole::playback),evidence.durationMs,cancellation);
        if (!playback.ok()) return reject(playback.error,playback.nativeError);
        evidence.playback = *playback.value;
    }
    // Restore cursors and observe the group's shared first fault before proof.
    // No release/reopen between hash, parser, format and decoder validation.
    for (unsigned slot = 0; slot < 2; ++slot) for (std::size_t i = 0; i < held->slots()[slot].refCount; ++i) {
        if (cancellation->load()) return reject(CustodyFileError::ioFailed,ERROR_OPERATION_ABORTED);
        LARGE_INTEGER zero{}; const auto hr = readers[slot][i].stream->Seek(zero,STREAM_SEEK_SET,nullptr);
        if (FAILED(hr)) return reject(nativeFileError(hr),nativeCode(hr));
        if (cancellation->load()) return reject(CustodyFileError::ioFailed,ERROR_OPERATION_ABORTED);
    }
    CustodyAllocator<ProtectedInspection> allocator;
    auto* raw = allocator.allocate(1);
    try { new (raw) ProtectedInspection(std::move(held),std::move(readers),std::move(manifestBytes),std::move(session),evidence,cancellation); }
    catch (...) { allocator.deallocate(raw,1); throw; }
    Proof proof{raw,[](const ProtectedInspection* p) {
        p->~ProtectedInspection(); CustodyAllocator<ProtectedInspection>{}.deallocate(const_cast<ProtectedInspection*>(p),1);
    },allocator};
    if (cancellation->load()) return reject(CustodyFileError::ioFailed,ERROR_OPERATION_ABORTED);
    return {std::move(proof),CustodyFileError::none,0};
} catch (const std::bad_alloc&) { return {std::nullopt,CustodyFileError::allocationFailed,ERROR_NOT_ENOUGH_MEMORY}; }

CustodyFileResult<LocalRecordingPackage::PlaybackEvidence> LocalRecordingPackage::readProtectedPlayback(
    std::shared_ptr<const ProtectedPackedCustodyTree> proof, std::uint64_t durationMs,
    std::shared_ptr<const std::atomic<bool>> cancellation) try {
    if (!proof || !cancellation || !durationMs) return {std::nullopt,CustodyFileError::invalidInput,0};
    CustodyNativeJob job;
    if (!job) return {std::nullopt,CustodyFileError::allocationFailed,ERROR_NOT_ENOUGH_QUOTA};
    auto reader = openProtectedCustodyReader(std::move(proof),cancellation);
    if (!reader.ok()) return {std::nullopt,reader.error,reader.nativeError};
    return decodeProtectedPlayback(reader.value->stream.Get(),durationMs,cancellation);
} catch (const std::bad_alloc&) { return {std::nullopt,CustodyFileError::allocationFailed,ERROR_NOT_ENOUGH_MEMORY}; }

CustodyFileResult<LocalRecordingPackage::PlaybackEvidence> LocalRecordingPackage::readProtectedPlayback(
    const std::filesystem::path& root, std::shared_ptr<const ProtectedCustodyPackagePair> pair,
    std::uint64_t durationMs, std::shared_ptr<const std::atomic<bool>> cancellation) try {
    constexpr auto maximum = static_cast<std::uint64_t>((std::numeric_limits<LONGLONG>::max)());
    if (!pair || !cancellation || !durationMs || durationMs > maximum / 10'000 - 100)
        return {std::nullopt, CustodyFileError::invalidInput, 0};
    if (cancellation->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
    const auto& package = pair->current();
    if (package.phase != CustodyPackagePhase::sealedNormal && package.phase != CustodyPackagePhase::sealedDegraded)
        return {std::nullopt, CustodyFileError::invalidInput, 0};
    std::size_t playback = package.refCount;
    for (std::size_t i = 0; i < package.refCount; ++i)
        if (package.refs[i].role == CustodyRole::playback && package.refs[i].sealed) playback = i;
    if (playback == package.refCount) return {std::nullopt, CustodyFileError::invalidInput, 0};
    std::optional<CustodyNativeJob> job; // Declared first: streams/pair release before admission.
    auto held = std::move(pair); // Release before the admitted decoder job ends.
    auto readers = openProtectedCustodyReaders(root, held, cancellation);
    if (!readers.ok()) return {std::nullopt, readers.error, readers.nativeError};
    // Group verification admits its own IO; decoder admission starts only now.
    job.emplace();
    if (!*job) return {std::nullopt, CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA};
    auto decoded = decodeProtectedPlayback((*readers.value)[held->selectedSlot()][playback].stream.Get(), durationMs, cancellation);
    if (!decoded.ok()) return decoded;
    readers.value.reset(); held.reset();
    if (cancellation->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
    return decoded;
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_MEMORY}; }
#endif

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
    // The wall-clock bounds stay optional so a package written before they
    // existed is still readable and simply carries no time to report.
    static const std::regex shape(
        R"manifest(\{"schema_version":"local-recording-manifest\.v5","canonical_mix_profile":"canonical-mix\.v1","source_kind":"initial_mixed_recording","media_scribe_source_mode":"single_wav_v1"(?:,"capture_status":"(normal|degraded)","capture_reason_code":"([a-z_]+)")?,"duration_ms":([0-9]+)(?:,"started_at_ms":([0-9]+),"stopped_at_ms":([0-9]+),"display_timezone_offset_minutes":(-?[0-9]+))?,"artifacts":\{"media":\{"bytes":([0-9]+),"sha256":"([0-9a-f]{64})"\},"playback":\{"bytes":([0-9]+),"sha256":"([0-9a-f]{64})"\}\}\})manifest");
    std::smatch fields;
    std::uint64_t durationMs = 0, wavBytes = 0, playbackBytes = 0;
    if (!std::regex_match(json, fields, shape) ||
        !parseNumber(fields[3].str(), durationMs) || durationMs == 0 ||
        !parseNumber(fields[7].str(), wavBytes) ||
        !parseNumber(fields[9].str(), playbackBytes)) {
        result.integrity = PackageIntegrity::malformed;
        return result;
    }
    // An impossible bound is dropped instead of trusted; the duration stays
    // authoritative for the package itself, and no time is reported.
    std::uint64_t startedAtMs = 0, stoppedAtMs = 0;
    int displayOffsetMinutes = 0;
    if (fields[4].matched && fields[5].matched && parseNumber(fields[4].str(), startedAtMs) &&
        parseNumber(fields[5].str(), stoppedAtMs) && startedAtMs != 0 && stoppedAtMs >= startedAtMs) {
        const auto offset = std::strtol(fields[6].str().c_str(), nullptr, 10);
        if (offset < -14 * 60 || offset > 14 * 60) {
            startedAtMs = 0;
            stoppedAtMs = 0;
        } else {
            displayOffsetMinutes = static_cast<int>(offset);
        }
    } else {
        startedAtMs = 0;
        stoppedAtMs = 0;
    }
    result.startedAtMs = startedAtMs;
    result.stoppedAtMs = stoppedAtMs;
    result.displayTimezoneOffsetMinutes = displayOffsetMinutes;
    const bool mediaValid = matchesArtifact(directory, wav, wavBytes, fields[8].str()) &&
        canonicalWav(wav, wavBytes, durationMs);
    const bool playbackMatches = matchesArtifact(directory, playback, playbackBytes, fields[10].str());
    const bool playbackValid = playbackMatches && canonicalPlayback(playback, durationMs);
    const bool degraded = retained || fields[1].str() == "degraded" ||
        (fields[2].matched && fields[2].str() != "none");
    result.integrity = mediaValid && playbackMatches && (degraded || playbackValid)
        ? (degraded ? PackageIntegrity::degraded : PackageIntegrity::valid)
        : PackageIntegrity::malformed;
    // Playback eligibility is independent of upload eligibility. Require an
    // explicit custody root for UI file access; old metadata-only callers keep
    // their signature and cannot accidentally authorize opening an arbitrary path.
    result.playbackAvailable = !custodyRoot.empty() && playbackValid;
    if (result.integrity == PackageIntegrity::valid) result.trackBytes = {size, wavBytes, playbackBytes};
    if (mediaValid || result.playbackAvailable) result.durationMs = durationMs;
    return result;
}

} // namespace graf::windows
