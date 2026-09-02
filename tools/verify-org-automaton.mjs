#!/usr/bin/env node
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const agentModule = path.join(root, 'agent-module');

for (const rel of [
  'automaton-tools.manifest.json',
  'openclaw-workflow-map.json',
  'deploy-overrides.json',
]) {
  assert.equal(existsSync(path.join(agentModule, rel)), true, `missing agent-module/${rel}`);
}

const deployOverrides = JSON.parse(
  readFileSync(path.join(agentModule, 'deploy-overrides.json'), 'utf8'),
);
assert.equal(String(deployOverrides.openclaw_adapter_base_url ?? '').trim(), '');
assert.equal(Boolean(deployOverrides.activation_server_url?.trim()), false);
assert.equal(deployOverrides.openclaw_fallback_local, false);
assert.doesNotMatch(
  JSON.stringify(deployOverrides),
  /127\.0\.0\.1|192\.168\.|10\.\d+\.|172\.(1[6-9]|2\d|3[0-1])\./,
  'GitHub overlay must not hardcode Adapter host',
);

const automatonManifest = JSON.parse(
  readFileSync(path.join(agentModule, 'automaton-tools.manifest.json'), 'utf8'),
);
const workflowMap = JSON.parse(
  readFileSync(path.join(agentModule, 'openclaw-workflow-map.json'), 'utf8'),
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
}

console.log('verify-org-automaton: ok');
