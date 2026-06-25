const { spawnSync } = require("node:child_process");
const { chromium } = require("playwright");

const repoRoot = process.cwd();
const serverDir = `${repoRoot}/apps/server`;
const chromePath = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const python = String.raw`
import json

from tests.unit.test_cabinet_web_shell import _review
from twobrain_rec_server.api.schemas import (
    NotesActionCategoryState,
    NotesActionTruthState,
    OutcomeItemView,
    OutcomeSourceReferenceView,
    PlaybackReviewState,
    SpeakerLane,
    SpeakerLaneSegment,
    SpeakerReviewState,
    TranscriptReviewState,
    TranscriptSegmentView,
)
from twobrain_rec_server.cabinet.web import render_meeting_detail_page


def playback_review():
    return PlaybackReviewState(
        available=True,
        duration_seconds=180,
        speed_options=[0.75, 1.0, 1.25, 1.5, 2.0],
        unavailable_reason="none",
        playback_path="/api/v1/cabinet/meetings/safe-runtime/playback",
        policy_label="Аудио доступно для проверки",
        source_mode="combined_review_stream",
        included_sources=["local_microphone", "incoming_system"],
    )


def transcript_review():
    return TranscriptReviewState(
        available=True,
        language="ru",
        search_enabled=True,
        segments=[
            TranscriptSegmentView(
                segment_id="safe-runtime-1",
                sequence=0,
                start_seconds=0.0,
                end_seconds=8.0,
                timestamp_label="00:00",
                speaker_label="Speaker 1",
                source_role="local_microphone",
                text="Безопасный синтетический текст для проверки строки.",
                seekable=True,
                seek_seconds=0.0,
            ),
            TranscriptSegmentView(
                segment_id="safe-runtime-2",
                sequence=1,
                start_seconds=18.0,
                end_seconds=31.0,
                timestamp_label="00:18",
                speaker_label="Speaker 2",
                source_role="incoming_system",
                text="Еще один безопасный синтетический текст для проверки.",
                seekable=True,
                seek_seconds=18.0,
            ),
            TranscriptSegmentView(
                segment_id="safe-runtime-3",
                sequence=2,
                start_seconds=64.0,
                end_seconds=78.0,
                timestamp_label="01:04",
                speaker_label="Speaker 3",
                source_role="local_microphone",
                text="Третья безопасная строка нужна для проверки длинной шкалы.",
                seekable=True,
                seek_seconds=64.0,
            ),
        ],
    )


def speaker_review():
    return SpeakerReviewState(
        available=True,
        assignment_state="reserved",
        degraded_reason=None,
        speakers=[
            SpeakerLane(
                speaker_key="speaker-1",
                label="Speaker 1",
                talk_time_percent=32,
                source_roles=["local_microphone"],
                segments=[SpeakerLaneSegment(start_seconds=0.0, end_seconds=8.0)],
            ),
            SpeakerLane(
                speaker_key="speaker-2",
                label="Speaker 2",
                talk_time_percent=44,
                source_roles=["incoming_system"],
                segments=[SpeakerLaneSegment(start_seconds=18.0, end_seconds=31.0)],
            ),
            SpeakerLane(
                speaker_key="speaker-3",
                label="Speaker 3",
                talk_time_percent=24,
                source_roles=["local_microphone"],
                segments=[SpeakerLaneSegment(start_seconds=64.0, end_seconds=78.0)],
            ),
        ],
    )


def category(state, label, *, item=False):
    items = []
    if item:
        items = [
            OutcomeItemView(
                category="summary",
                sequence=0,
                text="Синтетический итог встречи нужен только для проверки верстки.",
                truth_label="supported",
                source_refs=[
                    OutcomeSourceReferenceView(
                        sequence=1,
                        start_seconds=18.0,
                        end_seconds=31.0,
                        evidence_kind="segment",
                    )
                ],
            )
        ]
    return NotesActionCategoryState(
        state=state,
        label=label,
        reason="Состояние итогов проверяется синтетическим runtime verifier.",
        readiness_impact="closes_gap" if state in {"available", "not_found", "not_inferable"} else "keeps_gap_open",
        copy_key=f"notes.runtime.{state}",
        items=items,
    )


def outcome_truth():
    summary = category("available", "Итоги готовы", item=True)
    not_found = category("not_found", "Не найдено")
    return NotesActionTruthState(
        summary=summary,
        key_points=summary,
        decisions=not_found,
        action_items=not_found,
        followups=not_found,
        risks=not_found,
        questions=not_found,
        evidence=summary,
        source_basis="stored_output",
    )


def page(*, embedded):
    review = _review()
    review.playback = playback_review()
    review.transcript = transcript_review()
    review.speakers = speaker_review()
    review.notes_action_truth = outcome_truth()
    return render_meeting_detail_page(review, embedded=embedded)


print(json.dumps({
    "web": page(embedded=False),
    "embedded": page(embedded=True),
}, ensure_ascii=False))
`;

function renderPages() {
  const result = spawnSync("uv", ["run", "--extra", "dev", "python", "-c", python], {
    cwd: serverDir,
    env: { ...process.env, PYTHONPATH: "src:." },
    encoding: "utf8",
  });
  if (result.status !== 0) {
    throw new Error(`renderer failed\nstdout=${result.stdout}\nstderr=${result.stderr}`);
  }
  return JSON.parse(result.stdout);
}

