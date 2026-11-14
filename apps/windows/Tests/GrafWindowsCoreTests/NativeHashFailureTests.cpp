#include <windows.h>
#include <bcrypt.h>

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <algorithm>
#include <cassert>
#include <chrono>
#include <fstream>
#include <functional>
#include <iterator>
#include <iostream>
#include <sstream>
#include <utility>
#include <objidl.h>
#include <mfapi.h>
#include <mfidl.h>
#include <mfreadwrite.h>
#include <wrl/client.h>

// Faults are local to this executable, never production settings or fallbacks.
namespace {
enum class HashFault { none, create, update, finish };
HashFault fault = HashFault::none;
unsigned faultOrdinal = 1, creates = 0, updates = 0, finishes = 0, destroys = 0;
unsigned algorithmOpens = 0, algorithmCloses = 0, properties = 0;
std::function<void()> duringUpdate;
constexpr NTSTATUS failed = static_cast<NTSTATUS>(0xC0000001UL);

NTSTATUS WINAPI testCreate(BCRYPT_ALG_HANDLE algorithm, BCRYPT_HASH_HANDLE* hash,
    PUCHAR object, ULONG objectBytes, PUCHAR secret, ULONG secretBytes, ULONG flags) {
    ++creates;
    assert(algorithm == BCRYPT_SHA256_ALG_HANDLE);
    assert(!object && !objectBytes && !secret && !secretBytes && !flags);
    if (fault == HashFault::create && creates == faultOrdinal) return failed;
    return BCryptCreateHash(algorithm, hash, object, objectBytes, secret, secretBytes, flags);
}
NTSTATUS WINAPI testUpdate(BCRYPT_HASH_HANDLE hash, PUCHAR bytes, ULONG size, ULONG flags) {
    ++updates;
    if (fault == HashFault::update && updates == faultOrdinal) return failed;
    if (duringUpdate) std::exchange(duringUpdate, {})();
    return BCryptHashData(hash, bytes, size, flags);
}
NTSTATUS WINAPI testFinish(BCRYPT_HASH_HANDLE hash, PUCHAR bytes, ULONG size, ULONG flags) {
    ++finishes;
    if (fault == HashFault::finish) return failed;
    return BCryptFinishHash(hash, bytes, size, flags);
}
void inject(HashFault selected, unsigned ordinal = 1) {
    assert(algorithmOpens == 0 && algorithmCloses == 0 && properties == 0);
    fault = selected;
    faultOrdinal = ordinal;
    creates = updates = finishes = destroys = 0;
}
} // namespace

#define BCryptOpenAlgorithmProvider(...) (++algorithmOpens, BCryptOpenAlgorithmProvider(__VA_ARGS__))
#define BCryptCloseAlgorithmProvider(...) (++algorithmCloses, BCryptCloseAlgorithmProvider(__VA_ARGS__))
#define BCryptSetProperty(...) (++properties, BCryptSetProperty(__VA_ARGS__))
#define BCryptDestroyHash(...) (++destroys, BCryptDestroyHash(__VA_ARGS__))
#define BCryptCreateHash testCreate
#define BCryptHashData testUpdate
#define BCryptFinishHash testFinish
#include "../../RecApp/Storage/Sha256.cpp"
#undef BCryptOpenAlgorithmProvider
#undef BCryptCloseAlgorithmProvider
#undef BCryptSetProperty
#undef BCryptDestroyHash
#undef BCryptCreateHash
#undef BCryptHashData
#undef BCryptFinishHash

#include "../../RecApp/Recording/LocalRecordingPackage.h"
#include "../../RecApp/Upload/DesktopHttpTransport.h"
#include "../../RecApp/Storage/ProtectedCustodyCodec.h"
#include "../../RecApp/Storage/ProtectedPackedCustodyCodec.h"
#include "../../RecApp/Storage/ProtectedCustodyPrimitives.h"
#include "../GeneratedRecordingFixtures.h"

