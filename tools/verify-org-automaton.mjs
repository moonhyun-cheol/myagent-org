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
assert.match(String(deployOverrides.openclaw_adapter_base_url ?? ''), /8790/);
assert.equal(deployOverrides.openclaw_fallback_local, false);

const automatonManifest = JSON.parse(
  readFileSync(path.join(agentModule, 'automaton-tools.manifest.json'), 'utf8'),
);
assert.ok(
  (automatonManifest.tools ?? []).some((tool) =>
    (tool.slash_prefixes ?? []).some((prefix) => prefix.startsWith('/반품율')),
  ),
  'automaton-tools.manifest.json must route /반품율* slash commands',
);

console.log('verify-org-automaton: ok');
