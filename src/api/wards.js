/**
 * Wards API module.
 *
 * Verified backend routes from app/api/v1/wards.py:
 *   - GET /wards               → list all wards
 *   - GET /wards/{ward_id}     → single ward detail
 *   - GET /wards/{ward_id}/summary → occupancy + alert summary stats
 */
import { apiFetch } from './client';

/**
 * List all configured hospital wards.
 *
 * @returns {Promise<Array<{ id: string, name: string, capacity: number, created_at: string }>>}
 */
export function getWards() {
  return apiFetch('/wards');
}

/**
 * Retrieve details of a specific ward by ID.
 *
 * @param {string} wardId
 * @returns {Promise<{ id: string, name: string, capacity: number, created_at: string }>}
 */
export function getWard(wardId) {
  return apiFetch(`/wards/${wardId}`);
}

/**
 * Retrieve occupancy and alert summary statistics for a ward.
 *
 * All fields are verified against WardSummaryOut schema and
 * get_ward_summary_metrics() / get_summary() implementations.
 *
 * @param {string} wardId
 * @returns {Promise<{
 *   id: string,
 *   name: string,
 *   capacity: number,
 *   occupied_beds: number,
 *   available_beds: number,
 *   ward: string,
 *   activeAlerts: number,
 *   trendingUp: number,
 *   stable: number,
 *   avgConfirmMinutes: number,
 *   riskLoad: number,
 *   totalPatients: number,
 * }>}
 */
export function getWardSummary(wardId) {
  return apiFetch(`/wards/${wardId}/summary`);
}
