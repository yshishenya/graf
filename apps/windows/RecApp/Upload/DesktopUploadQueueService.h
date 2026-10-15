#pragma once

#include "../Contracts/WindowsDesktopContracts.h"
#include "DesktopApiClient.h"
#include "DesktopLocalPurgeService.h"
#include "../Storage/ProtectedCustodyMetadata.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <functional>
#include <optional>
#include <string>
#include <vector>

namespace graf::windows {

template<class String> struct BasicDesktopTransportResult;

enum class UploadQueueStatus {
    pending,
    uploading,
    needsAuth,
    retry,
    uploaded,
    quarantined,
    // The server classified this item as paused until a workspace admin acts or
    // as not retryable, so no automatic attempt can succeed. It is not
    // quarantined: playback/deletion remain available. Only an admin pause can
    // be rearmed; a permanent rejection also forbids explicit attempts.
    blocked,
};

template<class String> struct BasicDesktopAccountIdentity {
    String userId;
    String workspaceId;
};
using DesktopAccountIdentity = BasicDesktopAccountIdentity<std::string>;

template<class String> bool validLocalBufferPurgeTask(const BasicLocalPurgeTask<String>& task) noexcept {
    return task.taskType == "purge_local_buffers" && DesktopApiClient::accountId(task.taskId) &&
        DesktopApiClient::accountId(task.meetingId);
}

template<class String, class Path>
struct BasicUploadCustodyItem {
    String localRecordingId;
    String directoryId;
    String sessionId;
    Path packageDirectory;
    UploadQueueStatus status = UploadQueueStatus::pending;
    std::array<std::uint64_t, 3> acceptedBytes{};
    std::uint32_t attempts = 0;
    String safeReason;
    String ownerUserId = {};
    String ownerWorkspaceId = {};
    // Learned from the server and kept in the ledger so a restart does not lose
    // the binding between the local package and its server meeting.
    String meetingId = {};
    // Wall clock of the last change to this row. A row that stopped changing long
    // ago is distinguishable from one that is still moving.
    std::uint64_t updatedAtMs = 0;
    // The rest of what the server said about this row: which media revision it
    // accepted, which upload session carries it, and how far the meeting and its
    // processing have come. macOS keeps the same fingerprint in its queue row
    // (`ServerTruthFingerprint`); without it a restart can only re-ask the server
    // and cannot tell the owner what the server last said. Declared after the
    // fields the row has always had so existing positional initializers in tests
    // and fixtures keep their meaning.
    String mediaRevisionId = {};
    String uploadSessionId = {};
    String serverStatus = {};
    String processingStatus = {};
    String mediaRevisionStatus = {};
};

template<class Item> [[nodiscard]] bool hasUploadServerIdentity(const Item& item) noexcept {
    return !item.meetingId.empty() || item.attempts > 0 || item.status == UploadQueueStatus::uploaded ||
        item.acceptedBytes[0] || item.acceptedBytes[1] || item.acceptedBytes[2] ||
        !item.uploadSessionId.empty() || !item.mediaRevisionId.empty() || !item.serverStatus.empty() ||
        !item.processingStatus.empty() || !item.mediaRevisionStatus.empty();
}

using UploadCustodyItem = BasicUploadCustodyItem<std::string, std::filesystem::path>;

template<class Item> bool sameUploadIdentity(const Item& a, const Item& b) noexcept {
    return a.localRecordingId == b.localRecordingId && a.directoryId == b.directoryId && a.sessionId == b.sessionId &&
        a.packageDirectory == b.packageDirectory && a.ownerUserId == b.ownerUserId &&
        a.ownerWorkspaceId == b.ownerWorkspaceId && a.status == b.status && a.attempts == b.attempts;
}

// One durable deletion request. macOS stores the same state under
// `deletionOperations`: a server-only deletion has no local package to remember
// it by, so it survives a restart only if the ledger keeps it.
enum class DeletionOperationPhase {
    queued,
    sending,
    resolving,
    // The server named this target in a receipt. Deletion is monotonic: once
    // accepted, only `verified` may follow.
    accepted,
    rejected,
    // The local copies are gone and the server acknowledged it.
    verified,
};

[[nodiscard]] inline bool deletionPhaseIsAccepted(DeletionOperationPhase phase) noexcept {
    return phase == DeletionOperationPhase::accepted || phase == DeletionOperationPhase::verified;
}

template<class String>
struct BasicDeletionOperationRecord {
    String operationId;
    DeletionTarget target = DeletionTarget::ownOrigin;
    String targetId;
    String actorUserId;
    String workspaceId;
    String serverOrigin;
    DeletionOperationPhase phase = DeletionOperationPhase::queued;
    std::uint64_t requestedAtMs = 0;
    std::uint64_t updatedAtMs = 0;
    std::uint32_t attemptCount = 0;
    // Zero means nothing is scheduled. A wait is a delay, never a give-up.
    std::uint64_t nextAttemptAtMs = 0;
    // Set only when the server accepted this exact target, so a late answer for
    // another recording can never confirm this one.
    String receiptRequestId;
    String safeReason;
};

using DeletionOperationRecord = BasicDeletionOperationRecord<std::string>;

// One bounded response; the protected path retains body/reason in its existing quota.
template<class String> struct BasicDeletionWireResult {
    std::uint32_t status = 0;
    String body;
    bool transportFailed = false;
    std::uint32_t retryAfterSeconds = 0;
    String waitReason;
    [[nodiscard]] bool answered() const noexcept {
        return waitReason.empty() && !transportFailed && status != 0;
    }
    [[nodiscard]] bool accepted() const noexcept {
        return answered() && (status == 200 || status == 202);
    }
};

template<class String> struct BasicDeletionTargetRequest {
    DeletionTarget target = DeletionTarget::ownOrigin;
    String targetId;
};
template<class String> struct BasicDeletionRequestPlan {
    String operationId;
    DeletionTarget target = DeletionTarget::ownOrigin;
    String targetId;
    String path;
    String body;
};
template<class String, template<class> class Allocator> struct BasicDeletionPlan {
    // False on a private candidate. Only an adopted durable intent may be saved.
    bool saved = false;
    std::vector<String, Allocator<String>> operationIds;
    std::vector<BasicDeletionRequestPlan<String>, Allocator<BasicDeletionRequestPlan<String>>> requests;
    std::vector<String, Allocator<String>> localOnly;
};
using ProtectedDeletionTargets = CustodyVector<BasicDeletionTargetRequest<CustodyString>>;
using ProtectedDeletionPlan = BasicDeletionPlan<CustodyString, CustodyAllocator>;

template<class String> struct BasicLocalPurgeAcknowledgement {
    String taskId;
    String meetingId;
    std::uint64_t acknowledgedAtMs = 0;
};

// Charged domain data only. Publish as shared<const Value>; mutate only a private
// worker copy. It holds no native proof, identity, generation, lease or authority.
class ProtectedUploadQueueValue final {
public:
    using Item = BasicUploadCustodyItem<CustodyString, CustodyString>;
    using Operation = BasicDeletionOperationRecord<CustodyString>;
    using PurgeAcknowledgement = BasicLocalPurgeAcknowledgement<CustodyString>;
    ProtectedUploadQueueValue(const ProtectedUploadQueueValue&) = default;
    [[nodiscard]] const CustodyVector<Item>& items() const noexcept { return items_; }
    [[nodiscard]] const CustodyVector<Operation>& deletionOperations() const noexcept { return operations_; }
    [[nodiscard]] const CustodyVector<PurgeAcknowledgement>& purgeAcknowledgements() const noexcept { return acknowledgements_; }
    [[nodiscard]] std::uint64_t updatedAtMs() const noexcept { return updatedAtMs_; }
    [[nodiscard]] bool legacy() const noexcept { return legacy_; }
    // Throws ParseCancelled/bad_alloc; a partially mutated private copy is discarded.
    [[nodiscard]] bool requeueNeedsAuth(std::uint64_t nowMs, const std::atomic<bool>* cancellation = nullptr);
    // Private domain insertion only; the native owner still has to persist the
    // complete value and the caller must adopt its exact commit outcome.
    [[nodiscard]] bool enqueue(Item, std::uint64_t nowMs, const std::atomic<bool>* cancellation);
    // Private candidate only, never a durable success. The native caller must
    // bind index to the current adopted snapshot/account/document before use.
    [[nodiscard]] bool canManualSend(std::size_t index, std::string_view user, std::string_view workspace,
        bool confirmUnowned) const noexcept;
    [[nodiscard]] bool prepareManualSend(std::size_t index, std::string_view user, std::string_view workspace,
        bool confirmUnowned, std::uint64_t nowMs, const std::atomic<bool>* cancellation);
    [[nodiscard]] bool canLocalRemoval(std::size_t index, std::string_view user, std::string_view workspace,
        bool resumeIntent = false) const noexcept;
    // Native-confirmed local copy only: never creates server requests or proof.
    [[nodiscard]] bool planLocalRemoval(std::size_t index, std::string_view user, std::string_view workspace,
        std::uint64_t nowMs, ProtectedDeletionPlan&, bool& changed, const std::atomic<bool>* cancellation,
        bool resumeIntent = false);
    [[nodiscard]] bool applyDeletionAnswer(const Operation& expected, const BasicDeletionWireResult<CustodyString>&,
        std::uint64_t nowMs, bool& changed, const std::atomic<bool>* cancellation);
    [[nodiscard]] bool planDeletionSelection(const ProtectedDeletionTargets&, std::string_view user,
        std::string_view workspace, std::string_view origin, std::uint64_t nowMs, ProtectedDeletionPlan&,
        bool& changed, const std::atomic<bool>* cancellation);
    [[nodiscard]] bool deletionBlocks(const Item&) const noexcept;
    // Domain intent only. Neither this marker nor a no-op ticket proves absence.
    [[nodiscard]] bool prepareLocalPurgeTask(const BasicLocalPurgeTask<CustodyString>&,
        std::string_view user, std::string_view workspace, std::uint64_t nowMs,
        bool& changed, const std::atomic<bool>* cancellation);
    [[nodiscard]] bool localPurgeAcknowledged(const BasicLocalPurgeTask<CustodyString>&) const noexcept;
    [[nodiscard]] CustodyVector<CustodyString> meetingsAwaitingLocalPurge(std::string_view user,
        std::string_view workspace, std::string_view origin, const std::atomic<bool>* cancellation) const;
    // Private candidate only: one domain mutation, not a durable commit/ACK.
    // Reject a stale row before changing it; the worker owns commit/adoption.
    [[nodiscard]] bool applyUploadResult(const Item& expected, const BasicDesktopTransportResult<CustodyString>&,
        std::uint64_t nowMs, const std::atomic<bool>* cancellation);
    // Private preparation only. The complete nonempty candidate must still be
    // committed/adopted before its selection can be dispatched.
    [[nodiscard]] CustodyVector<std::size_t> prepareUploads(bool authRecovered, std::uint32_t maxAttempts,
        std::uint64_t nowMs, const std::atomic<bool>* cancellation);
    [[nodiscard]] CustodyFileResult<CustodyBytes> serialize(std::shared_ptr<const std::atomic<bool>> cancellation) const;
private:
    ProtectedUploadQueueValue() = default;
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<const ProtectedUploadQueueValue>> decode(
        std::string_view, const std::atomic<bool>* cancellation);
    friend class ProtectedUploadQueueCandidate;
    friend class ProtectedCustodyStoreOwner;
    friend struct ProtectedUploadQueueValueTestPeer;
    CustodyVector<Item> items_;
    CustodyVector<Operation> operations_;
    CustodyVector<PurgeAcknowledgement> acknowledgements_;
    std::uint64_t updatedAtMs_ = 0;
    bool legacy_ = false;
};

// Display-only evidence bound to every index of one immutable queue snapshot.
// Unknown is distinct from a measured duration that rounds to zero seconds.
struct ProtectedLocalRecordingTiming {
    std::uint64_t durationMs = 0, startedAtMs = 0, stoppedAtMs = 0;
    int displayTimezoneOffsetMinutes = 0;
};
struct ProtectedLocalRecordingTimings {
    std::shared_ptr<const ProtectedUploadQueueValue> snapshot;
    CustodyVector<std::optional<ProtectedLocalRecordingTiming>> rows;
};

// Worker-only semantic snapshot of BOTH genuine queue payloads. Does not prove
// matching intent/account/epoch/root authority or authorize any effect/mutation.
class ProtectedUploadQueueCandidate final {
public:
    using Item = ProtectedUploadQueueValue::Item;
    using Operation = ProtectedUploadQueueValue::Operation;
    using PurgeAcknowledgement = ProtectedUploadQueueValue::PurgeAcknowledgement;
    [[nodiscard]] static CustodyFileResult<std::shared_ptr<const ProtectedUploadQueueCandidate>> read(
        std::shared_ptr<const ProtectedCustodyQueueInput>, std::shared_ptr<const std::atomic<bool>> cancellation);
    [[nodiscard]] const CustodyVector<Item>& items() const noexcept { return value_->items(); }
    [[nodiscard]] const CustodyVector<Operation>& deletionOperations() const noexcept { return value_->deletionOperations(); }
    [[nodiscard]] const CustodyVector<PurgeAcknowledgement>& purgeAcknowledgements() const noexcept { return value_->purgeAcknowledgements(); }
    [[nodiscard]] const std::shared_ptr<const ProtectedCustodyQueueInput>& input() const noexcept { return input_; }
    [[nodiscard]] std::uint64_t updatedAtMs() const noexcept { return value_->updatedAtMs(); }
    [[nodiscard]] bool legacy() const noexcept { return value_->legacy(); }
    ProtectedUploadQueueCandidate(const ProtectedUploadQueueCandidate&) = delete;
    ~ProtectedUploadQueueCandidate() = default;
private:
    ProtectedUploadQueueCandidate() = default;
    std::shared_ptr<const ProtectedCustodyQueueInput> input_; // Release leases AFTER parsed storage.
    std::shared_ptr<const ProtectedUploadQueueValue> value_;
};

template<class String> struct BasicUploadServerTruth {
    String localRecordingId;
    bool meetingExists = false;
    bool uploadSessionExists = false;
    std::array<std::uint64_t, 3> acceptedBytes{};
    bool finalized = false;
    // Server meeting id. The cabinet binds a local row to its server meeting by
    // this id, so the local copy disappears from the list once the server owns
    // it instead of staying next to it as a second entry.
    String meetingId = {};
    // Server-side identity of the accepted media revision and of the upload
    // session that carries it, plus the lifecycle states the server named.
    // Persisted with the row; declared last so existing positional initializers
    // keep their meaning.
    String mediaRevisionId = {};
    String uploadSessionId = {};
    String serverStatus = {};
    String processingStatus = {};
    String mediaRevisionStatus = {};
};
using UploadServerTruth = BasicUploadServerTruth<std::string>;

enum class LocalCopyRemovalResult {
    removed,
    confirmationRequired,
    unknownRecording,
    unsafePath,
    recycleFailed,
    ledgerFailure,
};

enum class ShortRecordingDiscardResult {
    discarded,
    notMarked,
    unsafePath,
    ledgerFailure,
};

class DesktopUploadQueueService final {
public:
    // Optional persistence seam for interruption/failure tests. Production uses
    // AtomicFileStore::writeWithinRoot; a successful writer must replace atomically.
    using LedgerWriter = std::function<bool(const std::filesystem::path&, const std::filesystem::path&, std::string_view)>;
    explicit DesktopUploadQueueService(
        std::filesystem::path ledgerPath,
        std::filesystem::path custodyRoot = {},
        LedgerWriter ledgerWriter = {});

