#!/usr/bin/env node
import {
  existsSync,
  mkdirSync,
  readFileSync,
  rmSync,
  statSync,
  writeFileSync,
} from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';

import {
  listWorkKitGroups,
  packAllWorkKitShelves,
  readJson,
  shelfAssetName,
} from './pack-work-kit-shelf.mjs';
import { sha256File } from './update/update-signing.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const outDir = path.join(root, 'deploy', 'output');
const metaPath = path.join(root, 'work-kits', 'catalog-meta.json');
const channelFeedPath = path.join(root, 'channels', 'work-kits.json');

const { values } = parseArgs({
  options: {
    bump: { type: 'boolean', default: false },
  },
  allowPositionals: false,
});

function fail(message) {
  console.error(`publish-work-kit-catalog: ${message}`);
  process.exit(1);
}

if (!existsSync(metaPath)) fail(`missing ${metaPath}`);
const meta = readJson(metaPath);
const channel = String(meta.channel ?? 'beta').trim().toLowerCase();
let sequence = Number(meta.sequence);
if (!Number.isSafeInteger(sequence) || sequence < 1) {
  fail('catalog-meta.json sequence must be a positive integer');
}
if (values.bump) sequence += 1;

const repository = String(
  process.env.MY_AGENT_WORK_KIT_UPDATE_GITHUB_REPO
  ?? meta.update_repository
  ?? '',
).trim();
if (!repository) fail('update_repository required in catalog-meta.json or env');

const releaseTagPrefix = String(meta.release_tag_prefix ?? 'work-kits').trim();
const releaseTag = `${releaseTagPrefix}-${sequence}`;

if (existsSync(outDir)) rmSync(outDir, { recursive: true, force: true });
mkdirSync(outDir, { recursive: true });

const packed = packAllWorkKitShelves(root, outDir);
const packedByKey = new Map(packed.map((p) => [`${p.group}/${p.id}`, p]));

const feedGroups = listWorkKitGroups(root).map((group) => ({
  id: group.id,
  label: group.label,
  order: group.order,
  shelves: group.shelves.map(({ shelf }) => {
    const key = `${group.id}/${shelf.id}`;
    const pack = packedByKey.get(key);
    if (!pack) fail(`pack missing for ${key}`);
    const assetName = shelfAssetName(group.id, shelf.id);
    return {
      id: shelf.id,
      label: shelf.label,
      description: shelf.description,
      pull: shelf.pull ?? [],
      plugins: shelf.plugins ?? { enable: {} },
      ui: shelf.ui ?? { pinned_skill_ids: [] },
      hints: shelf.hints,
      min_core_sequence: shelf.min_core_sequence,
      asset: {
        sequence,
        name: assetName,
        repository,
        release_tag: releaseTag,
        size: pack.size,
        sha256: sha256File(pack.outPath),
      },
    };
  }),
}));

const feedDocument = {
  channel,
  sequence,
  groups: feedGroups,
};

writeFileSync(channelFeedPath, `${JSON.stringify(feedDocument, null, 2)}\n`, 'utf8');
writeFileSync(
  metaPath,
  `${JSON.stringify({ ...meta, channel, sequence, update_repository: repository }, null, 2)}\n`,
  'utf8',
);

const manifestPath = path.join(root, 'manifest.json');
if (existsSync(manifestPath)) {
  const product = readJson(manifestPath);
  writeFileSync(
    manifestPath,
    `${JSON.stringify({
      ...product,
      work_kit_catalog_feed_url: `https://raw.githubusercontent.com/${repository}/main/channels/work-kits.json`,
    }, null, 2)}\n`,
    'utf8',
  );
}

console.log(`publish-work-kit-catalog: ok`);
console.log(`  feed: ${channelFeedPath}`);
console.log(`  sequence: ${sequence}`);
console.log(`  release_tag: ${releaseTag}`);
console.log(`  assets: ${packed.length} in ${outDir}`);
for (const p of packed) {
  console.log(`    ${p.name} (${p.size} bytes)`);
}
