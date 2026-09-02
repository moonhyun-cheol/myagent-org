import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const DISABLED = new Set(['0', 'off', 'none', 'false', 'disabled']);

function usable(value) {
  const text = String(value ?? '').trim();
  if (!text || DISABLED.has(text.toLowerCase())) return '';
  return text;
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
  return {
    brand_manual_url: usable(process.env.MY_AGENT_BRAND_MANUAL_URL) || usable(file.brand_manual_url),
    product_data_base_url:
      usable(process.env.MY_AGENT_PRODUCT_DATA_BASE_URL) || usable(file.product_data_base_url),
    nas,
  };
}
