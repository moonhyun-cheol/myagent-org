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
    adapter_auth: {
      mode: usable(file?.adapter_auth?.mode) || 'install_bootstrap',
      bootstrap_path: usable(file?.adapter_auth?.bootstrap_path) || '/cqr/adapter/auth/bootstrap',
      bootstrap_key: usable(process.env.MY_AGENT_ADAPTER_BOOTSTRAP_KEY)
        || usable(file?.adapter_auth?.bootstrap_key),
    },
    adapter_progress: {
      request_path: usable(file?.adapter_progress?.request_path) || '/cqr/adapter/request',
      status_path_template: usable(file?.adapter_progress?.status_path_template)
        || '/cqr/adapter/jobs/{job_id}',
      poll_interval_ms: Number(file?.adapter_progress?.poll_interval_ms) || 2500,
      timeout_ms: Number(file?.adapter_progress?.timeout_ms) || 1800000,
    },
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
    adapter_auth: op.adapter_auth,
    adapter_progress: op.adapter_progress,
  };
}
