#!/usr/bin/env node
import { createHash } from 'node:crypto';
import {
  existsSync,
  readFileSync,
  statSync,
} from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';

import {
  giteaApiUrl,
  loadReleaseTargets,
  releaseAssetUrl,
  validateAssetName,
  validateRef,
} from './release/release-target.mjs';
import { sha256File } from './update/update-signing.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

function fail(message) {
  throw new Error(`publish-gitea-releases: ${message}`);
}

function readJson(filePath) {
  return JSON.parse(readFileSync(filePath, 'utf8'));
}

function requireFile(filePath, label) {
  if (!existsSync(filePath) || !statSync(filePath).isFile()) fail(`${label} missing: ${filePath}`);
  return filePath;
}

function localAsset(filePath, name = path.basename(filePath)) {
  requireFile(filePath, 'release asset');
  return {
    path: filePath,
    name: validateAssetName(name),
    size: statSync(filePath).size,
    sha256: sha256File(filePath),
  };
}

function assertFeedAsset(filePath, feedAsset) {
  const asset = localAsset(filePath, feedAsset.name);
  if (asset.size !== Number(feedAsset.size)) fail(`size mismatch for ${asset.name}`);
  if (asset.sha256 !== String(feedAsset.sha256).toLowerCase()) fail(`SHA-256 mismatch for ${asset.name}`);
  return asset;
}

function uniqueAssets(assets) {
  const byName = new Map();
  for (const asset of assets) {
    const previous = byName.get(asset.name);
    if (previous && (previous.sha256 !== asset.sha256 || previous.size !== asset.size)) {
      fail(`conflicting release assets named ${asset.name}`);
    }
    byName.set(asset.name, asset);
  }
  return [...byName.values()];
}

export function collectMirrorPlans(workspaceRoot = root, selectedTrack = 'all') {
  const requested = selectedTrack === 'all'
    ? new Set(['organization', 'work-kits', 'launcher'])
    : new Set(String(selectedTrack).split(',').map((item) => item.trim()).filter(Boolean));
  for (const item of requested) {
    if (!['organization', 'work-kits', 'launcher'].includes(item)) fail(`unknown track: ${item}`);
  }
  const plans = [];

  if (requested.has('organization')) {
    const latest = readJson(path.join(workspaceRoot, 'deploy', 'output', 'LATEST_SECURE_UPDATE.json'));
    const feedPath = requireFile(path.join(workspaceRoot, 'channels', `${latest.channel}.json`), 'organization feed');
    const feed = readJson(feedPath).document;
    if (feed.kind !== 'organization-module' || Number(feed.update_sequence) !== Number(latest.update_sequence)) {
      fail('organization latest metadata and channel feed do not match');
    }
    const zipPath = path.join(workspaceRoot, 'deploy', 'output', feed.asset.name);
    plans.push({
      track: 'organization',
      tag: validateRef(feed.asset.release_tag, 'organization release tag'),
      title: `MY Agent organization update ${feed.update_sequence}`,
      notes: feed.release_notes || `Organization module update ${feed.update_sequence}`,
      prerelease: feed.channel !== 'stable',
      assets: uniqueAssets([
        assertFeedAsset(zipPath, feed.asset),
        localAsset(feedPath, `update-feed-${feed.channel}.json`),
      ]),
    });
  }

  if (requested.has('work-kits')) {
    const feedPath = requireFile(path.join(workspaceRoot, 'channels', 'work-kits.json'), 'Work Kit feed');
    const feed = readJson(feedPath);
    const assets = [];
    const tags = new Set();
    for (const group of feed.groups ?? []) {
      for (const shelf of group.shelves ?? []) {
        if (!shelf.asset) continue;
        tags.add(shelf.asset.release_tag);
        assets.push(assertFeedAsset(
          path.join(workspaceRoot, 'deploy', 'output', shelf.asset.name),
          shelf.asset,
        ));
      }
    }
    if (tags.size !== 1) fail('Work Kit assets must share one release tag');
    const featureIndexPath = requireFile(
      path.join(workspaceRoot, 'deploy', 'output', 'FEATURE_PACKS.json'),
      'Feature Pack index',
    );
    const featureIndex = readJson(featureIndexPath);
    for (const [featureId, metadata] of Object.entries(featureIndex.features ?? {})) {
      assets.push(assertFeedAsset(
        path.join(workspaceRoot, 'deploy', 'output', 'features', `${featureId}.zip`),
        { name: `${featureId}.zip`, size: metadata.size, sha256: metadata.sha256 },
      ));
    }
    assets.push(localAsset(feedPath, 'work-kits.json'));
    assets.push(localAsset(featureIndexPath, 'FEATURE_PACKS.json'));
    plans.push({
      track: 'work-kits',
      tag: validateRef([...tags][0], 'Work Kit release tag'),
      title: `CQR Work Kits ${feed.sequence}`,
      notes: `Work Kit catalog ${feed.sequence}`,
      prerelease: feed.channel !== 'stable',
      assets: uniqueAssets(assets),
    });
  }

  if (requested.has('launcher')) {
    const latest = readJson(path.join(workspaceRoot, 'manager', 'deploy', 'output', 'LATEST_LAUNCHER_UPDATE.json'));
    const feedPath = requireFile(
      path.join(workspaceRoot, 'manager', 'channels', `launcher-${latest.channel}.json`),
      'launcher feed',
    );
    const feed = readJson(feedPath).document;
    if (feed.kind !== 'work-kit-launcher' || Number(feed.update_sequence) !== Number(latest.update_sequence)) {
      fail('launcher latest metadata and channel feed do not match');
    }
    const outDir = path.join(workspaceRoot, 'manager', 'deploy', 'output');
    const installName = `WorkKitLauncher-v${feed.version}-install.zip`;
    plans.push({
      track: 'launcher',
      tag: validateRef(feed.asset.release_tag, 'launcher release tag'),
      title: `WorkKitLauncher ${feed.version} (update ${feed.update_sequence})`,
      notes: feed.release_notes || `WorkKitLauncher update ${feed.update_sequence}`,
      prerelease: feed.channel !== 'stable',
      assets: uniqueAssets([
        assertFeedAsset(path.join(outDir, feed.asset.name), feed.asset),
        localAsset(path.join(outDir, installName), installName),
        localAsset(feedPath, `launcher-feed-${feed.channel}.json`),
      ]),
    });
  }

  return plans;
}

