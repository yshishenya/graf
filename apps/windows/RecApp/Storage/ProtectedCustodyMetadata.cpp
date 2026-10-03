#include "ProtectedCustodyMetadata.h"
#include <algorithm>
#include <limits>
#include <mutex>
#ifdef _WIN32
#include <windows.h>
#endif

namespace graf::windows {

CustodyMetadataCommit commitProtectedCustodyMetadata(const std::filesystem::path& root,
    std::string_view package, const CustodyContext& context, std::uint64_t base,
    const CustodyBytes& value, std::shared_ptr<const std::atomic<bool>> cancellation) {
    CustodyMetadataCommit result;
    result.context = context; result.baseGeneration = base;
    bool publicationStarted = false;
    const auto reject = [&](CustodyFileError error, std::uint32_t native = 0) {
        result.error = error; result.nativeError = native;
        if (publicationStarted) result.state = CustodyCommitState::ambiguous;
        result.snapshot.reset(); // Error return must not retry an allocating snapshot move.
        if (result.lease) result.lease->blockWrites();
        else result.pin_.reset(); // Failed factory/admission has no retained owner.
        return std::move(result);
    };
    const auto role = static_cast<unsigned>(context.role);
    if (role < static_cast<unsigned>(CustodyRole::manifest) || role > static_cast<unsigned>(CustodyRole::migrationIntent)
        || !cancellation || value.empty() || value.size() > ProtectedCustodyCodec::logicalLimit(context.role)
        || base == (std::numeric_limits<std::uint64_t>::max)()) return reject(CustodyFileError::invalidInput);
    result.targetGeneration = base + 1;
#ifndef _WIN32
    (void)root; (void)package;
    return reject(CustodyFileError::unsupportedPlatform);
#else
    if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
    try {
        result.pin_.emplace();
        if (!*result.pin_) { result.pin_.reset(); return reject(CustodyFileError::allocationFailed); }
        // ponytail: serialize metadata staging (one 256KiB dirty block/process).
        // Split only on measured contention with equally bounded dirty admission.
        static std::mutex staging;
        std::lock_guard<std::mutex> lock(staging);
        if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
        CustodyDirtySlot dirty;
        if (!dirty) return reject(CustodyFileError::allocationFailed, ERROR_NOT_ENOUGH_QUOTA);
        CustodyIndex candidate{base + 1, value.size(), {}};
        const auto count = (value.size() + ProtectedCustodyCodec::blockBytes - 1) / ProtectedCustodyCodec::blockBytes;
        candidate.entries.reserve(count);
        CustodyBytes chunk; chunk.reserve(std::min<std::size_t>(value.size(), ProtectedCustodyCodec::blockBytes));
        struct Wipe { CustodyBytes& bytes; ~Wipe() { if (!bytes.empty()) SecureZeroMemory(bytes.data(), bytes.size()); } } wipe{chunk};
        auto opened = ProtectedCustodyFiles::open(root, package, context,
            base ? CustodyFileAccess::writeExisting : CustodyFileAccess::createNew);
        if (!opened.ok()) return reject(opened.error, opened.nativeError);
        result.lease = std::move(*opened.value);
        if (base) {
            auto current = result.lease->readValidatedSnapshot();
            if (!current.ok()) return reject(current.error, current.nativeError);
            if (current.value->state != CustodySnapshotState::verified || current.value->index.generation != base)
                return reject(CustodyFileError::conflict);
        }
        const auto indexCopies = base ? 1U : 2U;
        const auto peak = value.size() + count * 4096 + indexCopies * ProtectedCustodyCodec::indexEnvelopeLimit(context.role);
        auto reserved = result.lease->checkWriteReserve(peak, static_cast<std::uint32_t>(count) + indexCopies);
        if (!reserved.ok()) return reject(reserved.error, reserved.nativeError);
        std::uint64_t position = 0;
        for (std::size_t offset = 0; offset < value.size(); offset += chunk.size(), ++position) {
            if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
            const auto bytes = std::min<std::size_t>(ProtectedCustodyCodec::blockBytes, value.size() - offset);
            if (!chunk.empty()) SecureZeroMemory(chunk.data(), chunk.size());
            chunk.assign(value.begin() + offset, value.begin() + offset + bytes);
            auto version = result.lease->nextBlockVersion(position);
            if (!version.ok()) return reject(version.error, version.nativeError);
            auto cipher = ProtectedCustodyCodec::sealBlock(context, position, *version.value, chunk);
            if (!cipher.ok()) return reject(codecFileError(cipher.error), cipher.nativeError);
            auto written = result.lease->writeBlock(position, *version.value, static_cast<std::uint32_t>(bytes), *cipher.value);
            if (!written.ok()) return reject(written.error, written.nativeError);
            candidate.entries.push_back({*version.value, *written.value, 0});
        }
        if (!chunk.empty()) SecureZeroMemory(chunk.data(), chunk.size());
        CustodyBytes{}.swap(chunk);
        const auto slot = static_cast<std::uint32_t>(base % 2);
        std::array<CustodyBytes, 2> indices;
        for (unsigned copy = 0; copy < indexCopies; ++copy) {
            auto cipher = ProtectedCustodyCodec::sealIndex(context, base ? slot : copy, candidate);
            if (!cipher.ok()) return reject(codecFileError(cipher.error), cipher.nativeError);
            indices[copy] = std::move(*cipher.value);
        }
        if (cancellation->load()) return reject(CustodyFileError::ioFailed, ERROR_OPERATION_ABORTED);
        for (unsigned copy = 0; copy < indexCopies; ++copy) {
            // Cancellation no longer rolls back publication; finish both birth
            // slots/reopen even when UI/account capability becomes stale.
            publicationStarted = true;
            const auto published = result.lease->publishIndex(base ? slot : copy, indices[copy]);
            if (published.state != CustodyPublishState::published) {
                if (copy == 0 && published.state == CustodyPublishState::notPublished) publicationStarted = false;
                return reject(published.error, published.nativeError);
            }
        }
        indices = {}; // Release writer cipher copies before independent reopen.
        auto reopened = result.lease->readValidatedSnapshot();
        if (!reopened.ok()) return reject(reopened.error, reopened.nativeError);
        const auto& accepted = reopened.value->index;
        if (reopened.value->state != CustodySnapshotState::verified || accepted.generation != candidate.generation
            || accepted.logicalLength != candidate.logicalLength || accepted.entries.size() != candidate.entries.size()
            || !std::equal(accepted.entries.begin(), accepted.entries.end(), candidate.entries.begin(), [](const auto& a, const auto& b) {
                return a.version == b.version && a.envelopeBytes == b.envelopeBytes && a.flags == b.flags;
            })) return reject(CustodyFileError::conflict);
        result.snapshot = std::move(*reopened.value);
        result.state = CustodyCommitState::committed;
        return result;
    } catch (const std::bad_alloc&) { return reject(CustodyFileError::allocationFailed); }
      catch (const std::system_error& error) { return reject(CustodyFileError::ioFailed, static_cast<std::uint32_t>(error.code().value())); }
#endif
}

} // namespace graf::windows
