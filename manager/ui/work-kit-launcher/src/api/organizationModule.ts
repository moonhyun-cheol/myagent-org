import { apiFetch } from './http';

export interface InstalledOrganizationModuleInfo {
  id?: string;
  version?: string;
  update_sequence?: number;
}

export interface OrganizationModuleStatus {
  installed?: InstalledOrganizationModuleInfo | null;
  feed_url?: string | null;
  can_check_remote?: boolean;
}

export interface OrganizationModuleUpdate {
  sequence: number;
  version: string;
  first_install?: boolean;
}

export type OrganizationModuleSyncResult =
  | { status: 'updated'; from: number | null; to: number }
  | { status: 'current'; sequence: number | null }
  | { status: 'unavailable' }
  | { status: 'error'; message: string };

export async function fetchOrganizationModule(): Promise<OrganizationModuleStatus> {
  const res = await apiFetch('/organization-module');
  if (!res.ok) throw new Error(`조직 모듈 상태 실패 (${res.status})`);
  return (await res.json()) as OrganizationModuleStatus;
}

export async function checkOrganizationModule(): Promise<OrganizationModuleUpdate | null> {
  const res = await apiFetch('/organization-module/check', { method: 'POST' });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(
      (data as { message?: string }).message || `조직 모듈 확인 실패 (${res.status})`,
    );
  }
  return (data.update ?? null) as OrganizationModuleUpdate | null;
}

export async function applyOrganizationModule(): Promise<InstalledOrganizationModuleInfo | null> {
  const res = await apiFetch('/organization-module/apply', { method: 'POST' });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(
      (data as { message?: string }).message || `조직 모듈 업데이트 실패 (${res.status})`,
    );
  }
  return ((data as { installed?: InstalledOrganizationModuleInfo }).installed ?? null);
}

function installedSequence(status: OrganizationModuleStatus | null): number | null {
  const seq = status?.installed?.update_sequence;
  return typeof seq === 'number' && Number.isFinite(seq) ? seq : null;
}

/**
 * Check the signed org-module feed through Core and apply the newest skills.
 * Never throws — callers decide whether to surface the result.
 */
export async function syncOrganizationModule(): Promise<OrganizationModuleSyncResult> {
  try {
    const status = await fetchOrganizationModule();
    if (status.can_check_remote !== true) return { status: 'unavailable' };
    const before = installedSequence(status);
    const update = await checkOrganizationModule();
    if (!update) return { status: 'current', sequence: before };
    const installed = await applyOrganizationModule();
    const after = typeof installed?.update_sequence === 'number'
      ? installed.update_sequence
      : update.sequence;
    return { status: 'updated', from: before, to: after };
  } catch (error) {
    return {
      status: 'error',
      message: error instanceof Error ? error.message : '스킬 업데이트 확인 실패',
    };
  }
}

/** Human-readable one-liner for a sync result (Korean UI). */
export function describeOrganizationSync(result: OrganizationModuleSyncResult): string {
  switch (result.status) {
    case 'updated':
      return result.from != null
        ? `스킬을 최신으로 업데이트했습니다 (${result.from} → ${result.to}).`
        : `스킬을 받았습니다 (${result.to}).`;
    case 'current':
      return result.sequence != null
        ? `스킬이 이미 최신입니다 (${result.sequence}).`
        : '스킬이 이미 최신입니다.';
    case 'unavailable':
      return '스킬 업데이트 피드가 연결되지 않아 확인하지 못했습니다.';
    case 'error':
      return `스킬 업데이트 실패: ${result.message}`;
  }
}
