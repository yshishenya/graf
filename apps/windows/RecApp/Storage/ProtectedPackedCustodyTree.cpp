#include "ProtectedPackedCustodyTree.h"
#include "ProtectedCustodyPrimitives.h"
#include <algorithm>

namespace graf::windows {
namespace {
template<class T> CustodyFileResult<T> failed(CustodyFileError e, std::uint32_t native = 0) {
    return {std::nullopt, e, native};
}
template<class T> CustodyFileResult<T> passed(T value) { return {std::move(value), CustodyFileError::none, 0}; }
}
PackedPlainRead::~PackedPlainRead() { custody_detail::WipeBytes wipe{bytes}; }
ProtectedPackedCustodyTree::ProtectedPackedCustodyTree(CustodyPin&& pin, std::shared_ptr<ProtectedPackedCustodyOwner> owner,
    const std::array<PackedRootDescriptor, 2>& heads, std::uint32_t selected) noexcept
    : pin_(std::move(pin)), owner_(std::move(owner)), heads_(heads), selected_(selected) {}

CustodyFileResult<bool> ProtectedPackedCustodyTree::walk(Guard& guard, const PackedRootDescriptor& descriptor,
    const PackedReference& reference, std::uint64_t base) {
    if (reference.kind == PackedRecordKind::empty || reference.kind == PackedRecordKind::zero) return passed(true);
    auto bytes = guard.read(reference.offset, reference.envelopeBytes);
    if (!bytes.ok()) return guard.reject(bytes.error, bytes.nativeError);
    auto decoded = ProtectedPackedCustodyCodec::openReferenced(guard.context(), base, reference, *bytes.value);
    if (!decoded.ok()) return guard.reject(codecFileError(decoded.error), decoded.nativeError);
    custody_detail::WipeBytes wipe{decoded.value->body};
    CustodyBytes(0).swap(*bytes.value); // Only three charged NODE bodies and one DATA at maximum depth.
    if (reference.kind == PackedRecordKind::data)
        return decoded.value->body.size() == reference.payloadBytes ? passed(true) : guard.reject(CustodyFileError::invalidContent);
    if (decoded.value->body.size() != 4096) return guard.reject(CustodyFileError::invalidContent);
    const auto stride = reference.kind == PackedRecordKind::nodeL2 ? 4096ULL : reference.kind == PackedRecordKind::nodeL1 ? 64ULL : 1ULL;
    for (std::uint32_t i = 0; i < 64; ++i) {
        auto child = ProtectedPackedCustodyFormat::decodeChild(decoded.value->body.data()+64*i, 64, descriptor, reference, base, i);
        if (!child) return guard.reject(CustodyFileError::invalidContent);
        auto result = walk(guard, descriptor, *child, base+i*stride);
        if (!result.ok()) return result;
    }
    return passed(true);
}

CustodyFileResult<std::shared_ptr<const ProtectedPackedCustodyTree>> ProtectedPackedCustodyTree::verify(
    std::shared_ptr<ProtectedPackedCustodyOwner> owner) {
    using Proof = std::shared_ptr<const ProtectedPackedCustodyTree>;
    if (!owner) return failed<Proof>(CustodyFileError::invalidInput);
    Guard guard(owner);
    try {
        CustodyPin pin;
        if (!pin) return failed<Proof>(CustodyFileError::allocationFailed);
        const auto size = guard.size();
        if (!size.ok()) return failed<Proof>(size.error, size.nativeError);
        auto prefix = guard.read(0, 128);
        if (!prefix.ok()) return failed<Proof>(prefix.error, prefix.nativeError);
        if (!ProtectedPackedCustodyFormat::prefixMatches(prefix.value->data(), prefix.value->size(), guard.context())) {
            const auto fault = guard.reject(CustodyFileError::identityMismatch);
            return failed<Proof>(fault.error, fault.nativeError);
        }
        CustodyBytes(0).swap(*prefix.value);
        std::array<PackedRootDescriptor, 2> heads{};
        for (std::uint32_t slot = 0; slot < 2; ++slot) {
            auto bytes = guard.read(128 + slot*16384ULL, 16384);
            if (!bytes.ok()) return failed<Proof>(bytes.error, bytes.nativeError);
            auto decoded = ProtectedPackedCustodyCodec::openHead(guard.context(), slot, *bytes.value);
            if (!decoded.ok()) {
                const auto fault = guard.reject(codecFileError(decoded.error), decoded.nativeError);
                return failed<Proof>(fault.error, fault.nativeError);
            }
            custody_detail::WipeBytes wipe{decoded.value->body};
            auto descriptor = ProtectedPackedCustodyFormat::decodeDescriptor(decoded.value->body.data(),
                decoded.value->body.size(), decoded.value->version, *size.value);
            if (!descriptor) {
                const auto fault = guard.reject(CustodyFileError::invalidContent);
                return failed<Proof>(fault.error, fault.nativeError);
            }
            heads[slot] = *descriptor;
        }
        const auto selected = ProtectedPackedCustodyFormat::selectHeads(heads);
        if (!selected) {
            const auto fault = guard.reject(CustodyFileError::invalidContent);
            return failed<Proof>(fault.error, fault.nativeError);
        }
        for (const auto& descriptor : heads) {
            const auto checked = walk(guard, descriptor, descriptor.root, 0);
            if (!checked.ok()) return failed<Proof>(checked.error, checked.nativeError);
        }
        const auto checked = guard.check();
        if (!checked.ok()) return failed<Proof>(checked.error, checked.nativeError);
        CustodyAllocator<ProtectedPackedCustodyTree> allocator;
        auto* raw = allocator.allocate(1);
        new (raw) ProtectedPackedCustodyTree(std::move(pin), std::move(owner), heads, *selected);
        Proof proof(raw, [](const ProtectedPackedCustodyTree* tree) {
            tree->~ProtectedPackedCustodyTree();
            CustodyAllocator<ProtectedPackedCustodyTree>{}.deallocate(const_cast<ProtectedPackedCustodyTree*>(tree), 1);
        }, CustodyAllocator<ProtectedPackedCustodyTree>{});
        return passed(std::move(proof)); // Guard lock still held through result construction.
    } catch (const std::bad_alloc&) {
        const auto fault = guard.reject(CustodyFileError::allocationFailed);
        return failed<Proof>(fault.error, fault.nativeError);
    }
}

CustodyFileResult<PackedPlainRead> ProtectedPackedCustodyTree::readBlock(std::uint64_t block) const {
    const auto& descriptor = heads_[selected_];
    if (block >= descriptor.blockCount) return failed<PackedPlainRead>(CustodyFileError::invalidInput);
    Guard guard(owner_);
    try {
        auto checked = guard.check();
        if (!checked.ok()) return failed<PackedPlainRead>(checked.error, checked.nativeError);
        CustodyPin pin;
        if (!pin) return failed<PackedPlainRead>(CustodyFileError::allocationFailed);
        PackedPlainRead result(std::move(pin)); // Admission before even a Debug iterator proxy.
        auto reference = descriptor.root;
        std::uint64_t base = 0;
        for (unsigned depth = 0; depth < 3 && reference.kind != PackedRecordKind::zero; ++depth) {
            auto bytes = guard.read(reference.offset, reference.envelopeBytes);
            if (!bytes.ok()) return failed<PackedPlainRead>(bytes.error, bytes.nativeError);
            auto decoded = ProtectedPackedCustodyCodec::openReferenced(guard.context(), base, reference, *bytes.value);
            if (!decoded.ok()) {
                const auto fault = guard.reject(codecFileError(decoded.error), decoded.nativeError);
                return failed<PackedPlainRead>(fault.error, fault.nativeError);
            }
            custody_detail::WipeBytes wipe{decoded.value->body};
            if (decoded.value->body.size() != 4096) {
                const auto fault = guard.reject(CustodyFileError::invalidContent);
                return failed<PackedPlainRead>(fault.error, fault.nativeError);
            }
            const auto stride = depth == 0 ? 4096ULL : depth == 1 ? 64ULL : 1ULL;
            const auto slot = static_cast<std::uint32_t>((block-base)/stride);
            std::optional<PackedReference> next;
            for (std::uint32_t i = 0; i < 64; ++i) {
                auto child = ProtectedPackedCustodyFormat::decodeChild(decoded.value->body.data()+64*i, 64, descriptor, reference, base, i);
                if (!child) {
                    const auto fault = guard.reject(CustodyFileError::invalidContent);
                    return failed<PackedPlainRead>(fault.error, fault.nativeError);
                }
                if (i == slot) next = *child;
            }
            if (!next) {
                const auto fault = guard.reject(CustodyFileError::invalidContent);
                return failed<PackedPlainRead>(fault.error, fault.nativeError);
            }
            reference = *next; base += slot*stride;
        }
        const auto count = static_cast<std::uint32_t>(std::min<std::uint64_t>(ProtectedPackedCustodyFormat::blockBytes,
            descriptor.logicalBytes-block*ProtectedPackedCustodyFormat::blockBytes));
        if (reference.kind == PackedRecordKind::zero) result.bytes.resize(count, 0);
        else {
            auto bytes = guard.read(reference.offset, reference.envelopeBytes);
            if (!bytes.ok()) return failed<PackedPlainRead>(bytes.error, bytes.nativeError);
            auto decoded = ProtectedPackedCustodyCodec::openReferenced(guard.context(), block, reference, *bytes.value);
            if (!decoded.ok()) {
                const auto fault = guard.reject(codecFileError(decoded.error), decoded.nativeError);
                return failed<PackedPlainRead>(fault.error, fault.nativeError);
            }
            custody_detail::WipeBytes wipe{decoded.value->body};
            if (reference.kind != PackedRecordKind::data || decoded.value->body.size() != count) {
                const auto fault = guard.reject(CustodyFileError::invalidContent);
                return failed<PackedPlainRead>(fault.error, fault.nativeError);
            }
            result.bytes = std::move(decoded.value->body);
        }
        checked = guard.check();
        if (!checked.ok()) return failed<PackedPlainRead>(checked.error, checked.nativeError);
        result.proof = shared_from_this();
        return passed(std::move(result));
    } catch (const std::bad_alloc&) {
        const auto fault = guard.reject(CustodyFileError::allocationFailed);
        return failed<PackedPlainRead>(fault.error, fault.nativeError);
    }
}
} // namespace graf::windows
