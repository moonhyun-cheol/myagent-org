import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const DISABLED = new Set(['0', 'off', 'none', 'false', 'disabled']);

function usable(value) {
  const text = String(value ?? '').trim();
  if (!text || DISABLED.has(text.toLowerCase())) return '';
  if (text.startsWith('_')) return '';
  return text.replace(/\/+$/, '');
}

function hubField(file, key, envKeys = []) {
  const hub = file && typeof file.hub === 'object' && file.hub ? file.hub : {};
  for (const envKey of envKeys) {
    const fromEnv = usable(process.env[envKey]);
    if (fromEnv) return fromEnv;
  }
  return usable(hub[key]) || usable(file[key]);
}

export function loadOperatorConfig(root) {
  const filePath = path.join(root, '_local', 'operator.json');
  let file = {};
  if (existsSync(filePath)) {
    try {
      file = JSON.parse(readFileSync(filePath, 'utf8'));
    } catch {
      file = {};
    }
  }
  const nas = file && typeof file.nas === 'object' && file.nas ? file.nas : {};
  const deploymentPhase = usable(file.deployment_phase) || 'operator_pc';
  return {
    deployment_phase: deploymentPhase,
    openclaw_adapter_base_url: hubField(file, 'openclaw_adapter_base_url', [
      'MY_AGENT_OPENCLAW_ADAPTER_BASE_URL',
      'OPENCLAW_ADAPTER_BASE_URL',
    ]),
    brand_manual_url: hubField(file, 'brand_manual_url', ['MY_AGENT_BRAND_MANUAL_URL']),
    product_data_base_url: hubField(file, 'product_data_base_url', [
      'MY_AGENT_PRODUCT_DATA_BASE_URL',
    ]),
    nas,
  };
}

/** URLs baked into published org module (deploy-overrides + module.json). */
export function operatorHubForPublish(root) {
  const op = loadOperatorConfig(root);
  return {
    deployment_phase: op.deployment_phase,
    openclaw_adapter_base_url: op.openclaw_adapter_base_url,
    brand_manual_url: op.brand_manual_url,
    product_data_base_url: op.product_data_base_url,
  };
}
