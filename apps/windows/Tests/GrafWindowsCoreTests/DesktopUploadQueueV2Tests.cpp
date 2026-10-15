#include "../../RecApp/Upload/DesktopUploadQueueService.h"
#include "../../RecApp/Upload/DesktopHttpTransport.h"
#include "../../RecApp/Storage/AtomicFileStore.h"
#include "../../RecApp/Contracts/JsonReader.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <limits>
#include <stdexcept>
#include <cstdlib>
#include <new>

namespace {
std::size_t failAllocationMin = 0, failAllocationMax = 0;
}

// Existing test-executable allocation interception pattern; no production seam.
void* operator new(std::size_t bytes) {
    if (failAllocationMin && bytes >= failAllocationMin && bytes <= failAllocationMax) {
        failAllocationMin = 0;
        throw std::bad_alloc();
    }
    if (auto* memory = std::malloc(bytes ? bytes : 1)) return memory;
    throw std::bad_alloc();
}
void operator delete(void* memory) noexcept { std::free(memory); }
void operator delete(void* memory, std::size_t) noexcept { std::free(memory); }

namespace graf::windows {
// Pure domain data only: cannot create a Candidate/input/native owner or lease.
struct ProtectedUploadQueueValueTestPeer {
    static void replaceFirst(ProtectedUploadQueueValue& value, ProtectedUploadQueueValue::Item row) {
        value.items_.front() = std::move(row);
    }
    static void manualFixture(ProtectedUploadQueueValue& value, ProtectedUploadQueueValue::Item row) {
        value.items_.clear(); value.items_.push_back(std::move(row));
        value.operations_.clear(); value.acknowledgements_.clear();
    }
    static auto decode(std::string_view json, const std::atomic<bool>* cancel) {
        return ProtectedUploadQueueValue::decode(json, cancel);
    }
    static void seedStatuses(ProtectedUploadQueueValue& value) {
        const auto first = value.items_.front();
        value.items_.clear();
        for (unsigned status = 0; status <= 6; ++status) {
            auto row = first;
            row.localRecordingId = "row_";
            row.localRecordingId += static_cast<char>('0' + status);
            row.status = static_cast<UploadQueueStatus>(status);
            row.safeReason = "account_mismatch";
            row.mediaRevisionId = "revision"; row.uploadSessionId = "upload";
            row.serverStatus = "processing"; row.processingStatus = "queued";
            row.mediaRevisionStatus = "accepted";
            value.items_.push_back(std::move(row));
        }
    }
    static void escapedPath(ProtectedUploadQueueValue& value) {
        value.items_[0].packageDirectory = "unicode_\xc3\xa9\\\"\b\f";
    }
    static void deletionFixture(ProtectedUploadQueueValue& value, bool meeting = false) {
        value.items_[0].status = UploadQueueStatus::retry;
        if (meeting) value.items_[0].meetingId = value.operations_[0].targetId;
    }
    static void deletionPhase(ProtectedUploadQueueValue& value, DeletionOperationPhase phase) {
        auto& operation = value.operations_.back();
        operation.phase = phase;
        if (deletionPhaseIsAccepted(phase)) operation.receiptRequestId = "77777777-7777-4777-8777-777777777777";
    }
    static void deletionForeignRows(ProtectedUploadQueueValue& value) {
        auto foreign = value.items_.front(); foreign.localRecordingId = "foreign";
        foreign.ownerWorkspaceId = "99999999-9999-4999-8999-999999999999";
        value.items_.push_back(foreign);
        foreign.localRecordingId = "unowned"; foreign.ownerUserId.clear(); foreign.ownerWorkspaceId.clear();
        value.items_.push_back(std::move(foreign));
    }
    static void purgeFixture(ProtectedUploadQueueValue& value, std::string_view meeting) {
        value.items_[0].meetingId = meeting;
        value.items_[0].status = UploadQueueStatus::uploaded;
        value.acknowledgements_.clear();
    }
};
}

