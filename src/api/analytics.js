/**
 * Analytics API module.
 *
 * Verified backend routes from app/api/v1/analytics.py & app/api/v1/wards.py:
 *   - GET /analytics/precision-recall-history?days=30&bucket_size_days=5
 *   - GET /analytics/staff-response-by-ward?days=30
 *   - GET /wards/{ward_id}/summary
 */
import { apiFetch } from './client';

/**
 * Retrieve historical precision and recall metrics.
 *
 * @param {object} [params]
 * @param {number} [params.days]             - default 30
 * @param {number} [params.bucket_size_days] - default 5
 * @returns {Promise<Array<{ day: string, precision: number|null, recall: number|null }>>}
 */
export async function getPrecisionRecallHistory(params = {}) {
  const query = new URLSearchParams();
  if (params.days) query.set('days', String(params.days));
  if (params.bucket_size_days) query.set('bucket_size_days', String(params.bucket_size_days));

  const queryString = query.toString() ? `?${query.toString()}` : '';
  return apiFetch(`/analytics/precision-recall-history${queryString}`);
}

/**
 * Retrieve staff response time / review rate grouped by ward.
 *
 * @param {object} [params]
 * @param {number} [params.days] - default 30
 * @returns {Promise<Array<{ ward: string, reviewed: number }>>}
 */
export async function getStaffResponseByWard(params = {}) {
  const query = new URLSearchParams();
  if (params.days) query.set('days', String(params.days));

  const queryString = query.toString() ? `?${query.toString()}` : '';
  return apiFetch(`/analytics/staff-response-by-ward${queryString}`);
}

/**
 * Retrieve occupancy and alert summary statistics for a ward.
 *
 * @param {string} wardId
 * @returns {Promise<{ id: string, name: string, capacity: number, occupied_beds: number, available_beds: number, ward: string, activeAlerts: number, trendingUp: number, stable: number, avgConfirmMinutes: number, riskLoad: number, totalPatients: number }>}
 */
export async function getWardSummary(wardId) {
  return apiFetch(`/wards/${wardId}/summary`);
}
