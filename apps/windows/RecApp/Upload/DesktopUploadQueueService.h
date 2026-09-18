#pragma once

#include "../Contracts/WindowsDesktopContracts.h"
#include "DesktopApiClient.h"
#include "DesktopLocalPurgeService.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <functional>
#include <optional>
#include <string>
#include <vector>

namespace graf::windows {

enum class UploadQueueStatus {
    pending,
    uploading,
    needsAuth,
    retry,
    uploaded,
    quarantined,
    // The server classified this item as paused until a workspace admin acts or
    // as not retryable, so no automatic attempt can succeed. It is not
    // quarantined: once the condition is resolved the owner can ask for one
    // explicit attempt, which is what the macOS port calls manual only.
    blocked,
};

struct DesktopAccountIdentity {
    std::string userId;
    std::string workspaceId;
};

struct UploadCustodyItem {
    std::string localRecordingId;
    std::string directoryId;
    std::string sessionId;
    std::filesystem::path packageDirectory;
    UploadQueueStatus status = UploadQueueStatus::pending;
    std::array<std::uint64_t, 3> acceptedBytes{};
    std::uint32_t attempts = 0;
    std::string safeReason;
    std::string ownerUserId = {};
    std::string ownerWorkspaceId = {};
    // Learned from the server and kept in the ledger so a restart does not lose
    // the binding between the local package and its server meeting.
    std::string meetingId = {};
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
    std::string mediaRevisionId = {};
    std::string uploadSessionId = {};
    std::string serverStatus = {};
    std::string processingStatus = {};
    std::string mediaRevisionStatus = {};
};

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

[[nodiscard]] bool deletionPhaseIsAccepted(DeletionOperationPhase phase) noexcept;

struct DeletionOperationRecord {
    std::string operationId;
    DeletionTarget target = DeletionTarget::ownOrigin;
    std::string targetId;
    std::string actorUserId;
    std::string workspaceId;
    std::string serverOrigin;
    DeletionOperationPhase phase = DeletionOperationPhase::queued;
    std::uint64_t requestedAtMs = 0;
    std::uint64_t updatedAtMs = 0;
    std::uint32_t attemptCount = 0;
    // Zero means nothing is scheduled. A wait is a delay, never a give-up.
    std::uint64_t nextAttemptAtMs = 0;
    // Set only when the server accepted this exact target, so a late answer for
    // another recording can never confirm this one.
    std::string receiptRequestId;
    std::string safeReason;
};

struct UploadServerTruth {
    std::string localRecordingId;
    bool meetingExists = false;
    bool uploadSessionExists = false;
    std::array<std::uint64_t, 3> acceptedBytes{};
    bool finalized = false;
    // Server meeting id. The cabinet binds a local row to its server meeting by
    // this id, so the local copy disappears from the list once the server owns
    // it instead of staying next to it as a second entry.
    std::string meetingId;
    // Server-side identity of the accepted media revision and of the upload
    // session that carries it, plus the lifecycle states the server named.
    // Persisted with the row; declared last so existing positional initializers
    // keep their meaning.
    std::string mediaRevisionId;
    std::string uploadSessionId;
    std::string serverStatus;
    std::string processingStatus;
    std::string mediaRevisionStatus;
};

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
    explicit DesktopUploadQueueService(
        std::filesystem::path ledgerPath,
        std::filesystem::path custodyRoot = {});

