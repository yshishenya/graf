const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");

const repoRoot = process.cwd();
const serverDir = path.join(repoRoot, "apps/server");
const css = fs.readFileSync(
  path.join(serverDir, "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css"),
);
const js = fs.readFileSync(
  path.join(serverDir, "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"),
);
const icon = fs.readFileSync(
  path.join(serverDir, "src/twobrain_rec_server/cabinet/static/cabinet/graf-icon.png"),
);
const wordmark = fs.readFileSync(
  path.join(serverDir, "src/twobrain_rec_server/cabinet/static/cabinet/graf-wordmark-dark.png"),
);
const wordmark2x = fs.readFileSync(
  path.join(serverDir, "src/twobrain_rec_server/cabinet/static/cabinet/graf-wordmark-dark@2x.png"),
);

const python = String.raw`
import json
from datetime import UTC, datetime
from uuid import UUID

from tests.unit.test_cabinet_web_shell import _review
from twobrain_rec_server.api.schemas import (
    ContentExportCapabilityResponse,
    ContentExportDefaults,
    ContentExportReadiness,
    NotesActionCategoryState,
    NotesActionTruthState,
    OutcomeItemView,
    OutcomeSourceReferenceView,
    PlaybackReviewState,
    SpeakerLane,
    SpeakerLaneSegment,
    SpeakerReviewState,
    TranscriptReviewState,
    TranscriptSpeakerTurnView,
)
from twobrain_rec_server.cabinet.rendering import (
    render_meeting_detail_page,
    render_shared_meeting_summary_page,
)

SEGMENT_IDS = [
    UUID("00000000-0000-0000-0000-000000000139"),
    UUID("00000000-0000-0000-0000-000000000140"),
    UUID("00000000-0000-0000-0000-000000000141"),
    UUID("00000000-0000-0000-0000-000000000142"),
]
SEGMENT_ID = SEGMENT_IDS[0]
RESULT_ID = UUID("10000000-0000-0000-0000-000000000139")
OUTCOME_ID = UUID("20000000-0000-0000-0000-000000000139")


def category(name, state, items=None):
    labels = {
        "summary": "Итоги готовы",
        "action_items": "Действия",
        "decisions": "Решения",
        "risks": "Риски",
    }
    return NotesActionCategoryState(
        state=state,
        label=labels.get(name, "Не найдено"),
        reason="Синтетическое состояние для runtime-проверки.",
        readiness_impact="closes_gap" if state in {"available", "not_found"} else "keeps_gap_open",
        copy_key=f"notes.runtime.{name}.{state}",
        items=items or [],
    )


def accepted_review(*, transcript=True, playback=True):
    review = _review()
    review.meeting.title = "Синтетический проектный синк"
    review.meeting.status = "ready"
    review.meeting.status_label = "Готово"
    review.meeting.primary_action = "open"
    review.meeting.transcript_available = transcript
    review.meeting.notes_available = True
    review.processing.state = "ready"
    review.processing.content_available = True
    review.processing.transcript_available = transcript
    review.processing.summary_available = True
    review.playback = PlaybackReviewState(
        available=playback,
        duration_seconds=120,
        playback_path="/synthetic/runtime.wav" if playback else None,
        policy_label="Аудио доступно для проверки" if playback else "Аудио недоступно",
        source_mode="stored_review_m4a" if playback else "none",
        included_sources=["local_microphone", "incoming_system"] if playback else [],
    )
    review.speakers = SpeakerReviewState(
        available=playback,
        assignment_state="reserved" if playback else "unavailable",
        speakers=(
            [
                SpeakerLane(
                    speaker_key="speaker_anna",
                    label="Анна",
                    talk_time_percent=55,
                    source_roles=["local_microphone"],
                    segments=[SpeakerLaneSegment(start_seconds=0, end_seconds=66)],
                ),
                SpeakerLane(
                    speaker_key="speaker_boris",
                    label="Борис",
                    talk_time_percent=45,
                    source_roles=["incoming_system"],
                    segments=[SpeakerLaneSegment(start_seconds=66, end_seconds=120)],
                ),
            ]
            if playback
            else []
        ),
    )
    review.transcript = TranscriptReviewState(
        available=transcript,
        language="ru" if transcript else None,
        search_enabled=transcript,
        speaker_turns=(
            [
                TranscriptSpeakerTurnView(
                    turn_id=str(segment_id),
                    sequence=sequence,
                    start_seconds=12.5 + sequence * 15,
                    end_seconds=22.5 + sequence * 15,
                    timestamp_label=f"00:{12 + sequence * 15:02d}",
                    speaker_key="speaker_anna",
                    speaker_label="Анна",
                    source_role="local_microphone",
                    text=f"Синтетический фрагмент источника {sequence + 1}.",
                    source_segment_ids=[str(segment_id)],
                    seekable=playback,
                    seek_seconds=12.5 + sequence * 15 if playback else None,
                )
                for sequence, segment_id in enumerate(SEGMENT_IDS)
            ]
            if transcript
            else []
        ),
    )
    sources = [
        OutcomeSourceReferenceView(
            transcript_segment_id=segment_id,
            sequence=sequence,
            start_seconds=12.5 + sequence * 15,
            end_seconds=22.5 + sequence * 15,
            evidence_kind="segment",
            speaker_label="Анна",
            source_role="local_microphone",
            seekable=True,
        )
        for sequence, segment_id in enumerate(SEGMENT_IDS)
    ]
    source = sources[0]
    summary = category(
        "summary",
        "available",
        [
            OutcomeItemView(
                category="summary",
                sequence=0,
                text="Команда согласовала запуск и план проверки.",
                truth_label="supported",
                source_refs=sources,
            )
        ],
    )
    actions = category(
        "action_items",
        "available",
        [
            OutcomeItemView(
                category="action_items",
                sequence=0,
                text="Подготовить план запуска.",
                owner_text="Анна",
                due_date_text="до пятницы",
                truth_label="supported",
                source_refs=[source],
            )
        ],
    )
    decisions = category(
        "decisions",
        "available",
        [
            OutcomeItemView(
                category="decisions",
                sequence=0,
                text="Запускать после контрольной проверки.",
                truth_label="supported",
                source_refs=[source],
            )
        ],
    )
    risks = category(
        "risks",
        "available",
        [
            OutcomeItemView(
                category="risks",
                sequence=0,
                text="Срок зависит от готовности доступов.",
                truth_label="supported",
                source_refs=[source],
            )
        ],
    )
    empty = category("empty", "not_found")
    review.notes_action_truth = NotesActionTruthState(
        summary=summary,
        key_points=empty,
        decisions=decisions,
        action_items=actions,
        followups=empty,
        risks=risks,
        questions=empty,
        evidence=empty,
        source_basis="stored_output",
    )
    review.content_exports = ContentExportCapabilityResponse(
        processing_result_id=RESULT_ID,
        outcome_set_id=OUTCOME_ID,
        transcript=ContentExportReadiness(state="available" if transcript else "missing"),
        summary=ContentExportReadiness(state="available"),
        combined=ContentExportReadiness(state="available" if transcript else "missing"),
        formats={"transcript": ["txt"], "summary": ["txt"], "combined": ["txt"]},
        defaults=ContentExportDefaults(),
        language="ru",
        duration_seconds=120,
    )
    return review


accepted = accepted_review()
candidate = accepted_review()
processing = _review()
processing.meeting.title = "Синтетическая встреча в обработке"
no_player = accepted_review(transcript=False, playback=False)

print(json.dumps({
    "accepted": render_meeting_detail_page(accepted),
    "candidate": render_meeting_detail_page(candidate),
    "processing": render_meeting_detail_page(processing),
    "no-player": render_meeting_detail_page(no_player),
    "summary-only": render_shared_meeting_summary_page(
        meeting_title="Синтетический проектный синк",
        occurred_at=datetime(2026, 8, 4, 12, 0, tzinfo=UTC),
        duration_seconds=120,
        summary_sections=[
            {"category": "summary", "text": "Команда согласовала запуск и план проверки."},
            {
                "category": "action_items",
                "text": "Подготовить план запуска.",
                "owner_text": "Анна",
                "due_date_text": "до пятницы",
            },
            {"category": "decisions", "text": "Запускать после контрольной проверки."},
        ],
        authenticated=True,
    ),
}, ensure_ascii=False))
`;

