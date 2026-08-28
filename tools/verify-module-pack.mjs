#!/usr/bin/env node
import assert from 'node:assert/strict';
import { existsSync, mkdtempSync, mkdirSync, readFileSync, rmSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import { assertAgentModuleLayout, stageAgentModule } from './pack-agent-module.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

assertAgentModuleLayout(root);

const emptyGit = mkdtempSync(path.join(os.tmpdir(), 'org-module-empty-'));
try {
  spawnSync('git', ['init'], { cwd: emptyGit, encoding: 'utf8' });
  let failed = false;
  try {
    assertAgentModuleLayout(emptyGit);
  } catch {
    failed = true;
  }
  assert.equal(failed, true, 'empty source must fail the curated pack layout check');
} finally {
  rmSync(emptyGit, { recursive: true, force: true });
}

const stageParent = mkdtempSync(path.join(os.tmpdir(), 'org-module-stage-'));
try {
  const extractDir = path.join(stageParent, 'modules', 'organization');
  mkdirSync(extractDir, { recursive: true });
  const staged = stageAgentModule(root, extractDir);
  assert.ok(staged.capabilities.includes('skills'));
  assert.ok(staged.capabilities.includes('brand-context'));
  assert.ok(staged.capabilities.includes('research-pipeline'));
  assert.ok(staged.capabilities.includes('brand-knowledge'));
  assert.ok(staged.capabilities.includes('automaton-routing'));
  assert.equal(existsSync(path.join(root, 'agent-module', 'data', 'CQR_INTERNAL_STRATEGY_v3.1.md')), true);
  assert.equal(existsSync(path.join(root, 'agent-module', 'data', 'model_row_index.txt')), true);
  assert.equal(existsSync(path.join(root, 'agent-module', 'data', 'options.db')), false);
} finally {
  rmSync(stageParent, { recursive: true, force: true });
}

const publish = readFileSync(path.join(root, 'tools', 'publish-module-update.mjs'), 'utf8');
assert.match(publish, /stageAgentModule/);
assert.match(publish, /channelFeedPath/);
assert.match(publish, /brand_manual_url/);
const companyManifest = JSON.parse(readFileSync(path.join(root, 'manifest.json'), 'utf8'));
assert.match(String(companyManifest.brand_manual_url ?? ''), /192\.168\.1\.248:8080\/api\/brand-manual\/current\.md/);
assert.match(publish, /MY_AGENT_ORGANIZATION_MODULE_SOURCE \|\| root/);
  assert.equal(existsSync(path.join(root, 'agent-module', 'prompt_concept')), true);
  assert.equal(existsSync(path.join(root, 'agent-module', 'market_research', 'cqr_product_pipeline')), true);
  assert.equal(existsSync(path.join(root, 'agent-module', 'automaton-tools.manifest.json')), true);
  assert.equal(existsSync(path.join(root, 'agent-module', 'openclaw-workflow-map.json')), true);
  assert.equal(existsSync(path.join(root, 'agent-module', 'deploy-overrides.json')), true);

console.log('verify-module-pack: ok');
