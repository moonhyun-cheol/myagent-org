#!/usr/bin/env node
import assert from 'node:assert/strict';
import { existsSync, mkdtempSync, mkdirSync, readFileSync, rmSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import {
  listWorkKitGroups,
  packWorkKitShelf,
  readJson,
  shelfAssetName,
} from './pack-work-kit-shelf.mjs';
import { sha256File } from './update/update-signing.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const EXPECTED_PINS = {
  'cqr/brand-info': ['org:cqr_brand_manual', 'cqr_brand_manual'],
  'cqr/product-dev': [
    'org:brand_concept',
    'brand_concept',
    'org:market_research',
    'market_research',
    'org:size_guide',
    'size_guide',
  ],
  'cqr/ops': [],
};

const skillsManifest = readJson(path.join(root, 'agent-module', 'skills', 'manifest.json'));
const orgSkillIds = new Set(Object.keys(skillsManifest.skills ?? {}));

function orgPinsFromShelf(shelf) {
  const pins = shelf.ui?.pinned_skill_ids ?? [];
  return pins.filter((p) => p.startsWith('org:')).map((p) => p.slice(4));
}

const groups = listWorkKitGroups(root);
assert.ok(groups.some((g) => g.id === 'cqr'), 'cqr group');
const cqr = groups.find((g) => g.id === 'cqr');
assert.equal(cqr.shelves.length, 3, 'cqr must have 3 shelves');

for (const { shelf } of cqr.shelves) {
  const key = `cqr/${shelf.id}`;
  const expected = EXPECTED_PINS[key];
  assert.ok(expected, `unexpected shelf ${key}`);
  assert.deepEqual(shelf.ui?.pinned_skill_ids ?? [], expected, `pins for ${key}`);
  for (const orgId of orgPinsFromShelf(shelf)) {
    assert.ok(orgSkillIds.has(orgId), `org skill missing in manifest: ${orgId}`);
  }
  assert.equal(shelf.group, 'cqr');
  assert.equal(shelf.schema_version, 1);
}

assert.ok(existsSync(path.join(root, 'work-kits', 'catalog-meta.json')));
const meta = readJson(path.join(root, 'work-kits', 'catalog-meta.json'));
assert.ok(meta.sequence >= 1);
assert.ok(String(meta.update_repository ?? '').trim());

const temp = mkdtempSync(path.join(os.tmpdir(), 'work-kit-pack-'));
try {
  const archive = path.join(temp, shelfAssetName('cqr', 'brand-info'));
  packWorkKitShelf(root, 'cqr', 'brand-info', archive);
  assert.ok(existsSync(archive));
  const extract = path.join(temp, 'extract');
  mkdirSync(extract, { recursive: true });
  const untar = spawnSync('tar', ['-xzf', archive, '-C', extract], { encoding: 'utf8' });
  assert.equal(untar.status, 0, untar.stderr);
  assert.ok(existsSync(path.join(extract, 'shelf.json')));
} finally {
  rmSync(temp, { recursive: true, force: true });
}

const feedPath = path.join(root, 'channels', 'work-kits.json');
if (existsSync(feedPath)) {
  const feed = readJson(feedPath);
  assert.ok(feed.sequence >= 1);
  assert.ok(Array.isArray(feed.groups));
  const feedCqr = feed.groups.find((g) => g.id === 'cqr');
  assert.ok(feedCqr, 'feed must list cqr group');
  for (const [key, pins] of Object.entries(EXPECTED_PINS)) {
    const [, shelfId] = key.split('/');
    const feedShelf = feedCqr.shelves?.find((s) => s.id === shelfId);
    assert.ok(feedShelf, `feed shelf ${key}`);
    assert.deepEqual(feedShelf.ui?.pinned_skill_ids ?? [], pins);
    if (feedShelf.asset?.name) {
      const assetPath = path.join(root, 'deploy', 'output', feedShelf.asset.name);
      if (existsSync(assetPath)) {
        if (feedShelf.asset.sha256) {
          assert.equal(sha256File(assetPath), feedShelf.asset.sha256);
        }
        if (feedShelf.asset.size) {
          assert.equal(readFileSync(assetPath).length, feedShelf.asset.size);
        }
      }
    }
  }
}

const publish = readFileSync(path.join(root, 'tools', 'publish-work-kit-catalog.mjs'), 'utf8');
assert.match(publish, /channels\/work-kits\.json/);

console.log('verify-work-kit-pack: ok');
