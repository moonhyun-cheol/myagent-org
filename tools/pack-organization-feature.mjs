/**
 * Pack a signed Organization Feature ZIP (Core contract:
 * my-agent-organization-feature/v1 + my-agent-organization-feature-payload/v1).
 */
import {
  cpSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
} from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import {
  createSignedEnvelope,
  sha256Bytes,
  sha256File,
  verifySignedEnvelope,
} from './update/update-signing.mjs';

export const FEATURE_JSON_SCHEMA = 'my-agent-organization-feature/v1';
export const FEATURE_PAYLOAD_SCHEMA = 'my-agent-organization-feature-payload/v1';
export const AUTOMATON_FEATURE_ID = 'org.cqr.automaton-routing';
export const FEATURE_PACKS_ROOT = 'feature-packs';

export function failFeaturePack(message) {
  throw new Error(message);
}

function quotePs(value) {
  return String(value).replace(/'/g, "''");
}

function walkFiles(dir, prefix = '') {
  const out = [];
  for (const ent of readdirSync(dir, { withFileTypes: true })) {
    const abs = path.join(dir, ent.name);
    const rel = prefix ? `${prefix}/${ent.name}` : ent.name;
    if (ent.isDirectory()) {
      out.push(...walkFiles(abs, rel.replaceAll('\\', '/')));
      continue;
    }
    if (ent.name === 'update-payload.json') continue;
    out.push({
      path: rel.replaceAll('\\', '/'),
      size: statSync(abs).size,
      sha256: sha256File(abs),
    });
  }
  return out.sort((a, b) => a.path.localeCompare(b.path));
}

function zipDirectory(sourceDir, zipPath) {
  if (existsSync(zipPath)) rmSync(zipPath, { force: true });
  const zip = spawnSync(
    'powershell',
    [
      '-NoProfile',
      '-Command',
      [
        "$ErrorActionPreference = 'Stop'",
        'Add-Type -AssemblyName System.IO.Compression.FileSystem',
        `[IO.Compression.ZipFile]::CreateFromDirectory('${quotePs(sourceDir)}', '${quotePs(zipPath)}', [IO.Compression.CompressionLevel]::Optimal, $false, [Text.Encoding]::UTF8)`,
      ].join('; '),
    ],
    { encoding: 'utf8' },
  );
  if (zip.status !== 0 || !existsSync(zipPath)) {
    failFeaturePack(zip.stderr?.toString().trim() || `feature zip missing: ${zipPath}`);
  }
}

/**
 * @param {object} opts
 * @param {string} opts.sourceRoot
 * @param {string} opts.featurePackDir relative under sourceRoot, e.g. feature-packs/automaton-routing
 * @param {string} opts.outZipPath
 * @param {string} opts.privateKeyPem
 * @param {string} opts.publicKeyPem
 * @param {object} [opts.hub] operator hub injection for adapter-connection
 */
export function packSignedOrganizationFeature(opts) {
  const {
    sourceRoot,
    featurePackDir,
    outZipPath,
    privateKeyPem,
    publicKeyPem,
    hub,
  } = opts;
  const authoring = path.join(sourceRoot, featurePackDir);
  if (!existsSync(path.join(authoring, 'feature.json'))) {
    failFeaturePack(`missing feature.json in ${featurePackDir}`);
  }
  const featureJson = JSON.parse(readFileSync(path.join(authoring, 'feature.json'), 'utf8'));
  if (featureJson.schema !== FEATURE_JSON_SCHEMA) {
    failFeaturePack(`unsupported feature.json schema: ${featureJson.schema}`);
  }
  const featureId = String(featureJson.id ?? '').trim();
  if (!featureId) failFeaturePack('feature.json id required');

  const stageParent = path.join(path.dirname(outZipPath), `_feature-stage-${featureId.replaceAll('.', '-')}`);
  if (existsSync(stageParent)) rmSync(stageParent, { recursive: true, force: true });
  mkdirSync(stageParent, { recursive: true });

  try {
    // Copy authoring files except template/docs that are not runtime entrypoints.
    for (const name of readdirSync(authoring)) {
      if (name === 'AUTOMATON.md') continue;
      const abs = path.join(authoring, name);
      if (statSync(abs).isDirectory()) continue;
      if (name === 'adapter-connection.template.json') continue;
      cpSync(abs, path.join(stageParent, name));
    }

    const templatePath = path.join(authoring, 'adapter-connection.template.json');
    if (!existsSync(templatePath)) {
      failFeaturePack('adapter-connection.template.json is required');
    }
    const adapterConnection = JSON.parse(readFileSync(templatePath, 'utf8'));
    if (hub) {
      adapterConnection.base_url = hub.openclaw_adapter_base_url || '';
      adapterConnection.transport = {
        ...adapterConnection.transport,
        ...hub.adapter_progress,
      };
      adapterConnection.authentication = {
        ...adapterConnection.authentication,
        mode: hub.adapter_auth?.mode || 'install_bootstrap',
        bootstrap_path: hub.adapter_auth?.bootstrap_path || '/cqr/adapter/auth/bootstrap',
      };
      if (hub.adapter_auth?.bootstrap_key) {
        adapterConnection.authentication.bootstrap_key = hub.adapter_auth.bootstrap_key;
      }
    }
    writeFileSync(
      path.join(stageParent, 'adapter-connection.json'),
      `${JSON.stringify(adapterConnection, null, 2)}\n`,
      'utf8',
    );

    const deployOverridesPath = path.join(stageParent, 'deploy-overrides.json');
    if (existsSync(deployOverridesPath) && hub) {
      let deployOverrides = {};
      try {
        deployOverrides = JSON.parse(readFileSync(deployOverridesPath, 'utf8'));
      } catch {
        deployOverrides = {};
      }
      const patched = {
        ...deployOverrides,
        openclaw_fallback_local: false,
        deployment_phase: hub.deployment_phase,
      };
      if (hub.openclaw_adapter_base_url) {
        patched.openclaw_adapter_base_url = hub.openclaw_adapter_base_url;
      }
      writeFileSync(deployOverridesPath, `${JSON.stringify(patched, null, 2)}\n`, 'utf8');
    }

    // Ensure feature.json matches packed identity.
    writeFileSync(
      path.join(stageParent, 'feature.json'),
      `${JSON.stringify(featureJson, null, 2)}\n`,
      'utf8',
    );

    const files = walkFiles(stageParent);
    const payload = {
      schema: FEATURE_PAYLOAD_SCHEMA,
      feature_id: featureId,
      version: featureJson.version,
      update_sequence: featureJson.update_sequence,
      files,
    };
    const envelope = createSignedEnvelope(payload, privateKeyPem);
    if (!verifySignedEnvelope(envelope, publicKeyPem)) {
      failFeaturePack('feature payload signature verification failed');
    }
    writeFileSync(
      path.join(stageParent, 'update-payload.json'),
      `${JSON.stringify(envelope, null, 2)}\n`,
      'utf8',
    );

    mkdirSync(path.dirname(outZipPath), { recursive: true });
    zipDirectory(stageParent, outZipPath);
    return {
      featureId,
      version: featureJson.version,
      update_sequence: featureJson.update_sequence,
      outZipPath,
      size: statSync(outZipPath).size,
      sha256: sha256File(outZipPath),
      inventory: files.map((f) => f.path),
    };
  } finally {
    if (existsSync(stageParent)) rmSync(stageParent, { recursive: true, force: true });
  }
}

export function resolveAutomatonFeatureAuthoring(sourceRoot) {
  return path.join(sourceRoot, FEATURE_PACKS_ROOT, 'automaton-routing');
}

/** Build lightweight slash index entries from the Automaton tools manifest. */
export function buildOptionalSlashIndexFromManifest(manifest) {
  const messageKo =
    '이 명령은 「CQR 명령어 모음」 Work Kit을 적용해야 사용할 수 있습니다. MY Agent 관리자에서 받은 뒤 적용하세요.';
  const slashes = [];
  for (const tool of manifest.tools ?? []) {
    for (const prefix of tool.slash_prefixes ?? []) {
      slashes.push({
        prefix,
        feature_id: AUTOMATON_FEATURE_ID,
        message_ko: messageKo,
      });
    }
  }
  return { version: 1, slashes };
}

export { sha256Bytes };
