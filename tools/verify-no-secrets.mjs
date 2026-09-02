#!/usr/bin/env node
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const BINARY_EXT = new Set([
  '.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.zip', '.pem', '.pyc', '.woff', '.woff2',
]);

/** Placeholders allowed in docs/examples (not real hosts). */
const ALLOW_LINE = [
  /192\.168\.x\.x/i,
  /hub\.example(?:\.internal)?/i,
  /example\.(?:com|internal)/i,
  /YOUR[_-]?HUB/i,
  /<host>/i,
];

const RULES = [
  {
    name: 'private IPv4',
    re: /\b(?:192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})\b/g,
  },
  {
    name: 'NAS UNC share',
    re: /\\\\(?:Nas|NAS)\\[^\s"'`]+/gi,
  },
  {
    name: 'internal dev path',
    re: /minyoung_coding|my_openclaw_Bulbasaur/gi,
  },
  {
    name: 'internal NAS label',
    re: /공용_시장조사|CQR개발방향/g,
  },
];

function listTrackedFiles() {
  const result = spawnSync('git', ['ls-files', '-z'], { cwd: root, encoding: 'buffer' });
  if (result.status !== 0) {
    throw new Error(result.stderr?.toString() || 'git ls-files failed');
  }
  return result.stdout
    .toString('utf8')
    .split('\0')
    .filter(Boolean)
    .map((rel) => rel.replace(/\//g, path.sep));
}

function lineAllowed(line) {
  if (ALLOW_LINE.some((re) => re.test(line))) return true;
  // Regex / sanitizer references, not real share paths
  if (/re\.sub|privateHostRe|r"\\\\Nas\\\\|\\\\Nas\\\\\[/i.test(line)) return true;
  return false;
}

const SKIP_FILES = new Set([
  'tools/verify-no-secrets.mjs',
  'tools/verify-module-pack.mjs',
]);

function scanFile(rel) {
  const normalized = rel.replace(/\\/g, '/');
  if (SKIP_FILES.has(normalized)) return [];
  const ext = path.extname(rel).toLowerCase();
  if (BINARY_EXT.has(ext)) return [];
  const abs = path.join(root, rel);
  let text;
  try {
    text = readFileSync(abs, 'utf8');
  } catch {
    return [];
  }
  const hits = [];
  for (const line of text.split(/\r?\n/)) {
    if (lineAllowed(line)) continue;
    for (const rule of RULES) {
      rule.re.lastIndex = 0;
      const match = rule.re.exec(line);
      if (match) {
        hits.push({ rule: rule.name, rel, sample: line.trim().slice(0, 120) });
        break;
      }
    }
  }
  return hits;
}

const tracked = listTrackedFiles();
const violations = tracked.flatMap(scanFile);

if (violations.length > 0) {
  console.error('verify-no-secrets: sensitive values in git-tracked files:\n');
  for (const hit of violations) {
    console.error(`  [${hit.rule}] ${hit.rel}`);
    console.error(`    ${hit.sample}\n`);
  }
  console.error('Move secrets to _local/operator.json (gitignored) or operator-config.example.json placeholders.');
  process.exit(1);
}

console.log(`verify-no-secrets: ok (${tracked.length} tracked files)`);
