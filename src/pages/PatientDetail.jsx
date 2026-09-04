import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { RefreshCw, AlertCircle, ArrowLeft, Check, FilePlus } from 'lucide-react';
import { getPatient, getPatientVitals, getPatientLatestPrediction } from '../api/patients';
import { useAuth } from '../context/AuthContext';

export default function PatientDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [patient, setPatient] = useState(null);
  const [vitals, setVitals] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Role gating checks
  const role = user?.role?.toLowerCase() ?? '';
  const canConfirmOrDismiss = role === 'physician' || role === 'admin';
  const canEscalate = role === 'nurse' || role === 'physician' || role === 'admin';

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [ptData, vitalsData, predData] = await Promise.all([
        getPatient(id),
        getPatientVitals(id),
        getPatientLatestPrediction(id),
      ]);
      setPatient(ptData);
      setVitals(vitalsData || []);
      setPrediction(predData);
    } catch (err) {
      setError(err?.message || 'Failed to load patient profile.');
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (isLoading) {
    return (
      <div className="p-12 text-center text-pastel-sub dark:text-pastel-subDark flex items-center justify-center gap-2.5">
        <RefreshCw size={18} className="animate-spin text-pastel-brand" />
        <span>Loading patient data from backend…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-3 rounded-xl bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 text-[13px] mb-4">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
        <div>
          <button
            onClick={loadData}
            className="px-4 py-2 rounded-xl bg-pastel-brand text-white text-[13px] font-medium hover:bg-[#0B5D74] transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!patient) {
    return (
      <div className="p-8 text-center text-pastel-sub dark:text-pastel-subDark">
        <p className="mb-4">Patient profile not found.</p>
        <button className="btn ghost sm" onClick={() => navigate(-1)}>
          <ArrowLeft size={14} className="inline mr-1" /> Back
        </button>
      </div>
    );
  }

  // Formatting helpers for real backend responses
  const initials = patient.name ? patient.name.split(' ').map((n) => n[0]).join('') : 'P';
  const sexFormatted = patient.sex === 'MALE' ? 'M' : patient.sex === 'FEMALE' ? 'F' : patient.sex;
  const wardName = patient.ward?.name || 'Ward';
  const admissionFormatted = patient.admission_date
    ? new Date(patient.admission_date).toLocaleDateString()
    : 'Recently';

  // Real risk_score from backend prediction (0.0 to 1.0)
  const hasScore = prediction?.risk_score != null;
  const riskScore = hasScore ? Math.round(prediction.risk_score * 100) : null;
  const rawTier = prediction?.risk_tier || null;
  const tier = rawTier === 'CRITICAL' || rawTier === 'HIGH' ? 'critical' : rawTier === 'MODERATE' ? 'watch' : rawTier === 'LOW' ? 'stable' : 'unassessed';
  const badgeLabel = rawTier ? rawTier.toLowerCase() : 'no prediction';

  // Format vitals for Recharts line chart (sorted ascending by recorded_at)
  const sortedVitals = [...vitals].sort((a, b) => new Date(a.recorded_at) - new Date(b.recorded_at));
  const vitalsChartData = sortedVitals.map((v) => ({
    t: new Date(v.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    hr: v.heart_rate,
    rr: v.respiratory_rate,
    bp: v.systolic_bp,
    spo2: v.spo2,
    temp: v.temperature,
  }));

  const latestVital = sortedVitals.length > 0 ? sortedVitals[sortedVitals.length - 1] : null;
  const lastVitalsTime = latestVital
    ? new Date(latestVital.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : 'No readings';

  return (
    <>
      <button className="btn ghost sm" style={{ marginBottom: 16 }} onClick={() => navigate(-1)}>
        <i className="ti ti-arrow-left" aria-hidden="true"></i> Back
      </button>

      <div className="flex justify-between items-center" style={{ marginBottom: 20 }}>
        <div className="flex items-center gap-12">
          <div className={`patient-avatar ${tier}`} style={{ width: 48, height: 48, fontSize: 15 }}>{initials}</div>
          <div>
            <h1 className="page-title">{patient.name}</h1>
            <p className="page-sub">
              {patient.bed_number}, {wardName} · {patient.age}{sexFormatted} · admitted {admissionFormatted} · {patient.admission_reason || 'Under observation'}
            </p>
          </div>
        </div>
        <span className={`badge ${tier}`}>{badgeLabel}</span>
      </div>

      <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(4,1fr)' }}>
        <div className="stat-card">
          <p className="stat-label">Risk score</p>
          {hasScore ? (
            <p className={`stat-value ${tier}`}>{riskScore}<span className="stat-unit">/100</span></p>
          ) : (
            <p className="stat-value text-pastel-sub">N/A</p>
          )}
        </div>
        <div className="stat-card">
          <p className="stat-label">Confidence</p>
          <p className="stat-value text-pastel-sub">N/A</p>
        </div>
        <div className="stat-card">
          <p className="stat-label">Last vitals</p>
          <p style={{ fontSize: 15, fontWeight: 500, marginTop: 8 }}>{lastVitalsTime}</p>
        </div>
        <div className="stat-card">
          <p className="stat-label">Trajectory</p>
          <p style={{ fontSize: 13, fontWeight: 500, marginTop: 8, color: tier === 'critical' ? 'var(--trace-critical)' : 'var(--text-secondary)' }}>
            {rawTier ? `${rawTier} Risk` : 'No prediction'}
          </p>
        </div>
      </div>

      <div className="panel" style={{ marginBottom: 16 }}>
        <p className="panel-title">Full vitals history</p>
        {vitalsChartData.length === 0 ? (
          <p className="p-4 text-[13px] text-pastel-sub dark:text-pastel-subDark">No vitals readings recorded yet for this patient.</p>
        ) : (
          <div style={{ height: 240 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={vitalsChartData}>
                <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="t" tick={{ fill: 'var(--text-dim)', fontSize: 11 }} axisLine={{ stroke: 'var(--line)' }} tickLine={false} />
                <YAxis tick={{ fill: 'var(--text-dim)', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: 'var(--bg-card-raised)', border: '1px solid var(--line-strong)', borderRadius: 8, fontSize: 12 }} />
                <Line type="monotone" dataKey="hr" stroke="var(--trace-critical)" strokeWidth={2} dot name="Heart rate" />
                <Line type="monotone" dataKey="rr" stroke="var(--trace-watch)" strokeWidth={2} dot name="Respiratory rate" />
                <Line type="monotone" dataKey="bp" stroke="var(--trace-accent)" strokeWidth={2} dot name="Blood pressure" />
                <Line type="monotone" dataKey="spo2" stroke="var(--trace-stable)" strokeWidth={2} dot name="SpO2" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="panel" style={{ marginBottom: 16 }}>
        <p className="panel-title">Raw readings</p>
        {sortedVitals.length === 0 ? (
          <p className="p-4 text-[13px] text-pastel-sub dark:text-pastel-subDark">No raw readings logged.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th><th>Heart rate</th><th>Resp. rate</th><th>Blood pressure</th><th>SpO2</th><th>Temp</th>
              </tr>
            </thead>
            <tbody>
              {sortedVitals.map((v) => (
                <tr key={v.id}>
                  <td className="mono">{new Date(v.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                  <td className="mono">{v.heart_rate} bpm</td>
                  <td className="mono">{v.respiratory_rate} /min</td>
                  <td className="mono">{v.systolic_bp}/{v.diastolic_bp} mmHg</td>
                  <td className="mono">{v.spo2}%</td>
                  <td className="mono">{v.temperature}°C</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Role-Gated Controls */}
      <div className="flex gap-8">
        <button
          className="btn confirm disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={!canConfirmOrDismiss}
          title={!canConfirmOrDismiss ? 'Only Physicians and Admins can confirm alerts' : ''}
        >
          <Check size={14} className="inline mr-1" /> Confirm alert
        </button>
        <button
          className="btn ghost disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={!canConfirmOrDismiss}
          title={!canConfirmOrDismiss ? 'Only Physicians and Admins can dismiss alerts' : ''}
        >
          Dismiss
        </button>
        <button
          className="btn primary disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={!canEscalate}
        >
          <FilePlus size={14} className="inline mr-1" /> Escalate to physician
        </button>
      </div>
    </>
  );
}
