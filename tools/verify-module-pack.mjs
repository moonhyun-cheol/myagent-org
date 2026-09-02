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
  assert.ok(
    existsSync(path.join(root, 'agent-module', 'skills', 'product-data-access.md')),
    'skills/product-data-access.md required',
  );
  assert.ok(staged.capabilities.includes('automaton-routing'));
  const skillsManifest = JSON.parse(
    readFileSync(path.join(root, 'agent-module', 'skills', 'manifest.json'), 'utf8'),
  );
  for (const def of Object.values(skillsManifest.skills ?? {})) {
    for (const rel of def.brand_files ?? []) {
      assert.doesNotMatch(rel, /^data\//, `brand_files must not reference local data/: ${rel}`);
    }
  }
} finally {
  rmSync(stageParent, { recursive: true, force: true });
}

const publish = readFileSync(path.join(root, 'tools', 'publish-module-update.mjs'), 'utf8');
assert.match(publish, /stageAgentModule/);
assert.match(publish, /channelFeedPath/);
assert.match(publish, /loadOperatorConfig/);
assert.match(publish, /brand_manual_url/);
assert.match(publish, /openclaw_adapter_base_url/);
assert.match(publish, /deploy-overrides.json/);
const companyManifest = JSON.parse(readFileSync(path.join(root, 'manifest.json'), 'utf8'));
assert.equal(String(companyManifest.brand_manual_url ?? '').trim(), '');
assert.equal(String(companyManifest.product_data_base_url ?? '').trim(), '');
assert.match(publish, /MY_AGENT_ORGANIZATION_MODULE_SOURCE \|\| root/);
assert.equal(existsSync(path.join(root, 'operator-config.example.json')), true);
assert.equal(existsSync(path.join(root, 'agent-module', 'prompt_concept')), true);
assert.equal(existsSync(path.join(root, 'agent-module', 'market_research', 'cqr_product_pipeline')), true);
assert.equal(existsSync(path.join(root, 'agent-module', 'automaton-tools.manifest.json')), true);
assert.equal(existsSync(path.join(root, 'agent-module', 'openclaw-workflow-map.json')), true);
assert.equal(existsSync(path.join(root, 'agent-module', 'deploy-overrides.json')), true);

const privateHostRe = /127\.0\.0\.1|192\.168\.|10\.\d+\.|172\.(1[6-9]|2\d|3[0-1])\.|\\\\Nas\\/i;
const trackedHostFiles = [
  'manifest.json',
  'operator-config.example.json',
  'agent-module/deploy-overrides.json',
  'agent-module/prompt_concept/AGENTS.md',
  'agent-module/prompt_concept/MY_prompt.md',
  'agent-module/prompt_concept/scripts/extract_nas_docs.py',
  'agent-module/prompt_concept/scripts/brand_scan.py',
  'agent-module/prompt_concept/scripts/brand_scan_active.py',
];
for (const rel of trackedHostFiles) {
  const text = readFileSync(path.join(root, rel), 'utf8');
  assert.doesNotMatch(text, privateHostRe, `git-tracked ${rel} must not hardcode a private host or NAS share`);
}

assert.equal(existsSync(path.join(root, 'channels', 'work-kits.json')), true);
assert.equal(existsSync(path.join(root, 'work-kits', 'profiles', 'cqr', 'brand-info', 'shelf.json')), true);
const workKitPublish = readFileSync(path.join(root, 'tools', 'publish-work-kit-catalog.mjs'), 'utf8');
assert.match(workKitPublish, /channels\/work-kits\.json/);

console.log('verify-module-pack: ok');
