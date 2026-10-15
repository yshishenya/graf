#include "ProtectedCustodyWriter.h"
#include "ProtectedPackedCustodyTree.h"
#include <algorithm>
#include <cstring>
#include <limits>
#include <system_error>
#ifdef _WIN32
#include <windows.h>
#endif

namespace graf::windows {
namespace {
constexpr auto blockBytes = ProtectedCustodyCodec::blockBytes;
constexpr auto noBlock = (std::numeric_limits<std::uint64_t>::max)();
void wipeBytes(void* data, std::size_t size) noexcept {
#ifdef _WIN32
    if (size) SecureZeroMemory(data, size);
#else
    auto* p = static_cast<volatile std::uint8_t*>(data);
    while (size--) *p++ = 0;
#endif
}
void wipe(CustodyBytes& bytes) noexcept { wipeBytes(bytes.data(), bytes.size()); }
struct PlainWipe { CustodyBytes& value; ~PlainWipe() { wipe(value); } };
std::uint32_t payloadAt(const CustodyIndex& index, std::uint64_t position) {
    return static_cast<std::uint32_t>(std::min<std::uint64_t>(blockBytes, index.logicalLength - position * blockBytes));
}
}

struct ProtectedCustodyWriter::State {
    static void* operator new(std::size_t) { return CustodyAllocator<State>{}.allocate(1); }
    static void operator delete(void* memory) noexcept { CustodyAllocator<State>{}.deallocate(static_cast<State*>(memory), 1); }
    CustodyPin pin; // Files/snapshots/dirty bytes close BEFORE admission releases.
    std::unique_ptr<ProtectedCustodyFiles> files;
    std::shared_ptr<const ProtectedPackedCustodyTree> packed;
    PackedTreeCommit packedResult;
    CustodyContext context{};
    CustodyIndex candidate;
    std::optional<CustodySnapshot> committed;
    std::shared_ptr<const std::atomic<bool>> cancellation;
    std::optional<CustodyDirtySlot> dirtySlot;
    CustodyBytes dirty;
    std::uint64_t dirtyPosition = noBlock;
    bool changed = false, failed = false;
    CustodyCommitState lastCommit = CustodyCommitState::notCommitted;
    std::uint64_t lastBase = 0, lastTarget = 0;
    std::uint32_t failureNative = 0;
    CustodyFileError readyError = CustodyFileError::writerFailed;
    ~State() {
        clearDirty();
        if (packed) packed->owner_->revokeWrites(); // RAM capability only; readers retain their owner.
    }
    void clearDirty() noexcept {
        wipe(dirty); dirty.clear();
        // Empty shrink releases MSVC storage without constructing a new proxy.
        // If another STL refuses the request, retained capacity stays charged.
        try { dirty.shrink_to_fit(); } catch (const std::bad_alloc&) {}
        dirtyPosition = noBlock;
        dirtySlot.reset();
    }
    CustodyFileResult<std::uint64_t> fail(CustodyFileError error, std::uint32_t native = 0, bool transition = false) {
        if (!failed) {
            failureNative = native;
            if (packed && !transition) lastBase = lastTarget = packed->generation();
            if (lastCommit != CustodyCommitState::ambiguous) lastCommit = CustodyCommitState::notCommitted;
            if (packed && !transition) packedResult = {packed, nullptr, lastCommit, error, native};
        }
        failed = true; if (files) files->blockWrites();
        // A revoked write capability is not a physical fault: healthy readers remain valid.
        if (packed && (error != CustodyFileError::writerFailed || native)) packed->owner_->blockWrites();
        return {std::nullopt, error, native};
    }
    bool ready() {
        if (failed) return false;
        if (packed) {
            const auto checked = packed->checkWrite(); // First shared fault precedes input, RAM hits and cancellation.
            if (!checked.ok()) {
                fail(checked.error, checked.nativeError); readyError = checked.error;
                return false;
            }
        }
        if (cancellation->load()) {
#ifdef _WIN32
            fail(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
#else
            fail(CustodyFileError::unsupportedPlatform);
#endif
            return false;
        }
        return true;
    }
    CustodyFileResult<std::uint64_t> stopped() {
        const auto error = readyError; readyError = CustodyFileError::writerFailed;
        return {std::nullopt, error, failureNative};
    }
    std::uint64_t nextTarget() const noexcept {
        return packed->generation() == noBlock ? noBlock : packed->generation()+1;
    }
    CustodyFileResult<std::uint64_t> adopt(PackedTreeCommit result, std::uint64_t target) {
        lastBase = result.lease ? result.lease->generation() : packed->generation();
        lastTarget = target; lastCommit = result.state;
        packedResult = std::move(result); // Retain actual failed base, including ambiguous HEAD.
        if (lastCommit != CustodyCommitState::committed)
            return fail(packedResult.error, packedResult.nativeError, true);
        packed = packedResult.snapshot; lastTarget = packed->generation();
        return {packed->logicalBytes(), CustodyFileError::none, 0};
    }
    CustodyFileResult<std::uint64_t> flushPacked() {
        const auto start = dirtyPosition*blockBytes;
        if (packed->logicalBytes() < start) {
            const auto target = nextTarget();
            auto gap = adopt(packed->setSize(start), target); // Only the explicit gap, NOT the pending DATA.
            if (!gap.ok()) return gap;
            if (!ready()) return stopped();
        }
        const auto target = nextTarget();
        auto published = adopt(dirtyPosition < (packed->logicalBytes()+blockBytes-1)/blockBytes
            ? packed->replaceBlock(dirtyPosition, dirty) : packed->appendBlock(dirty), target);
        if (!published.ok()) return published;
        const auto bytes = dirty.size(); clearDirty();
        return {bytes, CustodyFileError::none, 0};
    }
    CustodyFileResult<std::uint64_t> flushDirty() {
        if (dirtyPosition == noBlock) return {0, CustodyFileError::none, 0};
        if (!ready()) return stopped();
        const auto payload = payloadAt(candidate, dirtyPosition);
        if (dirty.size() != payload) return fail(CustodyFileError::invalidContent);
        if (packed) return flushPacked();
        auto reserve = files->checkWriteReserve(dirty.size() + 4096 + ProtectedCustodyCodec::indexEnvelopeLimit(context.role), 2);
        if (!reserve.ok()) return fail(reserve.error, reserve.nativeError);
        auto version = files->nextBlockVersion(dirtyPosition);
        if (!version.ok()) return fail(version.error, version.nativeError);
        auto cipher = ProtectedCustodyCodec::sealBlock(context, dirtyPosition, *version.value, dirty);
        if (!cipher.ok()) return fail(codecFileError(cipher.error), cipher.nativeError);
        auto written = files->writeBlock(dirtyPosition, *version.value, payload, *cipher.value);
        if (!written.ok()) return fail(written.error, written.nativeError);
        candidate.entries[static_cast<std::size_t>(dirtyPosition)] = {*version.value, *written.value, 0};
        clearDirty(); return {payload, CustodyFileError::none, 0};
    }
    CustodyFileResult<std::uint64_t> loadDirty(std::uint64_t position) {
        if (dirtyPosition == position) return {dirty.size(), CustodyFileError::none, 0};
        auto flushed = flushDirty(); if (!flushed.ok()) return flushed;
        if (!ready()) return stopped();
        dirtySlot.emplace();
        if (!*dirtySlot) return fail(CustodyFileError::allocationFailed);
        dirty.reserve(blockBytes); // Before reading any plaintext into this owned buffer.
        const auto payload = payloadAt(candidate, position);
        if (packed) {
            dirty.assign(payload, 0);
            if (position < (packed->logicalBytes()+blockBytes-1)/blockBytes) {
                auto plain = packed->readBlock(position);
                if (!plain.ok()) return fail(plain.error, plain.nativeError);
                std::copy_n(plain.value->bytes.begin(), std::min(dirty.size(), plain.value->bytes.size()), dirty.begin());
            }
        } else {
            const auto& entry = candidate.entries[static_cast<std::size_t>(position)];
            if (entry.flags == 1) dirty.assign(payload, 0);
            else {
                auto cipher = files->readBlock(position, entry.version, payload, entry.envelopeBytes);
                if (!cipher.ok()) return fail(cipher.error, cipher.nativeError);
                auto plain = ProtectedCustodyCodec::openBlock(context, position, entry.version, payload, *cipher.value);
                if (!plain.ok()) return fail(codecFileError(plain.error), plain.nativeError);
                PlainWipe cleanup{*plain.value}; dirty.assign(plain.value->begin(), plain.value->end());
            }
        }
        dirtyPosition = position; return {payload, CustodyFileError::none, 0};
    }
    CustodyFileResult<std::uint64_t> resize(std::uint64_t length) {
        if (!ready()) return stopped();
        if (length > ProtectedCustodyCodec::logicalLimit(context.role)) return fail(CustodyFileError::invalidInput);
        const auto oldLength = candidate.logicalLength;
        if (length == oldLength) return {length, CustodyFileError::none, 0};
        if (packed && length < oldLength) {
            auto flushed = flushDirty(); if (!flushed.ok()) return flushed;
            if (!ready()) return stopped();
            const auto target = packed->logicalBytes() == length ? packed->generation() : nextTarget();
            auto trimmed = adopt(packed->setSize(length), target); if (!trimmed.ok()) return trimmed;
            candidate.logicalLength = length; changed = true;
            return {length, CustodyFileError::none, 0};
        }
        const auto count = static_cast<std::size_t>(length / blockBytes + (length % blockBytes != 0));
        if (!packed) candidate.entries.reserve(count); // Packed never has per-block entries.
        if (length < oldLength && dirtyPosition != noBlock && dirtyPosition >= count) clearDirty();
        const auto boundary = length > oldLength ? (oldLength ? (oldLength - 1) / blockBytes : noBlock)
            : (length ? (length - 1) / blockBytes : noBlock);
        const bool rewrite = boundary != noBlock && (length < oldLength ? length % blockBytes != 0 : oldLength % blockBytes != 0);
        if (rewrite) { auto loaded = loadDirty(boundary); if (!loaded.ok()) return loaded; }
        else { auto flushed = flushDirty(); if (!flushed.ok()) return flushed; }
        if (!packed) candidate.entries.resize(count, {0, 0, 1});
        candidate.logicalLength = length;
        if (rewrite) {
            const auto payload = payloadAt(candidate, boundary);
            if (payload < dirty.size()) wipeBytes(dirty.data() + payload, dirty.size() - payload);
            dirty.resize(payload, 0);
        }
        changed = true; return {length, CustodyFileError::none, 0};
    }
};

ProtectedCustodyWriter::ProtectedCustodyWriter(std::unique_ptr<State> state) : state_(std::move(state)) {
    static_assert(sizeof(State) <= 4096);
}
ProtectedCustodyWriter::~ProtectedCustodyWriter() = default;
CustodyFileResult<std::unique_ptr<ProtectedCustodyWriter>> ProtectedCustodyWriter::open(
    std::shared_ptr<const ProtectedPackedCustodyTree> proof, std::shared_ptr<const std::atomic<bool>> cancellation) try {
    if (!proof || !cancellation) return {std::nullopt, CustodyFileError::invalidInput, 0};
    if (cancellation->load()) return {std::nullopt, CustodyFileError::writerFailed, 0};
    auto state = std::make_unique<State>();
    if (!state->pin) return {std::nullopt, CustodyFileError::allocationFailed, 0};
    state->context.role = proof->role_; state->cancellation = std::move(cancellation);
    auto writer = std::unique_ptr<ProtectedCustodyWriter>(new ProtectedCustodyWriter(std::move(state)));
    auto checked = proof->setSize(proof->logicalBytes());
    if (checked.state != CustodyCommitState::committed) return {std::nullopt, checked.error, checked.nativeError};
    if (writer->state_->cancellation->load()) return {std::nullopt, CustodyFileError::writerFailed, 0};
    // Install capability only after all allocations/checks; failed open cannot revoke a healthy owner.
    writer->state_->packed = std::move(checked.snapshot);
    writer->state_->candidate.logicalLength = writer->state_->packed->logicalBytes();
    writer->state_->lastBase = writer->state_->lastTarget = writer->state_->packed->generation();
    return {std::move(writer), CustodyFileError::none, 0};
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }
  catch (const std::system_error& error) { return {std::nullopt, CustodyFileError::ioFailed, static_cast<std::uint32_t>(error.code().value())}; }
std::uint64_t ProtectedCustodyWriter::size() const noexcept { return streamAttached_.load() ? 0 : sizeImpl(); }
std::uint64_t ProtectedCustodyWriter::generation() const noexcept {
    return streamAttached_.load() ? 0 : generationImpl();
}
std::uint64_t ProtectedCustodyWriter::sizeImpl() const noexcept { return state_->candidate.logicalLength; }
std::uint64_t ProtectedCustodyWriter::generationImpl() const noexcept {
    return state_->packed ? state_->packed->generation() : state_->committed ? state_->committed->index.generation : 0;
}
std::uint64_t ProtectedCustodyWriter::logicalLimit() const noexcept { return ProtectedCustodyCodec::logicalLimit(state_->context.role); }
CustodyFileResult<bool> ProtectedCustodyWriter::streamReady() {
    if (state_->ready()) return {true, CustodyFileError::none, 0};
    const auto denied = state_->stopped();
    return {std::nullopt, denied.error, denied.nativeError};
}
CustodyFileResult<bool> ProtectedCustodyWriter::attachStream() {
    bool expected = false;
    if (!streamAttached_.compare_exchange_strong(expected, true)) return {std::nullopt, CustodyFileError::conflict, 0};
    try {
        const auto checked = streamReady();
        if (!checked.ok()) detachStream();
        return checked;
    } catch (...) { detachStream(); throw; }
}
void ProtectedCustodyWriter::detachStream() noexcept { streamAttached_.store(false); }
void ProtectedCustodyWriter::failStream(CustodyFileError error, std::uint32_t native) noexcept { (void)state_->fail(error, native); }

CustodyFileResult<std::shared_ptr<const ProtectedPackedCustodyTree>> ProtectedCustodyWriter::committedPackedSnapshot() try {
    if (streamAttached_.load()) return {std::nullopt, CustodyFileError::conflict, 0};
    const auto ready = streamReady();
    if (!ready.ok()) return {std::nullopt, ready.error, ready.nativeError};
    if (!state_->packed || state_->changed || state_->dirtyPosition != noBlock
        || state_->lastCommit != CustodyCommitState::committed || sizeImpl() != state_->packed->logicalBytes())
        return {std::nullopt, CustodyFileError::conflict, 0};
    const auto checked = state_->packed->checkRead();
    if (!checked.ok()) { failStream(checked.error, checked.nativeError); return {std::nullopt, checked.error, checked.nativeError}; }
    return {state_->packed, CustodyFileError::none, 0};
} catch (const std::bad_alloc&) { failStream(CustodyFileError::allocationFailed, 0); return {std::nullopt, CustodyFileError::allocationFailed, 0}; }
  catch (const std::system_error& error) {
      const auto native = static_cast<std::uint32_t>(error.code().value());
      failStream(CustodyFileError::ioFailed, native); return {std::nullopt, CustodyFileError::ioFailed, native};
  }

CustodyFileResult<std::unique_ptr<ProtectedCustodyWriter>> ProtectedCustodyWriter::open(
    const std::filesystem::path& root, std::string_view package, const CustodyContext& context,
    std::uint64_t base, std::shared_ptr<const std::atomic<bool>> cancellation) try {
    if (!cancellation || context.role < CustodyRole::canonical || context.role > CustodyRole::playback || base == noBlock)
        return {std::nullopt, CustodyFileError::invalidInput, 0};
#ifndef _WIN32
    (void)root; (void)package; return {std::nullopt, CustodyFileError::unsupportedPlatform, 0};
#else
    if (cancellation->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
    auto state = std::make_unique<State>();
    if (!state->pin) return {std::nullopt, CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA};
    state->context = context; state->cancellation = std::move(cancellation); state->lastTarget = base;
    auto files = ProtectedCustodyFiles::open(root, package, context, base ? CustodyFileAccess::writeExisting : CustodyFileAccess::createNew);
    if (!files.ok()) return {std::nullopt, files.error, files.nativeError};
    state->files = std::move(*files.value);
    if (base) {
        auto snapshot = state->files->readValidatedSnapshot();
        if (!snapshot.ok()) return {std::nullopt, snapshot.error, snapshot.nativeError};
        if (snapshot.value->state != CustodySnapshotState::verified || snapshot.value->index.generation != base)
            return {std::nullopt, CustodyFileError::conflict, 0};
        state->candidate = snapshot.value->index; state->committed = std::move(*snapshot.value);
    }
    if (state->cancellation->load()) return {std::nullopt, CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED};
    return {std::unique_ptr<ProtectedCustodyWriter>(new ProtectedCustodyWriter(std::move(state))), CustodyFileError::none, 0};
#endif
} catch (const std::bad_alloc&) { return {std::nullopt, CustodyFileError::allocationFailed, 0}; }
  catch (const std::system_error& error) { return {std::nullopt, CustodyFileError::ioFailed, static_cast<std::uint32_t>(error.code().value())}; }

CustodyFileResult<std::uint64_t> ProtectedCustodyWriter::setSize(std::uint64_t length) {
    return streamAttached_.load() ? CustodyFileResult<std::uint64_t>{std::nullopt, CustodyFileError::conflict, 0} : setSizeImpl(length);
}
CustodyFileResult<std::uint64_t> ProtectedCustodyWriter::setSizeImpl(std::uint64_t length) try {
    return state_->resize(length);
} catch (const std::bad_alloc&) { return state_->fail(CustodyFileError::allocationFailed); }
  catch (const std::system_error& error) { return state_->fail(CustodyFileError::ioFailed, static_cast<std::uint32_t>(error.code().value())); }

CustodyFileResult<std::uint64_t> ProtectedCustodyWriter::writeAt(std::uint64_t offset, const void* data, std::size_t bytes) {
    return streamAttached_.load() ? CustodyFileResult<std::uint64_t>{std::nullopt, CustodyFileError::conflict, 0} : writeAtImpl(offset, data, bytes);
}
CustodyFileResult<std::uint64_t> ProtectedCustodyWriter::writeAtImpl(std::uint64_t offset, const void* data, std::size_t bytes) try {
    if (!state_->ready()) return state_->stopped();
    const auto limit = ProtectedCustodyCodec::logicalLimit(state_->context.role);
    if ((!data && bytes) || offset > limit || bytes > limit - offset) return state_->fail(CustodyFileError::invalidInput);
    std::size_t copied = 0;
    while (copied < bytes) {
        if (!state_->ready()) return state_->stopped();
        const auto at = offset + copied;
        const auto within = static_cast<std::size_t>(at % blockBytes);
        const auto count = std::min<std::size_t>(bytes - copied, blockBytes - within);
        if (at + count > sizeImpl()) { auto extended = state_->resize(at + count); if (!extended.ok()) return extended; }
        auto loaded = state_->loadDirty(at / blockBytes); if (!loaded.ok()) return loaded;
        std::memcpy(state_->dirty.data() + within, static_cast<const std::uint8_t*>(data) + copied, count);
        state_->changed = true; copied += count;
        if (state_->context.role == CustodyRole::canonical && within + count == blockBytes) {
            const auto result = checkpointImpl();
            if (result.state != CustodyCommitState::committed) return state_->fail(result.error, result.nativeError);
        }
    }
    if (!state_->ready()) return state_->stopped(); // Preserve actual prior ACK, but no late byte acceptance.
    return {copied, CustodyFileError::none, 0};
} catch (const std::bad_alloc&) { return state_->fail(CustodyFileError::allocationFailed); }
  catch (const std::system_error& error) { return state_->fail(CustodyFileError::ioFailed, static_cast<std::uint32_t>(error.code().value())); }

CustodyFileResult<std::uint64_t> ProtectedCustodyWriter::readAt(std::uint64_t offset, void* output, std::size_t bytes) {
    return streamAttached_.load() ? CustodyFileResult<std::uint64_t>{std::nullopt, CustodyFileError::conflict, 0} : readAtImpl(offset, output, bytes);
}
CustodyFileResult<std::uint64_t> ProtectedCustodyWriter::readAtImpl(std::uint64_t offset, void* output, std::size_t bytes) {
    std::size_t copied = 0;
    const auto reject = [&](CustodyFileError error, std::uint32_t native = 0) {
        wipeBytes(output, copied);
        return state_->fail(error, native);
    };
    try {
        if (!state_->ready()) return state_->stopped();
        if (!output && bytes) return reject(CustodyFileError::invalidInput);
        if (state_->packed) {
            const auto checked = state_->packed->checkRead();
            if (!checked.ok()) return reject(checked.error, checked.nativeError);
        }
        const auto count = static_cast<std::size_t>(std::min<std::uint64_t>(bytes, offset < sizeImpl() ? sizeImpl() - offset : 0));
        while (copied < count) {
            if (!state_->ready()) return reject(CustodyFileError::writerFailed, state_->failureNative);
            const auto at = offset + copied, position = at / blockBytes;
            const auto within = static_cast<std::size_t>(at % blockBytes);
            const auto payload = payloadAt(state_->candidate, position);
            const auto part = std::min<std::size_t>(count - copied, payload - within);
            auto* target = static_cast<std::uint8_t*>(output) + copied;
            if (state_->dirtyPosition == position) std::memcpy(target, state_->dirty.data() + within, part);
            else if (state_->packed) {
                if (position < (state_->packed->logicalBytes()+blockBytes-1)/blockBytes) {
                    auto plain = state_->packed->readBlock(position);
                    if (!plain.ok()) return reject(plain.error, plain.nativeError);
                    std::memset(target, 0, part);
                    if (within < plain.value->bytes.size())
                        std::memcpy(target, plain.value->bytes.data()+within, std::min(part, plain.value->bytes.size()-within));
                } else std::memset(target, 0, part); // Only Writer's explicitly pending ZERO view.
            } else {
                const auto& entry = state_->candidate.entries[static_cast<std::size_t>(position)];
                if (entry.flags == 1) std::memset(target, 0, part);
                else {
                    auto cipher = state_->files->readBlock(position, entry.version, payload, entry.envelopeBytes);
                    if (!cipher.ok()) return reject(cipher.error, cipher.nativeError);
                    auto plain = ProtectedCustodyCodec::openBlock(state_->context, position, entry.version, payload, *cipher.value);
                    if (!plain.ok()) return reject(codecFileError(plain.error), plain.nativeError);
                    PlainWipe cleanup{*plain.value}; std::memcpy(target, plain.value->data() + within, part);
                }
            }
            copied += part;
        }
        if (!state_->ready()) return reject(CustodyFileError::writerFailed, state_->failureNative);
        if (state_->packed) {
            const auto checked = state_->packed->checkRead();
            if (!checked.ok()) return reject(checked.error, checked.nativeError);
        }
        return {copied, CustodyFileError::none, 0};
    } catch (const std::bad_alloc&) { return reject(CustodyFileError::allocationFailed); }
      catch (const std::system_error& error) { return reject(CustodyFileError::ioFailed, static_cast<std::uint32_t>(error.code().value())); }
}

CustodyWriterCommit ProtectedCustodyWriter::checkpoint() {
    if (streamAttached_.load()) return {CustodyCommitState::notCommitted, CustodyFileError::conflict, 0, 0, 0};
    return checkpointImpl();
}
CustodyWriterCommit ProtectedCustodyWriter::checkpointImpl() {
    const auto base = generationImpl();
    CustodyWriterCommit result{CustodyCommitState::notCommitted, CustodyFileError::none, 0, base, base};
    const auto reject = [&](CustodyFileError error, std::uint32_t native = 0) {
        state_->lastCommit = result.state; state_->lastTarget = result.targetGeneration; state_->fail(error, native);
        result.error = error; result.nativeError = native; return result;
    };
    try {
        if (!state_->ready()) {
            const auto denied = state_->stopped();
            result.state = state_->lastCommit; result.targetGeneration = state_->lastTarget;
            return reject(denied.error, denied.nativeError);
        }
        if (state_->packed) {
            const bool hadDirty = state_->dirtyPosition != noBlock;
            auto flushed = state_->flushDirty();
            if (flushed.ok() && hadDirty && sizeImpl() == state_->packed->logicalBytes()) {
                // This exact DATA ACK is already independently verified. No new transition
                // after late cancellation, nor redundant noop HEAD reads/admission.
                state_->changed = false;
                return {CustodyCommitState::committed, CustodyFileError::none, 0, state_->lastBase, state_->lastTarget};
            }
            if (flushed.ok()) {
                if (!state_->ready()) {
                    const auto denied = state_->stopped();
                    return {state_->lastCommit, denied.error, denied.nativeError, state_->lastBase, state_->lastTarget};
                }
                const auto target = sizeImpl() == state_->packed->logicalBytes() ? generationImpl() : state_->nextTarget();
                flushed = state_->adopt(state_->packed->setSize(sizeImpl()), target);
            }
            if (!flushed.ok()) return {state_->lastCommit, flushed.error, flushed.nativeError, state_->lastBase, state_->lastTarget};
            state_->changed = false;
            return {CustodyCommitState::committed, CustodyFileError::none, 0, state_->lastBase, state_->lastTarget};
        }
        if (!state_->changed && base) { result.state = CustodyCommitState::committed; return result; }
        if (base == noBlock) return reject(CustodyFileError::invalidInput);
        result.targetGeneration = base + 1;
        auto flushed = state_->flushDirty(); if (!flushed.ok()) return reject(flushed.error, flushed.nativeError);
        state_->candidate.generation = base + 1;
        const auto slot = static_cast<std::uint32_t>(base % 2);
        auto cipher = ProtectedCustodyCodec::sealIndex(state_->context, slot, state_->candidate);
        if (!cipher.ok()) return reject(codecFileError(cipher.error), cipher.nativeError);
        auto reserve = state_->files->checkWriteReserve(cipher.value->size(), 1);
        if (!reserve.ok()) return reject(reserve.error, reserve.nativeError);
        if (!state_->ready()) return reject(CustodyFileError::writerFailed, state_->failureNative);
        const auto published = state_->files->publishIndex(slot, *cipher.value);
        if (published.state != CustodyPublishState::notPublished) result.state = CustodyCommitState::ambiguous;
        if (published.state != CustodyPublishState::published) return reject(published.error, published.nativeError);
        cipher.value.reset(); // Final independent reopen, with writer cipher/dirty copies released.
        auto reopened = state_->files->readValidatedSnapshot();
        if (!reopened.ok()) return reject(reopened.error, reopened.nativeError);
        const auto& accepted = reopened.value->index;
        const auto& expected = state_->candidate;
        if (reopened.value->state != CustodySnapshotState::verified || accepted.generation != expected.generation
            || accepted.logicalLength != expected.logicalLength || accepted.entries.size() != expected.entries.size()
            || !std::equal(accepted.entries.begin(), accepted.entries.end(), expected.entries.begin(), [](const auto& a, const auto& b) {
                return a.version == b.version && a.envelopeBytes == b.envelopeBytes && a.flags == b.flags;
            })) return reject(CustodyFileError::conflict);
        state_->committed = std::move(*reopened.value); state_->changed = false;
        state_->lastTarget = result.targetGeneration; state_->lastCommit = result.state = CustodyCommitState::committed; return result;
    } catch (const std::bad_alloc&) { return reject(CustodyFileError::allocationFailed); }
      catch (const std::system_error& error) { return reject(CustodyFileError::ioFailed, static_cast<std::uint32_t>(error.code().value())); }
}

} // namespace graf::windows