namespace {
void testProtectedPurgeIntent(std::string_view source) {
    using namespace graf::windows;
    const auto baseline = CustodyOwnedMemory::usedBytes();
    {
        auto cancel = std::make_shared<std::atomic<bool>>(false);
        auto decoded = ProtectedUploadQueueValueTestPeer::decode(source, cancel.get()); assert(decoded.ok());
        ProtectedUploadQueueValue value(**decoded.value);
        BasicLocalPurgeTask<CustodyString> task;
        task.taskId = "77777777-7777-4777-8777-777777777777";
        task.meetingId = "88888888-8888-4888-8888-888888888888";
        task.taskType = "purge_local_buffers";
        ProtectedUploadQueueValueTestPeer::purgeFixture(value, task.meetingId);
        const auto row = value.items().front();
        const auto before = value.serialize(cancel); assert(before.ok());
        bool changed = true;
        auto invalid = task; invalid.taskType = "purge_local_exports";
        assert(!value.prepareLocalPurgeTask(invalid, row.ownerUserId, row.ownerWorkspaceId, 2000, changed, cancel.get()) && !changed);
        assert(!value.localPurgeAcknowledged(task));
        assert(value.prepareLocalPurgeTask(task, "99999999-9999-4999-8999-999999999999", row.ownerWorkspaceId, 2000, changed, cancel.get()) && !changed);
        assert(*value.serialize(cancel).value == *before.value);
        assert(value.prepareLocalPurgeTask(task, row.ownerUserId, row.ownerWorkspaceId, 2000, changed, cancel.get()) && changed);
        assert(value.items()[0].status == UploadQueueStatus::uploaded && value.items()[0].safeReason == "local_delete_pending");
        assert(!value.localPurgeAcknowledged(task) && value.purgeAcknowledgements().empty());
        assert(value.prepareLocalPurgeTask(task, row.ownerUserId, row.ownerWorkspaceId, 3000, changed, cancel.get()) && !changed);
        auto bytes = value.serialize(cancel); assert(bytes.ok());
        auto cold = ProtectedUploadQueueValueTestPeer::decode(std::string_view(reinterpret_cast<const char*>(bytes.value->data()), bytes.value->size()), cancel.get());
        assert(cold.ok() && (*cold.value)->items()[0].safeReason == "local_delete_pending" && !(*cold.value)->localPurgeAcknowledged(task));
        cancel->store(true); bool cancelled = false;
        try { (void)value.prepareLocalPurgeTask(task, row.ownerUserId, row.ownerWorkspaceId, 4000, changed, cancel.get()); }
        catch (const json_detail::ParseCancelled&) { cancelled = true; }
        assert(cancelled);
    }
    assert(CustodyOwnedMemory::usedBytes() == baseline);
}
void testProtectedDeletionAnswer(std::string_view source) {
    using namespace graf::windows;
    const auto baseline = CustodyOwnedMemory::usedBytes();
    {
        auto cancel = std::make_shared<std::atomic<bool>>(false);
        const auto decoded = ProtectedUploadQueueValueTestPeer::decode(source, cancel.get()); assert(decoded.ok());
        ProtectedUploadQueueValue seed(**decoded.value);
        ProtectedUploadQueueValueTestPeer::deletionFixture(seed);
        const auto row = seed.items().front(); bool changed = false;
        ProtectedDeletionTargets targets{{DeletionTarget::ownOrigin, row.directoryId}};
        ProtectedDeletionPlan plan;
        assert(seed.planDeletionSelection(targets, row.ownerUserId, row.ownerWorkspaceId,
            "https://example.test", 2000, plan, changed, cancel.get()) && changed && !plan.saved);
        ProtectedUploadQueueValueTestPeer::deletionForeignRows(seed);
        const auto expected = seed.deletionOperations().back();
        const auto before = seed.serialize(cancel); assert(before.ok());
        BasicDeletionWireResult<CustodyString> wire;
        wire.status = 200;
        wire.body = "{\"receipt_type\":\"meeting_deletion\",\"request_id\":\"77777777-7777-4777-8777-777777777777\","
            "\"meeting_id\":\"88888888-8888-4888-8888-888888888888\",\"phase\":\"accepted\",\"local_recording_id\":\"";
        wire.body += row.directoryId; wire.body += "\"}";
        for (unsigned field = 0; field != 13; ++field) {
            ProtectedUploadQueueValue candidate(seed); auto stale = expected;
            switch (field) {
            case 0: stale.operationId = "99999999-9999-4999-8999-999999999999"; break;
            case 1: stale.actorUserId = "99999999-9999-4999-8999-999999999999"; break;
            case 2: stale.workspaceId = "99999999-9999-4999-8999-999999999999"; break;
            case 3: stale.serverOrigin = "https://other.example.test"; break;
            case 4: stale.target = DeletionTarget::meeting; break;
            case 5: stale.targetId = "another-target"; break;
            case 6: stale.phase = DeletionOperationPhase::sending; break;
            case 7: stale.receiptRequestId = "99999999-9999-4999-8999-999999999999"; break;
            case 8: ++stale.requestedAtMs; break;
            case 9: ++stale.updatedAtMs; break;
            case 10: ++stale.attemptCount; break;
            case 11: ++stale.nextAttemptAtMs; break;
            case 12: stale.safeReason = "connection"; break;
            }
            changed = true;
            assert(!candidate.applyDeletionAnswer(stale, wire, 3000, changed, cancel.get()) && !changed);
            const auto bytes = candidate.serialize(cancel); assert(bytes.ok() && *bytes.value == *before.value);
        }
        ProtectedUploadQueueValue candidate(seed);
        assert(!candidate.applyDeletionAnswer(expected, wire, 3000, changed, nullptr));
        cancel->store(true); bool cancelled = false;
        try { (void)candidate.applyDeletionAnswer(expected, wire, 3000, changed, cancel.get()); }
        catch (const json_detail::ParseCancelled&) { cancelled = true; }
        assert(cancelled); cancel->store(false);
        {
            ProtectedUploadQueueValue discarded(seed);
            CustodyAllocator<char> allocator;
            const auto count = CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes();
            auto* reservation = allocator.allocate(count); bool denied = false;
            try { (void)discarded.applyDeletionAnswer(expected, wire, 3000, changed, cancel.get()); }
            catch (const std::bad_alloc&) { denied = true; }
            allocator.deallocate(reservation, count); assert(denied);
        }
        assert(candidate.applyDeletionAnswer(expected, wire, 3000, changed, cancel.get()) && changed);
        const auto accepted = candidate.deletionOperations().back();
        assert(accepted.phase == DeletionOperationPhase::accepted && accepted.attemptCount == 1 &&
            accepted.receiptRequestId == "77777777-7777-4777-8777-777777777777" && accepted.nextAttemptAtMs == 0);
        assert(candidate.items().front().meetingId == "88888888-8888-4888-8888-888888888888" &&
            candidate.items().front().updatedAtMs == 3000);
        assert(candidate.items()[1].meetingId == seed.items()[1].meetingId &&
            candidate.items()[2].meetingId == seed.items()[2].meetingId);
        const auto once = candidate.serialize(cancel); assert(once.ok());
        assert(candidate.applyDeletionAnswer(accepted, wire, 4000, changed, cancel.get()) && !changed);
        const auto twice = candidate.serialize(cancel); assert(twice.ok() && *once.value == *twice.value);
        wire.status = 401;
        assert(!candidate.applyDeletionAnswer(accepted, wire, 4000, changed, cancel.get()));
        ProtectedUploadQueueValue retry(seed); wire.status = 429; wire.retryAfterSeconds = 60;
        assert(retry.applyDeletionAnswer(expected, wire, 3000, changed, cancel.get()) && changed);
        assert(retry.deletionOperations().back().phase == DeletionOperationPhase::resolving &&
            retry.deletionOperations().back().safeReason == "rate_limit" &&
            retry.deletionOperations().back().nextAttemptAtMs == 63000);
        const auto unchanged = seed.serialize(cancel); assert(unchanged.ok() && *unchanged.value == *before.value);
    }
    assert(CustodyOwnedMemory::usedBytes() == baseline);
}
void testProtectedDeletionIntent(std::string_view source) {
    using namespace graf::windows;
    const auto baseline = CustodyOwnedMemory::usedBytes();
    {
        auto cancel = std::make_shared<std::atomic<bool>>(false);
        const auto decoded = ProtectedUploadQueueValueTestPeer::decode(source, cancel.get()); assert(decoded.ok());
        const auto& published = **decoded.value;
        ProtectedUploadQueueValue candidate(published);
        ProtectedUploadQueueValueTestPeer::deletionFixture(candidate);
        const auto expected = candidate.items().front();
        ProtectedDeletionTargets targets{{DeletionTarget::ownOrigin, expected.directoryId}};
        ProtectedDeletionPlan plan;
        const auto before = candidate.serialize(cancel); assert(before.ok());
        assert(candidate.prepareUploads(false, 10, 1900, cancel.get()).size() == 1);
        bool changed = true;
        for (unsigned field = 0; field != 3; ++field) {
            auto user = expected.ownerUserId, workspace = expected.ownerWorkspaceId;
            auto selection = targets;
            if (field == 0) user = "99999999-9999-4999-8999-999999999999";
            if (field == 1) workspace = "99999999-9999-4999-8999-999999999999";
            if (field == 2) selection.front().targetId = "absent-directory";
            assert(!candidate.planDeletionSelection(selection, user, workspace, "https://example.test",
                2000, plan, changed, cancel.get()) && !changed);
            const auto bytes = candidate.serialize(cancel); assert(bytes.ok() && *bytes.value == *before.value);
        }
        const auto prepare = [&](auto& value, std::string_view origin, std::uint64_t now, const std::atomic<bool>* cancellation) {
            return value.planDeletionSelection(targets, expected.ownerUserId, expected.ownerWorkspaceId,
                origin, now, plan, changed, cancellation);
        };
        assert(!prepare(candidate, "file:///tmp", 2000, cancel.get()) && !changed);
        assert(!prepare(candidate, "https://example.test", 2000, nullptr));
        cancel->store(true); bool cancelled = false;
        try { (void)prepare(candidate, "https://example.test", 2000, cancel.get()); }
        catch (const json_detail::ParseCancelled&) { cancelled = true; }
        assert(cancelled); cancel->store(false);
        assert(prepare(candidate, "https://example.test", 2000, cancel.get()) && changed && !plan.saved);
        assert(candidate.deletionOperations().back().targetId == expected.directoryId && expected.directoryId != expected.localRecordingId);
        assert(candidate.deletionBlocks(expected) && candidate.prepareUploads(false, 10, 2100, cancel.get()).empty());
        auto foreign = expected; foreign.ownerWorkspaceId = "99999999-9999-4999-8999-999999999999";
        assert(!candidate.deletionBlocks(foreign));
        // Domain fixtures only: no server acceptance/purge authority is forged.
        for (const auto phase : {DeletionOperationPhase::queued, DeletionOperationPhase::accepted,
                                 DeletionOperationPhase::verified, DeletionOperationPhase::rejected}) {
            ProtectedUploadQueueValueTestPeer::deletionPhase(candidate, phase);
            const auto once = candidate.serialize(cancel); assert(once.ok());
            assert(prepare(candidate, "https://example.test", 3000, cancel.get()) && !changed && !plan.saved);
            const auto twice = candidate.serialize(cancel); assert(twice.ok() && *once.value == *twice.value);
            assert(candidate.deletionBlocks(expected) == (phase != DeletionOperationPhase::rejected));
            assert(!prepare(candidate, "https://other.example.test", 3000, cancel.get()));
        }
        ProtectedUploadQueueValue meeting(published);
        ProtectedUploadQueueValueTestPeer::deletionFixture(meeting, true);
        const auto row = meeting.items().front();
        assert(prepare(meeting, "https://example.test", 2000, cancel.get()) && !changed);
        assert(meeting.deletionOperations().size() == 1 && meeting.deletionBlocks(row));
        assert(published.deletionOperations().size() == 1 && !published.deletionBlocks(published.items().front()));
    }
    assert(CustodyOwnedMemory::usedBytes() == baseline);
}
void testProtectedUploadResult(std::string_view source) {
    using namespace graf::windows;
    const auto baseline = CustodyOwnedMemory::usedBytes();
    {
        auto cancel = std::make_shared<std::atomic<bool>>(false);
        const auto decoded = ProtectedUploadQueueValueTestPeer::decode(source, cancel.get());
        assert(decoded.ok());
        const auto& published = **decoded.value;
        const auto before = published.serialize(cancel); assert(before.ok());
        const auto& expected = published.items().front();
        struct Case { DesktopTransportStatus status; const char* classification; const char* reason;
            std::uint32_t delay; UploadQueueStatus next; const char* nextReason; bool spend; };
        const Case cases[]{
            {DesktopTransportStatus::uploaded, "", "", 0, UploadQueueStatus::uploaded, "", false},
            {DesktopTransportStatus::authRequired, "", "", 0, UploadQueueStatus::needsAuth, "auth_required", false},
            {DesktopTransportStatus::authRequired, "", "account_mismatch", 0, UploadQueueStatus::needsAuth, "account_mismatch", false},
            {DesktopTransportStatus::invalidPackage, "", "", 0, UploadQueueStatus::quarantined, "invalid_package", false},
            {DesktopTransportStatus::serverRejected, "not_retryable", "unsupported_recording_source_kind", 0,
                UploadQueueStatus::blocked, "unsupported_recording_source_kind", false},
            {DesktopTransportStatus::serverRejected, "not_retryable", "unknown", 0, UploadQueueStatus::blocked, "not_retryable", false},
            {DesktopTransportStatus::serverRejected, "paused_until_user_action", "", 0, UploadQueueStatus::needsAuth, "auth_required", false},
            {DesktopTransportStatus::serverRejected, "paused_until_admin_action", "", 0, UploadQueueStatus::blocked, "needs_admin", false},
            {DesktopTransportStatus::serverRejected, "terminal", "", 0, UploadQueueStatus::quarantined, "terminal_undelivered", false},
            {DesktopTransportStatus::serverRejected, "", "", 0, UploadQueueStatus::retry, "server_rejected", true},
            {DesktopTransportStatus::unsupportedPlatform, "", "", 0, UploadQueueStatus::retry, "unsupported_platform", true},
            {DesktopTransportStatus::retryableFailure, "", "", 0, UploadQueueStatus::retry, "transport_unavailable", true},
            {DesktopTransportStatus::retryableFailure, "", "", 60, UploadQueueStatus::retry, "rate_limited", false},
        };
        ProtectedDesktopTransportResult result;
        result.serverTruth.emplace();
        auto& truth = *result.serverTruth;
        truth.localRecordingId = expected.localRecordingId;
        truth.acceptedBytes = {44, 55, 66}; truth.meetingId = "meeting-id";
        truth.mediaRevisionId = "revision-id"; truth.uploadSessionId = "upload-id";
        truth.serverStatus = "uploading"; truth.processingStatus = "queued";
        truth.mediaRevisionStatus = "accepted"; truth.uploadSessionExists = true;
        for (const auto& test : cases) {
            result.status = test.status; result.retryClass = test.classification;
            result.safeReason = test.reason; result.retryAfterSeconds = test.delay;
            ProtectedUploadQueueValue candidate(published);
            assert(candidate.applyUploadResult(expected, result, 2000, cancel.get()));
            const auto& row = candidate.items().front();
            assert(row.status == test.next && row.safeReason == test.nextReason);
            assert(row.attempts == expected.attempts + (test.spend ? 1 : 0));
            assert(row.acceptedBytes == truth.acceptedBytes && row.meetingId == truth.meetingId);
            assert(row.mediaRevisionId == truth.mediaRevisionId && row.uploadSessionId == truth.uploadSessionId);
            assert(row.serverStatus == truth.serverStatus && row.processingStatus == truth.processingStatus &&
                row.mediaRevisionStatus == truth.mediaRevisionStatus && row.updatedAtMs == 2000 && candidate.updatedAtMs() == 2000);
            const auto encoded = candidate.serialize(cancel); assert(encoded.ok());
            const auto view = [](const CustodyBytes& b) { return std::string_view(reinterpret_cast<const char*>(b.data()), b.size()); };
            const auto tail = [](std::string_view json) { return json.substr(json.find(",\"deletion_operations\":")); };
            assert(tail(view(*before.value)) == tail(view(*encoded.value)));
            const auto restarted = ProtectedUploadQueueValueTestPeer::decode(view(*encoded.value), cancel.get());
            assert(restarted.ok());
            const auto roundtrip = (*restarted.value)->serialize(cancel);
            assert(roundtrip.ok() && *roundtrip.value == *encoded.value);
        }
        const auto unchanged = [&](const ProtectedUploadQueueValue& candidate) {
            const auto bytes = candidate.serialize(cancel);
            assert(bytes.ok() && *bytes.value == *before.value);
        };
        result.status = DesktopTransportStatus::retryableFailure;
        for (unsigned field = 0; field < 8; ++field) {
            auto stale = expected;
            switch (field) {
            case 0: stale.localRecordingId += "_stale"; break;
            case 1: stale.directoryId += "_stale"; break;
            case 2: stale.sessionId += "_stale"; break;
            case 3: stale.packageDirectory += "_stale"; break;
            case 4: stale.ownerUserId += "_stale"; break;
            case 5: stale.ownerWorkspaceId += "_stale"; break;
            case 6: stale.status = UploadQueueStatus::retry; break;
            case 7: ++stale.attempts; break;
            }
            ProtectedUploadQueueValue candidate(published);
            assert(!candidate.applyUploadResult(stale, result, 2000, cancel.get())); unchanged(candidate);
        }
        ProtectedUploadQueueValue rejected(published);
        assert(!rejected.applyUploadResult(expected, result, 2000, nullptr)); unchanged(rejected);
        result.status = static_cast<DesktopTransportStatus>(-1);
        assert(!rejected.applyUploadResult(expected, result, 2000, cancel.get())); unchanged(rejected);
        result.status = DesktopTransportStatus::authRequired; result.safeReason = "unsafe\nreason";
        assert(!rejected.applyUploadResult(expected, result, 2000, cancel.get())); unchanged(rejected);
        result.status = DesktopTransportStatus::uploaded;
        truth.localRecordingId = "foreign";
        assert(rejected.applyUploadResult(expected, result, 2000, cancel.get()));
        assert(rejected.items().front().acceptedBytes == expected.acceptedBytes && rejected.items().front().meetingId.empty());
        ProtectedUploadQueueValue cancelled(published);
        cancel->store(true);
        bool stopped = false;
        try { (void)cancelled.applyUploadResult(expected, result, 2000, cancel.get()); }
        catch (const json_detail::ParseCancelled&) { stopped = true; }
        assert(stopped);
        cancel->store(false); unchanged(cancelled); // Pure fixture token, no native flight.
        truth.localRecordingId = expected.localRecordingId;
        truth.meetingId.assign(200, 'a'); // Force charged growth after the byte-count mutation.
        CustodyAllocator<std::uint8_t> allocator;
        const auto pressureBytes = CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes();
        auto* pressure = allocator.allocate(pressureBytes);
        bool refused = false;
        try { (void)cancelled.applyUploadResult(expected, result, 2000, cancel.get()); }
        catch (const std::bad_alloc&) { refused = true; }
        assert(refused);
        allocator.deallocate(pressure, pressureBytes);
        unchanged(published); // A failed private candidate is never published.
    }
    assert(CustodyOwnedMemory::usedBytes() == baseline);
}

void testProtectedLocalRemoval(std::string_view source) {
    using namespace graf::windows;
    const auto baseline = CustodyOwnedMemory::usedBytes();
    {
        auto cancel = std::make_shared<std::atomic<bool>>(false);
        const auto decoded = ProtectedUploadQueueValueTestPeer::decode(source, cancel.get()); assert(decoded.ok());
        const auto& published = **decoded.value;
        const auto owner = std::string_view(published.items().front().ownerUserId);
        const auto workspace = std::string_view(published.items().front().ownerWorkspaceId);
        const auto before = published.serialize(cancel); assert(before.ok());
        const auto now = published.updatedAtMs() + 2000;
        auto row = published.items().front(); row.directoryId = row.localRecordingId;
        row.meetingId = "meeting"; row.mediaRevisionId = "revision"; row.uploadSessionId = "upload";
        row.serverStatus = "uploaded"; row.processingStatus = "queued"; row.mediaRevisionStatus = "accepted";
        row.acceptedBytes = {11, 22, 33}; row.attempts = 7;
        row.safeReason = "retry_budget_exhausted";
        const auto fixture = [&](auto item) { auto v = published; ProtectedUploadQueueValueTestPeer::replaceFirst(v, std::move(item)); return v; };
        for (unsigned status = 0; status != 7; ++status) {
            row.status = static_cast<UploadQueueStatus>(status);
            auto value = fixture(row);
            ProtectedDeletionPlan plan; bool changed = false;
            const bool allowed = row.status != UploadQueueStatus::uploading;
            assert(value.canLocalRemoval(0, owner, workspace) == allowed);
            assert(value.planLocalRemoval(0, owner, workspace, now, plan, changed, cancel.get()) == allowed);
            if (!allowed) continue;
            assert(changed && plan.requests.empty() && plan.operationIds.empty() && plan.localOnly.size() == 1);
            const auto& after = value.items().front();
            assert(after.status == UploadQueueStatus::quarantined && after.safeReason == "local_delete_pending");
            assert(after.localRecordingId == row.localRecordingId && after.directoryId == row.directoryId && after.sessionId == row.sessionId &&
                after.packageDirectory == row.packageDirectory && after.ownerUserId == row.ownerUserId && after.ownerWorkspaceId == row.ownerWorkspaceId);
            assert(after.meetingId == row.meetingId && after.mediaRevisionId == row.mediaRevisionId && after.uploadSessionId == row.uploadSessionId &&
                after.serverStatus == row.serverStatus && after.processingStatus == row.processingStatus && after.mediaRevisionStatus == row.mediaRevisionStatus &&
                after.attempts == row.attempts && after.acceptedBytes == row.acceptedBytes);
            const auto saved = value.serialize(cancel); assert(saved.ok());
            for (const auto field : {"deletion_operations", "purge_acknowledgements"}) {
                const auto oldFields = json_detail::JsonReader<>(std::string_view(reinterpret_cast<const char*>(before.value->data()), before.value->size())).read();
                const auto newFields = json_detail::JsonReader<>(std::string_view(reinterpret_cast<const char*>(saved.value->data()), saved.value->size())).read();
                assert(oldFields && newFields && oldFields->at(field) == newFields->at(field));
            }
            const auto cold = ProtectedUploadQueueValueTestPeer::decode({reinterpret_cast<const char*>(saved.value->data()), saved.value->size()}, cancel.get()); assert(cold.ok());
            assert(!(*cold.value)->canLocalRemoval(0, owner, workspace) && (*cold.value)->canLocalRemoval(0, owner, workspace, true));
            assert(value.planLocalRemoval(0, owner, workspace, now + 1, plan, changed, cancel.get(), true) && !changed);
            assert(*value.serialize(cancel).value == *saved.value);
        }
        row.status = UploadQueueStatus::retry;
        for (unsigned invalid = 0; invalid != 6; ++invalid) {
            auto wrong = row;
            if (invalid == 0) wrong.ownerUserId.clear();
            if (invalid == 1) wrong.ownerWorkspaceId.clear();
            if (invalid == 2) wrong.ownerUserId = "99999999-9999-4999-8999-999999999999";
            if (invalid == 3) wrong.ownerWorkspaceId = "99999999-9999-4999-8999-999999999999";
            if (invalid == 4) wrong.directoryId = "../outside";
            if (invalid == 5) wrong.safeReason = "local_delete_pending";
            auto value = fixture(wrong); ProtectedDeletionPlan plan; bool changed = false;
            assert(!value.canLocalRemoval(0, owner, workspace));
            assert(!value.planLocalRemoval(0, owner, workspace, now, plan, changed, cancel.get()) && !changed);
        }
        auto value = fixture(row); ProtectedDeletionPlan plan; bool changed = false;
        assert(!value.planLocalRemoval(value.items().size(), owner, workspace, now, plan, changed, cancel.get()));
        assert(!value.planLocalRemoval(0, "invalid", workspace, now, plan, changed, cancel.get()));
        assert(!value.planLocalRemoval(0, owner, workspace, 0, plan, changed, cancel.get()));
        assert(!value.planLocalRemoval(0, owner, workspace, now, plan, changed, nullptr));
        assert(!value.planLocalRemoval(0, owner, workspace, now, plan, changed, cancel.get(), true));
        cancel->store(true); bool stopped = false;
        try { (void)value.planLocalRemoval(0, owner, workspace, now, plan, changed, cancel.get()); }
        catch (const json_detail::ParseCancelled&) { stopped = true; }
        assert(stopped); cancel->store(false);
        assert(*published.serialize(cancel).value == *before.value);
    }
    assert(CustodyOwnedMemory::usedBytes() == baseline);
}

void testProtectedManualSend(std::string_view source) {
    using namespace graf::windows;
    const auto baseline = CustodyOwnedMemory::usedBytes();
    {
        auto cancel = std::make_shared<std::atomic<bool>>(false);
        const auto decoded = ProtectedUploadQueueValueTestPeer::decode(source, cancel.get()); assert(decoded.ok());
        const auto& published = **decoded.value;
        const auto owner = std::string_view(published.items().front().ownerUserId);
        const auto workspace = std::string_view(published.items().front().ownerWorkspaceId);
        const std::string_view foreign = "99999999-9999-4999-8999-999999999999";
        auto row = published.items().front();
        row.status = UploadQueueStatus::retry; row.attempts = 8; row.safeReason = "retry_budget_exhausted";
        row.meetingId = "meeting"; row.mediaRevisionId = "revision"; row.uploadSessionId = "upload";
        row.serverStatus = "uploading"; row.processingStatus = "queued"; row.mediaRevisionStatus = "pending";
        row.acceptedBytes = {11, 22, 33};
        const auto owned = row;
        const auto fixture = [&](const auto& item) {
            ProtectedUploadQueueValue value(published);
            ProtectedUploadQueueValueTestPeer::manualFixture(value, item);
            return value;
        };
        const auto reject = [&](const auto& item, std::string_view user, std::string_view scope, bool confirmed = true) {
            auto value = fixture(item);
            const auto before = value.serialize(cancel); assert(before.ok());
            assert(!value.prepareManualSend(0, user, scope, confirmed, 2000, cancel.get()));
            const auto after = value.serialize(cancel); assert(after.ok() && *after.value == *before.value);
        };
        for (const auto status : {UploadQueueStatus::pending, UploadQueueStatus::retry,
                                  UploadQueueStatus::needsAuth, UploadQueueStatus::blocked}) {
            row = owned; row.status = status;
            auto value = fixture(row);
            assert(value.prepareManualSend(0, owner, workspace, false, 2000, cancel.get()));
            const auto& next = value.items().front();
            assert(next.status == UploadQueueStatus::retry && next.attempts == 0 && next.safeReason == "manual_retry");
            assert(next.acceptedBytes == row.acceptedBytes && next.localRecordingId == row.localRecordingId &&
                next.directoryId == row.directoryId && next.sessionId == row.sessionId && next.packageDirectory == row.packageDirectory &&
                next.meetingId == row.meetingId && next.mediaRevisionId == row.mediaRevisionId && next.uploadSessionId == row.uploadSessionId &&
                next.serverStatus == row.serverStatus && next.processingStatus == row.processingStatus && next.mediaRevisionStatus == row.mediaRevisionStatus);
            assert(next.ownerUserId == row.ownerUserId && next.ownerWorkspaceId == row.ownerWorkspaceId &&
                next.updatedAtMs == 2000 && value.updatedAtMs() == 2000);
            const auto bytes = value.serialize(cancel); assert(bytes.ok());
            const auto cold = ProtectedUploadQueueValueTestPeer::decode(
                {reinterpret_cast<const char*>(bytes.value->data()), bytes.value->size()}, cancel.get());
            assert(cold.ok() && (*cold.value)->items().front().acceptedBytes == row.acceptedBytes);
        }
        for (const auto reason : {"not_retryable", "unsupported_recording_source_kind", "invalid_recording_source_mode", "local_delete_pending"}) {
            row = owned; row.safeReason = reason; reject(row, owner, workspace);
        }
        row = owned; row.status = UploadQueueStatus::blocked; row.safeReason = "admin_paused";
        auto paused = fixture(row); assert(paused.prepareManualSend(0, owner, workspace, false, 2000, cancel.get()));
        for (const auto status : {UploadQueueStatus::uploading, UploadQueueStatus::uploaded, UploadQueueStatus::quarantined}) {
            row = owned; row.status = status; reject(row, owner, workspace);
        }
        reject(owned, foreign, workspace); reject(owned, owner, foreign);
        reject(owned, "", workspace); reject(owned, owner, "bad");
        row = owned; row.ownerUserId.clear(); reject(row, owner, workspace);
        row = owned; row.ownerWorkspaceId.clear(); reject(row, owner, workspace);
        row = owned; row.ownerUserId.clear(); row.ownerWorkspaceId.clear();
        row.attempts = 0; row.acceptedBytes = {}; row.meetingId.clear(); row.uploadSessionId.clear();
        row.mediaRevisionId.clear(); row.serverStatus.clear(); row.processingStatus.clear(); row.mediaRevisionStatus.clear();
        const auto pristine = row;
        reject(pristine, owner, workspace, false);
        auto claimed = fixture(pristine);
        assert(claimed.prepareManualSend(0, owner, workspace, true, 2000, cancel.get()));
        assert(std::string_view(claimed.items().front().ownerUserId) == owner &&
            std::string_view(claimed.items().front().ownerWorkspaceId) == workspace);
        for (unsigned history = 0; history != 9; ++history) {
            row = pristine;
            switch (history) {
                case 0: row.attempts = 1; break;
                case 1: row.acceptedBytes[0] = 1; break;
                case 2: row.acceptedBytes[1] = 1; break;
                case 3: row.acceptedBytes[2] = 1; break;
                case 4: row.meetingId = "meeting"; break;
                case 5: row.uploadSessionId = "upload"; break;
                case 6: row.mediaRevisionId = "revision"; break;
                case 7: row.serverStatus = "processing"; break;
                case 8: row.processingStatus = "queued"; break;
            }
            reject(row, owner, workspace);
        }
        row = pristine; row.mediaRevisionStatus = "accepted"; reject(row, owner, workspace);
        auto invalid = fixture(owned);
        assert(!invalid.prepareManualSend(1, owner, workspace, true, 2000, cancel.get()));
        assert(!invalid.prepareManualSend(0, owner, workspace, true, 0, cancel.get()));
        assert(!invalid.prepareManualSend(0, owner, workspace, true, 2000, nullptr));
        ProtectedUploadQueueValue deleting(published);
        ProtectedUploadQueueValueTestPeer::deletionFixture(deleting, true);
        assert(deleting.deletionBlocks(deleting.items().front()));
        assert(!deleting.prepareManualSend(0, owner, workspace, true, 2000, cancel.get()));
        auto cancelled = fixture(pristine);
        const auto before = cancelled.serialize(cancel); assert(before.ok());
        cancel->store(true); bool stopped = false;
        try { (void)cancelled.prepareManualSend(0, owner, workspace, true, 2000, cancel.get()); }
        catch (const json_detail::ParseCancelled&) { stopped = true; }
        assert(stopped); cancel->store(false);
        const auto after = cancelled.serialize(cancel); assert(after.ok() && *after.value == *before.value);
        CustodyAllocator<std::uint8_t> allocator;
        const auto pressureBytes = CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes();
        auto* pressure = allocator.allocate(pressureBytes); bool refused = false;
        try { (void)cancelled.prepareManualSend(0, owner, workspace, true, 2000, cancel.get()); }
        catch (const std::bad_alloc&) { refused = true; }
        allocator.deallocate(pressure, pressureBytes); assert(refused);
        const auto unchanged = published.serialize(cancel); assert(unchanged.ok());
        assert(std::string_view(reinterpret_cast<const char*>(unchanged.value->data()), unchanged.value->size()) == source);
    }
    assert(CustodyOwnedMemory::usedBytes() == baseline);
}

void testProtectedQueueValue(std::string_view source) {
    using namespace graf::windows;
    const auto baseline = CustodyOwnedMemory::usedBytes();
    {
        auto cancel = std::make_shared<std::atomic<bool>>(false);
        auto decoded = ProtectedUploadQueueValueTestPeer::decode(source, cancel.get());
        assert(decoded.ok() && !(*decoded.value)->legacy());
        const auto& published = **decoded.value;
        auto bytes = published.serialize(cancel);
        assert(bytes.ok() && std::string_view(reinterpret_cast<const char*>(bytes.value->data()), bytes.value->size()) == source);
        {
            ProtectedUploadQueueValue inserted(published);
            ProtectedUploadQueueValue::Item row;
            row.localRecordingId = row.directoryId = row.sessionId = "new_recording";
            row.packageDirectory = "C:\\generated\\new_recording";
            assert(inserted.enqueue(row, 2100, cancel.get()));
            assert(inserted.items().size() == published.items().size() + 1 && inserted.updatedAtMs() == 2100);
            assert(inserted.items().back().updatedAtMs == 2100 && published.items().size() == 1);
            assert(!inserted.enqueue(row, 2200, cancel.get()));
            row.localRecordingId = "bad_owner";
            row.ownerUserId = "11111111-1111-4111-8111-111111111111";
            assert(!inserted.enqueue(row, 2200, cancel.get()));
            row.ownerUserId.clear(); row.safeReason = "unsafe\nreason";
            assert(!inserted.enqueue(row, 2200, cancel.get()));
            row.safeReason.clear(); row.packageDirectory.clear();
            assert(!inserted.enqueue(row, 2200, cancel.get()));
            const auto encoded = inserted.serialize(cancel); assert(encoded.ok());
            const auto loaded = ProtectedUploadQueueValueTestPeer::decode(
                {reinterpret_cast<const char*>(encoded.value->data()), encoded.value->size()}, cancel.get());
            assert(loaded.ok() && (*loaded.value)->items().size() == inserted.items().size());
            cancel->store(true);
            row.packageDirectory = "C:\\generated\\cancelled";
            bool refused = false;
            try { (void)inserted.enqueue(row, 2300, cancel.get()); }
            catch (const json_detail::ParseCancelled&) { refused = true; }
            assert(refused && inserted.items().size() == published.items().size() + 1);
            cancel->store(false); // Pure data fixture, no native operation in flight.
        }
        ProtectedUploadQueueValue copy(published);
        assert(!copy.requeueNeedsAuth(2000, cancel.get()) && copy.updatedAtMs() == published.updatedAtMs());
        ProtectedUploadQueueValueTestPeer::seedStatuses(copy);
        auto before = copy.serialize(cancel);
        assert(before.ok());
        auto immutable = ProtectedUploadQueueValueTestPeer::decode(
            {reinterpret_cast<const char*>(before.value->data()), before.value->size()}, cancel.get());
        assert(immutable.ok());
        assert(copy.requeueNeedsAuth(2000, cancel.get()) && copy.updatedAtMs() == 2000);
        for (unsigned index = 0; index <= 6; ++index) {
            const auto& old = (*immutable.value)->items()[index];
            const auto& row = copy.items()[index];
            assert(old.status == static_cast<UploadQueueStatus>(index));
            assert(row.status == (index == 2 ? UploadQueueStatus::retry : old.status));
            assert(row.safeReason == (index == 2 ? "auth_recovered" : "account_mismatch"));
            assert(row.updatedAtMs == (index == 2 ? 2000 : old.updatedAtMs));
            assert(row.localRecordingId == old.localRecordingId && row.directoryId == old.directoryId &&
                row.sessionId == old.sessionId && row.packageDirectory == old.packageDirectory &&
                row.acceptedBytes == old.acceptedBytes && row.attempts == old.attempts &&
                row.ownerUserId == old.ownerUserId && row.ownerWorkspaceId == old.ownerWorkspaceId &&
                row.meetingId == old.meetingId && row.mediaRevisionId == old.mediaRevisionId &&
                row.uploadSessionId == old.uploadSessionId && row.serverStatus == old.serverStatus &&
                row.processingStatus == old.processingStatus && row.mediaRevisionStatus == old.mediaRevisionStatus);
        }
        auto changed = copy.serialize(cancel);
        assert(changed.ok());
        const auto tail = [](const CustodyBytes& value) {
            auto view = std::string_view(reinterpret_cast<const char*>(value.data()), value.size());
            return view.substr(view.find(",\"deletion_operations\":"));
        };
        assert(tail(*before.value) == tail(*changed.value)); // All operation/ACK fields unchanged.
        assert(published.items().size() == 1 && published.items()[0].status == UploadQueueStatus::uploaded);
        assert(!copy.requeueNeedsAuth(3000, cancel.get()) && copy.updatedAtMs() == 2000);
        auto unchanged = copy.serialize(cancel);
        assert(unchanged.ok() && *unchanged.value == *changed.value);
        auto legacy = std::string(source.substr(0, source.find("],\"updated_at_ms\":") + 1)) + "}";
        legacy.replace(legacy.find("desktop-upload-queue.v3"), 23, "desktop-upload-queue.v2");
        auto v2 = ProtectedUploadQueueValueTestPeer::decode(legacy, cancel.get());
        assert(v2.ok() && (*v2.value)->legacy() && (*v2.value)->deletionOperations().empty());
        auto v3 = (*v2.value)->serialize(cancel);
        assert(v3.ok() && std::string_view(reinterpret_cast<const char*>(v3.value->data()), v3.value->size()).find(
            "desktop-upload-queue.v3") != std::string_view::npos);
        ProtectedUploadQueueValueTestPeer::escapedPath(copy);
        auto escaped = copy.serialize(cancel);
        assert(escaped.ok());
        auto roundtrip = ProtectedUploadQueueValueTestPeer::decode(
            {reinterpret_cast<const char*>(escaped.value->data()), escaped.value->size()}, cancel.get());
        assert(roundtrip.ok() && (*roundtrip.value)->items()[0].packageDirectory == copy.items()[0].packageDirectory);
        assert(!copy.serialize({}).ok());
        cancel->store(true);
        auto stopped = copy.serialize(cancel);
        assert(!stopped.ok() && stopped.error == CustodyFileError::ioFailed && stopped.nativeError == 995);
        bool cancelled = false;
        try { (void)copy.requeueNeedsAuth(4000, cancel.get()); }
        catch (const json_detail::ParseCancelled&) { cancelled = true; }
        assert(cancelled && copy.updatedAtMs() == 2000);
        cancel->store(false); // Test token only; no active native worker.
        CustodyAllocator<std::uint8_t> allocator;
        const auto pressureBytes = CustodyOwnedMemory::limit - CustodyOwnedMemory::usedBytes();
        auto* pressure = allocator.allocate(pressureBytes);
        bool refusedCopy = false;
        try { ProtectedUploadQueueValue refused(published); }
        catch (const std::bad_alloc&) { refusedCopy = true; }
        assert(refusedCopy && CustodyOwnedMemory::usedBytes() == CustodyOwnedMemory::limit);
        auto refused = copy.serialize(cancel);
        assert(!refused.ok() && refused.error == CustodyFileError::allocationFailed);
        allocator.deallocate(pressure, pressureBytes);
        assert(copy.serialize(cancel).ok());
    }
    assert(CustodyOwnedMemory::usedBytes() == baseline);
}

void testOwners(const std::filesystem::path& root) {
    using namespace graf::windows;
    const DesktopAccountIdentity owner{
        "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"};
    const auto path = root / "owner-queue.json";
    DesktopUploadQueueService queue(path, root);
    assert(queue.load());
    assert(queue.enqueue({"legacy", "directory", "session", root / "recording", UploadQueueStatus::pending, {}, 0, ""}));
    const auto read = [&] {
        std::ifstream file(path, std::ios::binary);
        return std::string(std::istreambuf_iterator<char>(file), std::istreambuf_iterator<char>());
    };
    auto legacy = read();
    const std::string emptyOwners = R"(,"owner_user_id":"","owner_workspace_id":"")";
    const auto at = legacy.find(emptyOwners);
    assert(at != std::string::npos);
    legacy.erase(at, emptyOwners.size());
    assert(AtomicFileStore::writeWithinRoot(root, path, legacy).ok());
    assert(queue.load());
    assert(queue.items()[0].ownerUserId.empty() && queue.items()[0].ownerWorkspaceId.empty());
    assert(!queue.assignOwner("absent", owner));
    assert(!queue.assignOwner("legacy", {}));
    assert(!queue.assignOwner("legacy", {owner.userId, "invalid"}));
    assert(queue.markNeedsAuth("legacy", "local_owner_unclaimed"));
    assert(queue.assignOwner("legacy", owner));
    assert(queue.items()[0].status == UploadQueueStatus::pending);
    assert(queue.load());
    assert(queue.items()[0].ownerUserId == owner.userId && queue.items()[0].ownerWorkspaceId == owner.workspaceId);
    assert(!queue.assignOwner("legacy", owner));
    assert(!queue.assignOwner("legacy", {owner.workspaceId, owner.userId}));
    assert(queue.markNeedsAuth("legacy", "account_mismatch"));
    assert(queue.requeueNeedsAuth());
    assert(queue.items()[0].ownerUserId == owner.userId);
    assert(queue.load() && queue.items()[0].ownerWorkspaceId == owner.workspaceId);
    assert(!queue.enqueue({"partial", "directory", "session", root / "recording", UploadQueueStatus::pending,
                           {}, 0, "", owner.userId, ""}));
    assert(queue.enqueue({"new", "directory", "session", root / "recording", UploadQueueStatus::pending,
                          {}, 0, "", owner.userId, owner.workspaceId}));
    assert(queue.load() && queue.items()[1].ownerUserId == owner.userId);

    // A malformed/partial/duplicate field is not a legacy row and cannot be claimed.
    for (const auto& suffix : {
        "\"owner_user_id\":\"" + owner.userId + "\"",
        "\"owner_user_id\":null,\"owner_workspace_id\":\"" + owner.workspaceId + "\"",
        "\"owner_user_id\":\"\",\"owner_workspace_id\":\"" + owner.workspaceId + "\"",
        "\"owner_user_id\":\"bad\",\"owner_workspace_id\":\"" + owner.workspaceId + "\"",
        "\"owner_user_id\":\"" + owner.userId + "\",\"owner_user_id\":\"\",\"owner_workspace_id\":\"\"",
        std::string(R"("owner_user_\u0069d":"","owner_workspace_id":"")")}) {
        auto malformed = legacy;
        malformed.insert(malformed.size() - 3, "," + suffix);
        assert(AtomicFileStore::writeWithinRoot(root, path, malformed).ok());
        DesktopUploadQueueService invalid(path, root);
        assert(!invalid.load() && invalid.quarantined());
        assert(!invalid.assignOwner("legacy", owner));
        assert(!invalid.load() && invalid.quarantined()); // Missing ledger + quarantine is not a fresh queue.
        assert(std::filesystem::remove(path.string() + ".quarantine"));
    }

    assert(AtomicFileStore::writeWithinRoot(root, path, legacy).ok());
    DesktopUploadQueueService failing(path, root);
    assert(failing.load());
    std::filesystem::rename(path, root / "owner-backup.json");
    std::filesystem::create_directory(path); // deterministic atomic replacement failure
    assert(!failing.assignOwner("legacy", owner));
    assert(failing.quarantined() && failing.pendingItems(32).empty());
    assert(failing.items()[0].ownerUserId.empty() && failing.items()[0].ownerWorkspaceId.empty());
    assert(!failing.assignOwner("legacy", owner));
    DesktopUploadQueueService saved(root / "owner-backup.json", root);
    assert(saved.load() && saved.items()[0].ownerUserId.empty());
}

void testRetryGuards(const std::filesystem::path& root) {
    using namespace graf::windows;
    std::filesystem::create_directories(root);
    const auto path = root / "queue.json";
    DesktopUploadQueueService queue(path, root);
    assert(queue.load());
    const DesktopAccountIdentity owner{
        "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"};
    for (const auto status : {UploadQueueStatus::uploaded, UploadQueueStatus::quarantined,
                              UploadQueueStatus::uploading, UploadQueueStatus::needsAuth}) {
        const auto id = "recording-" + std::to_string(static_cast<int>(status));
        assert(queue.enqueue({id, id, id, root / id, status, {11, 22, 33}, 8, "original",
            owner.userId, owner.workspaceId}));
        if (status != UploadQueueStatus::needsAuth) assert(!queue.requestRetry(id));
        else {
            assert(queue.requestRetry(id));
            assert(queue.items().back().attempts == 0 && queue.items().back().status == UploadQueueStatus::retry);
            assert((queue.items().back().acceptedBytes == std::array<std::uint64_t, 3>{11, 22, 33}));
            assert(queue.items().back().ownerUserId == owner.userId && queue.items().back().ownerWorkspaceId == owner.workspaceId);
        }
    }
    assert(queue.enqueue({"unclaimed", "directory", "session", root / "unclaimed", UploadQueueStatus::pending, {}, 0, ""}));
    assert(!queue.requestRetry("unclaimed") && !queue.requestRetry("unknown"));
    assert(queue.items().back().ownerUserId.empty());
    assert(queue.enqueue({"overflow", "directory", "session", root / "overflow", UploadQueueStatus::retry,
        {}, std::numeric_limits<std::uint32_t>::max(), "transport_unavailable", owner.userId, owner.workspaceId}));
    assert(queue.markRetry("overflow", "retry_budget_exhausted"));
    assert(queue.items().back().attempts == std::numeric_limits<std::uint32_t>::max());
    assert(queue.enqueue({"failed-write", "directory", "session", root / "failed-write",
        UploadQueueStatus::needsAuth, {11, 22, 33}, 8, "auth_required", owner.userId, owner.workspaceId}));
    std::filesystem::rename(path, root / "backup.json");
    std::filesystem::create_directory(path);
    assert(!queue.requestRetry("failed-write") && queue.quarantined());
    assert(queue.pendingItems(32).empty());
    assert(queue.items().back().status == UploadQueueStatus::needsAuth && queue.items().back().attempts == 8);
    assert(queue.items().back().safeReason == "auth_required");
}

void testInterruptedValidation(const std::filesystem::path& root) {
    using namespace graf::windows;
    std::filesystem::create_directories(root / "custody");
    const auto path = root / "custody" / "queue.json";
    DesktopUploadQueueService queue(path, path.parent_path());
    assert(queue.load());
    assert(queue.enqueue({"interrupted", "directory", "session", path.parent_path() / "package",
        UploadQueueStatus::uploading, {11, 22, 33}, 3, ""}));
    std::string original;
    {
        std::ifstream input(path, std::ios::binary);
        original.assign(std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>());
    }
    const auto malformed = original + " trailing";
    assert(AtomicFileStore::writeWithinRoot(root, path, malformed).ok());
    assert(!queue.load() && queue.quarantined() && queue.pendingItems(32).empty());
    {
        std::ifstream input(path.string() + ".quarantine", std::ios::binary);
        const std::string quarantined(std::istreambuf_iterator<char>(input), {});
        assert(quarantined == malformed); // No partial normalization before full validation.
    }
    // Valid input but recovery cannot atomically write outside the custody root.
    const auto outsideLedger = root / "outside.json";
    assert(AtomicFileStore::writeWithinRoot(root, outsideLedger, original).ok());
    DesktopUploadQueueService cannotPersist(outsideLedger, path.parent_path());
    assert(!cannotPersist.load() && cannotPersist.quarantined() && cannotPersist.pendingItems(32).empty());

    assert(AtomicFileStore::writeWithinRoot(root, path, original).ok());
    assert(queue.load() && queue.items()[0].status == UploadQueueStatus::retry);
    assert(queue.items()[0].attempts == 3 && queue.items()[0].ownerUserId.empty());
    assert((queue.items()[0].acceptedBytes == std::array<std::uint64_t, 3>{11, 22, 33}));
    assert(queue.items()[0].directoryId == "directory" && queue.items()[0].sessionId == "session");
}

void testLoadCandidate(const std::filesystem::path& root) {
    using namespace graf::windows;
    std::filesystem::create_directories(root);
    const auto path = root / "queue.json";
    const DesktopAccountIdentity owner{
        "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"};
    const std::string taskId = "66666666-6666-4666-8666-666666666666";
    const std::string meetingId = "77777777-7777-4777-8777-777777777777";
    const auto read = [](const std::filesystem::path& file) {
        std::ifstream input(file, std::ios::binary);
        return std::string(std::istreambuf_iterator<char>(input), {});
    };
    const auto write = [&](std::string_view bytes) {
        assert(AtomicFileStore::writeWithinRoot(root, path, bytes).ok());
    };
    int failure = 0;
    unsigned writes = 0;
    DesktopUploadQueueService* published = nullptr;
    DesktopUploadQueueService queue(path, root, [&](const auto& store, const auto& file, auto bytes) {
        ++writes;
        if (failure) {
            // No candidate row, retry stamp or receipt has been published while
            // a required rewrite is still unacknowledged.
            assert(published && published->items().size() == 1);
            assert(published->items()[0].status == UploadQueueStatus::uploaded);
            assert(published->deletionOperations().size() == 1);
            assert(published->localPurgeAcknowledgements().size() == 1);
            if (failure == 2) throw std::runtime_error("synthetic writer failure");
            return false;
        }
        return AtomicFileStore::writeWithinRoot(store, file, bytes).ok();
    });
    published = &queue;
    queue.setClock([] { return 1000; });
    assert(queue.load());
    assert(queue.enqueue({"retained", "directory", "session", root / "package",
        UploadQueueStatus::uploaded, {11, 22, 33}, 3, "", owner.userId, owner.workspaceId}));
    std::string operation;
    assert(queue.requestDeletion(DeletionTarget::meeting, meetingId, owner, "https://example.test", operation));
    const auto withoutAck = read(path);
    auto withAck = withoutAck;
    const std::string marker = "\"purge_acknowledgements\":[";
    const auto ackStart = withAck.find(marker);
    assert(ackStart != std::string::npos);
    withAck.insert(ackStart + marker.size(), "{\"task_id\":\"" + taskId +
        "\",\"meeting_id\":\"" + meetingId + "\",\"acknowledged_at_ms\":900}");
    write(withAck);
    assert(queue.load() && queue.hasLocalPurgeAcknowledgement(taskId));
    const auto writesBeforeRead = writes;
    assert(queue.load() && !queue.quarantined()); // RED: stale ACK was mistaken for a duplicate.
    assert(writes == writesBeforeRead && read(path) == withAck);
    assert(queue.items().size() == 1 && queue.deletionOperations().size() == 1);
    assert(queue.localPurgeAcknowledgements().size() == 1);
    testProtectedQueueValue(withAck);
    testProtectedUploadResult(withAck);
    testProtectedManualSend(withAck);
    testProtectedLocalRemoval(withAck);
    testProtectedDeletionIntent(withAck);
    testProtectedDeletionAnswer(withAck);
    testProtectedPurgeIntent(withAck);

    const auto assertRetained = [&] {
        assert(queue.quarantined() && queue.pendingItems(32).empty() && !queue.nextPending());
        assert(queue.items().size() == 1 && queue.items()[0].localRecordingId == "retained");
        assert(queue.items()[0].status == UploadQueueStatus::uploaded && queue.items()[0].attempts == 3);
        assert((queue.items()[0].acceptedBytes == std::array<std::uint64_t, 3>{11, 22, 33}));
        assert(queue.items()[0].ownerUserId == owner.userId && queue.items()[0].updatedAtMs == 1000);
        assert(queue.deletionOperations().size() == 1 && queue.deletionOperations()[0].operationId == operation);
        assert(queue.localPurgeAcknowledgements().size() == 1 &&
            queue.localPurgeAcknowledgements()[0].meetingId == meetingId);
        assert(!queue.markUploaded("retained"));
        unsigned recycled = 0;
        LocalPurgeTask task;
        task.taskId = taskId; task.meetingId = meetingId; task.taskType = "purge_local_buffers";
        const auto completion = queue.completeLocalPurgeTask(task, [&](const auto&) { ++recycled; return true; });
        assert(recycled == 0 && completion.verification == DesktopUploadQueueService::LocalPurgeVerification::unverified);
    };
    const auto replace = [](std::string bytes, std::string_view old, std::string_view value) {
        const auto at = bytes.find(old);
        assert(at != std::string::npos);
        bytes.replace(at, old.size(), value);
        return bytes;
    };
    // Unknown nested fields never replace the values of their containing row.
    auto shadow = withAck;
    shadow.insert(shadow.find("\"items\":[{") + 10,
        R"("extra":{"local_recording_id":"shadow","status":0,"accepted_bytes":[1,2,3],"meeting_id":"shadow"},)");
    shadow.insert(shadow.find("\"deletion_operations\":[{") + 24,
        "\"extra\":{\"target_id\":\"" + taskId + "\",\"phase\":2},");
    shadow.insert(shadow.find("\"purge_acknowledgements\":[{") + marker.size() + 1,
        "\"extra\":{\"task_id\":\"" + meetingId + "\",\"acknowledged_at_ms\":1},");
    write(shadow);
    assert(queue.load() && queue.items()[0].localRecordingId == "retained");
    assert(queue.items()[0].status == UploadQueueStatus::uploaded);
    assert((queue.items()[0].acceptedBytes == std::array<std::uint64_t, 3>{11, 22, 33}));
    assert(queue.items()[0].meetingId.empty() && queue.deletionOperations()[0].targetId == meetingId);
    assert(queue.deletionOperations()[0].phase == DeletionOperationPhase::queued);
    assert(queue.localPurgeAcknowledgements()[0].taskId == taskId &&
        queue.localPurgeAcknowledgements()[0].acknowledgedAtMs == 900);
    assert(read(path) == shadow);
    write(withAck);
    assert(queue.load());

    // A missing required field cannot be supplied by a nested extension.
    for (const auto key : {"local_recording_id", "status", "accepted_bytes", "operation_id", "task_id"}) {
        auto invalid = withAck;
        const auto at = invalid.find(std::string("\"") + key + "\":");
        assert(at != std::string::npos);
        // Wrap just this field; its token remains byte-identical for the old text scanner.
        const auto end = invalid.find(key == std::string_view("accepted_bytes") ? ']' : ',', at);
        assert(end != std::string::npos);
        const auto length = end - at + (key == std::string_view("accepted_bytes") ? 1 : 0);
        invalid.replace(at, length, "\"extra\":{" + invalid.substr(at, length) + "}");
        write(invalid);
        assert(!queue.load());
        assertRetained();
        assert(read(path.string() + ".quarantine") == invalid);
        assert(std::filesystem::remove(path.string() + ".quarantine"));
        write(withAck);
        assert(queue.load());
    }
    for (const auto key : {"meeting_id", "media_revision_id", "upload_session_id", "server_status",
                            "processing_status", "media_revision_status", "updated_at_ms"}) {
        const auto old = std::string("\"") + key + (key == std::string_view("updated_at_ms") ? "\":1000" : "\":\"\"");
        for (const auto value : {"null", "true", "{}", "[]", "1.5", "-1", "1e0"}) {
            const auto invalid = replace(withAck, old, std::string("\"") + key + "\":" + value);
            write(invalid);
            assert(!queue.load());
            assertRetained();
            assert(read(path.string() + ".quarantine") == invalid);
            assert(std::filesystem::remove(path.string() + ".quarantine"));
            write(withAck);
            assert(queue.load());
        }
        // Legacy omission is still valid; a nested optional value stays ignored.
        const auto nested = key == std::string_view("updated_at_ms") ? old : std::string("\"") + key + "\":\"spoof\"";
        const auto omitted = replace(withAck, old, std::string("\"extra\":{") + nested + "}");
        write(omitted);
        assert(queue.load());
        if (key == std::string_view("updated_at_ms")) assert(queue.items()[0].updatedAtMs == 0);
        else assert(queue.items()[0].meetingId.empty() && queue.items()[0].mediaRevisionId.empty() &&
            queue.items()[0].uploadSessionId.empty() && queue.items()[0].serverStatus.empty() &&
            queue.items()[0].processingStatus.empty() && queue.items()[0].mediaRevisionStatus.empty());
        write(withAck);
        assert(queue.load());
    }
    for (const auto value : {R"("retai\nned")", R"("retained\u0000")", R"("\ud800")",
                            R"("\udc00")", R"("retained\"")", R"("retained\\")", R"("retained\/")",
                            R"("\ud83d\ude00")", R"("\q")", "\"raw\nnewline\"", "\"\xc0\xaf\""}) {
        const auto invalid = replace(withAck, R"("local_recording_id":"retained")",
            std::string(R"("local_recording_id":)") + value);
        write(invalid);
        assert(!queue.load());
        assertRetained();
        assert(std::filesystem::remove(path.string() + ".quarantine"));
        write(withAck);
        assert(queue.load());
    }
    for (const auto escape : {R"(\n)", R"(\r)", R"(\t)", R"(\u0000)"}) {
        const auto invalid = replace(withAck, "package\"", std::string("package") + escape + '"');
        write(invalid);
        assert(!queue.load());
        assertRetained();
        assert(read(path.string() + ".quarantine") == invalid);
        assert(std::filesystem::remove(path.string() + ".quarantine"));
        write(withAck);
        assert(queue.load());
    }
    for (const auto value : {"-1", "1.0", "1e0", "\"1\"", "null", "true", "18446744073709551616"}) {
        const auto invalid = replace(withAck, "\"accepted_bytes\":[11,22,33]",
            std::string("\"accepted_bytes\":[") + value + ",22,33]");
        write(invalid);
        assert(!queue.load());
        assertRetained();
        assert(std::filesystem::remove(path.string() + ".quarantine"));
        write(withAck);
        assert(queue.load());
    }
    for (const auto value : {"[]", "[11,22]", "[11,22,33,44]", "[[11],22,33]"}) {
        write(replace(withAck, "\"accepted_bytes\":[11,22,33]", std::string("\"accepted_bytes\":") + value));
        assert(!queue.load());
        assertRetained();
        assert(std::filesystem::remove(path.string() + ".quarantine"));
        write(withAck);
        assert(queue.load());
    }
    auto escaped = replace(withAck, R"("local_recording_id":"retained")", R"("local_recording_id": "\u0072etained")");
    escaped = replace(escaped, R"("server_origin":"https://example.test")",
        R"("server_origin":"https:\/\/example.test")");
    escaped = replace(escaped, "package\"", R"(\u0070ackage")");
    escaped = replace(escaped, "\"accepted_bytes\":[11,22,33]",
        "\"accepted_bytes\": [ 18446744073709551615, 22 , 33 ]");
    escaped = replace(escaped, "\"status\":4", "\"status\": 4");
    write(escaped);
    assert(queue.load() && queue.items()[0].localRecordingId == "retained");
    assert(queue.items()[0].packageDirectory == root / "package");
    assert(queue.deletionOperations()[0].serverOrigin == "https://example.test");
    assert(queue.items()[0].acceptedBytes[0] == std::numeric_limits<std::uint64_t>::max());
    assert(read(path) == escaped);
    assert(queue.markUploaded("retained")); // Writer roundtrip preserves exact logical values.
    assert(queue.load() && queue.items()[0].acceptedBytes[0] == std::numeric_limits<std::uint64_t>::max());
    write(withAck);
    assert(queue.load());
    const auto duplicateAck = replace(withAck, "\"task_id\":\"" + taskId + "\"",
        "\"task_id\":\"" + taskId + "\",\"task_id\":\"" + meetingId + "\"");
    write(duplicateAck);
    assert(!queue.load());
    assertRetained();
    assert(std::filesystem::remove(path.string() + ".quarantine"));
    write(withAck);
    assert(queue.load());
    const auto writesAfterFields = writes;
    auto badItem = withAck;
    badItem.insert(badItem.find("],\"updated_at_ms\":"), ",{\"local_recording_id\":\"broken\"}");
    auto badOperation = withAck;
    badOperation.insert(badOperation.find("],\"purge_acknowledgements\":"), ",{\"operation_id\":\"broken\"}");
    auto badAck = withAck;
    badAck.insert(badAck.size() - 2, ",{\"task_id\":\"broken\"}");
    auto badRoot = withAck;
    const std::string packageKey = "\"package_directory\":\"";
    const auto packageStart = badRoot.find(packageKey) + packageKey.size();
    badRoot.replace(packageStart, badRoot.find('\"', packageStart) - packageStart, "outside-custody-root");
    const std::string documentStamp = "],\"updated_at_ms\":1000";
    const auto stampStart = withAck.find(documentStamp);
    assert(stampStart != std::string::npos);
    const auto badStamp = withAck.substr(0, stampStart + documentStamp.size());
    for (const auto& invalid : {badItem, badOperation, badAck, badRoot, withAck + " trailing", badStamp}) {
        write(invalid);
        assert(!queue.load());
        assertRetained();
        assert(writes == writesAfterFields && read(path.string() + ".quarantine") == invalid);
        assert(std::filesystem::remove(path.string() + ".quarantine"));
        write(withAck);
        assert(queue.load());
    }

