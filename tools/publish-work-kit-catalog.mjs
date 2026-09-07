#!/usr/bin/env node
import {
  existsSync,
  mkdirSync,
  readFileSync,
  rmSync,
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
import {
  AUTOMATON_FEATURE_ID,
  packSignedOrganizationFeature,
} from './pack-organization-feature.mjs';
import { sha256File } from './update/update-signing.mjs';
import { loadOperatorConfig, operatorHubForPublish } from './operator-config.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const outDir = path.join(root, 'deploy', 'output');
const metaPath = path.join(root, 'work-kits', 'catalog-meta.json');
const channelFeedPath = path.join(root, 'channels', 'work-kits.json');

const { values } = parseArgs({
  options: {
    bump: { type: 'boolean', default: false },
    'skip-hub': { type: 'boolean', default: false },
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

const privateKeyPath = path.resolve(
  process.env.MY_AGENT_MODULE_UPDATE_SIGNING_KEY
  ?? path.join(root, 'tools', 'keys', 'update-private.pem'),
);
const publicKeyPath = path.join(root, 'core', 'config', 'defaults', 'update-public.pem');
if (!existsSync(privateKeyPath)) fail(`module signing private key missing: ${privateKeyPath}`);
if (!existsSync(publicKeyPath)) fail(`module signing public key missing: ${publicKeyPath}`);
const privateKeyPem = readFileSync(privateKeyPath, 'utf8');
const publicKeyPem = readFileSync(publicKeyPath, 'utf8');

const skipHubInject = values['skip-hub']
  || ['1', 'true', 'yes'].includes(String(process.env.MY_AGENT_PUBLISH_SKIP_HUB ?? '').trim().toLowerCase());
const operator = loadOperatorConfig(root);
const hub = skipHubInject
  ? {
    deployment_phase: operator.deployment_phase || 'operator_pc',
    openclaw_adapter_base_url: '',
    brand_manual_url: '',
    product_data_base_url: '',
    adapter_auth: operator.adapter_auth,
    adapter_progress: operator.adapter_progress,
  }
  : operatorHubForPublish(root);

if (existsSync(outDir)) rmSync(outDir, { recursive: true, force: true });
mkdirSync(outDir, { recursive: true });

// Build signed Feature Packs required by any shelf.
const featureZipById = {};
const featureMeta = {};
const requiredFeatureIds = new Set();
for (const group of listWorkKitGroups(root)) {
  for (const { shelf } of group.shelves) {
    for (const id of Object.keys(shelf.features?.enable ?? {})) {
      requiredFeatureIds.add(id);
    }
  }
}
for (const featureId of requiredFeatureIds) {
  if (featureId !== AUTOMATON_FEATURE_ID) {
    fail(`unknown Feature Pack id (add packer mapping): ${featureId}`);
  }
  const outZipPath = path.join(outDir, 'features', `${featureId}.zip`);
  const packed = packSignedOrganizationFeature({
    sourceRoot: root,
    featurePackDir: path.join('feature-packs', 'automaton-routing'),
    outZipPath,
    privateKeyPem,
    publicKeyPem,
    hub,
  });
  featureZipById[featureId] = packed.outZipPath;
  featureMeta[featureId] = {
    version: packed.version,
    update_sequence: packed.update_sequence,
    size: packed.size,
    sha256: packed.sha256,
    inventory: packed.inventory,
  };
  console.log(`publish-work-kit-catalog: feature ${featureId} → ${packed.outZipPath}`);
}

const packed = packAllWorkKitShelves(root, outDir, { featureZipById });
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
      features: shelf.features,
      ui: shelf.ui ?? { pinned_skill_ids: [] },
      hints: shelf.hints,
      // min_core_sequence: set only after Core Feature support ships a known sequence.
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
writeFileSync(
  path.join(outDir, 'FEATURE_PACKS.json'),
  `${JSON.stringify({ features: featureMeta }, null, 2)}\n`,
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
  const feats = p.embedded_features?.length ? ` features=[${p.embedded_features.join(',')}]` : '';
  console.log(`    ${p.name} (${p.size} bytes)${feats}`);
}
