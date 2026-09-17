import { useQuery } from '@tanstack/react-query';
import { getAlerts } from '../api/alerts';
import {
  getPatientLatestPrediction,
  getPatientVitals,
  getPatients,
} from '../api/patients';

const TIER_STATUS = {
  CRITICAL: 'critical',
  HIGH: 'critical',
  MODERATE: 'warning',
  LOW: 'stable',
};

function toPatientView(patient, vitals, prediction, alerts) {
  const tier = prediction?.risk_tier || patient.risk_tier || null;
  const latest = [...(vitals || [])].sort(
    (a, b) => new Date(a.recorded_at) - new Date(b.recorded_at),
  );
  const risk = prediction?.risk_score == null ? null : Math.round(prediction.risk_score * 100);

  return {
    id: patient.id,
    name: patient.name,
    room: patient.bed_number || 'Bed unavailable',
    ward: patient.ward_name || 'Ward unavailable',
    wardId: patient.ward_id,
    age: patient.age,
    sex: patient.sex,
    status: TIER_STATUS[tier] || 'unassessed',
    tier,
    risk,
    vitals: latest.map((v) => ({
      time: v.recorded_at,
      recordedAt: v.recorded_at,
      hr: v.heart_rate,
      rr: v.respiratory_rate,
      systolicBp: v.systolic_bp,
      diastolicBp: v.diastolic_bp,
      spo2: v.spo2,
      temperature: v.temperature,
    })),
    baseline: null,
    prediction,
    alerts: alerts || [],
    features: (prediction?.features || []).map((feature) => ({
      name: feature.feature_name,
      contribution: feature.contribution,
    })),
    certainty: null,
    explanation: prediction
      ? `Latest backend prediction: ${prediction.risk_tier}.`
      : 'No backend prediction is available.',
    annotation: null,
    timeToIntervention: null,
    lastVitals: latest.at(-1)?.recorded_at || null,
  };
}

async function fetchClinicalPatients() {
  const patients = await getPatients();
  return Promise.all(
    patients.map(async (patient) => {
      const [vitals, prediction, alerts] = await Promise.all([
        getPatientVitals(patient.id),
        getPatientLatestPrediction(patient.id),
        getAlerts({ patient_id: patient.id }),
      ]);
      return toPatientView(patient, vitals, prediction, alerts);
    }),
  );
}

export function useClinicalPatients() {
  return useQuery({
    queryKey: ['clinical-patients'],
    queryFn: fetchClinicalPatients,
    staleTime: 15_000,
  });
}
