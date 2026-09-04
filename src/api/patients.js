/**
 * Patients API module.
 *
 * Interacts with backend patient endpoints:
 *   - GET /patients
 *   - GET /patients/{id}
 *   - GET /patients/{id}/vitals
 *   - GET /patients/{id}/predictions/latest
 */
import { apiFetch } from './client';

/**
 * Fetch list of active patients.
 *
 * @param {object} [params]
 * @param {string} [params.wardId]
 * @param {number} [params.limit]
 * @param {number} [params.offset]
 * @returns {Promise<Array<{ id: string, name: string, ward_name: string, bed_number: string, risk_tier: string|null, current_status: string }>>}
 */
export async function getPatients(params = {}) {
  const query = new URLSearchParams();
  if (params.wardId) query.set('ward_id', params.wardId);
  if (params.limit) query.set('limit', String(params.limit));
  if (params.offset) query.set('offset', String(params.offset));

  const queryString = query.toString() ? `?${query.toString()}` : '';
  return apiFetch(`/patients${queryString}`);
}

/**
 * Fetch patient profile details by ID.
 *
 * @param {string} patientId
 * @returns {Promise<{ id: string, name: string, age: number, sex: string, ward: { id: string, name: string, capacity: number }, bed_number: string, admission_date: string, discharge_date: string|null, discharge_status: string, created_at: string }>}
 */
export async function getPatient(patientId) {
  return apiFetch(`/patients/${patientId}`);
}

/**
 * Fetch vitals history for a patient.
 *
 * @param {string} patientId
 * @returns {Promise<Array<{ id: string, patient_id: string, recorded_by: string, heart_rate: number, respiratory_rate: number, systolic_bp: number, diastolic_bp: number, spo2: number, temperature: number, recorded_at: string, created_at: string }>>}
 */
export async function getPatientVitals(patientId) {
  return apiFetch(`/patients/${patientId}/vitals`);
}

/**
 * Fetch latest risk prediction for a patient.
 *
 * @param {string} patientId
 * @returns {Promise<{ id: string, patient_id: string, vital_reading_id: string, risk_score: number, risk_tier: string, created_at: string, features: Array<{ feature_name: string, contribution: number }> }|null>}
 */
export async function getPatientLatestPrediction(patientId) {
  try {
    return await apiFetch(`/patients/${patientId}/predictions/latest`);
  } catch (err) {
    if (err?.status === 404) return null; // Patient has no prediction yet
    throw err;
  }
}
