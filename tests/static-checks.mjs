// Read-only checks using existing Node.js. No Python emulation or execution.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = p => fs.readFileSync(path.join(root, p), 'utf8');
const json = p => JSON.parse(read(p));
let passed = 0;
const check = (name, fn) => { fn(); console.log('PASS ' + name); passed++; };
const config = read('src/moonshine_stt_wyoming/config.py');
const docker = read('Dockerfile');
const lock = read('requirements.lock') + '\n' + read('requirements-build.lock');
const deps = json('config/dependency-manifest.json');
const manifest = json('src/moonshine_stt_wyoming/model-manifest.json');
const pyproject = read('pyproject.toml');
const walk = dir => fs.readdirSync(dir, {withFileTypes:true}).flatMap(e => {
  // Validate maintained project sources; isolated runtimes, caches and models
  // are intentionally downloaded in Phase 3 and are not source artifacts.
  if (['.validation', '.venv', '.test-tmp', '__pycache__', 'models', 'recordings', '.git'].includes(e.name)) return [];
  const p = path.join(dir,e.name); return e.isDirectory() ? walk(p) : [p];
});
const files = walk(root);
check('project identity, package, entrypoints and absence of legacy references', () => {
  const project = 'moonshine-stt-wyoming';
  const pkg = 'moonshine_stt_wyoming';
  assert.equal(path.basename(root), project);
  assert.ok(pyproject.includes('name = "' + project + '"'));
  assert.ok(pyproject.includes(project + ' = "' + pkg + '.__main__:main"'));
  assert.ok(pyproject.includes(project + '-models = "' + pkg + '.model_download:main"'));
  assert.ok(fs.statSync(path.join(root, 'src', pkg)).isDirectory());
  assert.ok(docker.includes('"' + pkg + '"'));
  assert.ok(read('src/' + pkg + '/protocol.py').includes('"name": "' + project + '"'));
  for (const file of files) for (const separator of ['-', '_']) {
    const legacy = ['moonshine', 'wyoming'].join(separator);
    assert.ok(!path.relative(root, file).includes(legacy), file);
    assert.ok(!fs.readFileSync(file, 'utf8').includes(legacy), file);
  }
});
check('new project name with explicit historical/protected exceptions only', () => {
  const legacyProject = ['moonshine','stt','german','wyoming'].join('-');
  const legacyPackage = ['moonshine','stt','german','wyoming'].join('_');
  const historical = new Set(['docs/phase4-validation.md','docs/phase5-validation.md',
    'docs/phase6-validation.md','docs/phase7-validation.md',
    'docs/phase7-5-multilanguage-validation.md','docs/phase8-release-preparation.md','config/phase5-compose.yaml']);
  for(const file of files) {
    const relative = path.relative(root,file);
    assert.ok(!relative.includes(legacyProject) && !relative.includes(legacyPackage), relative);
    const text = fs.readFileSync(file,'utf8');
    assert.ok(!text.includes(legacyPackage), relative);
    if(!historical.has(relative)) assert.ok(!text.includes(legacyProject), relative);
  }
});
check('model-language relation validated at config and startup, Wyoming uses catalog', () => {
  assert.ok(config.includes('validate_selection(model, language)'));
  assert.ok(read('src/moonshine_stt_wyoming/stt_service.py').includes('validate_selection(self.config.model, self.config.language)'));
  assert.ok(read('src/moonshine_stt_wyoming/protocol.py').includes('model_spec(self.service.config.model)["language"]'));
});
check('port 10300 in configuration, defaults, Docker and tests', () => {
  assert.match(config, /port: int = 10300/);
  assert.match(config, /"WYOMING_PORT", 10300/);
  assert.match(read('config/defaults.env'), /WYOMING_PORT=10300/);
  assert.match(docker, /WYOMING_PORT=10300/);
  assert.ok(docker.includes('EXPOSE 10300/tcp'));
  assert.match(read('tests/test_config.py'), /config.port, 10300/);
});
check('no alternate default port anywhere', () => {
  for (const f of files) if (!f.endsWith('static-checks.mjs')) assert.ok(!fs.readFileSync(f,'utf8').includes('10301'), path.relative(root,f));
});
check('CPU/Small/startup-download/privacy/admission defaults', () => {
  for (const item of ['STT_DEVICE=cpu','MOONSHINE_MODEL=small-streaming-de','MOONSHINE_MODEL_DIR=/app/models','MOONSHINE_AUTO_DOWNLOAD=1','MOONSHINE_THREADS=1','LOG_TRANSCRIPTS=false','WYOMING_STT_CONCURRENT_REQUESTS=1','MAX_AUDIO_SECONDS=30']) assert.ok(docker.includes(item));
});
check('base image pinned to verified amd64 digest', () => {
  assert.ok(docker.includes(deps.base_image));
  assert.ok(docker.includes('FROM --platform=linux/amd64')); assert.match(deps.base_image, /@sha256:[a-f0-9]{64}$/);
  assert.equal(read('.python-version').trim(), deps.python);
});
check('runtime image excludes build tools and optional audio-device libraries', () => {
  assert.ok(docker.includes(' AS build'));
  assert.ok(docker.includes('COPY --from=build /opt/runtime /opt/runtime'));
  assert.ok(!docker.includes('apt-get') && !docker.includes('libportaudio2'));
});
check('hash-enforced binary-only dependency install', () => {
  assert.ok(docker.includes('--only-binary=:all: --require-hashes'));
  for (const [name, pkg] of Object.entries(deps.packages)) {
    assert.ok(lock.includes(name + '==' + pkg.version));
    assert.ok(pkg.artifacts.length);
    for (const artifact of pkg.artifacts) {
      assert.match(artifact.sha256, /^[a-f0-9]{64}$/);
      assert.ok(lock.includes('--hash=sha256:' + artifact.sha256));
    }
  }
  assert.equal((lock.match(/^[a-z][a-z0-9-]*==/gm)||[]).length,Object.keys(deps.packages).length);
});
check('primary pins match project metadata', () => {
  for (const name of ['moonshine-voice','wyoming','setuptools','wheel']) assert.ok(pyproject.includes(name+'=='+deps.packages[name].version));
});
check('Linux dependency closure in official metadata', () => {
  for (const pkg of Object.values(deps.packages)) for (const req of pkg.requires_dist || []) {
    const [spec, marker=''] = req.split(';');
    if (marker.includes('extra ==') || marker.includes('platform_system == "Windows"')) continue;
    const name = spec.trim().match(/^[A-Za-z0-9_-]+/)[0].toLowerCase().replaceAll('_','-');
    assert.ok(deps.packages[name], 'missing '+name);
  }
});
check('single canonical model manifest', () => assert.equal(json('config/model-manifest.json').canonical_manifest,'../src/moonshine_stt_wyoming/model-manifest.json'));
check('Small is the explicit standard in code, manifest and env reference', () => {
  assert.match(config, /model: str = "small-streaming-de"/);
  assert.equal(manifest.default_model, 'small-streaming-de');
  assert.ok(read('config/defaults.env').includes('MOONSHINE_MODEL=small-streaming-de'));
});
check('runtime and build dependency groups are separate', () => {
  for (const name of deps.groups.runtime) assert.ok(read('requirements.lock').includes(name+'=='));
  for (const name of deps.groups.build) {
    assert.ok(read('requirements-build.lock').includes(name+'=='));
    assert.ok(!read('requirements.lock').includes(name+'=='));
  }
});
check('manual metadata is optional and only missing models are provisioned', () => {
  assert.ok(read('src/moonshine_stt_wyoming/models.py').includes('hashes = None'));
  const manager=read('src/moonshine_stt_wyoming/model_manager.py');
  assert.ok(manager.includes('error.code != "model-missing"'));
  assert.ok(manager.includes('if not config.auto_download:'));
});
check('large local artifacts are excluded from Git and build context', () => {
  for (const pattern of ['.venv', '.validation', '.test-tmp', 'models', '*.ort', '*.wav', '*.log']) {
    assert.ok(read('.gitignore').includes(pattern));
    assert.ok(read('.dockerignore').includes(pattern));
  }
  for (const pattern of ['docs','tests','config']) assert.ok(read('.dockerignore').includes(pattern));
});
check('exact German Tiny and Small IDs/architectures/revisions', () => {
  assert.equal(Object.keys(manifest.models).length,13);
  assert.equal(new Set(Object.values(manifest.models).map(s=>s.language)).size,8);
  for (const [name, spec] of Object.entries(manifest.models)) {
    if(spec.language==='de') assert.equal(spec.revision,'quantized_26_08_24');
    assert.ok(name.endsWith('-'+spec.language));
    assert.equal(spec.architecture,name.startsWith('tiny')?'TINY_STREAMING':name.startsWith('small')?'SMALL_STREAMING':'MEDIUM_STREAMING');
    assert.ok(spec.base_url.startsWith('https://download.moonshine.ai/model/'+name+'/'));
    assert.equal(Object.keys(spec.files).length,8);
    for (const [file,meta] of Object.entries(spec.files)) {
      assert.ok(!file.includes('/') && !file.includes('..'));
      assert.ok(Number.isInteger(meta.size) && meta.size>0);
      assert.equal(Buffer.from(meta.crc32c,'base64').length,4);
    }
  }
});
check('unit tests cover required domains', () => {
  for (const p of ['test_config.py','test_audio.py','test_models.py','test_protocol.py','test_backend.py','test_transport.py','test_server.py']) assert.ok(read('tests/'+p).includes('unittest'));
});
check('unit-test runner uses stdlib AST and disables bytecode', () => {
  assert.match(read('tests/run.py'), /ast.parse/); assert.match(read('tests/run.py'), /dont_write_bytecode = True/);
  assert.ok(read('tests/support.py').includes('PROJECT / ".test-tmp"'));
});
check('no microphone source or automatic model helpers in server', () => {
  for (const p of files.filter(p=>p.endsWith('.py') && p.includes('/src/'))) {
    if (p.endsWith('model_download.py')) continue;
    const text=fs.readFileSync(p,'utf8');
    for(const forbidden of ['MicTranscriber','get_model_for_language','sounddevice.InputStream','sounddevice.rec','urlopen(','requests.get(']) assert.ok(!text.includes(forbidden), path.relative(root,p));
  }
});
check('official runtime uses local Transcriber, CPU and native logs off', () => {
  const s=read('src/moonshine_stt_wyoming/backends/moonshine_cpu.py');
  assert.match(s,/from moonshine_voice import Transcriber/);
  assert.ok(s.includes('model_path=str(directory)'));
  assert.match(s,/"ort_providers": "CPU"/);
  assert.match(s,/"log_output_text": "false"/);
});
check('blocking native calls dispatched and cancellation drained', () => {
  const s=read('src/moonshine_stt_wyoming/stt_service.py');
  assert.ok(s.includes('ThreadPoolExecutor(max_workers=1'));
  assert.match(s,/run_in_executor/); assert.ok(s.includes('asyncio.shield(future)'));
  assert.ok(s.includes('while not future.done()'));
});
check('bounded protocol framing and audio budget present', () => {
  assert.match(read('src/moonshine_stt_wyoming/transport.py'), /MAX_JSON_BYTES = 8192/);
  assert.match(read('src/moonshine_stt_wyoming/audio.py'), /MAX_CHUNK_BYTES = 65536/);
  assert.ok(read('src/moonshine_stt_wyoming/audio.py').includes('self.total_bytes + len(data) > self.max_bytes'));
});
check('healthcheck requires initialized backend and loaded/available model', () => {
  const s=read('src/moonshine_stt_wyoming/healthcheck.py');
  for(const k of ['backend_initialized','model_loaded','model_available']) assert.ok(s.includes(k));
  assert.ok(s.includes('config.model')); assert.ok(docker.includes('moonshine_stt_wyoming.healthcheck'));
});
check('non-root container; no host GPU/device assumptions', () => {
  assert.match(docker,/USER 65532:65532/);
  assert.ok(!docker.includes('privileged') && !docker.includes('/dev/dri') && !docker.includes('nvidia'));
});
check('required documentation exists', () => {
  for(const p of ['README.md','docs/architecture.md','docs/benchmark-plan.md','docs/versions.md']) assert.ok(read(p).length>100);
});
check('no model binaries in maintained project sources', () => {
  for(const f of files) assert.ok(!/\.(onnx|ort|bin|whl|tar|gz)$/.test(f));
});
check('upstream demo assets pruned before runtime copy and rootfs audited', () => {
  assert.ok(docker.includes('python /app/build-support/prune_runtime.py'));
  const audit = read('tests/inspect_phase4_rootfs.py');
  assert.ok(audit.includes('assert not report["audio_assets"]'));
  assert.ok(audit.includes('assert not report["model_artifacts"]'));
});
check('local Unraid draft is excluded from build context and has safe STT defaults', () => {
  const template = read('templates/moonshine-stt-wyoming.xml');
  assert.ok(read('.dockerignore').split('\n').includes('templates'));
  for (const item of ['--user=99:100','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges']) assert.ok(template.includes(item));
  assert.ok(template.includes('<Privileged>false</Privileged>'));
  assert.ok(template.includes('<Repository>ghcr.io/marco-taylor/moonshine-stt-wyoming:latest</Repository>'));
  assert.ok(template.includes('Default="small-streaming-de|'));
  for(const model of Object.keys(manifest.models)) assert.ok(template.includes(model));
  assert.ok(template.includes('Target="MOONSHINE_THREADS" Default="1|4"'));
  assert.ok(!template.includes('Type="Device"'));
});
check('normal Unraid installation and manual/offline guidance exist', () => {
  const guide = read('docs/unraid-installation.md');
  for (const item of ['small-streaming-de','tiny-streaming-de','MOONSHINE_AUTO_DOWNLOAD=0','99:100','10300','quantized_26_08_24']) assert.ok(guide.includes(item));
});
console.log(passed + ' static checks passed. Python and native runtime execution are verified separately.');