function renderPages() {
  const result = spawnSync(path.join(serverDir, ".venv/bin/python"), ["-c", python], {
    cwd: serverDir,
    env: { ...process.env, PYTHONPATH: "src:." },
    encoding: "utf8",
  });
  if (result.status !== 0) throw new Error(`renderer failed\n${result.stderr}`);
  return JSON.parse(result.stdout);
}

function silenceWav(seconds = 120, sampleRate = 8000) {
  const samples = seconds * sampleRate;
  const buffer = Buffer.alloc(44 + samples, 128);
  buffer.write("RIFF", 0);
  buffer.writeUInt32LE(36 + samples, 4);
  buffer.write("WAVEfmt ", 8);
  buffer.writeUInt32LE(16, 16);
  buffer.writeUInt16LE(1, 20);
  buffer.writeUInt16LE(1, 22);
  buffer.writeUInt32LE(sampleRate, 24);
  buffer.writeUInt32LE(sampleRate, 28);
  buffer.writeUInt16LE(1, 32);
  buffer.writeUInt16LE(8, 34);
  buffer.write("data", 36);
  buffer.writeUInt32LE(samples, 40);
  return buffer;
}

const candidateSourceRefs = [0, 1, 2, 3].map((sequence) => ({
  transcript_segment_id: `00000000-0000-0000-0000-${String(139 + sequence).padStart(12, "0")}`,
  sequence,
  start_seconds: 12.5 + sequence * 15,
  end_seconds: 22.5 + sequence * 15,
  evidence_kind: "segment",
  speaker_label: "Анна",
  source_role: "local_microphone",
  seekable: true,
}));

