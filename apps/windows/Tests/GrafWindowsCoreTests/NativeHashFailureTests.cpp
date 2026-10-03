#include <windows.h>
#include <bcrypt.h>

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <chrono>
#include <fstream>
#include <functional>
#include <sstream>
#include <utility>

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

int main() {
    using namespace graf::windows;
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
    V5LocalRecordingWriter writer(package, [](const auto& path, const auto&, std::uint64_t) {
        std::ofstream output(path, std::ios::binary); output << "synthetic-playback"; return output.good();
    });
    CanonicalAudioFrame frame; frame.mixed.fill(0.25F);
    assert(writer.append(frame) && writer.finalize().normalPackage());
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
    std::filesystem::remove_all(root);
}
