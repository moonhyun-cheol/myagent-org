import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
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

export function packWorkKitShelf(sourceRoot, groupId, shelfId, outPath) {
  const found = listShelvesInGroup(sourceRoot, groupId).find((s) => s.shelf.id === shelfId);
  if (!found) failPack(`shelf not found: ${groupId}/${shelfId}`);
  const shelfDir = found.shelfDir;
  mkdirSync(path.dirname(outPath), { recursive: true });
  if (existsSync(outPath)) rmSync(outPath, { force: true });
  const tar = spawnSync(
    'tar',
    ['-czf', outPath, '-C', shelfDir, '.'],
    { encoding: 'utf8' },
  );
  if (tar.status !== 0 || !existsSync(outPath)) {
    failPack(tar.stderr?.toString().trim() || `tar failed for ${groupId}/${shelfId}`);
  }
  return {
    outPath,
    size: statSync(outPath).size,
    shelf: found.shelf,
  };
}

export function packAllWorkKitShelves(sourceRoot, outDir) {
  const packed = [];
  for (const group of listWorkKitGroups(sourceRoot)) {
    for (const { shelf } of group.shelves) {
      const name = shelfAssetName(group.id, shelf.id);
      const outPath = path.join(outDir, name);
      const result = packWorkKitShelf(sourceRoot, group.id, shelf.id, outPath);
      packed.push({
        group: group.id,
        id: shelf.id,
        name,
        outPath: result.outPath,
        size: result.size,
        shelf: result.shelf,
      });
    }
  }
  return packed;
}
