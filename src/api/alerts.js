/**
 * Alerts API module.
 *
 * Verified backend routes from app/api/v1/alerts.py:
 *   - GET /alerts?ward_id=...&patient_id=...&status=...&limit=...&offset=...
 *   - GET /alerts/{alert_id}
 *   - PATCH /alerts/{alert_id}/acknowledge (Roles: Admin, Physician, Nurse)
 *   - PATCH /alerts/{alert_id}/confirm     (Roles: Admin, Physician)
 *   - PATCH /alerts/{alert_id}/dismiss     (Roles: Admin, Physician, Nurse) - requires { reason: string }
 *   - PATCH /alerts/{alert_id}/resolve     (Roles: Admin, Physician)
 */
import { apiFetch } from './client';

/**
 * List alerts with optional filters.
 *
 * @param {object} [params]
 * @param {string} [params.ward_id]
 * @param {string} [params.patient_id]
 * @param {string} [params.status]
 * @param {number} [params.limit]
 * @param {number} [params.offset]
 * @returns {Promise<Array<{ id: string, patient_id: string, prediction_id: string, severity: string, status: string, message: string, created_at: string }>>}
 */
export async function getAlerts(params = {}) {
  const query = new URLSearchParams();
  if (params.ward_id) query.set('ward_id', params.ward_id);
  if (params.patient_id) query.set('patient_id', params.patient_id);
  if (params.status) query.set('status', params.status);
  if (params.limit) query.set('limit', String(params.limit));
  if (params.offset) query.set('offset', String(params.offset));

  const queryString = query.toString() ? `?${query.toString()}` : '';
  return apiFetch(`/alerts${queryString}`);
}

/**
 * Retrieve details for a specific alert by ID.
 *
 * @param {string} alertId
 * @returns {Promise<object>}
 */
export async function getAlert(alertId) {
  return apiFetch(`/alerts/${alertId}`);
}

/**
 * Acknowledge an active alert.
 * HTTP PATCH /alerts/{alert_id}/acknowledge
 * Allowed Roles: Admin, Physician, Nurse
 *
 * @param {string} alertId
 * @returns {Promise<object>}
 */
export async function acknowledgeAlert(alertId) {
  return apiFetch(`/alerts/${alertId}/acknowledge`, {
    method: 'PATCH',
  });
}

/**
 * Confirm an alert.
 * HTTP PATCH /alerts/{alert_id}/confirm
 * Allowed Roles: Admin, Physician
 *
 * @param {string} alertId
 * @returns {Promise<object>}
 */
export async function confirmAlert(alertId) {
  return apiFetch(`/alerts/${alertId}/confirm`, {
    method: 'PATCH',
  });
}

/**
 * Dismiss an alert with a mandatory reason string.
 * HTTP PATCH /alerts/{alert_id}/dismiss
 * Allowed Roles: Admin, Physician, Nurse
 *
 * @param {string} alertId
 * @param {string} reason
 * @returns {Promise<object>}
 */
export async function dismissAlert(alertId, reason) {
  if (!reason || !reason.trim()) {
    throw new Error('A dismiss reason is required.');
  }
  return apiFetch(`/alerts/${alertId}/dismiss`, {
    method: 'PATCH',
    body: JSON.stringify({ reason: reason.trim() }),
  });
}

/**
 * Resolve a confirmed alert.
 * HTTP PATCH /alerts/{alert_id}/resolve
 * Allowed Roles: Admin, Physician
 *
 * @param {string} alertId
 * @returns {Promise<object>}
 */
export async function resolveAlert(alertId) {
  return apiFetch(`/alerts/${alertId}/resolve`, {
    method: 'PATCH',
  });
}
