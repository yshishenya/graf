// Isolated SDK test derivative: no change to the working checkout or production startup.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const [repoArgument, outputArgument, expectedAppMain, scenario = 'problem', settingsOrigin] = process.argv.slice(2);
assert(['problem', 'settings', 'startup-exit', 'shell-close', 'notification-context'].includes(scenario));
if (scenario === 'settings') assert(/^https:\/\/localhost:[1-9][0-9]{3,4}$/.test(settingsOrigin ?? '') &&
 Number(new URL(settingsOrigin).port) <= 65535, 'Settings requires a generated loopback HTTPS origin');
assert(repoArgument && outputArgument && /^[a-f0-9]{64}$/.test(expectedAppMain ?? ''),
 'Usage: node prepare-appmain-problem-ui.mjs <repo> <empty-test-directory> <expected-AppMain-SHA256>');
const repo = fs.realpathSync(repoArgument), output = fs.realpathSync(outputArgument);
assert(output !== repo && !output.startsWith(repo + path.sep) && fs.readdirSync(output).length === 0);
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const app = 'apps/windows/RecApp/AppMain.cpp', project = 'apps/windows/RecApp/GrafWindowsApp.vcxproj';
const prefix = 'apps/windows/Tests/GrafWindowsContractTests/';
const git = spawnSync('git', ['-C', repo, 'ls-files', '-z', '--cached', '--others', '--exclude-standard', '--', 'apps/windows'], {encoding:'utf8'});
assert.equal(git.status, 0); const files = [...new Set(git.stdout.split('\0').filter(Boolean))].sort();
const inputs = {}, outputs = {};
for (const name of files) {
 assert(name.startsWith('apps/windows/') && !name.split('/').includes('..'));
 assert(fs.lstatSync(path.join(repo, name)).isFile(), 'Only regular source inputs');
 const bytes = fs.readFileSync(path.join(repo, name)); inputs[name] = outputs[name] = sha(bytes);
 fs.mkdirSync(path.dirname(path.join(output, name)), {recursive:true}); fs.writeFileSync(path.join(output, name), bytes, {flag:'wx'});
}
assert.equal(inputs[app], expectedAppMain);
const original = fs.readFileSync(path.join(output, app), 'utf8');
const section = (text, start, end) => {
 assert.equal(text.split(start).length, 2); assert.equal(text.split(end).length, 2);
 const first = text.indexOf(start), last = text.indexOf(end, first + start.length); assert(last > first);
 return text.slice(first, last);
};
const launchStart = '    void OnLaunched(LaunchActivatedEventArgs const&) {';
const launch = section(original, launchStart, '\nprivate:');
const fixture = scenario === 'settings' ? 'AppMainSettingsUi' :
 scenario === 'notification-context' ? 'AppMainNotificationContextUi' : 'AppMainProblemUi';
let derived;
if (scenario === 'startup-exit' || scenario === 'shell-close') {
 const once = (text, from, to) => { assert.equal(text.split(from).length, 2); return text.replace(from, to); };
 const preamble = section(launch, '        try {\n            const auto directory = localAppData();',
     '        Resources().MergedDictionaries().Append(XamlControlsResources());');
 let isolated = once(launch, preamble, ''); // No real attribution storage or protocol activation.
 const setup = fs.readFileSync(path.join(output, prefix + (scenario === 'startup-exit' ? 'AppMainStartupExitUiLaunch.inc' : 'AppMainShellCloseUiLaunch.inc')), 'utf8');
 isolated = once(isolated, '        window_.Content(root_);', '        window_.Content(root_);\n' + setup);
 isolated = once(isolated, 'capture_ = std::make_unique<NativeCapture>(localCustodyRoot(), selectAec());',
     `capture_ = std::make_unique<NativeCapture>(${scenario === 'startup-exit' ? 'startupExit' : 'shellClose'}->root, graf::windows::AecSelection{std::make_shared<graf::windows::testing::ProblemUiAec>(), false});`);
 isolated = once(isolated, '            capture_->startStorageValidation();',
     (scenario === 'startup-exit' ? '            startupExit->hold = graf::windows::NativeCaptureStorageTestPeer::holdStartup(*capture_);\n' : '') + '            throw std::runtime_error("generated startup failure");');
 isolated = once(isolated, 'window_.AppWindow().Title(L"GRAF");', `window_.AppWindow().Title(L"GRAF — isolated ${scenario} check");`);
 // The production close handlers and polling timer, including their placement,
 // are the subject under test; do not substitute a copied implementation.
 assert.equal(section(isolated, '        window_.AppWindow().Closing(', '        window_.Activated([this](auto const&, auto const&) {'),
     section(launch, '        window_.AppWindow().Closing(', '        window_.Activated([this](auto const&, auto const&) {'));
 derived = original.replace(launch, isolated);
} else {
 const body = fs.readFileSync(path.join(output, prefix + fixture + 'Launch.inc'), 'utf8');
 derived = original.replace(launch, launchStart + '\n' + body + '\n    }\n');
}
const initializer = 'graf::windows::AutomaticRecordingPolicy automaticPolicy_{verifiedTargets_};';
assert.equal(derived.split(initializer).length, 2);
derived = derived.replace(initializer, 'graf::windows::AutomaticRecordingPolicy automaticPolicy_{verifiedTargets_, graf::windows::AutomaticRecordingPreferenceStore{}};');
const entryStart = 'int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {';
const entry = section(derived, entryStart, '\n#else\n');
derived = derived.replace(entry, `${entryStart}
    try {
        winrt::init_apartment(winrt::apartment_type::single_threaded);
        winrt::Microsoft::UI::Xaml::Application::Start([](auto&&) { winrt::make<GrafApp>(); });
        return graf::windows::testing::problemUiResult;
    } catch (...) {
        std::fputs("AppMainProblemUiTests setup failed\\n", stderr); std::fflush(stderr); return 2;
    }
}
`);
const methods = [
 ['configureCabinet', '    void configureCabinet()', '    void updateLocalRecordings()'],
 ['answerNativeSettings', '    std::string answerNativeSettings(', '    const graf::windows::VerifiedTargetIdentity* verifiedTarget('],
 ['bindNotificationContext', '    void bindNotificationContext()', '    void setLocalNotificationStatus('],
 ['interactionPermit', '    [[nodiscard]] graf::windows::InteractionPermit interactionPermit()', '    void invalidateNotificationInteraction()'],
 ['problemContextCurrent', '    [[nodiscard]] bool problemContextCurrent(', '    [[nodiscard]] bool problemActionCurrent('],
 ['problemActionCurrent', '    [[nodiscard]] bool problemActionCurrent(', '    void openProblemRecording('],
 ['openProblemRecording', '    void openProblemRecording(', '    void reconcileRecordingProblems()'],
 ['confirmLocalAction', '    void confirmLocalAction(', '    void showCabinetFallback('],
 ['pollLocalRecordingRemoval', '    void pollLocalRecordingRemoval()', '    // The shell retains only the charged reply address.'],
 ['reconcileRecordingProblems', '    void reconcileRecordingProblems()', '    void refreshSelectedRecording()'],
 ['refreshSelectedRecording', '    void refreshSelectedRecording()', '    bool calendarAuthCurrent(']
];
if (scenario === 'startup-exit' || scenario === 'shell-close') methods.push(
 ['exitPolicy', '    [[nodiscard]] bool shellExitJobsDrained()', '    bool recordingIndicatorAvailable()'],
 ['refreshNativeState', '    void refreshNativeState()', '    static void updateMeter('],
 ['showStartupError', '    void showStartupError(', '    static double reminderWallTime()']);