function repositoryApiPath(target, suffix = '') {
  const repository = target.repository.split('/').map(encodeURIComponent).join('/');
  return `repos/${repository}${suffix}`;
}

async function apiRequest(target, suffix, { token = '', method = 'GET', body, form, allow404 = false } = {}) {
  const headers = { Accept: 'application/json' };
  if (token) headers.Authorization = `token ${token}`;
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const response = await fetch(giteaApiUrl(target, repositoryApiPath(target, suffix)), {
    method,
    headers,
    body: form ?? (body === undefined ? undefined : JSON.stringify(body)),
    redirect: 'error',
  });
  if (allow404 && response.status === 404) return null;
  if (!response.ok) {
    const detail = (await response.text()).slice(0, 1000);
    fail(`Gitea API ${method} ${suffix || '/'} returned ${response.status}${detail ? `: ${detail}` : ''}`);
  }
  if (response.status === 204) return null;
  return response.json();
}

function localTagCommit(tag) {
  const result = spawnSync('git', ['rev-parse', `${tag}^{commit}`], {
    cwd: root,
    encoding: 'utf8',
    shell: false,
  });
  return result.status === 0 ? String(result.stdout).trim().toLowerCase() : null;
}

async function inspectTag(target, tag) {
  const localCommit = localTagCommit(tag);
  const remote = await apiRequest(
    target,
    `/tags/${encodeURIComponent(tag)}`,
    { allow404: true },
  );
  if (!remote) return { exists: false, local_commit: localCommit, remote_commit: null, matches: false };
  const remoteCommit = String(remote.commit?.sha ?? remote.id ?? '').toLowerCase();
  return {
    exists: true,
    local_commit: localCommit,
    remote_commit: remoteCommit,
    matches: Boolean(localCommit) && localCommit === remoteCommit,
  };
}

async function sha256Remote(url) {
  const response = await fetch(url, { redirect: 'follow' });
  if (!response.ok || !response.body) fail(`could not verify remote asset ${url}: HTTP ${response.status}`);
  const hash = createHash('sha256');
  let size = 0;
  for await (const chunk of response.body) {
    const bytes = Buffer.from(chunk);
    hash.update(bytes);
    size += bytes.length;
  }
  return { size, sha256: hash.digest('hex') };
}

