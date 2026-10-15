// Isolated SDK test derivative: no change to the working checkout or production startup.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const [repoArgument, outputArgument, expectedAppMain] = process.argv.slice(2);
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
const body = fs.readFileSync(path.join(output, prefix + 'AppMainProblemUiLaunch.inc'), 'utf8');
let derived = original.replace(launch, launchStart + '\n' + body + '\n    }\n');
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
 ['interactionPermit', '    [[nodiscard]] graf::windows::InteractionPermit interactionPermit()', '    void invalidateNotificationInteraction()'],
 ['problemContextCurrent', '    [[nodiscard]] bool problemContextCurrent(', '    [[nodiscard]] bool problemActionCurrent('],
 ['problemActionCurrent', '    [[nodiscard]] bool problemActionCurrent(', '    void openProblemRecording('],
 ['openProblemRecording', '    void openProblemRecording(', '    void reconcileRecordingProblems()'],
 ['confirmLocalAction', '    void confirmLocalAction(', '    void showCabinetFallback('],
 ['pollLocalRecordingRemoval', '    void pollLocalRecordingRemoval()', '    // The shell retains only the charged reply address.'],
 ['reconcileRecordingProblems', '    void reconcileRecordingProblems()', '    void refreshSelectedRecording()'],
 ['refreshSelectedRecording', '    void refreshSelectedRecording()', '    bool calendarAuthCurrent(']
];
const bindings = {};
for (const [name, start, end] of methods) {
 const before = section(original, start, end), after = section(derived, start, end);
 assert.equal(after, before); bindings[name] = sha(before);
}
const header = fs.readFileSync(path.join(output, prefix + 'AppMainProblemUiFixture.h'), 'utf8');
assert(!/^\s*#define\b/m.test(header), 'No production macro replacements');
const projectText = fs.readFileSync(path.join(output, project), 'utf8');
const item = '<ClCompile Include="AppMain.cpp" />'; assert.equal(projectText.split(item).length, 2);
const derivativeProject = projectText.replace(item, '<ClCompile Include="AppMain.cpp"><ForcedIncludeFiles>$(MSBuildProjectDirectory)\\..\\Tests\\GrafWindowsContractTests\\AppMainProblemUiFixture.h;%(ForcedIncludeFiles)</ForcedIncludeFiles></ClCompile>');
fs.writeFileSync(path.join(output, app), derived); fs.writeFileSync(path.join(output, project), derivativeProject);
outputs[app] = sha(derived); outputs[project] = sha(derivativeProject);
for (const [name, data] of Object.entries({'source.json':inputs, 'test-source.json':outputs,
 'appmain-test-bindings.json':{production:expectedAppMain, derivative:outputs[app], replacements:['OnLaunched','automaticPolicy_','wWinMain'],
     forced_include_compile_item:'AppMain.cpp', unchanged_methods:bindings, installed_acceptance:false}}))
 fs.writeFileSync(path.join(output, name), JSON.stringify(data, null, 2)+'\n', {flag:'wx'});
console.log(JSON.stringify({inputs:files.length, original:expectedAppMain, derivative:outputs[app], method_count:methods.length}));
