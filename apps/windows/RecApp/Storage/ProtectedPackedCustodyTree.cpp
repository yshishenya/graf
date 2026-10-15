#include "ProtectedPackedCustodyTree.h"
#include "ProtectedCustodyPrimitives.h"
#include <algorithm>
#include <limits>

namespace graf::windows {
namespace {
template<class T> CustodyFileResult<T> failed(CustodyFileError e, std::uint32_t native = 0) {
    return {std::nullopt, e, native};
}
template<class T> CustodyFileResult<T> passed(T value) { return {std::move(value), CustodyFileError::none, 0}; }
}
PackedPlainRead::~PackedPlainRead() { custody_detail::WipeBytes wipe{bytes}; }
ProtectedPackedCustodyTree::ProtectedPackedCustodyTree(CustodyPin&& pin, std::shared_ptr<ProtectedPackedCustodyOwner> owner,
    const std::array<PackedRootDescriptor, 2>& heads, std::uint32_t selected, CustodyRole role,
    std::optional<PackedRootDescriptor> retained) noexcept
    : pin_(std::move(pin)), owner_(std::move(owner)), heads_(heads), selected_(selected), role_(role), retained_(retained) {}

std::shared_ptr<const ProtectedPackedCustodyTree> ProtectedPackedCustodyTree::makeProof(
    CustodyPin&& pin, std::shared_ptr<ProtectedPackedCustodyOwner> owner,
    const std::array<PackedRootDescriptor, 2>& heads, std::uint32_t selected, CustodyRole role,
    std::optional<PackedRootDescriptor> retained) {
    CustodyAllocator<ProtectedPackedCustodyTree> allocator;
    auto* raw = allocator.allocate(1);
    new (raw) ProtectedPackedCustodyTree(std::move(pin), std::move(owner), heads, selected, role, retained);
    return {raw, [](const ProtectedPackedCustodyTree* tree) {
        tree->~ProtectedPackedCustodyTree();
        CustodyAllocator<ProtectedPackedCustodyTree>{}.deallocate(const_cast<ProtectedPackedCustodyTree*>(tree), 1);
    }, CustodyAllocator<ProtectedPackedCustodyTree>{}};
}

CustodyFileResult<std::array<PackedRootDescriptor, 2>> ProtectedPackedCustodyTree::readHeads(Guard& guard) {
    using Heads = std::array<PackedRootDescriptor, 2>;
    const auto size = guard.size();
    if (!size.ok()) return failed<Heads>(size.error, size.nativeError);
    Heads heads{};
    for (std::uint32_t slot = 0; slot < 2; ++slot) {
        auto bytes = guard.read(128 + slot*16384ULL, 16384);
        if (!bytes.ok()) return failed<Heads>(bytes.error, bytes.nativeError);
        auto decoded = ProtectedPackedCustodyCodec::openHead(guard.context(), slot, *bytes.value);
        if (!decoded.ok()) {
            const auto fault = guard.reject(codecFileError(decoded.error), decoded.nativeError);
            return failed<Heads>(fault.error, fault.nativeError);
        }
        custody_detail::WipeBytes wipe{decoded.value->body};
        const auto descriptor = ProtectedPackedCustodyFormat::decodeDescriptor(decoded.value->body.data(),
            decoded.value->body.size(), decoded.value->version, *size.value);
        if (!descriptor) {
            const auto fault = guard.reject(CustodyFileError::invalidContent);
            return failed<Heads>(fault.error, fault.nativeError);
        }
        heads[slot] = *descriptor;
    }
    return passed(heads);
}

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
    return verifyImpl(std::move(owner), nullptr, nullptr);
}
CustodyFileResult<std::shared_ptr<const ProtectedPackedCustodyTree>> ProtectedPackedCustodyTree::verifyRetained(
    std::shared_ptr<ProtectedPackedCustodyOwner> owner, const PackedCustodyContext& context,
    const PackedRootDescriptor& retained) {
    return verifyImpl(std::move(owner), &context, &retained);
}
CustodyFileResult<std::shared_ptr<const ProtectedPackedCustodyTree>> ProtectedPackedCustodyTree::verifyImpl(
    std::shared_ptr<ProtectedPackedCustodyOwner> owner, const PackedCustodyContext* context,
    const PackedRootDescriptor* retained) {
    using Proof = std::shared_ptr<const ProtectedPackedCustodyTree>;
    if (!owner) return failed<Proof>(CustodyFileError::invalidInput);
    Guard guard(owner);
    try {
        CustodyPin pin;
        if (!pin) return failed<Proof>(CustodyFileError::allocationFailed);
        const auto initial = guard.check();
        if (!initial.ok()) return failed<Proof>(initial.error, initial.nativeError);
        const auto& own = guard.context();
        if (context && (context->object.storeId != own.object.storeId || context->object.objectId != own.object.objectId ||
            context->object.role != own.object.role || context->containerId != own.containerId)) {
            const auto fault = guard.reject(CustodyFileError::identityMismatch);
            return failed<Proof>(fault.error, fault.nativeError);
        }
        auto prefix = guard.read(0, 128);
        if (!prefix.ok()) return failed<Proof>(prefix.error, prefix.nativeError);
        if (!ProtectedPackedCustodyFormat::prefixMatches(prefix.value->data(), prefix.value->size(), guard.context())) {
            const auto fault = guard.reject(CustodyFileError::identityMismatch);
            return failed<Proof>(fault.error, fault.nativeError);
        }
        CustodyBytes(0).swap(*prefix.value);
        auto pair = readHeads(guard);
        if (!pair.ok()) return failed<Proof>(pair.error, pair.nativeError);
        const auto& heads = *pair.value;
        const auto selected = ProtectedPackedCustodyFormat::selectHeads(heads);
        if (!selected) {
            const auto fault = guard.reject(CustodyFileError::invalidContent);
            return failed<Proof>(fault.error, fault.nativeError);
        }
        for (const auto& descriptor : heads) {
            const auto checked = walk(guard, descriptor, descriptor.root, 0);
            if (!checked.ok()) return failed<Proof>(checked.error, checked.nativeError);
        }
        if (retained) {
            using Format = ProtectedPackedCustodyFormat;
            const auto actual = guard.size();
            if (!actual.ok()) return failed<Proof>(actual.error, actual.nativeError);
            const auto wire = Format::encodeReference(retained->root);
            const auto root = wire ? Format::decodeReference(wire->data(), wire->size(),
                {retained->logicalBytes ? PackedRecordKind::nodeL2 : PackedRecordKind::empty, 0,
                    retained->generation, retained->committedExtent, retained->committedExtent}) : std::nullopt;
            bool valid = root && *root == retained->root && retained->logicalBytes <= Format::logicalLimit &&
                retained->blockCount == (retained->logicalBytes+Format::blockBytes-1)/Format::blockBytes &&
                retained->committedExtent <= *actual.value && retained->generation <= heads[*selected].generation &&
                (retained->generation != 1 || (retained->logicalBytes == 0 && retained->committedExtent == Format::appendOffset));
            for (const auto& head : heads) {
                if (retained->generation == head.generation) valid &= *retained == head;
                else if (retained->generation < head.generation) valid &= retained->committedExtent <= head.committedExtent;
            }
            if (!valid) {
                const auto fault = guard.reject(CustodyFileError::invalidContent);
                return failed<Proof>(fault.error, fault.nativeError);
            }
            const auto checked = walk(guard, *retained, retained->root, 0);
            if (!checked.ok()) return failed<Proof>(checked.error, checked.nativeError);
        }
        const auto checked = guard.check();
        if (!checked.ok()) return failed<Proof>(checked.error, checked.nativeError);
        Proof proof = makeProof(std::move(pin), std::move(owner), heads, *selected, guard.context().object.role,
            retained ? std::optional<PackedRootDescriptor>{*retained} : std::nullopt);
        return passed(std::move(proof)); // Guard lock still held through result construction.
    } catch (const std::bad_alloc&) {
        const auto fault = guard.reject(CustodyFileError::allocationFailed);
        return failed<Proof>(fault.error, fault.nativeError);
    }
}

