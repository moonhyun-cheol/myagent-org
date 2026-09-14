#!/usr/bin/env node
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  compareSemVer,
  parseSemVer,
  validateLauncherVersionState,
  validateUpdateProgression,
} from './update/github-release-plan.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const manifest = JSON.parse(readFileSync(path.join(root, 'launcher-manifest.json'), 'utf8'));
const pkg = JSON.parse(readFileSync(path.join(root, 'ui', 'work-kit-launcher', 'package.json'), 'utf8'));
const lock = JSON.parse(readFileSync(path.join(root, 'ui', 'work-kit-launcher', 'package-lock.json'), 'utf8'));
const csproj = readFileSync(path.join(root, 'shell', 'WorkKitLauncher', 'WorkKitLauncher.csproj'), 'utf8');

assert.equal(compareSemVer('1.0.11', '1.0.10'), 1);
assert.equal(compareSemVer('1.0.10', '1.0.10'), 0);
assert.throws(() => parseSemVer('v1.0.11'), /invalid SemVer/);
assert.equal(validateLauncherVersionState({
  manifestVersion: manifest.version,
  packageVersion: pkg.version,
  lockVersion: lock.version,
  lockRootVersion: lock.packages?.['']?.version,
  csprojVersion: /<Version>([^<]+)<\/Version>/.exec(csproj)?.[1],
  assemblyVersion: /<AssemblyVersion>([^<]+)<\/AssemblyVersion>/.exec(csproj)?.[1],
  fileVersion: /<FileVersion>([^<]+)<\/FileVersion>/.exec(csproj)?.[1],
}), manifest.version);
assert.throws(() => validateLauncherVersionState({
  manifestVersion: '1.0.10',
  packageVersion: '1.0.6',
  lockVersion: '1.0.10',
  lockRootVersion: '1.0.10',
  csprojVersion: '1.0.10',
  assemblyVersion: '1.0.10.0',
  fileVersion: '1.0.10.0',
}), /version mismatch/);

const currentFeed = {
  document: {
    update_sequence: 5,
    version: '1.0.10',
    channel: 'stable',
    asset: { repository: 'moonhyun-cheol/myagent-org' },
  },
};
assert.equal(validateUpdateProgression({
  currentFeed,
  nextSequence: 6,
  nextVersion: '1.0.11',
  expectedChannel: 'stable',
  expectedRepository: 'moonhyun-cheol/myagent-org',
}), 'next-update');
assert.throws(() => validateUpdateProgression({ currentFeed, nextSequence: 7, nextVersion: '1.0.11' }), /exactly 6/);
assert.throws(() => validateUpdateProgression({ currentFeed, nextSequence: 6, nextVersion: '1.0.9' }), /rollback/);
assert.equal(validateUpdateProgression({
  currentFeed,
  nextSequence: 5,
  nextVersion: '1.0.10',
  resume: true,
}), 'resume-current');
assert.throws(() => validateUpdateProgression({
  currentFeed,
  nextSequence: 5,
  nextVersion: '1.0.11',
  resume: true,
}), /already-published version/);
assert.throws(() => validateUpdateProgression({ currentFeed: null, nextSequence: 2, nextVersion: '1.0.0' }), /must be 1/);

console.log('verify-launcher-version-policy: ok');
