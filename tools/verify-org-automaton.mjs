#!/usr/bin/env node
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const agentModule = path.join(root, 'agent-module');
const featurePack = path.join(root, 'feature-packs', 'automaton-routing');
const FEATURE_ID = 'org.cqr.automaton-routing';

// Base agent-module must NOT ship Automaton runtime payloads.
for (const rel of [
  'automaton-tools.manifest.json',
  'openclaw-workflow-map.json',
  'deploy-overrides.json',
  'adapter-connection.template.json',
  'adapter-connection.json',
  'AUTOMATON.md',
]) {
  assert.equal(
    existsSync(path.join(agentModule, rel)),
    false,
    `base agent-module must not contain ${rel}`,
  );
}

assert.equal(
  existsSync(path.join(agentModule, 'optional-feature-slash-index.json')),
  true,
  'optional-feature-slash-index.json required in base module',
);

for (const rel of [
  'feature.json',
  'automaton-tools.manifest.json',
  'openclaw-workflow-map.json',
  'deploy-overrides.json',
  'adapter-connection.template.json',
  'AUTOMATON.md',
]) {
  assert.equal(existsSync(path.join(featurePack, rel)), true, `missing feature-packs/automaton-routing/${rel}`);
}

const featureJson = JSON.parse(readFileSync(path.join(featurePack, 'feature.json'), 'utf8'));
assert.equal(featureJson.schema, 'my-agent-organization-feature/v1');
assert.equal(featureJson.id, FEATURE_ID);
assert.ok(featureJson.capabilities?.includes('automaton-routing'));
assert.equal(featureJson.entrypoints?.automaton_tools_manifest, 'automaton-tools.manifest.json');
assert.equal(featureJson.entrypoints?.openclaw_workflow_map, 'openclaw-workflow-map.json');
assert.equal(featureJson.entrypoints?.adapter_connection, 'adapter-connection.json');

const deployOverrides = JSON.parse(
  readFileSync(path.join(featurePack, 'deploy-overrides.json'), 'utf8'),
);
assert.equal(String(deployOverrides.openclaw_adapter_base_url ?? '').trim(), '');
assert.equal(Boolean(deployOverrides.activation_server_url?.trim()), false);
assert.equal(deployOverrides.openclaw_fallback_local, false);
assert.doesNotMatch(
  JSON.stringify(deployOverrides),
  /127\.0\.0\.1|192\.168\.|10\.\d+\.|172\.(1[6-9]|2\d|3[0-1])\./,
  'Feature Pack must not hardcode Adapter host in source',
);

const automatonManifest = JSON.parse(
  readFileSync(path.join(featurePack, 'automaton-tools.manifest.json'), 'utf8'),
);
const connectionTemplate = JSON.parse(
  readFileSync(path.join(featurePack, 'adapter-connection.template.json'), 'utf8'),
);
assert.equal(connectionTemplate.authentication?.mode, 'install_bootstrap');
assert.match(connectionTemplate.transport?.status_path_template ?? '', /\{job_id\}/);
assert.deepEqual(
  connectionTemplate.progress?.states,
  ['queued', 'running', 'completed', 'failed'],
);
assert.equal(connectionTemplate.progress?.edit_existing_message_when_supported, true);
assert.equal(connectionTemplate.progress?.append_status_when_edit_unsupported, true);
assert.doesNotMatch(
  JSON.stringify(connectionTemplate),
  /Bearer\s+[A-Za-z0-9._~-]{12,}/i,
  'template must not contain a static bearer token',
);
const workflowMap = JSON.parse(
  readFileSync(path.join(featurePack, 'openclaw-workflow-map.json'), 'utf8'),
);
const tools = automatonManifest.tools ?? [];
const workflows = workflowMap.workflows ?? {};
const requiredPrefixes = [
  '/반품율분석',
  '/카이제곱',
  '/미국샘플재고',
  '/CTR',
  '/발주검토자료',
  '/라이브계절지수',
  '/발주서등록',
  '/발주정보용판매',
  '/박스바코드생성',
  '/모델가계도',
  '/childasin',
];
assert.equal(
  existsSync(path.join(agentModule, 'pipelines', 'market_research.py')),
  true,
  'market_research pipeline entry missing',
);
const marketResearchEntry = readFileSync(
  path.join(agentModule, 'pipelines', 'market_research.py'),
  'utf8',
);
assert.match(
  marketResearchEntry,
  /def cmd_research\(/,
  'market_research pipeline must implement the research phase',
);
assert.match(
  marketResearchEntry,
  /cqr_product_pipeline\.cli\.run_research/,
  'market_research pipeline must dispatch to the deep-research CLI',
);
assert.doesNotMatch(
  marketResearchEntry,
  /entry-only|Runtime execution is not enabled in this pack version/,
  'market_research pipeline must not ship the registration-only stub',
);
assert.equal(
  existsSync(path.join(agentModule, 'market_research', 'CQR_MARKET_INJECT.md')),
  true,
  'CQR_MARKET_INJECT.md missing',
);
const inject = readFileSync(
  path.join(agentModule, 'market_research', 'CQR_MARKET_INJECT.md'),
  'utf8',
);
assert.match(inject, /\/심층리서치/);
assert.doesNotMatch(
  inject,
  /운영자 PC에서 위 명령을 직접 실행/,
  'inject must not dead-end deployed clients on manual run.ps1',
);
for (const prefix of requiredPrefixes) {
  assert.ok(
    tools.some((tool) => (tool.slash_prefixes ?? []).includes(prefix)),
    `automaton-tools.manifest.json must route ${prefix}`,
  );
}
const toolIds = new Set(tools.map((tool) => tool.id));
const workflowIds = Object.keys(workflows);
assert.deepEqual([...toolIds].sort(), [...workflowIds].sort(), 'slash tools and OpenClaw workflows must match');
for (const tool of tools) {
  assert.ok((tool.slash_prefixes ?? []).length > 0, `${tool.id} needs slash_prefixes`);
  assert.equal(tool.status_contract, 'adapter-job-v1', `${tool.id} needs adapter-job-v1 status_contract`);
}

const slashIndex = JSON.parse(
  readFileSync(path.join(agentModule, 'optional-feature-slash-index.json'), 'utf8'),
);
const indexPrefixes = new Set((slashIndex.slashes ?? []).map((s) => s.prefix));
for (const tool of tools) {
  for (const prefix of tool.slash_prefixes ?? []) {
    assert.ok(indexPrefixes.has(prefix), `optional slash index missing ${prefix}`);
    const entry = slashIndex.slashes.find((s) => s.prefix === prefix);
    assert.equal(entry.feature_id, FEATURE_ID);
    assert.ok(entry.message_ko?.trim());
  }
}

const opsShelf = JSON.parse(
  readFileSync(path.join(root, 'work-kits', 'profiles', 'cqr', 'ops', 'shelf.json'), 'utf8'),
);
assert.equal(opsShelf.features?.enable?.[FEATURE_ID]?.required, true);
for (const other of ['brand-info', 'product-dev']) {
  const shelf = JSON.parse(
    readFileSync(path.join(root, 'work-kits', 'profiles', 'cqr', other, 'shelf.json'), 'utf8'),
  );
  assert.equal(
    shelf.features?.enable?.[FEATURE_ID],
    undefined,
    `${other} must not enable Automaton Feature`,
  );
}

console.log('verify-org-automaton: ok');