    [[nodiscard]] bool load();
    [[nodiscard]] bool enqueue(UploadCustodyItem item);
    [[nodiscard]] bool reconcile(const UploadServerTruth& truth);
    // Server truth and terminal/retry status share one ledger replacement.
    [[nodiscard]] bool applyUploadResult(std::string_view localRecordingId,
        const BasicDesktopTransportResult<std::string>&);
    [[nodiscard]] bool markRetry(std::string_view localRecordingId, std::string reason);
    // Retry later without spending an attempt: the server answered 429 and asked
    // for a pause. The pause itself is held by the scheduler that drives retries.
    [[nodiscard]] bool markDeferred(std::string_view localRecordingId, std::string reason);
    // UI owner only, with no upload in flight and after current-account checks.
    // Explicit retry rearms only this owned row; accepted bytes/identity stay put.
    [[nodiscard]] bool requestRetry(std::string_view localRecordingId);
    // Shared with the shell action projection; its current-account/busy and
    // package-integrity checks still apply. Uses existing durable safe_reason.
    [[nodiscard]] static bool canRetry(const UploadCustodyItem& item) noexcept;
    [[nodiscard]] static bool isPermanentUploadReason(std::string_view reason) noexcept {
        return reason == "not_retryable" || reason == "unsupported_recording_source_kind" ||
            reason == "invalid_recording_source_mode";
    }
    [[nodiscard]] bool markNeedsAuth(std::string_view localRecordingId, std::string reason = "auth_required");
    // UI thread, only after explicit native confirmation against the current
    // account generation. A known owner can never be reassigned, even to itself.
    [[nodiscard]] bool assignOwner(std::string_view localRecordingId, const DesktopAccountIdentity& identity);
    [[nodiscard]] bool requeueNeedsAuth();
    [[nodiscard]] bool markQuarantined(std::string_view localRecordingId, std::string reason);
    // Stops automatic attempts without discarding the row: the server said only
    // an admin action or a fix on this computer can unblock it.
    // When supplied, server truth and the block are committed in one atomic
    // replacement: a restart must never see new bytes without the refusal.
    [[nodiscard]] bool markBlocked(std::string_view localRecordingId, std::string reason,
                                   const UploadServerTruth* truth = nullptr);
    [[nodiscard]] bool markUploaded(std::string_view localRecordingId);
    // UI thread, after scheduler cancellation/drain (busy == false) and native
    // confirmation. The callback must recycle, not permanently delete; it must
    // not mutate this queue. No server operation or purge ACK is performed.
    [[nodiscard]] LocalCopyRemovalResult removeLocalCopy(
        std::string_view localRecordingId, LocalPurgeProof proof,
        const std::function<bool(const std::filesystem::path&)>& recycle);
    [[nodiscard]] std::optional<UploadCustodyItem> nextPending() const;
    [[nodiscard]] std::vector<UploadCustodyItem> pendingItems(std::size_t limit) const;

