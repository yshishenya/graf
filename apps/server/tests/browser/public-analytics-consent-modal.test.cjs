/*
 * FR-004: refusal is as easy as consent.
 *
 * The synthetic harness proves what the controller decides, but it cannot show
 * what the visitor actually gets: the modal is built by the vendored consent
 * library from the options the controller passes to it. This scenario therefore
 * renders the real library with the real assembled options in a real browser and
 * checks the visitor's decision surface:
 *
 *  * exactly two decision buttons, in one group, of the same kind;
 *  * both reachable and activatable by the keyboard alone;
 *  * one activation is enough for either decision, and the refusal takes no
 *    additional step through the settings;
 *  * the refusal decision travels the same path as the consent decision.
 *
 * The library hides itself from automated browsers, so the harness disables that
 * single guard before handing the real options over. Nothing else about the
 * options is changed.
 *
 * Run: node public-analytics-consent-modal.test.cjs
 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const SERVER_ROOT = path.resolve(__dirname, "../..");
const STATIC_ROOT = path.join(SERVER_ROOT, "src/twobrain_rec_server/public/static/public");
const LIBRARY = path.join(STATIC_ROOT, "cookieconsent.umd.js");
const CONTROLLER = path.join(STATIC_ROOT, "analytics.js");
const CONSENT_STORAGE_KEY = "graf_public_cookie_consent";

const { chromium } = require(require.resolve("playwright", {
  paths: [process.env.GRAF_NODE_MODULES || path.join(__dirname, "node_modules")],
}));

function readConfig(pagePath) {
  const printed = execFileSync(
    path.join(SERVER_ROOT, ".venv/bin/python"),
    ["-m", "tests.fixtures.public_analytics_config", pagePath],
    { cwd: SERVER_ROOT, encoding: "utf8" },
  );
  return JSON.parse(printed);
}

function serveStatic() {
  const server = http.createServer((request, response) => {
    if (request.url === "/" || request.url.startsWith("/?")) {
      response.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
      response.end('<!doctype html><html lang="ru"><head></head><body></body></html>');
      return;
    }
    const file = path.join(STATIC_ROOT, path.basename(request.url.split("?")[0]));
    if (fs.existsSync(file)) {
      response.writeHead(200, {
        "Content-Type": request.url.endsWith(".css")
          ? "text/css; charset=utf-8"
          : "application/javascript; charset=utf-8",
      });
      response.end(fs.readFileSync(file));
      return;
    }
    response.writeHead(404);
    response.end("not found");
  });
  return server;
}

// A fresh page per decision: the library stores its decision, so a shared page
// would answer the second question with the first answer.
async function openDecisionPage(browser, origin, config) {
  const page = await browser.newPage();
  await page.goto(`${origin}/`);
  await page.evaluate((pageConfig) => {
    const holder = document.createElement("script");
    holder.type = "application/json";
    holder.id = "graf-public-analytics-config";
    holder.textContent = JSON.stringify(pageConfig);
    document.head.appendChild(holder);
  }, config);
  await page.addScriptTag({ path: LIBRARY });
  // The library refuses to show anything to an automated browser. Only that
  // guard is lifted; the options below are the ones the controller assembled.
  await page.addScriptTag({
    content:
      "window.__grafRealConsent = window.CookieConsent;" +
      "window.CookieConsent = Object.assign({}, window.CookieConsent, {" +
      "  run: function (options) {" +
      "    return window.__grafRealConsent.run(Object.assign({}, options, {hideFromBots: false}));" +
      "  }," +
      "});",
  });
  await page.addScriptTag({ path: CONTROLLER });
  await page.waitForSelector(".cm__btns", { timeout: 5000 });
  return page;
}

async function decisionButtons(page) {
  return page.evaluate(() => {
    const buttons = Array.from(document.querySelectorAll(".cm__btns button"));
    return buttons.map((button) => ({
      ariaHidden: button.getAttribute("aria-hidden"),
      className: button.className,
      disabled: button.disabled,
      groupIndex: Array.from(document.querySelectorAll(".cm__btn-group")).indexOf(
        button.parentElement,
      ),
      role: button.dataset.role,
      tabIndex: button.tabIndex,
      tagName: button.tagName,
      text: button.textContent.trim(),
      type: button.getAttribute("type"),
    }));
  });
}

// The library hides the modal by dropping a class from the document element; the
// wrapper stays in the document, so the visible state is what has to be checked.
function waitForDecision(page) {
  return page.waitForFunction(
    () => !document.documentElement.classList.contains("show--consent"),
    undefined,
    { timeout: 5000 },
  );
}

async function storedConsent(page) {
  return page.evaluate((key) => {
    const raw = window.localStorage.getItem(key);
    return raw === null ? null : JSON.parse(raw);
  }, CONSENT_STORAGE_KEY);
}

async function main() {
  assert.ok(fs.existsSync(LIBRARY), "the vendored consent library must be present");
  const server = serveStatic();
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({ headless: true });

  try {
    const config = readConfig("/download");

    // 1. The visitor's decision surface: two decisions, one kind of action.
    const page = await openDecisionPage(browser, origin, config);
    const buttons = await decisionButtons(page);
    const decisions = buttons.filter(
      (button) => button.role === "all" || button.role === "necessary",
    );
    const secondary = buttons.filter(
      (button) => button.role !== "all" && button.role !== "necessary",
    );

    assert.equal(decisions.length, 2, "the modal offers exactly two decisions");
    assert.deepEqual(
      decisions.map((button) => button.role),
      ["all", "necessary"],
      "acceptance and refusal are the two decisions",
    );
    assert.deepEqual(
      decisions.map((button) => button.text),
      ["Разрешить все", "Только необходимые"],
    );
    for (const button of decisions) {
      assert.equal(button.tagName, "BUTTON", "a decision must be a native button");
      assert.equal(button.type, "button", "a decision must not submit a form");
      assert.equal(button.disabled, false);
      assert.equal(button.tabIndex, 0, "a decision must stay in the tab order");
      assert.equal(button.ariaHidden, null, "a decision must not be hidden from readers");
      assert.equal(button.groupIndex, 0, "both decisions share one group");
      assert.ok(
        !button.className.includes("--secondary"),
        "neither decision may be styled as the secondary action",
      );
    }
    // The settings entry is a separate, clearly secondary action rather than a
    // third way to decide.
    assert.equal(secondary.length, 1);
    assert.equal(secondary[0].role, "show");
    assert.ok(secondary[0].className.includes("--secondary"));
    assert.notEqual(secondary[0].groupIndex, 0);

    // 2. Refusal by keyboard alone, in one activation.
    const refusal = page.locator('.cm__btns button[data-role="necessary"]');
    await refusal.focus();
    assert.equal(
      await page.evaluate(() => document.activeElement.dataset.role),
      "necessary",
      "the refusal button must take focus",
    );
    await page.keyboard.press("Enter");
    await waitForDecision(page);
    const refused = await storedConsent(page);
    assert.ok(refused, "the refusal is stored");
    assert.deepEqual(refused.categories, ["necessary"], "only necessary stays allowed");
    assert.equal(
      refused.data.graf_consent_state,
      "necessary_only",
      "the refusal is recorded by the controller",
    );
    assert.equal(
      await page.evaluate(() => window.GRAFPublicAnalytics.currentConsentState),
      "necessary_only",
      "the controller reads the refusal from the same decision path",
    );
    console.log("ok refusal_needs_one_keyboard_activation");
    await page.close();

    // 3. Acceptance by keyboard alone, through the same single activation.
    const acceptPage = await openDecisionPage(browser, origin, config);
    const acceptance = acceptPage.locator('.cm__btns button[data-role="all"]');
    await acceptance.focus();
    await acceptPage.keyboard.press("Space");
    await waitForDecision(acceptPage);
    const accepted = await storedConsent(acceptPage);
    assert.ok(accepted, "the acceptance is stored");
    assert.equal(accepted.data.graf_consent_state, "accepted_all");
    assert.equal(
      await acceptPage.evaluate(() => window.GRAFPublicAnalytics.currentConsentState),
      "accepted_all",
    );
    // The two decisions differ only in the answer: same storage, same shape,
    // same handler. A refusal is not a longer journey than an acceptance.
    assert.deepEqual(
      Object.keys(accepted).sort(),
      Object.keys(refused).sort(),
      "both decisions write the same record shape",
    );
    console.log("ok consent_and_refusal_use_the_same_single_step_path");
    await acceptPage.close();

    // 4. The refusal button is the same action on the credential pages, which
    // FR-027 measures.
    const signupPage = await openDecisionPage(browser, origin, readConfig("/sign-up"));
    const signupDecisions = (await decisionButtons(signupPage)).filter(
      (button) => button.role === "all" || button.role === "necessary",
    );
    assert.deepEqual(
      signupDecisions.map((button) => button.text),
      ["Разрешить все", "Только необходимые"],
    );
    assert.equal(signupPage.url().endsWith("/"), true);
    console.log("ok refusal_is_the_same_action_on_the_signup_page");
    await signupPage.close();

    console.log("public_analytics_consent_modal_harness=pass");
  } finally {
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
  }
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
});