PackedTreeCommit ProtectedPackedCustodyTree::appendBlock(const CustodyBytes& input) const {
    return commitBlock(&input, std::nullopt);
}
PackedTreeCommit ProtectedPackedCustodyTree::replaceBlock(std::uint64_t index, const CustodyBytes& input) const {
    return commitBlock(&input, index);
}
PackedTreeCommit ProtectedPackedCustodyTree::setSize(std::uint64_t length) const {
    return commitBlock(nullptr, std::nullopt, length);
}
PackedTreeCommit ProtectedPackedCustodyTree::commitBlock(const CustodyBytes* input,
    std::optional<std::uint64_t> replacement, std::optional<std::uint64_t> resized) const {
    using Format = ProtectedPackedCustodyFormat;
    using Kind = PackedRecordKind;
    PackedTreeCommit result;
    result.lease = shared_from_this();
    Guard guard(owner_, true); // Remains held through catch AND nonallocating result return.
    bool headStarted = false;
    const auto reject = [&](CustodyFileError error, std::uint32_t native = 0) {
        const auto fault = guard.reject(error, native);
        result.error = fault.error; result.nativeError = fault.nativeError;
        result.state = headStarted ? CustodyCommitState::ambiguous : CustodyCommitState::notCommitted;
        return result;
    };
    try {
        const auto ready = retained_ ? guard.check() : guard.writeReady();
        if (!ready.ok()) { result.error = ready.error; result.nativeError = ready.nativeError; return result; }
        if (retained_) { result.error = CustodyFileError::conflict; return result; }
        const auto& base = heads_[selected_];
        if (resized ? *resized > Format::logicalLimit :
            (!input || input->empty() || input->size() > Format::blockBytes ||
            (replacement ? (*replacement >= base.blockCount || input->size() < std::min<std::uint64_t>(
                Format::blockBytes, base.logicalBytes-*replacement*Format::blockBytes)) :
                (base.logicalBytes % Format::blockBytes != 0 || base.logicalBytes >= Format::logicalLimit)))) {
            result.error = CustodyFileError::invalidInput; return result;
        }
        CustodyPin pin;
        CustodyDirtySlot dirty;
        if (!pin || !dirty) { result.error = CustodyFileError::allocationFailed; return result; }
        auto current = readHeads(guard);
        if (!current.ok()) return reject(current.error, current.nativeError);
        if (!(*current.value == heads_)) { result.error = CustodyFileError::conflict; return result; }
        const auto selected = Format::selectHeads(*current.value);
        if (!selected || *selected != selected_) return reject(CustodyFileError::invalidContent);
        if (resized && *resized == base.logicalBytes) {
            const auto checked = guard.check();
            if (!checked.ok()) return reject(checked.error, checked.nativeError);
            result.snapshot = shared_from_this(); result.state = CustodyCommitState::committed;
            return result;
        }
        if (base.generation == std::numeric_limits<std::uint64_t>::max()) {
            result.error = CustodyFileError::invalidInput; return result;
        }
        const auto generation = base.generation + 1;
        const auto block = replacement ? *replacement : base.blockCount;
        const auto length = resized ? *resized : std::max(base.logicalBytes, block*Format::blockBytes+input->size());
        const auto count = static_cast<std::uint32_t>((length+Format::blockBytes-1)/Format::blockBytes);
        const auto target = static_cast<std::uint32_t>((generation - 1) % 2);
        constexpr std::array<Kind, 4> kinds{Kind::data, Kind::nodeL0, Kind::nodeL1, Kind::nodeL2};
        const auto spanAt = [](unsigned level) { return std::uint64_t{1} << (6*level); };
        // Range decisions are also used against independent disk reads. No
        // caller descriptors, flat bitmap, or materialized large ZERO range.
        const auto direct = [&](const PackedReference& old, std::uint64_t first, unsigned level)
            -> std::optional<PackedReference> {
            if (first >= count) return PackedReference{};
            const auto end = first+spanAt(level);
            if (!resized) return block < first || block >= end ? std::optional<PackedReference>{old} : std::nullopt;
            if (level != 3 && (old.kind == Kind::zero || old.kind == Kind::empty)) {
                PackedReference zero; zero.kind = Kind::zero; return zero;
            }
            if (end*Format::blockBytes <= std::min(base.logicalBytes, length)) return old;
            return std::nullopt;
        };
        const auto load = [&](const PackedReference& ref, std::uint64_t first) -> CustodyFileResult<CustodyBytes> {
            auto bytes = guard.read(ref.offset, ref.envelopeBytes);
            if (!bytes.ok()) return failed<CustodyBytes>(bytes.error, bytes.nativeError);
            auto decoded = ProtectedPackedCustodyCodec::openReferenced(guard.context(), first, ref, *bytes.value);
            if (!decoded.ok()) return failed<CustodyBytes>(codecFileError(decoded.error), decoded.nativeError);
            custody_detail::WipeBytes wipe{decoded.value->body};
            return {std::move(decoded.value->body), CustodyFileError::none, 0};
        };
        const auto loadNode = [&](const PackedReference& ref, std::uint64_t first, unsigned level)
            -> CustodyFileResult<CustodyBytes> {
            if (ref.kind == Kind::empty || ref.kind == Kind::zero) {
                CustodyBytes body(4096, 0);
                custody_detail::WipeBytes wipe{body};
                if (ref.kind == Kind::zero) {
                    PackedReference zero; zero.kind = Kind::zero;
                    const auto wire = Format::encodeReference(zero);
                    for (std::uint32_t i = 0; i < 64; ++i)
                        if (first+i*spanAt(level-1) < base.blockCount)
                            std::copy(wire->begin(), wire->end(), body.begin()+64*i);
                }
                return {std::move(body), CustodyFileError::none, 0};
            }
            if (ref.kind != kinds[level]) return failed<CustodyBytes>(CustodyFileError::invalidContent);
            auto body = load(ref, first);
            if (!body.ok()) return body;
            custody_detail::WipeBytes wipe{*body.value};
            if (body.value->size() != 4096) return failed<CustodyBytes>(CustodyFileError::invalidContent);
            for (std::uint32_t i = 0; i < 64; ++i)
                if (!Format::decodeChild(body.value->data()+64*i, 64, base, ref, first, i))
                    return failed<CustodyBytes>(CustodyFileError::invalidContent);
            return {std::move(*body.value), CustodyFileError::none, 0};
        };
        const auto oldChild = [&](const CustodyBytes& body, const PackedReference& ref,
            std::uint64_t first, unsigned level, std::uint32_t i) -> std::optional<PackedReference> {
            if (ref.kind != Kind::empty && ref.kind != Kind::zero)
                return Format::decodeChild(body.data()+64*i, 64, base, ref, first, i);
            PackedReference child;
            if (ref.kind == Kind::zero && first+i*spanAt(level-1) < base.blockCount) child.kind = Kind::zero;
            return child;
        };
        const auto initialSize = guard.size();
        if (!initialSize.ok()) return reject(initialSize.error, initialSize.nativeError);
        const std::uint64_t appendLimit = resized ? 327680 : 290816;
        const auto reserve = guard.reserve(appendLimit + 15);
        if (!reserve.ok()) return reject(reserve.error, reserve.nativeError);
        struct Changed { PackedReference ref; std::uint64_t first; };
        std::array<Changed, 8> changed{};
        std::size_t changedCount = 0;
        const auto appendRecord = [&](Kind kind, std::uint64_t selector, const CustodyBytes& body) -> CustodyFileResult<PackedReference> {
            const auto fail = [&](CustodyFileError error, std::uint32_t native = 0) {
                const auto fault = guard.reject(error, native);
                return failed<PackedReference>(fault.error, fault.nativeError);
            };
            if (changedCount >= (resized ? 8U : 4U)) return fail(CustodyFileError::invalidContent);
            const auto size = guard.size();
            if (!size.ok()) return fail(size.error, size.nativeError);
            if (*size.value > static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max())-15)
                return fail(CustodyFileError::invalidContent);
            const PackedRecordAddress address{kind, (*size.value+15)&~std::uint64_t{15}, selector, generation,
                static_cast<std::uint32_t>(body.size())};
            auto sealed = ProtectedPackedCustodyCodec::seal(guard.context(), address, body);
            if (!sealed.ok()) return fail(codecFileError(sealed.error), sealed.nativeError);
            if (address.offset-*initialSize.value > appendLimit ||
                sealed.value->size() > appendLimit-(address.offset-*initialSize.value))
                return fail(CustodyFileError::invalidContent);
            const auto hash = custody_detail::digest(sealed.value->data(), sealed.value->size());
            if (!hash) return fail(CustodyFileError::hashFailed);
            const auto written = guard.append(address, *sealed.value);
            if (!written.ok()) return fail(written.error, written.nativeError);
            const PackedReference ref{kind, static_cast<std::uint32_t>(sealed.value->size()), address.offset,
                generation, kind == Kind::data ? address.bodyBytes : 0, *hash};
            changed[changedCount++] = {ref, selector};
            return passed(ref);
        };
        const auto build = [&](const auto& self, const PackedReference& old, std::uint64_t first, unsigned level)
            -> CustodyFileResult<PackedReference> {
            if (const auto inherited = direct(old, first, level)) return passed(*inherited);
            if (!level) {
                if (!resized) return appendRecord(Kind::data, first, *input);
                if (old.kind != Kind::data) return failed<PackedReference>(CustodyFileError::invalidContent);
                auto body = load(old, first); if (!body.ok()) return failed<PackedReference>(body.error, body.nativeError);
                custody_detail::WipeBytes wipe{*body.value};
                const auto payload = static_cast<std::size_t>(std::min<std::uint64_t>(Format::blockBytes, length-first*Format::blockBytes));
                // Never reallocate a decoded plaintext buffer before wiping it.
                CustodyBytes resizedBody(payload, 0);
                custody_detail::WipeBytes resizedWipe{resizedBody};
                std::copy_n(body.value->begin(), std::min(payload, body.value->size()), resizedBody.begin());
                return appendRecord(Kind::data, first, resizedBody);
            }
            auto body = loadNode(old, first, level); if (!body.ok()) return failed<PackedReference>(body.error, body.nativeError);
            custody_detail::WipeBytes wipe{*body.value};
            for (std::uint32_t i = 0; i < 64; ++i) {
                const auto child = oldChild(*body.value, old, first, level, i);
                if (!child) return failed<PackedReference>(CustodyFileError::invalidContent);
                const auto next = self(self, *child, first+i*spanAt(level-1), level-1);
                if (!next.ok()) return next;
                const auto wire = Format::encodeReference(*next.value);
                if (!wire) return failed<PackedReference>(CustodyFileError::invalidContent);
                std::copy(wire->begin(), wire->end(), body.value->begin()+64*i);
            }
            return appendRecord(kinds[level], first, *body.value);
        };
        const auto root = build(build, base.root, 0, 3);
        if (!root.ok()) return reject(root.error, root.nativeError);
        const PackedRootDescriptor candidate{generation, length, changedCount ?
            root.value->offset+root.value->envelopeBytes : base.committedExtent, count, *root.value};
        const auto validate = [&]() -> CustodyFileResult<bool> {
            const auto diff = [&](const auto& self, const PackedReference& old, const PackedReference& actual,
                std::uint64_t first, unsigned level) -> CustodyFileResult<bool> {
                if (const auto inherited = direct(old, first, level))
                    return actual == *inherited ? passed(true) : guard.reject(CustodyFileError::invalidContent);
                const auto expected = std::find_if(changed.begin(), changed.begin()+changedCount,
                    [&](const Changed& item) { return item.first == first && item.ref.kind == kinds[level]; });
                if (expected == changed.begin()+changedCount || !(actual == expected->ref))
                    return guard.reject(CustodyFileError::invalidContent);
                auto body = load(actual, first); if (!body.ok()) return guard.reject(body.error, body.nativeError);
                custody_detail::WipeBytes wipe{*body.value};
                if (!level) {
                    const auto payload = static_cast<std::size_t>(std::min<std::uint64_t>(Format::blockBytes, length-first*Format::blockBytes));
                    if (body.value->size() != payload) return guard.reject(CustodyFileError::invalidContent);
                    if (!resized) return *body.value == *input ? passed(true) : guard.reject(CustodyFileError::invalidContent);
                    auto prior = load(old, first); if (!prior.ok()) return guard.reject(prior.error, prior.nativeError);
                    custody_detail::WipeBytes priorWipe{*prior.value};
                    const auto retained = std::min(payload, prior.value->size());
                    if (!std::equal(prior.value->begin(), prior.value->begin()+retained, body.value->begin()) ||
                        !std::all_of(body.value->begin()+retained, body.value->end(), [](auto byte) { return byte == 0; }))
                        return guard.reject(CustodyFileError::invalidContent);
                    return passed(true);
                }
                if (body.value->size() != 4096) return guard.reject(CustodyFileError::invalidContent);
                auto prior = loadNode(old, first, level); if (!prior.ok()) return guard.reject(prior.error, prior.nativeError);
                custody_detail::WipeBytes priorWipe{*prior.value};
                for (std::uint32_t i = 0; i < 64; ++i) {
                    const auto child = Format::decodeChild(body.value->data()+64*i, 64, candidate, actual, first, i);
                    const auto before = oldChild(*prior.value, old, first, level, i);
                    if (!child || !before) return guard.reject(CustodyFileError::invalidContent);
                    const auto checked = self(self, *before, *child, first+i*spanAt(level-1), level-1);
                    if (!checked.ok()) return checked;
                }
                return passed(true);
            };
            const auto checked = diff(diff, base.root, candidate.root, 0, 3);
            if (!checked.ok()) return checked;
            return guard.check();
        };
        const auto flushed = guard.flush();
        if (!flushed.ok()) return reject(flushed.error, flushed.nativeError);
        const auto checked = validate();
        if (!checked.ok()) return reject(checked.error, checked.nativeError);
        auto nextHeads = heads_; nextHeads[target] = candidate;
        auto next = makeProof(std::move(pin), owner_, nextHeads, target, role_); // Allocations BEFORE head publication.
        {
            auto cell = [&]() {
                CustodyBytes body(128, 0);
                const auto put = [&](std::size_t at, std::uint64_t value, unsigned width) {
                    for (unsigned i = 0; i < width; ++i) body[at+i] = static_cast<std::uint8_t>(value>>(8*i));
                };
                put(0, generation, 8); put(8, candidate.logicalBytes, 8); put(16, candidate.committedExtent, 8);
                put(24, Format::blockBytes, 4); put(28, candidate.blockCount, 4); put(32, 64, 4); put(36, 3, 4);
                const auto wire = Format::encodeReference(candidate.root);
                std::copy(wire->begin(), wire->end(), body.begin()+48);
                return ProtectedPackedCustodyCodec::seal(guard.context(),
                    {Kind::head, 128+target*16384ULL, target, generation, 128}, body);
            }();
            if (!cell.ok()) return reject(codecFileError(cell.error), cell.nativeError);
            const auto published = guard.publishHead(target, *cell.value);
            headStarted = published.state != CustodyPublishState::notPublished;
            if (published.state != CustodyPublishState::published) return reject(published.error, published.nativeError);
        } // Release HEAD writer copies before the logical ACK's independent reads.
        auto pair = readHeads(guard);
        if (!pair.ok()) return reject(pair.error, pair.nativeError);
        const auto actualSelected = Format::selectHeads(*pair.value);
        if (!(*pair.value == nextHeads) || !actualSelected || *actualSelected != target ||
            !((*pair.value)[1-target] == base)) return reject(CustodyFileError::invalidContent);
        const auto rechecked = validate();
        if (!rechecked.ok()) return reject(rechecked.error, rechecked.nativeError);
        result.snapshot = std::move(next);
        result.state = CustodyCommitState::committed;
        return result;
    } catch (const std::bad_alloc&) {
        return reject(CustodyFileError::allocationFailed);
    }
}

CustodyFileResult<bool> ProtectedPackedCustodyTree::checkRead() const {
    Guard guard(owner_);
    try { return guard.check(); }
    catch (const std::bad_alloc&) { return guard.reject(CustodyFileError::allocationFailed); }
}
CustodyFileResult<bool> ProtectedPackedCustodyTree::checkWrite() const {
    Guard guard(owner_, true);
    try {
        if (!retained_) return guard.writeReady();
        const auto checked = guard.check();
        return checked.ok() ? failed<bool>(CustodyFileError::conflict) : checked;
    }
    catch (const std::bad_alloc&) { return guard.reject(CustodyFileError::allocationFailed); }
}

CustodyFileResult<PackedPlainRead> ProtectedPackedCustodyTree::readBlock(std::uint64_t block) const {
    const auto& descriptor = this->descriptor();
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