    // Feature 6796 parity with macOS. A recording the writer marked as a
    // discarded short recording is never uploaded, never becomes a meeting and
    // is removed without asking the user. The manifest marker outlives the
    // audio, so cleanup interrupted by a crash is retried by the next scan.
    // Deletes only regular files directly inside a verified package directory.
    [[nodiscard]] static bool isShortRecordingMarked(const std::filesystem::path& packageDirectory);
    [[nodiscard]] ShortRecordingDiscardResult discardShortRecording(
        const std::filesystem::path& packageDirectory);
    [[nodiscard]] std::size_t sweepDiscardedShortRecordings();
    [[nodiscard]] const std::vector<UploadCustodyItem>& items() const noexcept { return items_; }
    [[nodiscard]] bool quarantined() const noexcept { return quarantined_; }
    [[nodiscard]] const std::filesystem::path& ledgerPath() const noexcept { return ledgerPath_; }

    // Durable deletion requests. Storing one is the "saved" the cabinet is told
    // about: once stored, the request is carried out even if the network, the
    // sign-in or the process goes away in between.
    [[nodiscard]] bool requestDeletion(DeletionTarget target, std::string_view targetId,
                                       const DesktopAccountIdentity& owner, std::string_view serverOrigin,
                                       std::string& operationId);
    // Phase transitions are monotonic: time may not go backwards, an accepted
    // request may only become verified, and verified is terminal. Returns false
    // when the transition is not allowed, leaving the stored record untouched.
    [[nodiscard]] bool markDeletionPhase(std::string_view operationId, DeletionOperationPhase phase,
                                        std::string_view safeReason);
    [[nodiscard]] bool markDeletionAttempt(std::string_view operationId, std::uint64_t nextAttemptAtMs);
    // Acceptance is only recorded when the receipt names this exact target.
    [[nodiscard]] bool acceptDeletion(std::string_view operationId, const DeletionReceipt& receipt);
    [[nodiscard]] const std::vector<DeletionOperationRecord>& deletionOperations() const noexcept {
        return deletionOperations_;
    }
    // Requests made by the account the app is signed in as, oldest first.
    [[nodiscard]] std::vector<DeletionOperationRecord> currentDeletionOperations(
        const DesktopAccountIdentity& owner) const;
    [[nodiscard]] const DeletionOperationRecord* findDeletionOperation(std::string_view operationId) const noexcept;

