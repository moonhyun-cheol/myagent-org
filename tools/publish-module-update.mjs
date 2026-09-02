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
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

import {
  buildPayloadManifest,
  buildReleaseFeed,
  createSignedEnvelope,
  sha256Bytes,
  sha256File,
  verifySignedEnvelope,
} from './update/update-signing.mjs';
import { INSTALL_ROOT, stageAgentModule } from './pack-agent-module.mjs';
import { loadOperatorConfig } from './operator-config.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const outDir = path.join(root, 'deploy', 'output');
const stageDir = path.join(outDir, 'module-stage');
const productManifestPath = path.join(root, 'manifest.json');
const sourceRoot = path.resolve(
  process.env.MY_AGENT_ORGANIZATION_MODULE_SOURCE || root,
);
const privateKeyPath = path.resolve(
  process.env.MY_AGENT_MODULE_UPDATE_SIGNING_KEY
  ?? path.join(root, 'tools', 'keys', 'update-private.pem'),
);
const publicKeyPath = path.join(root, 'core', 'config', 'defaults', 'update-public.pem');

function fail(message) {
  console.error(`publish-module-update: ${message}`);
  process.exit(1);
}

if (!existsSync(privateKeyPath)) fail(`module signing private key missing: ${privateKeyPath}`);
if (!existsSync(publicKeyPath)) fail(`module signing public key missing: ${publicKeyPath}`);

const product = JSON.parse(readFileSync(productManifestPath, 'utf8'));
const operator = loadOperatorConfig(root);
const updateSequence = Number(product.update_sequence);
const minimumSupportedSequence = Number(product.minimum_supported_sequence ?? 1);
const version = String(product.version ?? '').trim();
const channel = String(product.update_channel ?? 'beta').trim().toLowerCase();
const installRoot = String(product.install_root ?? INSTALL_ROOT).replaceAll('\\', '/');
const githubRepository = String(
  process.env.MY_AGENT_MODULE_UPDATE_GITHUB_REPO ?? product.update_repository ?? '',
).trim();
const updateFeedUrl = String(product.update_feed_url ?? '').trim();
if (!Number.isSafeInteger(updateSequence) || updateSequence < 1) {
  fail('manifest.json update_sequence must be a positive safe integer');
}
if (!version) fail('manifest.json version is required');
if (installRoot !== INSTALL_ROOT) fail(`install_root must be ${INSTALL_ROOT}`);

const privateKeyPem = readFileSync(privateKeyPath, 'utf8');
const publicKeyPem = readFileSync(publicKeyPath, 'utf8');
const probeEnvelope = createSignedEnvelope({ purpose: 'my-agent-module-key-check' }, privateKeyPem);
if (!verifySignedEnvelope(probeEnvelope, publicKeyPem)) {
  fail('module signing private/public keys do not match');
}

if (existsSync(stageDir)) rmSync(stageDir, { recursive: true, force: true });
const extractDir = path.join(stageDir, installRoot);
mkdirSync(extractDir, { recursive: true });

let staged;
try {
  staged = stageAgentModule(sourceRoot, extractDir);
} catch (error) {
  fail(error instanceof Error ? error.message : String(error));
}

writeFileSync(
  path.join(extractDir, 'module.json'),
  `${JSON.stringify({
    id: 'organization',
    kind: 'organization-module',
    version,
    update_sequence: updateSequence,
    install_root: installRoot,
    required_core_api: String(product.required_core_api ?? ''),
    update_feed_url: updateFeedUrl,
    update_channel: channel,
    brand_manual_url: operator.brand_manual_url || undefined,
    product_data_base_url: operator.product_data_base_url || undefined,
    capabilities: staged.capabilities,
  }, null, 2)}\n`,
  'utf8',
);

const payloadDocument = buildPayloadManifest(stageDir, {
  updateSequence,
  minimumSupportedSequence,
  version,
  channel,
});
for (const file of payloadDocument.files) {
  if (file.path !== 'update-payload.json' && !file.path.startsWith(`${installRoot}/`)) {
    fail(`payload path escapes ${installRoot}: ${file.path}`);
  }
}
const payloadEnvelope = createSignedEnvelope(payloadDocument, privateKeyPem);
if (!verifySignedEnvelope(payloadEnvelope, publicKeyPem)) {
  fail('generated module payload signature verification failed');
}
const payloadEnvelopePath = path.join(stageDir, 'update-payload.json');
writeFileSync(payloadEnvelopePath, `${JSON.stringify(payloadEnvelope, null, 2)}\n`, 'utf8');

const zipName = `MYAgent-organization-v${version}-module.zip`;
const zipPath = path.join(outDir, zipName);
if (existsSync(zipPath)) rmSync(zipPath, { force: true });
const zip = spawnSync(
  'powershell',
  [
    '-NoProfile',
    '-Command',
    [
      "$ErrorActionPreference = 'Stop'",
      'Add-Type -AssemblyName System.IO.Compression.FileSystem',
      `[IO.Compression.ZipFile]::CreateFromDirectory('${stageDir.replace(/'/g, "''")}', '${zipPath.replace(/'/g, "''")}', [IO.Compression.CompressionLevel]::Optimal, $false, [Text.Encoding]::UTF8)`,
    ].join('; '),
  ],
  { encoding: 'utf8' },
);
if (zip.status !== 0 || !existsSync(zipPath)) {
  fail(zip.stderr?.toString().trim() || `module zip missing: ${zipPath}`);
}

const payloadEnvelopeBytes = readFileSync(payloadEnvelopePath);
const feedDocument = buildReleaseFeed({
  updateSequence,
  minimumSupportedSequence,
  version,
  channel,
  publishedAt: String(payloadEnvelope.document.created_at),
  repository: githubRepository,
  releaseTag: `update-${updateSequence}`,
  assetName: zipName,
  assetSize: statSync(zipPath).size,
  assetSha256: sha256File(zipPath),
  payloadManifestSha256: sha256Bytes(payloadEnvelopeBytes),
  releaseNotes: process.env.MY_AGENT_MODULE_UPDATE_RELEASE_NOTES ?? '',
});
const feedEnvelope = createSignedEnvelope(feedDocument, privateKeyPem);
if (!verifySignedEnvelope(feedEnvelope, publicKeyPem)) {
  fail('generated module feed signature verification failed');
}

mkdirSync(outDir, { recursive: true });
const feedPath = path.join(outDir, `update-feed-${channel}.json`);
const channelFeedPath = path.join(root, 'channels', `${channel}.json`);
const feedText = `${JSON.stringify(feedEnvelope, null, 2)}\n`;
writeFileSync(feedPath, feedText, 'utf8');
mkdirSync(path.dirname(channelFeedPath), { recursive: true });
writeFileSync(channelFeedPath, feedText, 'utf8');
writeFileSync(
  path.join(outDir, 'LATEST_SECURE_UPDATE.json'),
  `${JSON.stringify({
    kind: 'organization-module',
    channel,
    update_sequence: updateSequence,
    version,
    zip_path: zipPath,
    feed_path: feedPath,
    channel_feed_path: channelFeedPath,
    github_repository: githubRepository,
    github_release_tag: feedDocument.asset.release_tag,
    github_asset_name: feedDocument.asset.name,
    source_root: sourceRoot,
    pack_source: staged.sourceKind,
    capabilities: staged.capabilities,
  }, null, 2)}\n`,
  'utf8',
);

console.log('Organization module payload ->', zipPath);
console.log('Organization module feed    ->', feedPath);
console.log('Channel feed                ->', channelFeedPath);
console.log('Packed source               ->', sourceRoot, `(${staged.sourceKind})`);
