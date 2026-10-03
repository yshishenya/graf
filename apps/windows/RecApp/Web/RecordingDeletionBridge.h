#pragma once

#include "../Upload/DesktopApiClient.h"

#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace graf::windows {

// What the cabinet posts through the bridge. macOS validates the same shape in
// `EmbeddedCabinetDeletionSelection.parse`, and this is the same contract: the
// two apps must accept and refuse the same requests, or the same click would
// delete different things on different platforms.
struct CabinetDeletionInput {
    std::uint32_t version = 0;
    std::string action;
    std::string requestId;
    std::vector<std::string> localIds;
    std::vector<std::string> meetingIds;
};

// A local row the app shows in the cabinet. `id` is what the cabinet sends back;
// `originId` is the identifier the server knows for that local copy. They are not
// assumed to be the same value: the request must name what the server can act on,
// not what the page happened to display.
struct CabinetLocalRow {
    std::string id;
    std::string originId;
    bool canDelete = false;
};

// A selection the cabinet is allowed to ask for.
struct CabinetDeletionSelection {
    std::string requestId;
    std::vector<std::string> localIds;
    std::vector<std::string> meetingIds;
    [[nodiscard]] std::size_t total() const noexcept { return localIds.size() + meetingIds.size(); }
};

// One deletion this app must carry out.
struct CabinetDeletionTarget {
    DeletionTarget target = DeletionTarget::ownOrigin;
    std::string targetId;
};

// One deletion as the cabinet reads it (`cabinet.js:404-440`): the phase it
// prints, the reason it is waiting, and the target it names. The page reads the
// target as the encoded enum macOS sends (`{meeting: {_0: id}}`), so that shape
// is built from these fields rather than guessed at the call site.
struct CabinetDeletionOperation {
    std::string id;
    std::string phase;
    std::string waitReason;
    std::string targetMeetingId;
    std::string targetDirectoryId;
    std::string receiptMeetingId;
};

// The waiting reasons the page knows are its own camelCase ones; the ledger keeps
// its snake_case spellings. An unknown reason is passed through unchanged: the
// page then prints the phase instead of inventing a state that is not there.
[[nodiscard]] std::string pageDeletionWaitReason(std::string_view ledgerReason);

// What the cabinet is told once the requests are stored and attempted. The page
// reads exactly these fields (`cabinet.js:1536-1550`).
struct CabinetDeletionOutcome {
    // The requests are durable. False means the app could not store them, and the
    // user is asked to try again rather than being told a deletion is on its way.
    bool saved = false;
    // No answer within the window the cabinet waits for.
    bool unknown = false;
    std::size_t accepted = 0;
    std::size_t pending = 0;
    std::size_t rejected = 0;
};

class RecordingDeletionBridge final {
public:
    static constexpr std::uint32_t kBridgeVersion = 1;
    static constexpr std::string_view kHandlerName = "grafLocalRecording";
    static constexpr std::string_view kDeleteSelectionAction = "deleteSelection";
    // The cabinet refuses to select more than this, and so does the app: a longer
    // list is not a request either side understands.
    static constexpr std::size_t kSelectionLimit = 100;

    // Accepts only what macOS accepts: version 1 of this action, a well-formed
    // request id, two lists of identifiers without repetition, at least one and at
    // most `kSelectionLimit` entries, server meetings as UUIDs, and local rows the
    // app both knows and offers for deletion. Unknown extra fields are ignored,
    // exactly as the macOS dictionary lookup ignores them.
    [[nodiscard]] static std::optional<CabinetDeletionSelection> validate(
        const CabinetDeletionInput& input, const std::vector<CabinetLocalRow>& rows);
    // On a meeting page the cabinet may only ask for that meeting, or for local
    // rows alone. Without this a page could delete an unrelated meeting.
    [[nodiscard]] static bool fitsRoute(const CabinetDeletionSelection& selection,
                                        std::string_view routeMeetingId);
    // What has to be requested, local copies first, in the order the cabinet sent
    // them. A local row is requested against its own-origin identifier.
    [[nodiscard]] static std::vector<CabinetDeletionTarget> targets(
        const CabinetDeletionSelection& selection, const std::vector<CabinetLocalRow>& rows);
    // The answer the page waits for. The request id is re-validated inside: a page
    // cannot smuggle script through it.
    [[nodiscard]] static std::string completionScript(std::string_view requestId,
                                                      const CabinetDeletionOutcome& outcome);
    // The script that makes the cabinet see the same bridge it sees on macOS. It
    // declares the version the page gates on, so it must be injected only when a
    // real deletion operation exists behind it.
    [[nodiscard]] static std::string_view documentScript() noexcept;
};

} // namespace graf::windows