    // One answer to one request, in the shape this service understands. Kept free
    // of the transport type so the executor is testable without a server, and free
    // of bare status codes so "refused before the wire" is not read as a refusal
    // by the server.
    using DeletionWireResult = BasicDeletionWireResult<std::string>;
    // One deletion the user confirmed in the cabinet.
    using DeletionTargetRequest = BasicDeletionTargetRequest<std::string>;

    // One request that has to go to the server, with everything the worker needs
    // and nothing it must not have: the worker never touches this ledger.
    using DeletionRequestPlan = BasicDeletionRequestPlan<std::string>;

    using DeletionPlan = BasicDeletionPlan<std::string, std::allocator>;

    // What the cabinet is told. `saved` means the requests are durable, never that
    // anything was deleted; the counts say what the server has answered so far.
    struct DeletionSelectionOutcome {
        bool saved = false;
        std::size_t accepted = 0;
        std::size_t pending = 0;
        std::size_t rejected = 0;
    };

    // A purge task this device has already carried out and proven. Kept so a task
    // the server asks about again is answered from the record instead of a second
    // look at files that are already gone: macOS answers from the terminal item it
    // keeps, and a row that was removed cannot be asked about again. Only proven
    // deletions are recorded — a failed purge is retried, and freezing it would
    // leave the local copies unremovable.
    using LocalPurgeAcknowledgement = BasicLocalPurgeAcknowledgement<std::string>;

