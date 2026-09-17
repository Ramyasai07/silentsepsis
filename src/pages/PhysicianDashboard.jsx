import { useState, useEffect } from 'react';
import Topbar from '../components/Topbar';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useClinicalPatients } from '../hooks/useClinicalPatients';

export default function PhysicianDashboard() {
  const { data: patients = [], isLoading, error } = useClinicalPatients();
  const escalated = patients.filter((p) => ['CRITICAL', 'HIGH'].includes(p.tier));
  const [selectedId, setSelectedId] = useState(null);
  const [query, setQuery] = useState('');
  useEffect(() => {
    if (!selectedId && escalated.length > 0) setSelectedId(escalated[0].id);
  }, [selectedId, escalated]);
  const patient = patients.find((p) => p.id === selectedId);
  const filteredEscalated = escalated.filter((p) =>
    p.name.toLowerCase().includes(query.toLowerCase()) || p.id.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div>
      <Topbar title="Escalated cases" subtitle="Confirmed by nursing staff, sorted by risk" onSearchChange={setQuery} searchPlaceholder="Search patients…" />

      <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', gap: 18 }}>
        <div className="panel" style={{ padding: 8 }}>
          {isLoading && <p className="p-4 text-center text-dim text-sm">Loading patients…</p>}
          {error && <p className="p-4 text-center text-red-600 text-sm">Unable to load patients: {error.message}</p>}
          {filteredEscalated.length === 0 && <p className="p-4 text-center text-dim text-sm">No patients found</p>}
          {filteredEscalated.map((p) => (
            <div
              key={p.id}
              onClick={() => setSelectedId(p.id)}
              style={{
                padding: '10px 12px',
                borderRadius: 8,
                cursor: 'pointer',
                marginBottom: 4,
                background: p.id === selectedId ? 'var(--bg-card-raised)' : 'transparent',
                boxShadow: p.id === selectedId ? '0 0 0 1px var(--line-strong) inset' : 'none',
              }}
            >
              <div className="flex justify-between items-center">
                <span style={{ fontSize: 13, fontWeight: 500 }}>{p.name}</span>
                <span className={`badge ${p.tier}`} style={{ fontSize: 9 }}>{p.tier === 'critical' ? 'high' : 'watch'}</span>
              </div>
              <p className="patient-meta">{p.bed}, {p.ward}</p>
            </div>
          ))}
        </div>

        <div>
          {!patient && !isLoading && <div className="panel"><p className="text-dim text-sm">No high-risk backend predictions are available.</p></div>}
          {patient && (
          <div>
          <div className="panel" style={{ marginBottom: 16 }}>
            <div className="flex justify-between items-center" style={{ marginBottom: 16 }}>
              <div className="flex items-center gap-12">
                <div className={`patient-avatar ${patient.status}`} style={{ width: 40, height: 40 }}>{patient.name.split(' ').map((part) => part[0]).join('').slice(0, 2)}</div>
                <div>
                  <p style={{ fontWeight: 600, fontSize: 15, margin: 0 }}>{patient.name} — {patient.room}, {patient.ward}</p>
                  <p className="patient-meta">{patient.age ?? '—'}{patient.sex || ''}</p>
                </div>
              </div>
              <button className="btn primary sm">
                <i className="ti ti-file-plus" aria-hidden="true"></i> Escalate and order workup
              </button>
            </div>

            <div className="grid-3">
              <div className="stat-card" style={{ padding: 12 }}>
                <p className="stat-label">Risk score</p>
                <p className={`stat-value ${patient.status}`} style={{ fontSize: 22 }}>{patient.risk ?? '—'}<span className="stat-unit">/100</span></p>
              </div>
              <div className="stat-card" style={{ padding: 12 }}>
                <p className="stat-label">Confidence interval</p>
                <p className="stat-value text-dim" style={{ fontSize: 22 }}>N/A</p>
              </div>
              <div className="stat-card" style={{ padding: 12 }}>
                <p className="stat-label">Projected trajectory</p>
                <p style={{ fontSize: 14, fontWeight: 500, marginTop: 8, color: patient.status === 'critical' ? 'var(--trace-critical)' : 'var(--trace-watch)' }}>
                  Not provided by backend
                </p>
              </div>
            </div>
          </div>

          <div className="panel" style={{ marginBottom: 16 }}>
            <p className="panel-title">Vitals trend, last 12 hours</p>
            <div style={{ height: 200 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={patient.vitals}>
                  <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="time" tick={{ fill: 'var(--text-dim)', fontSize: 11 }} axisLine={{ stroke: 'var(--line)' }} tickLine={false} />
                  <YAxis tick={{ fill: 'var(--text-dim)', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: 'var(--bg-card-raised)', border: '1px solid var(--line-strong)', borderRadius: 8, fontSize: 12 }} />
                  <Line type="monotone" dataKey="hr" stroke="var(--trace-critical)" strokeWidth={2} dot={false} name="Heart rate" />
                  <Line type="monotone" dataKey="rr" stroke="var(--trace-watch)" strokeWidth={2} dot={false} name="Respiratory rate" />
                  <Line type="monotone" dataKey="spo2" stroke="var(--trace-accent)" strokeWidth={2} dot={false} name="SpO2" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="panel">
            <p className="panel-title">Why the model flagged this patient</p>
            {patient.features.length === 0 && <p className="text-dim text-sm">No significant feature contributions.</p>}
            {patient.features.map((f) => (
              <div key={f.name} className="flex justify-between items-center" style={{ padding: '9px 0', borderBottom: '1px solid var(--line)' }}>
                <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{f.name}</span>
                <div className="flex items-center gap-8">
                  <div style={{ width: 90, height: 6, background: 'var(--bg-panel)', borderRadius: 3 }}>
                    <div style={{ width: `${Math.min(100, Math.abs(f.contribution))}%`, height: '100%', borderRadius: 3, background: 'var(--trace-critical)' }} />
                  </div>
                  <span className="text-dim text-sm mono">{f.contribution > 0 ? '+' : ''}{f.contribution}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
        )}
        </div>
      </div>
      </div>
  );
}