namespace {
class HashInput final : public IStream {
public:
    std::string bytes;
    std::function<void()> afterRead;
    HRESULT readResult = S_OK, seekResult = S_OK;
    bool shortRead = false, invalidCount = false;
    unsigned reads = 0;
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID, void** p) override { if (!p) return E_POINTER; *p = this; AddRef(); return S_OK; }
    ULONG STDMETHODCALLTYPE AddRef() override { return ++refs_; }
    ULONG STDMETHODCALLTYPE Release() override { const auto n = --refs_; if (!n) delete this; return n; }
    HRESULT STDMETHODCALLTYPE Read(void* p, ULONG n, ULONG* got) override {
        ++reads;
        const auto count = static_cast<ULONG>(std::min<std::size_t>(n, bytes.size()-cursor_));
        std::memcpy(p, bytes.data()+cursor_, count); cursor_ += count;
        *got = invalidCount ? n+1 : shortRead && count ? count-1 : count;
        if (afterRead) std::exchange(afterRead, {})();
        return readResult != S_OK ? readResult : count == n ? S_OK : S_FALSE;
    }
    HRESULT STDMETHODCALLTYPE Seek(LARGE_INTEGER, DWORD, ULARGE_INTEGER* p) override { if (p) p->QuadPart = cursor_; return seekResult; }
    HRESULT STDMETHODCALLTYPE Write(const void*, ULONG, ULONG*) override { return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE SetSize(ULARGE_INTEGER) override { return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE CopyTo(IStream*, ULARGE_INTEGER, ULARGE_INTEGER*, ULARGE_INTEGER*) override { return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE Commit(DWORD) override { return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE Revert() override { return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE LockRegion(ULARGE_INTEGER, ULARGE_INTEGER, DWORD) override { return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE UnlockRegion(ULARGE_INTEGER, ULARGE_INTEGER, DWORD) override { return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE Stat(STATSTG*, DWORD) override { return E_NOTIMPL; }
    HRESULT STDMETHODCALLTYPE Clone(IStream**) override { return E_NOTIMPL; }
private:
    ULONG refs_ = 1;
    std::size_t cursor_ = 0;
};
void protectedHash() {
    using namespace graf::windows;
    auto cancelled = std::make_shared<std::atomic<bool>>(false);
    const auto input = [](std::size_t count) {
        Microsoft::WRL::ComPtr<HashInput> stream; stream.Attach(new HashInput);
        stream->bytes.assign(count, 'x'); return stream;
    };
    const auto before = CustodyOwnedMemory::usedBytes();
    for (std::size_t count : {0U, 1U, 65536U, 65537U}) {
        inject(HashFault::none); auto stream = input(count);
        const auto result = sha256ProtectedStream(stream.Get(), count, cancelled);
        assert(result.ok() && hexDigest(*result.value) == sha256(stream->bytes));
        assert(CustodyOwnedMemory::usedBytes() == before);
    }
    for (const auto selected : {HashFault::create, HashFault::update, HashFault::finish}) {
        for (unsigned ordinal : {1U, 2U}) {
            if (ordinal == 2 && selected != HashFault::update) continue;
            inject(selected, ordinal); auto stream = input(65537);
            const auto result = sha256ProtectedStream(stream.Get(), 65537, cancelled);
            assert(!result.ok() && result.error == CustodyFileError::hashFailed && result.nativeError == static_cast<std::uint32_t>(failed));
            assert(creates == 1 && destroys == (selected == HashFault::create ? 0U : 1U));
        }
    }
    inject(HashFault::none);
    for (unsigned cut = 0; cut < 8; ++cut) {
        auto stream = input(cut == 0 ? 2 : 3);
        if (cut == 1) stream->bytes += 'x';
        if (cut == 2) stream->readResult = STG_E_READFAULT;
        if (cut == 3) stream->shortRead = true;
        if (cut == 4) stream->invalidCount = true;
        if (cut == 5) stream->readResult = 2; // Unknown successful HRESULT is not EOF.
        if (cut == 6) stream->seekResult = STG_E_SEEKERROR;
        if (cut == 7) stream->afterRead = [&] { cancelled->store(true); };
        const auto result = sha256ProtectedStream(stream.Get(), 3, cancelled);
        assert(!result.ok());
        if (cut == 2 || cut == 6) assert(result.error == CustodyFileError::ioFailed && result.nativeError == static_cast<std::uint32_t>(cut == 2 ? STG_E_READFAULT : STG_E_SEEKERROR));
        if (cut == 7) assert(result.nativeError == ERROR_OPERATION_ABORTED);
        cancelled->store(false);
    }
    auto stream = input(3);
    assert(sha256ProtectedStream(nullptr, 3, cancelled).error == CustodyFileError::invalidInput);
    assert(sha256ProtectedStream(stream.Get(), 3, {}).error == CustodyFileError::invalidInput);
    {
        std::array<CustodyNativeJob, 4> jobs;
        assert(sha256ProtectedStream(stream.Get(), 3, cancelled).error == CustodyFileError::allocationFailed && stream->reads == 0);
    }
    {
        CustodyBytes pressure(0); pressure.reserve(CustodyOwnedMemory::limit-CustodyOwnedMemory::usedBytes());
        assert(sha256ProtectedStream(stream.Get(), 3, cancelled).error == CustodyFileError::allocationFailed && stream->reads == 0);
    }
    inject(HashFault::none);
    duringUpdate = [&] { cancelled->store(true); };
    assert(sha256ProtectedStream(stream.Get(), 3, cancelled).nativeError == ERROR_OPERATION_ABORTED);
    cancelled->store(false); assert(CustodyOwnedMemory::usedBytes() == before);
    inject(HashFault::none);
    auto retained = input(3); auto* raw = retained.Get();
    retained->afterRead = [&] { retained.Reset(); };
    assert(sha256ProtectedStream(raw, 3, cancelled).ok() && !retained); // Native Read still owns COM lifetime.
}
} // namespace

int main() {
    using namespace graf::windows;
    protectedHash(); inject(HashFault::none);
    constexpr auto abc = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";
    const std::string bytes(64 * 1024 + 1, 'x');
    const auto root = std::filesystem::temp_directory_path() /
        ("graf-hash-fault-" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    std::filesystem::create_directory(root);
    const auto file = root / "synthetic.bin";
    { std::ofstream output(file, std::ios::binary); output << bytes; assert(output.good()); }

    // Baselines really delegate native CNG, not the portable memory route.
    std::istringstream baseline("abc");
    assert(sha256Stream(baseline) == abc && creates == 1 && updates == 1 && finishes == 1 && destroys == 1);
    for (const std::size_t size : {std::size_t(0), std::size_t(64 * 1024), bytes.size()}) {
        inject(HashFault::none);
        const std::string binary(size, '\0');
        std::istringstream input(binary);
        assert(sha256Stream(input) == sha256(binary));
        assert(creates == 1 && destroys == 1 && finishes == 1);
        assert(updates == (size + 64 * 1024 - 1) / (64 * 1024));
    }
    inject(HashFault::none);
    assert(sha256File(file) == sha256(bytes) && creates == 1 && destroys == 1 && finishes == 1);
    // Nested streams overlap object lifetimes; neither may reuse the other's state.
    inject(HashFault::none);
    duringUpdate = [&] {
        std::istringstream nested("abc");
        assert(sha256Stream(nested) == abc && destroys == 1);
    };
    std::istringstream outer(bytes);
    assert(sha256Stream(outer) == sha256(bytes));
    assert(creates == 2 && destroys == 2 && finishes == 2 && !duringUpdate);
    for (const auto selected : {HashFault::create, HashFault::update, HashFault::finish}) {
        for (const unsigned ordinal : {1U, 2U}) {
            if (ordinal == 2 && selected != HashFault::update) continue;
            inject(selected, ordinal);
            assert(sha256("abc") == abc && creates == 0 && updates == 0);
            std::istringstream input(bytes);
            assert(sha256Stream(input).empty() && creates == 1);
            assert(destroys == (selected == HashFault::create ? 0U : 1U));
            if (selected == HashFault::create) assert(updates == 0 && finishes == 0);
            if (selected == HashFault::update) assert(updates == ordinal);
            inject(selected, ordinal);
            assert(sha256File(file).empty() && creates == 1);
            assert(destroys == (selected == HashFault::create ? 0U : 1U));
            // An identity calculation stays independent after native failure too.
            const auto attempts = creates;
            assert(sha256("abc") == abc && creates == attempts);
        }
    }

    inject(HashFault::none);
    const CustodyContext custody{{}, {}, CustodyRole::canonical};
    const CustodyBytes payload(bytes.begin(), bytes.end());
    const auto block = ProtectedCustodyCodec::sealBlock(custody, 0, 1, payload);
    assert(block.ok());
    const CustodyIndex index{1, payload.size(), {{1, static_cast<std::uint32_t>(block.value->size()), 0}}};
    const auto sealedIndex = ProtectedCustodyCodec::sealIndex(custody, 0, index); assert(sealedIndex.ok());
    for (const auto selected : {HashFault::create, HashFault::update, HashFault::finish}) {
        inject(selected);
        assert(ProtectedCustodyCodec::sealBlock(custody, 0, 1, payload).error == CustodyCodecError::hashFailed);
        inject(selected);
        assert(ProtectedCustodyCodec::openBlock(custody, 0, 1, static_cast<std::uint32_t>(payload.size()),
                                                *block.value).error == CustodyCodecError::hashFailed);
        inject(selected);
        assert(ProtectedCustodyCodec::sealIndex(custody, 0, index).error == CustodyCodecError::hashFailed);
        inject(selected);
        assert(ProtectedCustodyCodec::openIndex(custody, 0, *sealedIndex.value).error == CustodyCodecError::hashFailed);
    }
    inject(HashFault::update, 2);
    assert(ProtectedCustodyCodec::sealBlock(custody, 0, 1, payload).error == CustodyCodecError::hashFailed);
    inject(HashFault::none);
    const PackedCustodyContext packed{custody, {}};
    for (const auto kind : {PackedRecordKind::data, PackedRecordKind::nodeL0,
                            PackedRecordKind::nodeL1, PackedRecordKind::nodeL2, PackedRecordKind::head}) {
        const PackedRecordAddress address{kind, kind == PackedRecordKind::head ? 128ULL : 32896ULL, 0, 1,
            kind == PackedRecordKind::data ? 3U : (kind == PackedRecordKind::head ? 128U : 4096U)};
        const CustodyBytes body(address.bodyBytes, std::uint8_t{42});
        const auto cipher = ProtectedPackedCustodyCodec::seal(packed, address, body); assert(cipher.ok());
        const auto cipherHash = custody_detail::digest(cipher.value->data(), cipher.value->size()); assert(cipherHash);
        const PackedReference ref{kind, static_cast<std::uint32_t>(cipher.value->size()), address.offset, 1,
            kind == PackedRecordKind::data ? 3U : 0U, *cipherHash};
        for (const auto selected : {HashFault::create, HashFault::update, HashFault::finish}) {
            inject(selected);
            assert(ProtectedPackedCustodyCodec::seal(packed, address, body).error == CustodyCodecError::hashFailed);
            inject(selected);
            const auto opened = kind == PackedRecordKind::head
                ? ProtectedPackedCustodyCodec::openHead(packed, 0, *cipher.value)
                : ProtectedPackedCustodyCodec::openReferenced(packed, 0, ref, *cipher.value);
            assert(opened.error == CustodyCodecError::hashFailed);
        }
        if (kind != PackedRecordKind::head) {
            inject(HashFault::create, 2); // Envelope hash succeeds; typed plaintext hash fails.
            assert(ProtectedPackedCustodyCodec::openReferenced(packed, 0, ref, *cipher.value).error == CustodyCodecError::hashFailed);
        }
        inject(HashFault::none);
    }
    const auto package = root / "package";
    const auto legacy = testing::makeGeneratedLegacyPackage(package, 100);
    assert(legacy.durationMs == 1000);
    assert(LocalRecordingPackage::inspect(package).integrity == PackageIntegrity::valid);
    UploadCustodyItem item;
    item.localRecordingId = "synthetic-recording";
    item.directoryId = "synthetic-directory";
    item.sessionId = "synthetic-session";
    item.packageDirectory = package;
    item.ownerUserId = "11111111-1111-4111-8111-111111111111";
    item.ownerWorkspaceId = "22222222-2222-4222-8222-222222222222";
    DesktopHttpConfig config;
    config.sessionToken = "synthetic-token-not-a-credential";
    config.workspaceId = item.ownerWorkspaceId;
    config.confirmedIdentity = DesktopAccountIdentity{item.ownerUserId, item.ownerWorkspaceId};
    unsigned sends = 0;
    const DesktopHttpTransport::UploadSend send = [&](const auto&, const auto&) {
        ++sends;
        return DesktopHttpTransport::UploadResponse{503, ""};
    };
    inject(HashFault::none);
    assert(DesktopHttpTransport(config).upload(item, send).status == DesktopTransportStatus::retryableFailure);
    assert(sends == 1 && creates == 3 && destroys == 3); // media, playback, manifest before the first request

    sends = 0;
    inject(HashFault::create, 3); // Only manifest hashing fails; media/playback remain valid.
    assert(DesktopHttpTransport(config).upload(item, send).status == DesktopTransportStatus::invalidPackage);
    assert(creates == 3 && destroys == 2 && sends == 0);
    inject(HashFault::none);
    assert(sha256File(file) == sha256(bytes)); // failures did not poison the next operation
    assert(algorithmOpens == 0 && algorithmCloses == 0 && properties == 0);

    // Preserve the real writer's container, sample tables, duration and byte
    // count. A matching digest must not make undecodable AAC a normal package.
    const auto playback = package / "meeting-review.m4a";
    const auto manifest = package / "manifest.json";
    const auto decodeSynthetic = [&playback] {
        const auto com = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
        assert(SUCCEEDED(com));
        assert(MFStartup(MF_VERSION) == S_OK);
        bool complete = false;
        std::uint64_t frames = 0;
        {
            Microsoft::WRL::ComPtr<IMFSourceReader> reader;
            Microsoft::WRL::ComPtr<IMFMediaType> pcm;
            assert(MFCreateSourceReaderFromURL(playback.c_str(), nullptr, &reader) == S_OK);
            assert(MFCreateMediaType(&pcm) == S_OK);
            assert(pcm->SetGUID(MF_MT_MAJOR_TYPE, MFMediaType_Audio) == S_OK);
            assert(pcm->SetGUID(MF_MT_SUBTYPE, MFAudioFormat_PCM) == S_OK);
            assert(reader->SetCurrentMediaType(0, nullptr, pcm.Get()) == S_OK);
            while (frames <= 52'800) { // This isolated fixture is exactly 1 s, plus the existing 100 ms tolerance.
                DWORD stream = 0, flags = 0;
                LONGLONG timestamp = 0;
                Microsoft::WRL::ComPtr<IMFSample> sample;
                if (FAILED(reader->ReadSample(0, 0, &stream, &flags, &timestamp, &sample)) ||
                    stream != 0 || (flags & ~MF_SOURCE_READERF_ENDOFSTREAM)) break;
                if (sample) {
                    DWORD bytes = 0;
                    if (FAILED(sample->GetTotalLength(&bytes)) || bytes == 0 || bytes % 2) break;
                    frames += bytes / 2;
                }
                if (flags & MF_SOURCE_READERF_ENDOFSTREAM) { complete = true; break; }
                if (!sample) break;
            }
        }
        assert(MFShutdown() == S_OK);
        CoUninitialize();
        return std::pair{complete, frames};
    };
    const auto decodedOriginal = decodeSynthetic();
    assert(decodedOriginal.first && decodedOriginal.second > 0 && decodedOriginal.second <= 52'800);
    const auto readFixture = [](const std::filesystem::path& path) {
        std::ifstream input(path, std::ios::binary);
        assert(input);
        return std::string(std::istreambuf_iterator<char>(input), {});
    };
    auto audio = readFixture(playback);
    auto metadata = readFixture(manifest);
    const auto originalHash = sha256(audio);
    const auto digestPosition = metadata.find(originalHash);
    assert(digestPosition != std::string::npos && metadata.find(originalHash, digestPosition + 1) == std::string::npos);
    const auto bigEndian = [&audio](std::size_t at, std::size_t count) {
        assert(at <= audio.size() && count <= audio.size() - at);
        std::uint64_t value = 0;
        for (std::size_t i = 0; i < count; ++i) value = (value << 8) | static_cast<unsigned char>(audio[at + i]);
        return value;
    };
    bool changed = false;
    for (std::size_t at = 0; at < audio.size();) {
        assert(audio.size() - at >= 8);
        auto size = bigEndian(at, 4);
        const auto header = size == 1 ? std::size_t(16) : std::size_t(8);
        if (size == 1) size = bigEndian(at + 8, 8);
        if (size == 0) size = audio.size() - at;
        assert(size >= header && size <= audio.size() - at);
        if (audio.compare(at + 4, 4, "mdat") == 0) {
            assert(size > header);
            std::fill(audio.begin() + static_cast<std::ptrdiff_t>(at + header),
                audio.begin() + static_cast<std::ptrdiff_t>(at + size), static_cast<char>(0xff));
            changed = true;
        }
        at += static_cast<std::size_t>(size);
    }
    assert(changed && sha256(audio) != originalHash);
    metadata.replace(digestPosition, originalHash.size(), sha256(audio));
    { std::ofstream output(playback, std::ios::binary | std::ios::trunc); output.write(audio.data(), static_cast<std::streamsize>(audio.size())); assert(output.good()); }
    { std::ofstream output(manifest, std::ios::binary | std::ios::trunc); output << metadata; assert(output.good()); }
    inject(HashFault::none);
    const auto decodedCorruption = decodeSynthetic();
    assert(!decodedCorruption.first || decodedCorruption.second == 0);
    const auto malformed = LocalRecordingPackage::inspect(package, root);
    const auto withoutRoot = LocalRecordingPackage::inspect(package);
    sends = 0;
    const auto uploadStatus = DesktopHttpTransport(config).upload(item, send).status;
    std::cout << "AAC_MDAT_COUNTEREXAMPLE original_frames=" << decodedOriginal.second
        << " corrupt_decode_complete=" << decodedCorruption.first << " corrupt_frames=" << decodedCorruption.second
        << " explicit_root_normal=" << (malformed.integrity == PackageIntegrity::valid)
        << " explicit_root_playback=" << malformed.playbackAvailable
        << " default_root_normal=" << (withoutRoot.integrity == PackageIntegrity::valid)
        << " invalid_package=" << (uploadStatus == DesktopTransportStatus::invalidPackage)
        << " synthetic_sends=" << sends << std::endl;
    assert(malformed.integrity == PackageIntegrity::malformed && !malformed.playbackAvailable);
    assert((malformed.trackBytes == std::array<std::uint64_t, 3>{}));
    assert(withoutRoot.integrity == PackageIntegrity::malformed);
    assert(uploadStatus == DesktopTransportStatus::invalidPackage);
    assert(sends == 0);
    std::filesystem::remove_all(root);
}