    // What could be proven about one purge task: the server deleted a meeting and
    // asked this device to remove the local copies it still holds. Only `deleted`
    // means they are gone; everything else leaves them, and says so.
    enum class LocalPurgeVerification { deleted, failed, unverified };

    struct LocalPurgeCandidate {
        std::string localRecordingId;
        // The server already owns this recording, so its local copy is the buffer
        // the task is about. A copy still being uploaded is not: removing it would
        // destroy an upload that has not finished.
        bool purgeable = false;
    };

    struct LocalPurgeCompletion {
        LocalPurgeVerification verification = LocalPurgeVerification::unverified;
        LocalPurgeAckState ack = LocalPurgeAckState::failed;
        std::string reasonCode = "local_purge_unverified";
        std::size_t removed = 0;
    };

    // Owner thread. The rows a task names, matched by the meeting identifier the
    // server itself returned. Nothing else may stand in for that: a task about
    // another meeting is not a reason to touch this device's files.
    [[nodiscard]] std::vector<LocalPurgeCandidate> localPurgeCandidates(const LocalPurgeTask& task) const;
    // Owner thread. Removes the local copies a task names, the same safe way a
    // user-confirmed removal happens, and reports what could be proven. A task
    // whose type this client cannot verify is answered without touching a file.
    LocalPurgeCompletion completeLocalPurgeTask(const LocalPurgeTask& task,
        const std::function<bool(const std::filesystem::path&)>& recycle);
    // The meetings whose deletion this device confirmed with the server and whose
    // local copies are still here. The server creates the purge task on its own
    // side, and asking for it is how the two are matched.
    [[nodiscard]] std::vector<std::string> meetingsAwaitingLocalPurge() const;
    [[nodiscard]] bool hasLocalPurgeAcknowledgement(std::string_view taskId) const;
    [[nodiscard]] const std::vector<LocalPurgeAcknowledgement>& localPurgeAcknowledgements() const noexcept {
        return purgeAcknowledgements_;
    }
    [[nodiscard]] static LocalPurgeAckState localPurgeAckState(LocalPurgeVerification verification) noexcept;
    [[nodiscard]] static std::string_view localPurgeReasonCode(LocalPurgeVerification verification) noexcept;

