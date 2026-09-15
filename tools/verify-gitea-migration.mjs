#!/usr/bin/env node
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { collectMirrorPlans } from './publish-gitea-releases.mjs';
import {
  loadReleaseTargets,
  rawFileUrl,
  releaseAssetUrl,
  validateReleaseTarget,
} from './release/release-target.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const targets = loadReleaseTargets(root);

assert.equal(targets.migration_phase, 'primary');
assert.equal(targets.primary.provider, 'gitea');
assert.equal(targets.primary.repository, 'ins78516/myagent-org');
assert.equal(targets.primary.default_branch, 'main');
assert.equal(
  rawFileUrl(targets.primary, 'channels/beta.json'),
  'https://git.minyoungcorp.com/ins78516/myagent-org/raw/branch/main/channels/beta.json',
);
assert.equal(
  releaseAssetUrl(targets.primary, 'update-19', 'module.zip'),
  'https://git.minyoungcorp.com/ins78516/myagent-org/releases/download/update-19/module.zip',
);
assert.throws(() => validateReleaseTarget({
  provider: 'gitea',
  base_url: 'http://git.example.com',
  repository: 'owner/repo',
  default_branch: 'main',
}), /HTTPS/);
assert.throws(() => validateReleaseTarget({
  provider: 'gitea',
  base_url: 'https://token@git.example.com',
  repository: 'owner/repo',
  default_branch: 'main',
}), /credential-free/);
assert.throws(
  () => rawFileUrl(targets.primary, '../secret'),
  /unsafe/,
);
assert.throws(
  () => releaseAssetUrl(targets.primary, 'update-19', '../secret.zip'),
  /file name/,
);

// Primary phase authoring must point newly built clients and feeds at Gitea.
const manifest = JSON.parse(readFileSync(path.join(root, 'manifest.json'), 'utf8'));
const launcherManifest = JSON.parse(readFileSync(path.join(root, 'manager', 'launcher-manifest.json'), 'utf8'));
assert.equal(manifest.update_repository, targets.primary.repository);
assert.equal(launcherManifest.update_repository, targets.primary.repository);
assert.equal(manifest.update_feed_url, rawFileUrl(targets.primary, 'channels/beta.json'));
assert.equal(
  manifest.work_kit_catalog_feed_url,
  rawFileUrl(targets.primary, 'channels/work-kits.json'),
);
assert.equal(
  launcherManifest.update_feed_url,
  rawFileUrl(targets.primary, 'manager/channels/launcher-stable.json'),
);
assert.match(launcherManifest.update_asset_url_template, /^https:\/\/git\.minyoungcorp\.com\//);

// Existing signed seq 19/5/6 feeds are immutable migration artifacts. They may retain
// the legacy repository as long as their assets were mirrored to the primary host.
if (existsSync(path.join(root, 'deploy', 'output', 'LATEST_SECURE_UPDATE.json'))
    && existsSync(path.join(root, 'manager', 'deploy', 'output', 'LATEST_LAUNCHER_UPDATE.json'))) {
  const plans = collectMirrorPlans(root);
  assert.deepEqual(plans.map((plan) => plan.track), ['organization', 'work-kits', 'launcher']);
  assert.deepEqual(plans.map((plan) => plan.tag), ['update-19', 'work-kits-5', 'launcher-update-6']);
  assert.ok(plans.find((plan) => plan.track === 'work-kits')?.assets
    .some((asset) => asset.name === 'org.cqr.automaton-routing.zip'));
  assert.ok(plans.find((plan) => plan.track === 'launcher')?.assets
    .some((asset) => asset.name === 'WorkKitLauncher-v1.0.11-install.zip'));
}

const launcherService = readFileSync(
  path.join(root, 'manager', 'shell', 'WorkKitLauncher', 'LauncherUpdateService.cs'),
  'utf8',
);
assert.match(launcherService, /update_asset_url_template/);
assert.match(launcherService, /_feedUri\.GetLeftPart\(UriPartial\.Authority\)/);
assert.match(launcherService, /credential-free HTTPS/);

console.log('verify-gitea-migration: ok');
