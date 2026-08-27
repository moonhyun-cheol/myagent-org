#!/usr/bin/env node
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const manifest = JSON.parse(readFileSync(path.join(root, 'manifest.json'), 'utf8'));
const target = JSON.parse(readFileSync(path.join(root, 'repo-target.json'), 'utf8'));
const versionText = readFileSync(path.join(root, 'VERSION.txt'), 'utf8').replace(/\r\n/g, '\n');
const expected = [
  `MY Agent organization-module ${manifest.update_channel} v${manifest.version}`,
  `update_sequence: ${manifest.update_sequence}`,
  `channel: ${manifest.update_channel}`,
  '',
].join('\n');
const mismatches = [];
if (target.version !== manifest.version) mismatches.push(`version ${target.version} != ${manifest.version}`);
if (Number(target.update_sequence) !== Number(manifest.update_sequence)) {
  mismatches.push(`update_sequence ${target.update_sequence} != ${manifest.update_sequence}`);
}
if (target.github !== manifest.update_repository) {
  mismatches.push(`github ${target.github} != ${manifest.update_repository}`);
}
if (versionText !== expected) mismatches.push('VERSION.txt');
if (mismatches.length) {
  console.error('verify-repo-target FAILED:', mismatches.join('; '));
  process.exit(1);
}
console.log(`verify-repo-target: ok ${target.role} ${target.version} seq ${target.update_sequence} (${target.github})`);