    // Huge integers are malformed, not an allocating numeric substring.
    for (const auto& numericMarker : {std::string("\"status\":4"), std::string("\"accepted_bytes\":[11")}) {
        auto allocating = withAck;
        const auto start = allocating.find(numericMarker);
        assert(start != std::string::npos);
        const auto numberStart = start + numericMarker.size() - (numericMarker.back() == '4' ? 1 : 2);
        allocating.replace(numberStart, numericMarker.back() == '4' ? 1 : 2, std::string(1024, '9'));
        write(allocating);
        failAllocationMin = 1024; failAllocationMax = 1100;
        assert(!queue.load() && failAllocationMin == 1024);
        failAllocationMin = 0;
        assertRetained();
        assert(read(path.string() + ".quarantine") == allocating);
        assert(std::filesystem::remove(path.string() + ".quarantine"));
        write(withAck);
        assert(queue.load());
    }
    // A real decoded-string allocation failure preserves source and projection;
    // it must not be swallowed as malformed content by a helper.
    const auto allocating = replace(withAck, R"("safe_reason":"")",
        std::string(R"("safe_reason":")") + std::string(1024, 'a') + '"');
    write(allocating);
    failAllocationMin = 1024; failAllocationMax = 1100;
    assert(!queue.load() && failAllocationMin == 0);
    assertRetained();
    assert(read(path) == allocating && !std::filesystem::exists(path.string() + ".quarantine"));
    write(withAck);
    assert(queue.load());

    // An unreadable ledger is not a reason to clear the published projection.
    const auto backup = root / "backup.json";
    std::filesystem::rename(path, backup);
    std::filesystem::create_directory(path);
    assert(!queue.load());
    assertRetained();
    assert(read(backup) == withAck);
    // load must leave an I/O failure at its original name, not quarantine a directory.
    assert(std::filesystem::is_directory(path));
    assert(std::filesystem::remove(path));
    std::filesystem::rename(backup, path);
    assert(queue.load());

    // A valid replacement without ACKs must not inherit a previous receipt.
    write(withoutAck);
    assert(queue.load() && queue.localPurgeAcknowledgements().empty());
    assert(!queue.hasLocalPurgeAcknowledgement(taskId));
    write(withAck);
    assert(queue.load());

    auto interrupted = withAck;
    const auto status = interrupted.find("\"status\":4");
    assert(status != std::string::npos);
    interrupted.replace(status, std::string("\"status\":4").size(), "\"status\":1");
    for (const int injectedFailure : {1, 2}) {
        failure = injectedFailure;
        write(interrupted);
        assert(!queue.load());
        assertRetained();
        assert(read(path) == interrupted); // Failed rewrite neither renames nor replaces validated input.
        failure = 0;
        write(withAck);
        assert(queue.load());
    }

    // v2 still upgrades through the same writer; failure cannot publish half an upgrade.
    auto v2 = withoutAck.substr(0, withoutAck.find("],\"updated_at_ms\":") + 1) + "}";
    const auto schema = v2.find(std::string(kQueueSchemaVersion));
    assert(schema != std::string::npos);
    v2.replace(schema, std::string(kQueueSchemaVersion).size(), std::string(kQueueSchemaVersionV2));
    failure = 1;
    write(v2);
    assert(!queue.load());
    assertRetained();
    assert(read(path) == v2);
    failure = 0;
    assert(queue.load() && queue.items().size() == 1);
    assert(queue.deletionOperations().empty() && queue.localPurgeAcknowledgements().empty());
    assert(read(path).find(std::string(kQueueSchemaVersion)) != std::string::npos);

    // A previously observed ledger is not virgin after an unexplained disappearance.
    write(withAck);
    assert(queue.load());
    assert(std::filesystem::remove(path));
    assert(!queue.load());
    assertRetained();
    assert(!queue.load()); // A second missing-file observation cannot clear the fence.
    assertRetained();
    write(withAck);
    assert(queue.load());

    // Exact writer cap is accepted; one extra byte is isolated without adopting it.
    auto maximum = withAck;
    maximum.insert(maximum.size() - 1, 4 * 1024 * 1024 - maximum.size(), ' ');
    write(maximum);
    assert(queue.load());
    failAllocationMin = maximum.size(); failAllocationMax = maximum.size() + 64;
    assert(!queue.load() && failAllocationMin == 0);
    assertRetained();
    assert(read(path) == maximum && !std::filesystem::exists(path.string() + ".quarantine"));
    assert(queue.load());
    maximum.insert(maximum.size() - 1, 1, ' ');
    write(maximum);
    assert(!queue.load());
    assertRetained();
    assert(read(path.string() + ".quarantine") == maximum);

    // Even a known empty ledger with a zero stamp cannot silently disappear.
    const auto emptyPath = root / "empty.json";
    const auto empty = "{\"schema_version\":\"" + std::string(kQueueSchemaVersion) +
        "\",\"items\":[],\"updated_at_ms\":0,\"deletion_operations\":[],\"purge_acknowledgements\":[]}";
    assert(AtomicFileStore::writeWithinRoot(root, emptyPath, empty).ok());
    DesktopUploadQueueService knownEmpty(emptyPath, root);
    assert(knownEmpty.load());
    assert(std::filesystem::remove(emptyPath));
    assert(!knownEmpty.load() && knownEmpty.quarantined());
    DesktopUploadQueueService virgin(root / "virgin.json", root);
    assert(virgin.load() && !virgin.quarantined() && virgin.items().empty());
}

void testUploadProgressPercent() {
    using namespace graf::windows;
    // Прогресс собирается из двух половин: принятые сервером байты по дорожкам и
    // вес дорожек локального пакета. Неизмеримый прогресс молчит, а не показывает
    // ноль процентов.
    UploadCustodyItem item;
    item.acceptedBytes = {0, 0, 0};
    const std::array<std::uint64_t, 3> bytes{100, 300, 600};
    assert(DesktopUploadQueueService::uploadProgressPercent(item, bytes) == 0);
    item.acceptedBytes = {100, 300, 600};
    assert(DesktopUploadQueueService::uploadProgressPercent(item, bytes) == 100);
    item.acceptedBytes = {50, 150, 300};
    assert(DesktopUploadQueueService::uploadProgressPercent(item, bytes) == 50);
    // Сервер не может принять больше, чем дорожка весит: иначе прогресс
    // перескочил бы за сто процентов.
    item.acceptedBytes = {100, 300, 900};
    assert(DesktopUploadQueueService::uploadProgressPercent(item, bytes) == 100);
    // Пакет ещё не прочитан: веса дорожек нулевые, и прогресс неизвестен.
    item.acceptedBytes = {10, 10, 10};
    assert(!DesktopUploadQueueService::uploadProgressPercent(item, std::array<std::uint64_t, 3>{}).has_value());
    // Часть дорожек уже принята, часть ещё нет.
    item.acceptedBytes = {100, 0, 0};
    assert(DesktopUploadQueueService::uploadProgressPercent(item, bytes) == 10);
}
} // namespace