    // Owner thread. Stores the confirmed selection and says what to send. The
    // whole selection is resolved before anything is stored, so a refusal cannot
    // leave half of it durable.
    DeletionPlan planDeletionSelection(const std::vector<DeletionTargetRequest>& targets,
                                       const DesktopAccountIdentity& owner, std::string_view serverOrigin);
    // Owner thread. Records what one request answered. The attempt is counted here,
    // when it has actually happened, rather than when it was planned: a request
    // that was never sent must not age its own retry schedule.
    [[nodiscard]] bool applyDeletionAnswer(const DeletionRequestPlan& request,
                                           const DesktopAccountIdentity& owner,
                                           std::string_view serverOrigin,
                                           const DeletionWireResult& wire);
    // Whether an answer says something about this account rather than about this
    // one target. One timeout is evidence about the rest of the batch; a target
    // that no longer exists is that target's own problem.
    template<class String>
    [[nodiscard]] static bool deletionFailureIsShared(const BasicDeletionWireResult<String>& wire) noexcept;
    // The protocol gate. Nothing may be mutated before the server's declared
    // support is read, so the caller reads the notification context first and asks
    // this whether the pass may proceed. Empty means it may; anything else is the
    // reason every request of the pass waits.
    template<class String>
    [[nodiscard]] static String deletionGateReason(const BasicDeletionWireResult<String>& context,
        const BasicDesktopAccountIdentity<String>& owner, const std::atomic<bool>* cancellation = nullptr);
    // Owner thread. What the cabinet is told, read back from the ledger: an
    // accepted request is one the server named in a receipt, never one that was
    // merely sent.
    [[nodiscard]] DeletionSelectionOutcome deletionSelectionOutcome(const DeletionPlan& plan) const;

