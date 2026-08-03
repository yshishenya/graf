const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { chromium } = require(
  process.env.GRAF_NODE_MODULES
    ? path.join(process.env.GRAF_NODE_MODULES, "playwright")
    : "playwright",
);

const repoRoot = process.cwd();
const serverDir = path.join(repoRoot, "apps/server");
const chromePath = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const css = fs.readFileSync(
  path.join(serverDir, "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css"),
  "utf8",
);
const js = fs.readFileSync(
  path.join(serverDir, "src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"),
  "utf8",
);

const python = String.raw`
import json

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
    TranscriptReviewState,
    TranscriptSegmentView,
)
from twobrain_rec_server.cabinet.rendering import render_meeting_detail_page


def category(name, state, items=None):
    labels = {
        "summary": "Итоги готовы",
        "action_items": "Действия",
        "decisions": "Решения",
    }
    return NotesActionCategoryState(
        state=state,
        label=labels.get(name, "Не найдено"),
        reason="Синтетическое состояние для runtime-проверки.",
        readiness_impact="closes_gap" if state in {"available", "not_found"} else "keeps_gap_open",
        copy_key=f"notes.runtime.{name}.{state}",
        items=items or [],
    )


def stored_page(embedded=False):
    review = _review()
    review.playback = PlaybackReviewState(
        available=True,
        duration_seconds=120,
        speed_options=[0.75, 1.0, 1.25, 1.5, 2.0],
        unavailable_reason="none",
        playback_path="/synthetic/runtime.m4a",
        policy_label="Аудио доступно для проверки",
        source_mode="stored_review_m4a",
        included_sources=["local_microphone", "incoming_system"],
    )
    review.transcript = TranscriptReviewState(
        available=True,
        language="ru",
        search_enabled=True,
        segments=[
            TranscriptSegmentView(
                segment_id="synthetic-1",
                sequence=0,
                start_seconds=12.5,
                end_seconds=20.0,
                timestamp_label="00:12",
                speaker_label="SPEAKER_00",
                source_role="local_microphone",
                text="Синтетический фрагмент для проверки перехода.",
                seekable=True,
                seek_seconds=12.5,
            )
        ],
    )
    summary = category(
        "summary",
        "available",
        [
            OutcomeItemView(
                category="summary",
                sequence=0,
                text="Команда согласовала следующий шаг.",
                truth_label="supported",
                source_refs=[
                    OutcomeSourceReferenceView(
                        sequence=0,
                        start_seconds=12.5,
                        end_seconds=20.0,
                        evidence_kind="segment",
                    )
                ],
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
                text="Подготовить план миграции.",
                owner_text="Алексей",
                due_date_text="до пятницы",
                truth_label="supported",
                source_refs=[
                    OutcomeSourceReferenceView(
                        sequence=0,
                        start_seconds=45.0,
                        end_seconds=52.0,
                        evidence_kind="segment",
                    )
                ],
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
                text="Проверить план на следующей встрече.",
                truth_label="supported",
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
        risks=empty,
        questions=empty,
        evidence=empty,
        source_basis="stored_output",
    )
    review.content_exports = ContentExportCapabilityResponse(
        processing_result_id=None,
        outcome_set_id=None,
        transcript=ContentExportReadiness(state="available"),
        summary=ContentExportReadiness(state="available"),
        combined=ContentExportReadiness(state="available"),
        formats={"transcript": ["txt"], "summary": ["txt"], "combined": ["txt"]},
        defaults=ContentExportDefaults(),
        language="ru",
        duration_seconds=120,
    )
    return render_meeting_detail_page(review, embedded=embedded)


def blocked_page():
    review = _review()
    blocked = category("summary", "blocked", [
        OutcomeItemView(
            category="summary",
            sequence=0,
            text="НЕ ДОЛЖНО ПОПАСТЬ В HTML",
            truth_label="blocked",
        )
    ])
    review.notes_action_truth = NotesActionTruthState(
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
    return render_meeting_detail_page(review, embedded=True)


print(json.dumps({
    "webStored": stored_page(),
    "embeddedStored": stored_page(embedded=True),
    "embeddedBlocked": blocked_page(),
}, ensure_ascii=False))
`;

function renderPages() {
  const result = spawnSync("uv", ["run", "--extra", "dev", "python", "-c", python], {
    cwd: serverDir,
    env: { ...process.env, PYTHONPATH: "src:." },
    encoding: "utf8",
  });
  if (result.status !== 0) throw new Error(`renderer failed\n${result.stderr}`);
  return JSON.parse(result.stdout);
}

function preparedHtml(html) {
  return html
    .replace("</head>", `<style>${css}</style></head>`)
    .replace("</body>", `<script>${js}</script></body>`);
}

