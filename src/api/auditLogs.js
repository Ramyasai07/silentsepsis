import { apiFetch } from './client';

export function getAuditLogs(filters = {}) {
  const params = new URLSearchParams();
  const filterKeys = ['entity', 'entity_id', 'user_id', 'action', 'limit', 'offset'];

  filterKeys.forEach((key) => {
    if (filters[key] !== undefined && filters[key] !== '') {
      params.set(key, filters[key]);
    }
  });

  const query = params.toString();
  return apiFetch(`/audit-logs${query ? `?${query}` : ''}`);
}

export function getAuditLog(id) {
  return apiFetch(`/audit-logs/${id}`);
}