    [[nodiscard]] bool load();
    [[nodiscard]] bool enqueue(UploadCustodyItem item);
    [[nodiscard]] bool reconcile(const UploadServerTruth& truth);
    [[nodiscard]] bool markRetry(std::string_view localRecordingId, std::string reason);
    // Retry later without spending an attempt: the server answered 429 and asked
    // for a pause. The pause itself is held by the scheduler that drives retries.
    [[nodiscard]] bool markDeferred(std::string_view localRecordingId, std::string reason);
    // UI owner only, with no upload in flight and after current-account checks.
    // Explicit retry rearms only this owned row; accepted bytes/identity stay put.
    [[nodiscard]] bool requestRetry(std::string_view localRecordingId);
    [[nodiscard]] bool markNeedsAuth(std::string_view localRecordingId, std::string reason = "auth_required");
    // UI thread, only after explicit native confirmation against the current
    // account generation. A known owner can never be reassigned, even to itself.
    [[nodiscard]] bool assignOwner(std::string_view localRecordingId, const DesktopAccountIdentity& identity);
    [[nodiscard]] bool requeueNeedsAuth();
    [[nodiscard]] bool markQuarantined(std::string_view localRecordingId, std::string reason);
    // Stops automatic attempts without discarding the row: the server said only
    // an admin action or a fix on this computer can unblock it.
    [[nodiscard]] bool markBlocked(std::string_view localRecordingId, std::string reason);
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
    struct DeletionWireResult {
        std::uint32_t status = 0;
        std::string body;
        bool transportFailed = false;
        std::uint32_t retryAfterSeconds = 0;
        // Why this request is waiting, when the client itself is the reason: the
        // call was refused before the wire, or the server's declared support was
        // not verified first. Empty when the server answered. A request with a
        // reason is not an answer about the recording, so it is never recorded as
        // one and never a rejection.
        std::string waitReason;
        [[nodiscard]] bool answered() const noexcept {
            return waitReason.empty() && !transportFailed && status != 0;
        }
        [[nodiscard]] bool accepted() const noexcept {
            return answered() && (status == 200 || status == 202);
        }
    };
    // One deletion the user confirmed in the cabinet.
    struct DeletionTargetRequest {
        DeletionTarget target = DeletionTarget::ownOrigin;
        std::string targetId;
    };

    // One request that has to go to the server, with everything the worker needs
    // and nothing it must not have: the worker never touches this ledger.
    struct DeletionRequestPlan {
        std::string operationId;
        DeletionTarget target = DeletionTarget::ownOrigin;
        std::string targetId;
        std::string path;
        std::string body;
    };

    struct DeletionPlan {
        // The requests are durable. False means the app could not store them, and
        // the user is asked to try again instead of being told a deletion is on
        // its way.
        bool saved = false;
        // Every request this selection owns, including the ones that already have
        // an answer: the selection is durable, and the outcome is read back from
        // all of them.
        std::vector<std::string> operationIds;
        // What still has to be sent. A request that already has an answer, or that
        // is waiting for its next attempt, is not in here.
        std::vector<DeletionRequestPlan> requests;
        // Local copies the server has never been told about. There is no request to
        // store for them, so the caller removes them itself and counts the result.
        std::vector<std::string> localOnly;
    };

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
    struct LocalPurgeAcknowledgement {
        std::string taskId;
        std::string meetingId;
        std::uint64_t acknowledgedAtMs = 0;
    };

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
    [[nodiscard]] static bool deletionFailureIsShared(const DeletionWireResult& wire) noexcept;
    // The protocol gate. Nothing may be mutated before the server's declared
    // support is read, so the caller reads the notification context first and asks
    // this whether the pass may proceed. Empty means it may; anything else is the
    // reason every request of the pass waits.
    [[nodiscard]] static std::string deletionGateReason(const DeletionWireResult& context,
                                                        const DesktopAccountIdentity& owner);
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

    // The rows that intent names, so a deletion interrupted by a crash or a closed
    // lid is carried out again instead of staying a mark in the ledger forever.
    [[nodiscard]] std::vector<std::string> pendingLocalDeletionIds() const;

    // Wall clock used to stamp ledger changes, in milliseconds. Replaced in tests
    // so that time is not the thing under test.
    void setClock(std::function<std::uint64_t()> clock);
    [[nodiscard]] std::uint64_t nowMs() const;

private:
    [[nodiscard]] bool persist();
    [[nodiscard]] static std::string serialize(const std::vector<UploadCustodyItem>& items,
                                               const std::vector<DeletionOperationRecord>& operations,
                                               const std::vector<LocalPurgeAcknowledgement>& purgeAcknowledgements,
                                               std::uint64_t updatedAtMs);
    [[nodiscard]] static bool validIdentity(std::string_view value) noexcept;
    [[nodiscard]] static bool validSafeReason(std::string_view value) noexcept;
    [[nodiscard]] static bool validServerOrigin(std::string_view value) noexcept;
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
};

} // namespace graf::windows
