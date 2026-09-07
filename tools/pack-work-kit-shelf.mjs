import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
  cpSync,
  writeFileSync,
} from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

export const WORK_KITS_ROOT = 'work-kits';
export const WORK_KITS_PROFILES = path.join(WORK_KITS_ROOT, 'profiles');

const GROUP_ID_RE = /^[a-z0-9][a-z0-9_-]{0,63}$/;
const SHELF_ID_RE = /^[a-z0-9][a-z0-9_-]{0,63}$/;

export function failPack(message) {
  throw new Error(message);
}

export function readJson(filePath) {
  return JSON.parse(readFileSync(filePath, 'utf8'));
}

export function listWorkKitGroups(sourceRoot) {
  const profilesRoot = path.join(sourceRoot, WORK_KITS_PROFILES);
  if (!existsSync(profilesRoot)) {
    failPack(`missing ${WORK_KITS_PROFILES}`);
  }
  const groups = [];
  for (const ent of readdirSync(profilesRoot, { withFileTypes: true })) {
    if (!ent.isDirectory() || ent.name.startsWith('.')) continue;
    if (!GROUP_ID_RE.test(ent.name)) continue;
    const groupDir = path.join(profilesRoot, ent.name);
    const groupMetaPath = path.join(groupDir, 'group.json');
    const groupMeta = existsSync(groupMetaPath) ? readJson(groupMetaPath) : { id: ent.name, label: ent.name };
    if (groupMeta.id !== ent.name) {
      failPack(`group.json id must match folder: ${ent.name}`);
    }
    const shelves = listShelvesInGroup(sourceRoot, ent.name);
    groups.push({
      id: ent.name,
      label: String(groupMeta.label ?? ent.name),
      order: typeof groupMeta.order === 'number' ? groupMeta.order : undefined,
      shelves,
    });
  }
  groups.sort((a, b) => (a.order ?? 0) - (b.order ?? 0) || a.id.localeCompare(b.id));
  return groups;
}

export function listShelvesInGroup(sourceRoot, groupId) {
  if (!GROUP_ID_RE.test(groupId)) failPack(`invalid group id: ${groupId}`);
  const groupDir = path.join(sourceRoot, WORK_KITS_PROFILES, groupId);
  if (!existsSync(groupDir)) failPack(`group folder missing: ${groupId}`);
  const shelves = [];
  for (const ent of readdirSync(groupDir, { withFileTypes: true })) {
    if (!ent.isDirectory() || ent.name.startsWith('.')) continue;
    if (!SHELF_ID_RE.test(ent.name)) continue;
    const shelfDir = path.join(groupDir, ent.name);
    const shelfPath = path.join(shelfDir, 'shelf.json');
    if (!existsSync(shelfPath)) continue;
    const shelf = readJson(shelfPath);
    if (shelf.id !== ent.name) failPack(`shelf.json id must match folder: ${groupId}/${ent.name}`);
    if (shelf.group !== groupId) failPack(`shelf.json group must be ${groupId}: ${ent.name}`);
    shelves.push({ shelfDir, shelf });
  }
  shelves.sort((a, b) => a.shelf.id.localeCompare(b.shelf.id));
  return shelves;
}

export function shelfAssetName(groupId, shelfId) {
  return `${groupId}-${shelfId}.tar.gz`;
}

/**
 * Pack a shelf directory to tar.gz.
 * @param {object} [opts]
 * @param {Record<string, string>} [opts.featureZipById] feature_id → absolute zip path to embed under features/
 */
export function packWorkKitShelf(sourceRoot, groupId, shelfId, outPath, opts = {}) {
  const found = listShelvesInGroup(sourceRoot, groupId).find((s) => s.shelf.id === shelfId);
  if (!found) failPack(`shelf not found: ${groupId}/${shelfId}`);
  const shelfDir = found.shelfDir;
  const featureEnable = found.shelf.features?.enable ?? {};
  const featureIds = Object.keys(featureEnable);

  let packRoot = shelfDir;
  let staging = null;
  if (featureIds.length > 0 || opts.featureZipById) {
    staging = path.join(path.dirname(outPath), `_shelf-stage-${groupId}-${shelfId}`);
    if (existsSync(staging)) rmSync(staging, { recursive: true, force: true });
    mkdirSync(staging, { recursive: true });
    cpSync(shelfDir, staging, { recursive: true });
    // Do not ship authoring leftovers.
    const authoringFeatures = path.join(staging, 'features');
    if (existsSync(authoringFeatures)) {
      for (const name of readdirSync(authoringFeatures)) {
        if (name.endsWith('.zip')) rmSync(path.join(authoringFeatures, name), { force: true });
      }
    }
    mkdirSync(path.join(staging, 'features'), { recursive: true });
    for (const featureId of featureIds) {
      const zipSrc = opts.featureZipById?.[featureId];
      if (!zipSrc || !existsSync(zipSrc)) {
        failPack(`signed Feature Pack missing for ${groupId}/${shelfId}: ${featureId}`);
      }
      cpSync(zipSrc, path.join(staging, 'features', `${featureId}.zip`));
    }
    // Persist features block in shelf.json (already present).
    writeFileSync(
      path.join(staging, 'shelf.json'),
      `${JSON.stringify(found.shelf, null, 2)}\n`,
      'utf8',
    );
    packRoot = staging;
  }

  mkdirSync(path.dirname(outPath), { recursive: true });
  if (existsSync(outPath)) rmSync(outPath, { force: true });
  const tar = spawnSync(
    'tar',
    ['-czf', outPath, '-C', packRoot, '.'],
    { encoding: 'utf8' },
  );
  if (staging && existsSync(staging)) rmSync(staging, { recursive: true, force: true });
  if (tar.status !== 0 || !existsSync(outPath)) {
    failPack(tar.stderr?.toString().trim() || `tar failed for ${groupId}/${shelfId}`);
  }
  return {
    outPath,
    size: statSync(outPath).size,
    shelf: found.shelf,
    embedded_features: featureIds,
  };
}

export function packAllWorkKitShelves(sourceRoot, outDir, opts = {}) {
  const packed = [];
  for (const group of listWorkKitGroups(sourceRoot)) {
    for (const { shelf } of group.shelves) {
      const name = shelfAssetName(group.id, shelf.id);
      const outPath = path.join(outDir, name);
      const result = packWorkKitShelf(sourceRoot, group.id, shelf.id, outPath, opts);
      packed.push({
        group: group.id,
        id: shelf.id,
        name,
        outPath: result.outPath,
        size: result.size,
        shelf: result.shelf,
        embedded_features: result.embedded_features,
      });
    }
  }
  return packed;
}