async function inspectPage(browser, label, html, viewport) {
  const page = await browser.newPage({ viewport });
  const consoleErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  await page.setContent(html, { waitUntil: "domcontentloaded" });
  const metrics = await page.evaluate(async () => {
    const audio = document.querySelector("[data-playback-player]");
    if (audio) {
      audio.play = () => {
        audio.dispatchEvent(new Event("play"));
        return Promise.resolve();
      };
    }
    const seekButtons = Array.from(document.querySelectorAll("[data-seek-seconds]"));
    if (seekButtons[2]) seekButtons[2].click();
    await new Promise((resolve) => setTimeout(resolve, 30));
    const bar = document.querySelector("[data-playback-shell]");
    const progress = document.querySelector("[data-playback-progress]");
    const timelineRows = Array.from(document.querySelectorAll(".speaker-lane"));
    const outcomeRows = Array.from(document.querySelectorAll("[data-outcome-category]"));
    return {
      activeTab: document.querySelector("[data-detail-tab][aria-selected='true'], .tab.active")?.textContent?.trim() || "",
      audioCount: document.querySelectorAll("[data-playback-player]").length,
      playbackShells: document.querySelectorAll("[data-playback-shell]").length,
      sourceMode: bar ? bar.getAttribute("data-source-mode") : null,
      seekTargets: seekButtons.length,
      seekCurrentTime: audio ? audio.currentTime : null,
      progressMax: progress ? progress.getAttribute("max") : null,
      timelineRows: timelineRows.length,
      timelineSegments: document.querySelectorAll("[data-lane-segment]").length,
      speakerLabels: timelineRows.map((row) => row.textContent || ""),
      outcomeRows: outcomeRows.length,
      outcomeSourceBasis: document.querySelector("[data-outcome-source-basis]")?.getAttribute("data-outcome-source-basis") || null,
      horizontalOverflow: Math.max(
        0,
        document.documentElement.scrollWidth - document.documentElement.clientWidth,
        document.body.scrollWidth - document.body.clientWidth,
      ),
      barBottom: bar ? Math.round(window.innerHeight - bar.getBoundingClientRect().bottom) : null,
      mainPaddingBottom: parseFloat(window.getComputedStyle(document.querySelector(".detail-page-main")).paddingBottom || "0"),
    };
  });
  await page.close();

  const failures = [];
  if (
    !metrics.activeTab.includes("Recording") &&
    !metrics.activeTab.includes("Transcript") &&
    !metrics.activeTab.includes("Запись") &&
    !metrics.activeTab.includes("Расшифровка")
  ) {
    failures.push(`activeTab=${metrics.activeTab}`);
  }
  if (metrics.audioCount !== 1) failures.push(`audioCount=${metrics.audioCount}`);
  if (metrics.playbackShells !== 1) failures.push(`playbackShells=${metrics.playbackShells}`);
  if (metrics.sourceMode !== "combined_review_stream") failures.push(`sourceMode=${metrics.sourceMode}`);
  if (metrics.seekTargets !== 3) failures.push(`seekTargets=${metrics.seekTargets}`);
  if (Math.abs(metrics.seekCurrentTime - 64.0) > 0.2) failures.push(`seekCurrentTime=${metrics.seekCurrentTime}`);
  if (metrics.progressMax !== "180") failures.push(`progressMax=${metrics.progressMax}`);
  if (metrics.timelineRows !== 3) failures.push(`timelineRows=${metrics.timelineRows}`);
  if (metrics.timelineSegments !== 3) failures.push(`timelineSegments=${metrics.timelineSegments}`);
  if (!metrics.speakerLabels.every((labelText) => labelText.includes("Speaker") || labelText.includes("Спикер"))) {
    failures.push("speaker labels missing");
  }
  if (metrics.outcomeRows !== 8) failures.push(`outcomeRows=${metrics.outcomeRows}`);
  if (metrics.outcomeSourceBasis !== "stored_output") failures.push(`outcomeSourceBasis=${metrics.outcomeSourceBasis}`);
  if (metrics.horizontalOverflow > 1) failures.push(`horizontalOverflow=${metrics.horizontalOverflow}`);
  if (metrics.barBottom !== 0) failures.push(`barBottom=${metrics.barBottom}`);
  if (metrics.mainPaddingBottom < 160) failures.push(`mainPaddingBottom=${metrics.mainPaddingBottom}`);
  for (const error of consoleErrors) failures.push(`console=${error}`);
  return { label, viewport, failures, metrics };
}

(async () => {
  const pages = renderPages();
  const browser = await chromium.launch({ headless: true, executablePath: chromePath });
  const results = [
    await inspectPage(browser, "web-desktop", pages.web, { width: 1440, height: 900 }),
    await inspectPage(browser, "web-mobile", pages.web, { width: 390, height: 844 }),
    await inspectPage(browser, "embedded-desktop", pages.embedded, { width: 1200, height: 820 }),
    await inspectPage(browser, "embedded-mobile", pages.embedded, { width: 390, height: 844 }),
  ];
  await browser.close();
  const failures = results.flatMap((result) => result.failures.map((failure) => `${result.label}: ${failure}`));
  console.log(JSON.stringify({ failures, results }, null, 2));
  process.exit(failures.length === 0 ? 0 : 1);
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