    // A local copy the server has been told about, in the same sense macOS means
    // with `serverCreationAttempted`: there is a meeting, an upload was attempted,
    // or the upload finished. A recording that was only recorded — even though the
    // queue gives it a local session key — has nothing on the server to delete.
    [[nodiscard]] static bool hasServerIdentity(const UploadCustodyItem& item) noexcept;

    // True while this device holds the user's recorded intent to remove a local
    // copy but has not proven the files gone. The cabinet reads this as "очистка
    // ещё не завершена" and must not draw such a row as a recording.
    [[nodiscard]] static bool localDeletionPending(const UploadCustodyItem& item) noexcept;
    // Сколько записи уже принято сервером. Сервер называет принятые байты по
    // дорожкам, размеры дорожек знает локальный пакет; без обеих половин прогресс
    // неизвестен, и строка обязана молчать, а не показывать ноль. macOS считает
    // так же (`DesktopMeetingShellLocalQueuePolicy.progressPercent(for:)`).
    [[nodiscard]] static std::optional<int> uploadProgressPercent(
        const UploadCustodyItem& item, const std::array<std::uint64_t, 3>& trackBytes) noexcept;

    // User-confirmed quarantine intents only. Server intents retain uploaded
    // and must resume through their matching purge task, not user confirmation.
    [[nodiscard]] std::vector<std::string> pendingLocalDeletionIds() const;

    // Wall clock used to stamp ledger changes, in milliseconds. Replaced in tests
    // so that time is not the thing under test.
    void setClock(std::function<std::uint64_t()> clock);
    [[nodiscard]] std::uint64_t nowMs() const;

    // Shared package-directory identity boundary, also used by protected custody IO.
    [[nodiscard]] static bool validIdentity(std::string_view value) noexcept;
    // Lexical native-server origin boundary, not a meeting URL/host policy.
    [[nodiscard]] static bool validServerOrigin(std::string_view value) noexcept;

private:
    friend class ProtectedUploadQueueCandidate;
    [[nodiscard]] bool publishCandidate(DesktopUploadQueueService&, std::uint64_t now);
    friend class ProtectedUploadQueueValue;
    friend class ProtectedCustodyStoreOwner;
    LedgerWriter ledgerWriter_;
    static void applyServerTruth(UploadCustodyItem& item, const UploadServerTruth& truth);
    [[nodiscard]] bool persist();
    // Validation only on a fresh private candidate, without I/O or publication.
    [[nodiscard]] bool decodeLedger(std::string_view json, bool& legacy);
    // One canonical empty birth value, shared with the existing serializer.
    static constexpr std::string_view emptyLedgerJson = R"({"schema_version":"desktop-upload-queue.v3","items":[],"updated_at_ms":0,"deletion_operations":[],"purge_acknowledgements":[]})";
    [[nodiscard]] static std::string serialize(const std::vector<UploadCustodyItem>& items,
                                               const std::vector<DeletionOperationRecord>& operations,
                                               const std::vector<LocalPurgeAcknowledgement>& purgeAcknowledgements,
                                               std::uint64_t updatedAtMs);
    [[nodiscard]] static bool validSafeReason(std::string_view value) noexcept;
    [[nodiscard]] UploadCustodyItem* find(std::string_view localRecordingId) noexcept;
    [[nodiscard]] DeletionOperationRecord* findOperation(std::string_view operationId) noexcept;
    void stamp(UploadCustodyItem& item) const noexcept;

    std::filesystem::path ledgerPath_;
    std::filesystem::path custodyRoot_;
    std::vector<UploadCustodyItem> items_;
    std::vector<DeletionOperationRecord> deletionOperations_;
    std::vector<LocalPurgeAcknowledgement> purgeAcknowledgements_;
    std::uint64_t updatedAtMs_ = 0;
    std::function<std::uint64_t()> clock_;
    bool quarantined_ = false;
    bool ledgerKnown_ = false;
};

} // namespace graf::windows