const candidate = {
  candidate_id: "30000000-0000-0000-0000-000000000139",
  state: "ready",
  current_outcome_set_id: "20000000-0000-0000-0000-000000000139",
  poll_url: "/synthetic/candidate",
  outcome_set_id: "40000000-0000-0000-0000-000000000139",
  template_key: "graf-auto-v1",
  template_name: "Авто",
  template_version: 1,
  reason_code: null,
  retryable: false,
  next_action: "review",
  format_name: "Авто",
  provenance: {
    source_result_id: "10000000-0000-0000-0000-000000000139",
    source_revision_label: "Версия расшифровки 1",
    generator_version: "graf-outcomes-ai-v1",
  },
  preview: [
    {
      category: "summary",
      sequence: 0,
      text: "Команда согласовала запуск после контрольной проверки.",
      owner_text: "",
      due_date_text: "",
      truth_label: "supported",
      source_refs: candidateSourceRefs,
    },
    {
      category: "action_items",
      sequence: 0,
      text: "Подготовить контрольный план запуска.",
      owner_text: "Анна",
      due_date_text: "до пятницы",
      truth_label: "supported",
      source_refs: [{ transcript_segment_id: "00000000-0000-0000-0000-000000000139", sequence: 0, start_seconds: 12.5, end_seconds: 52, evidence_kind: "segment", speaker_label: "Анна", source_role: "local_microphone", seekable: true }],
    },
    {
      category: "decisions",
      sequence: 0,
      text: "Запускать после контрольной проверки.",
      owner_text: "",
      due_date_text: "",
      truth_label: "supported",
      source_refs: [{ transcript_segment_id: "00000000-0000-0000-0000-000000000139", sequence: 0, start_seconds: 12.5, end_seconds: 52, evidence_kind: "segment", speaker_label: "Анна", source_role: "local_microphone", seekable: true }],
    },
    {
      category: "risks",
      sequence: 0,
      text: "Срок зависит от готовности доступов.",
      owner_text: "",
      due_date_text: "",
      truth_label: "supported",
      source_refs: [{ transcript_segment_id: "00000000-0000-0000-0000-000000000139", sequence: 0, start_seconds: 12.5, end_seconds: 52, evidence_kind: "segment", speaker_label: "Анна", source_role: "local_microphone", seekable: true }],
    },
  ],
};

const pages = renderPages();
const audio = silenceWav();
let candidateVisible = true;
const server = http.createServer((request, response) => {
  const url = new URL(request.url, "http://127.0.0.1");
  const send = (status, type, body) => {
    response.writeHead(status, {
      "Cache-Control": "private, no-store",
      "Content-Type": type,
    });
    response.end(body);
  };
  if (url.pathname.endsWith("/cabinet.css")) return send(200, "text/css; charset=utf-8", css);
  if (url.pathname.endsWith("/cabinet.js")) return send(200, "text/javascript; charset=utf-8", js);
  if (url.pathname.endsWith("/graf-icon.png")) return send(200, "image/png", icon);
  if (url.pathname.endsWith("/graf-wordmark-dark@2x.png")) return send(200, "image/png", wordmark2x);
  if (url.pathname.endsWith("/graf-wordmark-dark.png")) return send(200, "image/png", wordmark);
  if (url.pathname === "/synthetic/runtime.wav") return send(200, "audio/wav", audio);
  if (/\/api\/v1\/cabinet\/meetings\/[^/]+\/summary-candidates\/[^/]+\/(accept|reject)$/.test(url.pathname)) {
    candidateVisible = false;
    return send(200, "application/json; charset=utf-8", JSON.stringify({ current_outcome_set_id: candidate.outcome_set_id }));
  }
  if (/\/api\/v1\/cabinet\/meetings\/[^/]+\/summary-candidates$/.test(url.pathname)) {
    const isCandidatePage = String(request.headers.referer || "").includes("/candidate");
    return send(200, "application/json; charset=utf-8", JSON.stringify({ candidates: isCandidatePage && candidateVisible ? [candidate] : [] }));
  }
  const key = url.pathname.slice(1) || "accepted";
  if (pages[key]) return send(200, "text/html; charset=utf-8", pages[key]);
  return send(404, "text/plain; charset=utf-8", "not found");
});

server.listen(0, "127.0.0.1", () => {
  const { port } = server.address();
  process.stdout.write(`${JSON.stringify({
    baseUrl: `http://127.0.0.1:${port}`,
    states: Object.keys(pages),
  })}\n`);
});

const close = () => server.close(() => process.exit(0));
process.on("SIGINT", close);
process.on("SIGTERM", close);
