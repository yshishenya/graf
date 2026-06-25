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
        duration_seconds=120,
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
                start_seconds=12.5,
                end_seconds=18.0,
                timestamp_label="00:12",
                speaker_label="Speaker 2",
                source_role="incoming_system",
                text="Еще один безопасный синтетический текст для проверки.",
                seekable=True,
                seek_seconds=12.5,
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
                talk_time_percent=45,
                source_roles=["local_microphone"],
                segments=[SpeakerLaneSegment(start_seconds=0.0, end_seconds=8.0)],
            ),
            SpeakerLane(
                speaker_key="speaker-2",
                label="Speaker 2",
                talk_time_percent=55,
                source_roles=["incoming_system"],
                segments=[SpeakerLaneSegment(start_seconds=12.5, end_seconds=18.0)],
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
                text=(
                    "Синтетический длинный итог встречи занимает несколько строк "
                    "и нужен только для проверки верстки."
                ),
                truth_label="supported",
                source_refs=[
                    OutcomeSourceReferenceView(
                        sequence=1,
                        start_seconds=12.5,
                        end_seconds=18.0,
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


def outcome_truth(mode):
    if mode == "stored":
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
    if mode == "processing":
        processing = category("processing", "Итоги готовятся")
        return NotesActionTruthState(
            summary=processing,
            key_points=processing,
            decisions=processing,
            action_items=processing,
            followups=processing,
            risks=processing,
            questions=processing,
            evidence=processing,
            source_basis="processing_status",
        )
    blocked = category("blocked", "Итоги заблокированы")
    return NotesActionTruthState(
        summary=blocked,
        key_points=blocked,
        decisions=blocked,
        action_items=blocked,
        followups=blocked,
        risks=blocked,
        questions=blocked,
        evidence=blocked,
        source_basis="blocked",
    )


def page(*, embedded, mode):
    review = _review()
    review.playback = playback_review()
    review.transcript = transcript_review()
    review.speakers = speaker_review()
    review.notes_action_truth = outcome_truth(mode)
    return render_meeting_detail_page(review, embedded=embedded)


print(json.dumps({
    "webStored": page(embedded=False, mode="stored"),
    "embeddedStored": page(embedded=True, mode="stored"),
    "webProcessing": page(embedded=False, mode="processing"),
    "embeddedBlocked": page(embedded=True, mode="blocked"),
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
  await page.setContent(html, { waitUntil: "domcontentloaded" });
  const metrics = await page.evaluate(async () => {
    const audio = document.querySelector("[data-playback-player]");
    if (audio) {
      audio.play = () => {
        audio.dispatchEvent(new Event("play"));
        return Promise.resolve();
      };
    }
    const seekButton = document.querySelectorAll("[data-seek-seconds]")[1];
    if (seekButton) seekButton.click();
    await new Promise((resolve) => setTimeout(resolve, 20));
    const bar = document.querySelector("[data-playback-shell]");
    const item = document.querySelector(".notes-outcome-row .outcome-item");
    const itemStyle = item ? window.getComputedStyle(item) : null;
    const outcomeRows = Array.from(document.querySelectorAll("[data-outcome-category]"));
    return {
      sourceBasis: document.querySelector("[data-outcome-source-basis]")?.getAttribute("data-outcome-source-basis") || null,
      outcomeRows: outcomeRows.length,
      states: outcomeRows.map((row) => [row.getAttribute("data-outcome-category"), row.getAttribute("data-outcome-state")]),
      outcomeItemCount: document.querySelectorAll(".outcome-item").length,
      itemGridColumnStart: itemStyle ? itemStyle.gridColumnStart : null,
      itemGridColumnEnd: itemStyle ? itemStyle.gridColumnEnd : null,
      audioCount: document.querySelectorAll("[data-playback-player]").length,
      barCount: document.querySelectorAll("[data-playback-shell]").length,
      seekTargets: document.querySelectorAll("[data-seek-seconds]").length,
      seekCurrentTime: audio ? audio.currentTime : null,
      timelineSegments: document.querySelectorAll("[data-lane-segment]").length,
      horizontalOverflow: Math.max(
        0,
        document.documentElement.scrollWidth - document.documentElement.clientWidth,
        document.body.scrollWidth - document.body.clientWidth,
      ),
      barBottom: bar ? Math.round(window.innerHeight - bar.getBoundingClientRect().bottom) : null,
      mainPaddingBottom: parseFloat(window.getComputedStyle(document.querySelector(".detail-page-main")).paddingBottom || "0"),
      hasEnglishCategoryLabel: document.body.innerText.includes("Key points") || document.body.innerText.includes("Evidence"),
    };
  });
  await page.close();
  const failures = [];
  if (metrics.outcomeRows !== 8) failures.push(`outcomeRows=${metrics.outcomeRows}`);
  if (metrics.audioCount !== 1) failures.push(`audioCount=${metrics.audioCount}`);
  if (metrics.barCount !== 1) failures.push(`barCount=${metrics.barCount}`);
  if (metrics.seekTargets < 2) failures.push(`seekTargets=${metrics.seekTargets}`);
  if (Math.abs(metrics.seekCurrentTime - 12.5) > 0.2) failures.push(`seekCurrentTime=${metrics.seekCurrentTime}`);
  if (metrics.timelineSegments !== 2) failures.push(`timelineSegments=${metrics.timelineSegments}`);
  if (metrics.horizontalOverflow > 1) failures.push(`horizontalOverflow=${metrics.horizontalOverflow}`);
  if (metrics.barBottom !== 0) failures.push(`barBottom=${metrics.barBottom}`);
  if (metrics.mainPaddingBottom < 160) failures.push(`mainPaddingBottom=${metrics.mainPaddingBottom}`);
  if (metrics.hasEnglishCategoryLabel) failures.push("english outcome category label visible");
  if (metrics.outcomeItemCount > 0 && (metrics.itemGridColumnStart !== "1" || metrics.itemGridColumnEnd !== "-1")) {
    failures.push(`itemGridColumn=${metrics.itemGridColumnStart}/${metrics.itemGridColumnEnd}`);
  }
  return { label, viewport, failures, metrics };
}

(async () => {
  const pages = renderPages();
  const browser = await chromium.launch({ headless: true, executablePath: chromePath });
  const results = [
    await inspectPage(browser, "web-stored-desktop", pages.webStored, { width: 1440, height: 900 }),
    await inspectPage(browser, "web-stored-mobile", pages.webStored, { width: 390, height: 844 }),
    await inspectPage(browser, "embedded-stored-desktop", pages.embeddedStored, { width: 1200, height: 820 }),
    await inspectPage(browser, "embedded-stored-mobile", pages.embeddedStored, { width: 390, height: 844 }),
    await inspectPage(browser, "web-processing-mobile", pages.webProcessing, { width: 390, height: 844 }),
    await inspectPage(browser, "embedded-blocked-mobile", pages.embeddedBlocked, { width: 390, height: 844 }),
  ];
  await browser.close();

  const stateMap = (result) => JSON.stringify(result.metrics.states);
  const failures = results.flatMap((result) => result.failures.map((failure) => `${result.label}: ${failure}`));
  if (stateMap(results[0]) !== stateMap(results[2])) failures.push("stored web/embedded states differ");
  if (results[0].metrics.sourceBasis !== "stored_output") failures.push("web stored source basis mismatch");
  if (results[2].metrics.sourceBasis !== "stored_output") failures.push("embedded stored source basis mismatch");
  if (results[4].metrics.sourceBasis !== "processing_status") failures.push("processing source basis mismatch");
  if (results[5].metrics.sourceBasis !== "blocked") failures.push("blocked source basis mismatch");

  console.log(JSON.stringify({ failures, results }, null, 2));
  process.exit(failures.length === 0 ? 0 : 1);
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
