import { readFileSync } from 'node:fs';
import path from 'node:path';

const REPOSITORY_RE = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
const SAFE_REF_RE = /^(?!-)(?!.*\.\.)[^\s~^:?*\[\\]+$/;

function requireHttpsBaseUrl(value, label) {
  let url;
  try {
    url = new URL(String(value ?? '').trim());
  } catch {
    throw new Error(`${label} must be an absolute HTTPS URL`);
  }
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash) {
    throw new Error(`${label} must be a credential-free HTTPS URL`);
  }
  if (url.pathname !== '/' && url.pathname !== '') {
    throw new Error(`${label} must not contain a path`);
  }
  return url.origin;
}

export function validateRepository(value) {
  const repository = String(value ?? '').trim();
  if (!REPOSITORY_RE.test(repository)) throw new Error('repository must use owner/name format');
  return repository;
}

export function validateRef(value, label = 'ref') {
  const ref = String(value ?? '').trim();
  if (!ref || !SAFE_REF_RE.test(ref)) throw new Error(`${label} is unsafe`);
  return ref;
}

export function validateAssetName(value) {
  const name = String(value ?? '').trim();
  if (!name || path.basename(name) !== name || name.includes('/') || name.includes('\\')) {
    throw new Error('asset name must be a file name');
  }
  return name;
}

export function validateRepoPath(value) {
  const repoPath = String(value ?? '').replaceAll('\\', '/').replace(/^\/+/, '');
  if (!repoPath || repoPath.split('/').some((part) => !part || part === '.' || part === '..')) {
    throw new Error('repository path is unsafe');
  }
  return repoPath;
}

export function validateReleaseTarget(input, label = 'release target') {
  if (!input || typeof input !== 'object') throw new Error(`${label} is required`);
  const provider = String(input.provider ?? '').trim().toLowerCase();
  if (!['github', 'gitea'].includes(provider)) {
    throw new Error(`${label}.provider must be github or gitea`);
  }
  const target = {
    provider,
    base_url: requireHttpsBaseUrl(input.base_url, `${label}.base_url`),
    repository: validateRepository(input.repository),
    default_branch: validateRef(input.default_branch || 'main', `${label}.default_branch`),
  };
  if (provider === 'github') {
    target.raw_base_url = requireHttpsBaseUrl(
      input.raw_base_url || 'https://raw.githubusercontent.com',
      `${label}.raw_base_url`,
    );
  }
  return target;
}

export function loadReleaseTargets(root) {
  const filePath = path.join(root, 'release-targets.json');
  const document = JSON.parse(readFileSync(filePath, 'utf8'));
  if (document.schema !== 'my-agent-release-targets/v1') {
    throw new Error('unsupported release-targets.json schema');
  }
  if (!['mirror', 'bridge', 'primary'].includes(document.migration_phase)) {
    throw new Error('migration_phase must be mirror, bridge, or primary');
  }
  return {
    schema: document.schema,
    migration_phase: document.migration_phase,
    primary: validateReleaseTarget(document.primary, 'primary'),
    legacy: validateReleaseTarget(document.legacy, 'legacy'),
  };
}

export function rawFileUrl(targetInput, relativePath) {
  const target = validateReleaseTarget(targetInput);
  const repoPath = validateRepoPath(relativePath)
    .split('/')
    .map(encodeURIComponent)
    .join('/');
  const repository = target.repository.split('/').map(encodeURIComponent).join('/');
  const branch = encodeURIComponent(target.default_branch);
  if (target.provider === 'gitea') {
    return `${target.base_url}/${repository}/raw/branch/${branch}/${repoPath}`;
  }
  return `${target.raw_base_url}/${repository}/${branch}/${repoPath}`;
}

export function releaseAssetUrl(targetInput, releaseTag, assetName) {
  const target = validateReleaseTarget(targetInput);
  const repository = target.repository.split('/').map(encodeURIComponent).join('/');
  return `${target.base_url}/${repository}/releases/download/`
    + `${encodeURIComponent(validateRef(releaseTag, 'release tag'))}/`
    + encodeURIComponent(validateAssetName(assetName));
}

export function giteaApiUrl(targetInput, relativePath = '') {
  const target = validateReleaseTarget(targetInput);
  if (target.provider !== 'gitea') throw new Error('Gitea API requires a gitea release target');
  const suffix = String(relativePath).replace(/^\/+/, '');
  return `${target.base_url}/api/v1${suffix ? `/${suffix}` : ''}`;
}