if (scenario === 'shell-close') methods.push(
 ['openMainWindow', '    void openMainWindow()', '    void openAccountSettings()'],
 ['refreshTrayAvailability', '    void refreshTrayAvailability()', '    void buildShell()'],
 ['recordingIndicator', '    bool recordingIndicatorAvailable()', '    void pauseResumeCapture()']);
const bindings = {};
for (const [name, start, end] of methods) {
 const before = section(original, start, end), after = section(derived, start, end);
 assert.equal(after, before); bindings[name] = sha(before);
}
const header = fs.readFileSync(path.join(output, prefix + fixture + 'Fixture.h'), 'utf8');
assert(!/^\s*#define\b/m.test(header), 'No production macro replacements');
const projectText = fs.readFileSync(path.join(output, project), 'utf8');
const item = '<ClCompile Include="AppMain.cpp" />'; assert.equal(projectText.split(item).length, 2);
const derivativeProject = projectText.replace(item, `<ClCompile Include="AppMain.cpp"><ForcedIncludeFiles>$(MSBuildProjectDirectory)\\..\\Tests\\GrafWindowsContractTests\\${fixture}Fixture.h;%(ForcedIncludeFiles)</ForcedIncludeFiles></ClCompile>`);
fs.writeFileSync(path.join(output, app), derived); fs.writeFileSync(path.join(output, project), derivativeProject);
outputs[app] = sha(derived); outputs[project] = sha(derivativeProject);
if (scenario === 'settings') {
 const cabinet = 'apps/windows/RecApp/Shell/CabinetWindow.h';
 const text = fs.readFileSync(path.join(output, cabinet), 'utf8');
 const constructor = 'CabinetWindow() = default;'; assert.equal(text.split(constructor).length, 2);
 const modified = text.replace(constructor, `CabinetWindow() : webView_(WebViewRoutePolicy("${settingsOrigin}")) {}`);
 fs.writeFileSync(path.join(output, cabinet), modified); outputs[cabinet] = sha(modified);
 const home = 'apps/windows/RecApp/Shell/CabinetWindow.cpp';
 const homeText = fs.readFileSync(path.join(output, home), 'utf8');
 const productionHome = 'open("https://rec.2brain.pro/desktop/meetings")';
 assert.equal(homeText.split(productionHome).length, 2);
 const testHome = homeText.replace(productionHome, `open("${settingsOrigin}/desktop/meetings")`);
 fs.writeFileSync(path.join(output, home), testHome); outputs[home] = sha(testHome);
}
for (const [name, data] of Object.entries({'source.json':inputs, 'test-source.json':outputs,
 'appmain-test-bindings.json':{scenario, settings_origin:settingsOrigin, production:expectedAppMain, derivative:outputs[app], replacements:[['startup-exit','shell-close'].includes(scenario) ? 'OnLaunched isolated preamble/observer/capture/startup fault/title; original close handlers and timer retained' : 'OnLaunched','automaticPolicy_','wWinMain', ...(scenario === 'settings' ? ['CabinetWindow default constructor (test origin only)', 'CabinetWindow home URL (test origin only)'] : [])],
     forced_include_compile_item:'AppMain.cpp', unchanged_methods:bindings, installed_acceptance:false}}))
 fs.writeFileSync(path.join(output, name), JSON.stringify(data, null, 2)+'\n', {flag:'wx'});
console.log(JSON.stringify({inputs:files.length, original:expectedAppMain, derivative:outputs[app], method_count:methods.length}));