int main() {
    using namespace graf::windows;
    const auto root = std::filesystem::temp_directory_path() / "graf-feature-200-queue-root";
    const auto path = root / "desktop-upload-queue.json";
    const auto package = root / "recording";
    const auto outside = root.parent_path() / "graf-feature-200-queue-escape";
    std::filesystem::remove_all(root);
    std::filesystem::remove_all(outside);
    std::filesystem::create_directories(package);
    testOwners(root);
    testUploadProgressPercent();
    testRetryGuards(root / "retry-guards");
    testInterruptedValidation(root / "interrupted-validation");
    testLoadCandidate(root / "load-candidate");
    assert(AtomicFileStore::isWithinRoot(root, package));
    assert(!AtomicFileStore::isWithinRoot(root, root));
    assert(!AtomicFileStore::isWithinRoot(root, outside));
    assert(AtomicFileStore::writeWithinRoot(root, outside / "escape.json", "blocked").error ==
           AtomicFileError::invalidPath);
    DesktopUploadQueueService queue(path, root);
    assert(queue.load());
    assert(queue.enqueue({"recording", "directory", "session", package, UploadQueueStatus::pending, {}, 0, ""}));
    assert(!queue.enqueue({"escape", "directory", "session-escape", outside, UploadQueueStatus::pending, {}, 0, ""}));
    assert(!queue.enqueue({"recording", "directory", "session2", package, UploadQueueStatus::pending, {}, 0, ""}));
    assert(queue.reconcile({"recording", true, true, {10, 20, 30}, false, "meeting-id", {}, {}, {}, {}, {}}));
    assert(queue.items()[0].status == UploadQueueStatus::uploading);
    assert(queue.items()[0].acceptedBytes[1] == 20);
    // The cabinet binds a local row to its server meeting by this id, so it has
    // to survive a restart instead of being relearned from the network.
    assert(queue.items()[0].meetingId == "meeting-id");
    // A later server response must not overwrite the binding, and an unusable
    // id must not reach the ledger.
    assert(queue.reconcile({"recording", true, true, {10, 20, 30}, false, "other-id", {}, {}, {}, {}, {}}));
    assert(queue.items()[0].meetingId == "meeting-id");
    assert(queue.reconcile({"recording", true, true, {10, 20, 30}, false, "not a safe id", {}, {}, {}, {}, {}}));
    assert(queue.items()[0].meetingId == "meeting-id");
    // The rest of the server's fingerprint is written with the row and read back
    // after a restart: which revision the server accepted, which session carries
    // it and how far the meeting and its processing have come. macOS keeps the
    // same values in its queue row.
    {
        graf::windows::UploadServerTruth truth;
        truth.localRecordingId = "recording";
        truth.meetingExists = true;
        truth.uploadSessionExists = true;
        truth.acceptedBytes = {10, 20, 30};
        truth.meetingId = "meeting-id";
        truth.mediaRevisionId = "11111111-2222-3333-4444-555555555555";
        truth.uploadSessionId = "66666666-7777-8888-9999-000000000000";
        truth.serverStatus = "ingested_pending_processing";
        truth.processingStatus = "queued";
        truth.mediaRevisionStatus = "uploaded";
        assert(queue.reconcile(truth));
    }
    // A value the ledger may not hold is refused instead of being written; the
    // values already stored stay untouched.
    {
        graf::windows::UploadServerTruth truth;
        truth.localRecordingId = "recording";
        truth.meetingExists = true;
        truth.uploadSessionExists = true;
        truth.acceptedBytes = {10, 20, 30};
        truth.meetingId = "meeting-id";
        truth.mediaRevisionId = "not a safe id";
        truth.serverStatus = "Not A Safe Status";
        assert(queue.reconcile(truth));
        assert(queue.items()[0].mediaRevisionId == "11111111-2222-3333-4444-555555555555");
        assert(queue.items()[0].serverStatus == "ingested_pending_processing");
    }
    DesktopUploadQueueService restarted(path, root);
    assert(restarted.load());
    assert(restarted.items().size() == 1 && restarted.items()[0].acceptedBytes[2] == 30);
    assert(restarted.items()[0].status == UploadQueueStatus::retry);
    assert(restarted.items()[0].meetingId == "meeting-id");
    assert(restarted.items()[0].mediaRevisionId == "11111111-2222-3333-4444-555555555555");
    assert(restarted.items()[0].uploadSessionId == "66666666-7777-8888-9999-000000000000");
    assert(restarted.items()[0].serverStatus == "ingested_pending_processing");
    assert(restarted.items()[0].processingStatus == "queued");
    assert(restarted.items()[0].mediaRevisionStatus == "uploaded");
    assert(restarted.pendingItems(32).size() == 1 && restarted.nextPending());
    assert(restarted.load() && restarted.items()[0].status == UploadQueueStatus::retry);
    assert(queue.markUploaded("recording"));
    assert(!queue.nextPending().has_value());
    std::filesystem::remove(path);
    {
        std::ofstream malformed(path, std::ios::binary);
        malformed << "{\"schema_version\":\"desktop-upload-queue.v2\",\"items\":[{\"local_recording_id\":\"broken\"";
    }
    DesktopUploadQueueService quarantined(path, root);
    assert(!quarantined.load() && quarantined.quarantined() && quarantined.items().empty());
    assert(std::filesystem::exists(path.string() + ".quarantine"));
    std::filesystem::remove(path.string() + ".quarantine");
    {
        std::ofstream malformedNumber(path, std::ios::binary);
        malformedNumber << "{\"schema_version\":\"desktop-upload-queue.v2\",\"items\":[{\"local_recording_id\":\"bad\",\"directory_id\":\"directory\",\"session_id\":\"session\",\"package_directory\":\"" << package.string() << "\",\"status\":1x,\"accepted_bytes\":[0,0,0],\"attempts\":0,\"safe_reason\":\"\"}]}";
    }
    DesktopUploadQueueService malformedNumberQueue(path, root);
    assert(!malformedNumberQueue.load() && malformedNumberQueue.quarantined());
    std::filesystem::remove_all(root);
    std::filesystem::remove_all(outside);
    return 0;
}
