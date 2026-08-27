import {
  cpSync,
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  rmSync,
  statSync,
} from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

export const AGENT_MODULE_DIR = 'agent-module';
export const INSTALL_ROOT = 'modules/organization';

export function failPack(message) {
  throw new Error(message);
}

export function resolveAgentModuleDir(sourceRoot) {
  return path.join(sourceRoot, AGENT_MODULE_DIR);
}

export function assertAgentModuleLayout(sourceRoot) {
  const agentModuleDir = resolveAgentModuleDir(sourceRoot);
  const skillsManifestPath = path.join(agentModuleDir, 'skills', 'manifest.json');
  if (!existsSync(skillsManifestPath)) {
    failPack(`curated pack missing: ${path.join(AGENT_MODULE_DIR, 'skills', 'manifest.json')}`);
  }
  const skillsManifest = JSON.parse(readFileSync(skillsManifestPath, 'utf8'));
  const skillCount = Object.keys(skillsManifest.skills ?? {}).length;
  const overlayCount = Object.keys(skillsManifest.overlays ?? {}).length;
  if (skillCount < 1 && overlayCount < 1) {
    failPack('agent-module/skills/manifest.json must declare skills or overlays');
  }
  for (const [id, def] of Object.entries(skillsManifest.skills ?? {})) {
    const mode = String(def?.mode ?? '');
    if (mode !== `org:${id}`) {
      failPack(`organization skill ${id} mode must be org:${id}`);
    }
    for (const rel of def.brand_files ?? []) {
      const abs = path.join(agentModuleDir, rel);
      if (!existsSync(abs)) failPack(`skill brand file missing: ${rel}`);
    }
    if (def.pipeline_script) {
      const abs = path.join(agentModuleDir, def.pipeline_script);
      if (!existsSync(abs)) failPack(`pipeline_script missing: ${def.pipeline_script}`);
    }
  }
  for (const overlay of Object.values(skillsManifest.overlays ?? {})) {
    for (const rel of overlay.brand_files ?? []) {
      const abs = path.join(agentModuleDir, rel);
      if (!existsSync(abs)) failPack(`overlay brand file missing: ${rel}`);
    }
  }
  return { agentModuleDir, skillsManifest, skillCount, overlayCount };
}

export function deriveCapabilities(extractDir, skillsManifest) {
  const capabilities = [];
  if (existsSync(path.join(extractDir, 'skills', 'manifest.json'))) capabilities.push('skills');
  const hasBrandDir = existsSync(path.join(extractDir, 'brand'))
    && readdirSync(path.join(extractDir, 'brand')).length > 0;
  const hasOverlays = Object.keys(skillsManifest.overlays ?? {}).length > 0;
  if (hasBrandDir || hasOverlays) capabilities.push('brand-context');
  if (existsSync(path.join(extractDir, 'pipelines'))) capabilities.push('research-pipeline');
  if (existsSync(path.join(extractDir, 'data'))) capabilities.push('brand-knowledge');
  if (!capabilities.includes('skills')) {
    failPack('packed module must include skills/manifest.json');
  }
  return capabilities;
}

function quotePs(value) {
  return String(value).replace(/'/g, "''");
}

function gitArchiveAgentModule(sourceRoot, archiveZip) {
  if (existsSync(archiveZip)) rmSync(archiveZip, { force: true });
  return spawnSync(
    'git',
    ['archive', '--format=zip', `--output=${archiveZip}`, `HEAD:${AGENT_MODULE_DIR}`],
    { cwd: sourceRoot, encoding: 'utf8' },
  );
}

function expandZip(archiveZip, destination) {
  const expand = spawnSync(
    'powershell',
    [
      '-NoProfile',
      '-Command',
      [
        "$ErrorActionPreference = 'Stop'",
        `Expand-Archive -LiteralPath '${quotePs(archiveZip)}' -DestinationPath '${quotePs(destination)}' -Force`,
      ].join('; '),
    ],
    { encoding: 'utf8' },
  );
  if (expand.status !== 0) {
    failPack(expand.stderr?.toString().trim() || 'failed to extract agent-module archive');
  }
}

export function stageAgentModule(sourceRoot, extractDir) {
  const { agentModuleDir, skillsManifest } = assertAgentModuleLayout(sourceRoot);
  mkdirSync(extractDir, { recursive: true });
  const archiveZip = path.join(path.dirname(extractDir), '_agent-module-archive.zip');
  const archived = gitArchiveAgentModule(sourceRoot, archiveZip);
  let sourceKind = 'git-archive';
  if (archived.status === 0 && existsSync(archiveZip) && statSync(archiveZip).size > 0) {
    expandZip(archiveZip, extractDir);
  } else {
    sourceKind = 'working-tree';
    cpSync(agentModuleDir, extractDir, { recursive: true });
  }
  if (existsSync(archiveZip)) rmSync(archiveZip, { force: true });
  if (!existsSync(path.join(extractDir, 'skills', 'manifest.json'))) {
    failPack('staged agent-module is missing skills/manifest.json');
  }
  return {
    sourceKind,
    skillsManifest,
    capabilities: deriveCapabilities(extractDir, skillsManifest),
  };
}
