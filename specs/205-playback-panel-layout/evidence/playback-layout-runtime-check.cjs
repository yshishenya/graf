const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { chromium, webkit } = require(
  process.env.GRAF_NODE_MODULES
    ? path.join(process.env.GRAF_NODE_MODULES, "playwright")
    : "playwright",
);
const browserType = process.env.GRAF_BROWSER === "webkit" ? webkit : chromium;

const root = process.cwd();
const serverDir = path.join(root, "apps/server");
const staticDir = path.join(serverDir, "src/twobrain_rec_server/cabinet/static/cabinet");
const css = fs.readFileSync(path.join(staticDir, "cabinet.css"), "utf8");
const js = fs.readFileSync(path.join(staticDir, "cabinet.js"), "utf8");
const chromePath = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

const python = String.raw`
import json
from datetime import UTC, datetime
from tests.unit.test_cabinet_web_shell import _item, _review
from twobrain_rec_server.api.schemas import MeetingFilterState, MeetingListResponse, PlaybackReviewState
from twobrain_rec_server.cabinet.rendering import render_meeting_detail_page, render_meeting_list_page
from twobrain_rec_server.cabinet.view_models import AccountProfileView

available = _review()
available.playback = PlaybackReviewState(
    available=True,
    duration_seconds=120,
    playback_path="/synthetic/runtime.m4a",
    source_mode="stored_review_m4a",
    included_sources=["local_microphone", "incoming_system"],
)
preparing = _review()
preparing.playback = PlaybackReviewState(
    state="preparing",
    reason_code="normalization_running",
    label="Готовим аудио…",
    automatic_recovery=True,
    duration_seconds=120,
)
unavailable = _review()
unavailable.playback = PlaybackReviewState(
    state="unavailable",
    reason_code="access_denied",
    label="Аудио недоступно",
    duration_seconds=120,
)
meeting_list = MeetingListResponse(
    items=[_item()],
    filters=MeetingFilterState(q=None, status=None, access=None, sort="updated_desc"),
    generated_at=datetime.now(UTC),
)
profile = AccountProfileView(
    display_name="Ян",
    primary_email="shishenya.ya@professionals4-0.ru",
)
print(json.dumps({
    "web": render_meeting_detail_page(available),
    "embedded": render_meeting_detail_page(available, embedded=True, profile=profile),
    "preparing": render_meeting_detail_page(preparing),
    "unavailable": render_meeting_detail_page(unavailable),
    "list": render_meeting_list_page(meeting_list),
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

function preparedHtml(html, { scripts = true } = {}) {
  return html
    .replace("</head>", `<style>${css}</style></head>`)
    .replace("</body>", `${scripts ? `<script>${js}</script>` : ""}</body>`);
}

async function nextLayout(page) {
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}

async function measure(page, label, { minTimelineHeight = 0 } = {}) {
  const metrics = await page.evaluate(() => {
    const main = document.querySelector(".detail-page-main");
    const playback = document.querySelector(".playback-bar");
    const shell = document.querySelector("[data-cabinet-shell]");
    const sidebar = document.querySelector(".sidebar");
    const timeline = document.querySelector("[data-speaker-timeline]");
    const mainRect = main.getBoundingClientRect();
    const playbackRect = playback.getBoundingClientRect();
    const shellRect = shell.getBoundingClientRect();
    const sidebarRect = sidebar.getBoundingClientRect();
    main.scrollTop = main.scrollHeight;
    return {
      overflow: main.scrollHeight > main.clientHeight,
      leftDelta: Math.abs(mainRect.left - playbackRect.left),
      rightDelta: Math.abs(mainRect.right - playbackRect.right),
      overlap: Math.max(0, mainRect.bottom - playbackRect.top),
      gap: Math.max(0, playbackRect.top - mainRect.bottom),
      barBottomDelta: Math.abs(shellRect.bottom - playbackRect.bottom),
      horizontalOverflow: Math.max(0, shell.scrollWidth - shell.clientWidth),
      scrollAtEnd: Math.abs(main.scrollTop + main.clientHeight - main.scrollHeight) <= 1,
      pinned: shell.classList.contains("is-rail-pinned"),
      viewportWidth: document.documentElement.clientWidth,
      mainLeft: mainRect.left,
      mainRight: mainRect.right,
      sidebarDisplay: getComputedStyle(sidebar).display,
      sidebarLeft: sidebarRect.left,
      sidebarRight: sidebarRect.right,
      shellColumns: getComputedStyle(shell).gridTemplateColumns,
      playbackState: playback.dataset.playbackState,
      timelineHeight: timeline?.getBoundingClientRect().height || 0,
    };
  });
  const failures = [];
  if (!metrics.overflow) failures.push("content is not scrollable");
  for (const key of ["leftDelta", "rightDelta", "overlap", "gap", "barBottomDelta", "horizontalOverflow"]) {
    if (metrics[key] > 1) failures.push(`${key}=${metrics[key]}`);
  }
  if (!metrics.scrollAtEnd) failures.push("content cannot reach scroll end");
  if (minTimelineHeight && metrics.timelineHeight < minTimelineHeight) {
    failures.push(`timelineHeight=${metrics.timelineHeight}`);
  }
  if (metrics.sidebarDisplay === "none") {
    if (Math.abs(metrics.mainLeft) > 1) failures.push(`hiddenSidebarMainLeft=${metrics.mainLeft}`);
    if (Math.abs(metrics.viewportWidth - metrics.mainRight) > 1) failures.push(`hiddenSidebarMainRight=${metrics.mainRight}`);
  } else if (Math.abs(metrics.sidebarRight - metrics.mainLeft) > 1) {
    failures.push(`sidebarMainBoundary=${metrics.sidebarRight}/${metrics.mainLeft}`);
  }
  return { label, metrics, failures };
}

async function inspect(browser, server, name, html, viewport, { toggle = false, timelineHeight = 0 } = {}) {
  const route = `/${name}`;
  server.pages.set(route, preparedHtml(html));
  const page = await browser.newPage({ viewport });
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(`${server.baseUrl}${route}`, { waitUntil: "domcontentloaded" });
  await page.evaluate(() => {
    const filler = document.createElement("div");
    filler.dataset.runtimeOverflow = "true";
    filler.style.height = "1400px";
    document.querySelector(".detail-main")?.append(filler);
  });
  if (timelineHeight) {
    await page.evaluate((height) => {
      const timeline = document.querySelector("[data-speaker-timeline]");
      if (!timeline) throw new Error("speaker timeline missing");
      timeline.style.height = `${height}px`;
      timeline.style.maxHeight = `${height}px`;
    }, timelineHeight);
  }
  await nextLayout(page);
  const results = [await measure(page, `${name}-initial`, { minTimelineHeight: timelineHeight })];
  if (toggle) {
    await page.locator("[data-cabinet-rail-toggle]").click();
    await nextLayout(page);
    results.push(await measure(page, `${name}-toggled`));
  }
  if (process.env.GRAF_PLAYBACK_SCREENSHOTS === "1") {
    const output = path.join(root, "output/playwright");
    fs.mkdirSync(output, { recursive: true });
    await page.screenshot({ path: path.join(output, `${name}.png`), fullPage: false });
  }
  if (errors.length) results[0].failures.push(`pageErrors=${errors.join(" | ")}`);
  await page.close();
  return results;
}

async function inspectWithoutPlayback(browser, server, html) {
  const route = "/web-without-playback";
  server.pages.set(route, preparedHtml(html));
  const page = await browser.newPage({ viewport: { width: 390, height: 720 } });
  await page.goto(`${server.baseUrl}${route}`, { waitUntil: "domcontentloaded" });
  const metrics = await page.evaluate(() => {
    const main = document.querySelector(".cabinet-main");
    const shell = document.querySelector("[data-cabinet-shell]");
    const mainRect = main.getBoundingClientRect();
    const shellRect = shell.getBoundingClientRect();
    return {
      playbackCount: document.querySelectorAll(".playback-bar").length,
      bottomDelta: Math.abs(mainRect.bottom - shellRect.bottom),
      horizontalOverflow: Math.max(0, shell.scrollWidth - shell.clientWidth),
      paddingBottom: Number.parseFloat(getComputedStyle(main).paddingBottom),
    };
  });
  const failures = [];
  if (metrics.playbackCount) failures.push(`playbackCount=${metrics.playbackCount}`);
  if (metrics.bottomDelta > 1) failures.push(`bottomDelta=${metrics.bottomDelta}`);
  if (metrics.horizontalOverflow > 1) failures.push(`horizontalOverflow=${metrics.horizontalOverflow}`);
  if (metrics.paddingBottom > 64) failures.push(`paddingBottom=${metrics.paddingBottom}`);
  await page.close();
  return { label: "web-without-playback", metrics, failures };
}

async function inspectNoJsNarrow(browser, server, html) {
  const route = "/web-no-js-narrow";
  server.pages.set(route, preparedHtml(html, { scripts: false }));
  const context = await browser.newContext({
    viewport: { width: 390, height: 720 },
    javaScriptEnabled: false,
  });
  const page = await context.newPage();
  await page.goto(`${server.baseUrl}${route}`, { waitUntil: "domcontentloaded" });
  const metrics = await page.evaluate(() => {
    const nav = document.querySelector(".cabinet-mobile-noscript-nav");
    const main = document.querySelector(".detail-page-main");
    const playback = document.querySelector(".playback-bar");
    const shell = document.querySelector("[data-cabinet-shell]");
    const navRect = nav.getBoundingClientRect();
    const mainRect = main.getBoundingClientRect();
    const playbackRect = playback.getBoundingClientRect();
    return {
      navDisplay: getComputedStyle(nav).display,
      navMainOverlap: Math.max(0, navRect.bottom - mainRect.top),
      mainPlaybackOverlap: Math.max(0, mainRect.bottom - playbackRect.top),
      horizontalOverflow: Math.max(0, shell.scrollWidth - shell.clientWidth),
      shellRows: getComputedStyle(shell).gridTemplateRows,
    };
  });
  const failures = [];
  if (metrics.navDisplay === "none") failures.push("noscript navigation hidden");
  for (const key of ["navMainOverlap", "mainPlaybackOverlap", "horizontalOverflow"]) {
    if (metrics[key] > 1) failures.push(`${key}=${metrics[key]}`);
  }
  await context.close();
  return { label: "web-no-js-narrow", metrics, failures };
}

async function inspectProfileMenu(browser, server, html) {
  const route = "/embedded-profile-menu";
  server.pages.set(route, preparedHtml(html));
  const page = await browser.newPage({ viewport: { width: 1000, height: 720 } });
  await page.goto(`${server.baseUrl}${route}`, { waitUntil: "domcontentloaded" });
  await page.locator("[data-cabinet-rail-toggle]").click();
  await page.locator("[data-profile-menu-trigger]").click();
  await page.locator(".sidebar-profile-menu__disclosure > summary").first().click();
  await nextLayout(page);
  const metrics = await page.evaluate(() => {
    const sidebar = document.querySelector(".sidebar");
    const menu = document.querySelector("[data-profile-menu]");
    const trigger = document.querySelector("[data-profile-menu-trigger]");
    const account = menu?.querySelector(".sidebar-profile-menu__account");
    const submenu = menu?.querySelector("[data-profile-menu-submenu]");
    if (!sidebar || !menu || !trigger || !account || !submenu) throw new Error("profile menu surface missing");
    const sidebarRect = sidebar.getBoundingClientRect();
    const menuRect = menu.getBoundingClientRect();
    const triggerRect = trigger.getBoundingClientRect();
    const accountRect = account.getBoundingClientRect();
    const submenuRect = submenu.getBoundingClientRect();
    const mainProbe = document.elementFromPoint(
      Math.min(window.innerWidth - 2, sidebarRect.right + Math.min(4, (menuRect.right - sidebarRect.right) / 2)),
      accountRect.top + accountRect.height / 2,
    );
    const submenuProbe = document.elementFromPoint(
      submenuRect.left + Math.min(8, submenuRect.width / 2),
      submenuRect.top + Math.min(8, submenuRect.height / 2),
    );
    return {
      menuExtendsPastSidebar: menuRect.right - sidebarRect.right,
      menuTriggerGap: triggerRect.top - menuRect.bottom,
      menuTopLayer: menu.matches(":popover-open"),
      menuRightVisible: menu.contains(mainProbe),
      submenuVisible: submenu.contains(submenuProbe),
      submenuInsideViewport: submenuRect.left >= 8 && submenuRect.right <= window.innerWidth - 8,
      playbackCount: document.querySelectorAll(".playback-bar").length,
    };
  });
  const failures = [];
  if (metrics.menuExtendsPastSidebar <= 1) failures.push("menu does not exercise sidebar clipping boundary");
  if (metrics.menuTriggerGap < 8) failures.push(`menuTriggerGap=${metrics.menuTriggerGap}`);
  if (!metrics.menuTopLayer) failures.push("profile menu is not in the browser top layer");
  if (!metrics.menuRightVisible) failures.push("profile menu is clipped by sidebar");
  if (!metrics.submenuVisible) failures.push("profile submenu is clipped or covered");
  if (!metrics.submenuInsideViewport) failures.push("profile submenu leaves viewport");
  if (metrics.playbackCount !== 1) failures.push(`playbackCount=${metrics.playbackCount}`);
  if (process.env.GRAF_PLAYBACK_SCREENSHOTS === "1") {
    const output = path.join(root, "output/playwright");
    fs.mkdirSync(output, { recursive: true });
    await page.screenshot({
      path: path.join(output, `${process.env.GRAF_BROWSER || "chromium"}-embedded-profile-menu.png`),
      fullPage: false,
    });
  }
  await page.close();
  return { label: "embedded-profile-menu", metrics, failures };
}

(async () => {
  const pages = renderPages();
  const pageServer = { pages: new Map(), baseUrl: "" };
  const httpServer = http.createServer((request, response) => {
    const html = pageServer.pages.get(request.url);
    response.writeHead(html ? 200 : 404, { "Content-Type": "text/html; charset=utf-8" });
    response.end(html || "not found");
  });
  await new Promise((resolve) => httpServer.listen(0, "127.0.0.1", resolve));
  pageServer.baseUrl = `http://127.0.0.1:${httpServer.address().port}`;
  const browser = await browserType.launch({
    headless: true,
    ...(browserType === chromium && fs.existsSync(chromePath) ? { executablePath: chromePath } : {}),
  });
  const results = [
    ...(await inspect(browser, pageServer, "web-wide", pages.web, { width: 1440, height: 720 }, { toggle: true })),
    ...(await inspect(browser, pageServer, "web-narrow", pages.web, { width: 390, height: 720 })),
    ...(await inspect(browser, pageServer, "web-expanded-timeline", pages.web, { width: 1440, height: 720 }, { timelineHeight: 260 })),
    ...(await inspect(browser, pageServer, "web-preparing", pages.preparing, { width: 390, height: 720 })),
    ...(await inspect(browser, pageServer, "web-unavailable", pages.unavailable, { width: 390, height: 720 })),
    ...(await inspect(browser, pageServer, "embedded-wide", pages.embedded, { width: 1000, height: 720 }, { toggle: true })),
    ...(await inspect(browser, pageServer, "embedded-narrow", pages.embedded, { width: 800, height: 620 })),
    await inspectProfileMenu(browser, pageServer, pages.embedded),
    await inspectWithoutPlayback(browser, pageServer, pages.list),
    await inspectNoJsNarrow(browser, pageServer, pages.web),
  ];
  await browser.close();
  await new Promise((resolve, reject) => httpServer.close((error) => error ? reject(error) : resolve()));
  const failures = results.flatMap((result) => result.failures.map((failure) => `${result.label}: ${failure}`));
  console.log(JSON.stringify({ failures, results }, null, 2));
  process.exit(failures.length ? 1 : 0);
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