async function uploadAsset(target, release, asset, token) {
  const bytes = readFileSync(asset.path);
  const form = new FormData();
  form.append('attachment', new Blob([bytes]), asset.name);
  return apiRequest(
    target,
    `/releases/${release.id}/assets?name=${encodeURIComponent(asset.name)}`,
    { token, method: 'POST', form },
  );
}

async function publishPlan(target, plan, { token, resume }) {
  let release = await apiRequest(
    target,
    `/releases/tags/${encodeURIComponent(plan.tag)}`,
    { token, allow404: true },
  );
  if (release && !resume) fail(`release ${plan.tag} already exists; use --resume to verify/fill missing assets`);
  if (!release) {
    release = await apiRequest(target, '/releases', {
      token,
      method: 'POST',
      body: {
        tag_name: plan.tag,
        name: plan.title,
        body: plan.notes,
        draft: false,
        prerelease: plan.prerelease,
      },
    });
  }

  const existing = new Map((release.assets ?? []).map((asset) => [asset.name, asset]));
  for (const asset of plan.assets) {
    let remote = existing.get(asset.name);
    if (remote) {
      if (Number(remote.size) !== asset.size) fail(`existing ${plan.tag}/${asset.name} has a different size`);
    } else {
      remote = await uploadAsset(target, release, asset, token);
    }
    const downloadUrl = remote.browser_download_url || releaseAssetUrl(target, plan.tag, asset.name);
    const verified = await sha256Remote(downloadUrl);
    if (verified.size !== asset.size || verified.sha256 !== asset.sha256) {
      fail(`remote verification failed for ${plan.tag}/${asset.name}`);
    }
  }
  return { tag: plan.tag, assets: plan.assets.length, url: release.html_url };
}

export async function main(argv = process.argv.slice(2)) {
  const { values } = parseArgs({
    args: argv,
    options: {
      confirm: { type: 'boolean', default: false },
      resume: { type: 'boolean', default: false },
      track: { type: 'string', default: 'all' },
    },
    allowPositionals: false,
  });
  const targets = loadReleaseTargets(root);
  const target = targets.primary;
  if (target.provider !== 'gitea') fail('primary release target must be Gitea');
  const plans = collectMirrorPlans(root, values.track);
  const repository = await apiRequest(target, '');
  if (repository.private) fail('Gitea repository must be public for login-free updates');
  if (repository.default_branch !== target.default_branch) fail('Gitea default branch does not match release-targets.json');

  const tagStatus = {};
  for (const plan of plans) tagStatus[plan.tag] = await inspectTag(target, plan.tag);
  const preflight = {
    mode: values.confirm ? 'publish' : 'dry-run',
    migration_phase: targets.migration_phase,
    target: {
      provider: target.provider,
      repository: target.repository,
      base_url: target.base_url,
      default_branch: target.default_branch,
    },
    releases: plans.map((plan) => ({
      track: plan.track,
      tag: plan.tag,
      title: plan.title,
      assets: plan.assets.map(({ name, size, sha256 }) => ({ name, size, sha256 })),
      tag_status: tagStatus[plan.tag],
    })),
  };
  console.log(JSON.stringify(preflight, null, 2));

  const unsafeTag = Object.entries(tagStatus).find(([, status]) => !status.exists || !status.matches);
  if (unsafeTag) {
    fail(`Gitea tag ${unsafeTag[0]} is missing or differs from local history; push main and tags first`);
  }
  if (!values.confirm) {
    console.log('Dry run only. Set MY_AGENT_GITEA_TOKEN and re-run with --confirm after reviewing the plan.');
    return preflight;
  }
  const token = String(process.env.MY_AGENT_GITEA_TOKEN ?? '').trim();
  if (!token) fail('MY_AGENT_GITEA_TOKEN is required with --confirm');

  const published = [];
  for (const plan of plans) published.push(await publishPlan(target, plan, { token, resume: values.resume }));
  console.log(JSON.stringify({ published }, null, 2));
  return { ...preflight, published };
}

const launchedDirectly = process.argv[1]
  && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url;
if (launchedDirectly) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exit(1);
  });
}