async function inspectPage(browser, label, html, viewport, pageServer, { blocked = false } = {}) {
  const pagePath = `/pages/${encodeURIComponent(label)}`;
  pageServer.pages.set(pagePath, preparedHtml(html));
  const page = await browser.newPage({ viewport });
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.goto(`${pageServer.baseUrl}${pagePath}`, { waitUntil: "domcontentloaded" });
  const metrics = await page.evaluate(async (isBlocked) => {
    const audio = document.querySelector("[data-playback-player]");
    if (audio) {
      audio.play = () => {
        audio.dispatchEvent(new Event("play"));
        return Promise.resolve();
      };
    }
    const categories = Array.from(document.querySelectorAll("[data-outcome-category]"));
    const source = document.querySelector(".notes-source-link");
    if (source) source.click();
    await new Promise((resolve) => setTimeout(resolve, 20));
    const afterSourceHash = window.location.hash;
    document.querySelector('[data-detail-tab="outcomes"]')?.click();
    const playerBar = document.querySelector("[data-playback-shell]");
    const more = document.querySelector(".notes-more");
    return {
      order: categories.map((row) => row.dataset.outcomeCategory),
      states: categories.map((row) => [row.dataset.outcomeCategory, row.dataset.outcomeState]),
      sourceBasis: document.querySelector("[data-outcome-source-basis]")?.dataset.outcomeSourceBasis || null,
      actionOwner: document.body.innerText.includes("Ответственный: Алексей"),
      actionDue: document.body.innerText.includes("Срок: до пятницы"),
      sourceControls: document.querySelectorAll(".notes-source-link").length,
      sourceNames: Array.from(document.querySelectorAll(".notes-source-link")).every((button) => Boolean(button.getAttribute("aria-label"))),
      sourceHash: afterSourceHash,
      exportTriggerPresent: Boolean(document.querySelector("[data-export-dialog-open]")),
      secondaryCollapsed: Boolean(more && !more.open),
      blockedTextPresent: document.body.innerText.includes("НЕ ДОЛЖНО ПОПАСТЬ В HTML"),
      horizontalOverflow: Math.max(
        0,
        document.documentElement.scrollWidth - document.documentElement.clientWidth,
        document.body.scrollWidth - document.body.clientWidth,
      ),
      playerBottom: playerBar ? Math.round(window.innerHeight - playerBar.getBoundingClientRect().bottom) : null,
      mainPaddingBottom: parseFloat(window.getComputedStyle(document.querySelector(".detail-page-main")).paddingBottom || "0"),
      englishCategory: document.body.innerText.includes("Key points") || document.body.innerText.includes("Evidence"),
      outcomeItemCount: document.querySelectorAll(".outcome-item").length,
      blocked: isBlocked,
    };
  }, blocked);
  metrics.pageErrors = pageErrors;
  await page.close();
  const failures = [];
  if (!blocked && JSON.stringify(metrics.order.slice(0, 3)) !== JSON.stringify(["summary", "action_items", "decisions"])) failures.push("priority order");
  if (!blocked && metrics.sourceControls !== 2) failures.push(`sourceControls=${metrics.sourceControls}`);
  if (!blocked && (!metrics.actionOwner || !metrics.actionDue)) failures.push("action metadata missing");
  if (!blocked && metrics.sourceHash !== "#recording") failures.push(`sourceHash=${metrics.sourceHash}`);
  if (!blocked && !metrics.exportTriggerPresent) failures.push("export trigger missing");
  if (!blocked && !metrics.secondaryCollapsed) failures.push("secondary sections are not collapsed");
  if (metrics.blockedTextPresent) failures.push("blocked outcome text leaked");
  if (!blocked && metrics.horizontalOverflow > 1) failures.push(`horizontalOverflow=${metrics.horizontalOverflow}`);
  if (!blocked && metrics.playerBottom !== 0) failures.push(`playerBottom=${metrics.playerBottom}`);
  if (!blocked && metrics.mainPaddingBottom < 160) failures.push(`mainPaddingBottom=${metrics.mainPaddingBottom}`);
  if (metrics.englishCategory) failures.push("english category visible");
  if (metrics.pageErrors.length) failures.push(`pageErrors=${metrics.pageErrors.join(" | ")}`);
  return { label, viewport, failures, metrics };
}

(async () => {
  const pages = renderPages();
  const pageServer = { pages: new Map(), baseUrl: "" };
  const server = http.createServer((request, response) => {
    const html = pageServer.pages.get(request.url);
    if (!html) {
      response.writeHead(404);
      response.end("not found");
      return;
    }
    response.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    response.end(html);
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  pageServer.baseUrl = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({
    headless: true,
    ...(fs.existsSync(chromePath) ? { executablePath: chromePath } : {}),
  });
  const results = [
    await inspectPage(browser, "web-stored-desktop", pages.webStored, { width: 1440, height: 900 }, pageServer),
    await inspectPage(browser, "web-stored-mobile", pages.webStored, { width: 390, height: 844 }, pageServer),
    await inspectPage(browser, "embedded-stored-mobile", pages.embeddedStored, { width: 390, height: 844 }, pageServer),
    await inspectPage(browser, "embedded-blocked-mobile", pages.embeddedBlocked, { width: 390, height: 844 }, pageServer, { blocked: true }),
  ];
  await browser.close();
  await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  const failures = results.flatMap((result) => result.failures.map((failure) => `${result.label}: ${failure}`));
  if (JSON.stringify(results[0].metrics.states) !== JSON.stringify(results[2].metrics.states)) failures.push("web/embedded state parity");
  if (results[0].metrics.sourceBasis !== "stored_output" || results[2].metrics.sourceBasis !== "stored_output") failures.push("stored source basis");
  if (results[3].metrics.sourceBasis !== "blocked") failures.push("blocked source basis");
  console.log(JSON.stringify({ failures, results }, null, 2));
  process.exit(failures.length ? 1 : 0);
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
