import { useState } from 'react';
import Topbar from '../components/Topbar';
import { patients } from '../data/mockData';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const escalated = patients.filter((p) => p.tier !== 'stable');

export default function PhysicianDashboard() {
  const [selectedId, setSelectedId] = useState(escalated[0].id);
  const patient = patients.find((p) => p.id === selectedId);

  return (
    <>
      <Topbar title="Escalated cases" subtitle="Confirmed by nursing staff, sorted by risk" />

      <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', gap: 18 }}>
        <div className="panel" style={{ padding: 8 }}>
          {escalated.map((p) => (
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
          <div className="panel" style={{ marginBottom: 16 }}>
            <div className="flex justify-between items-center" style={{ marginBottom: 16 }}>
              <div className="flex items-center gap-12">
                <div className={`patient-avatar ${patient.tier}`} style={{ width: 40, height: 40 }}>{patient.initials}</div>
                <div>
                  <p style={{ fontWeight: 600, fontSize: 15, margin: 0 }}>{patient.name} — {patient.bed}, {patient.ward}</p>
                  <p className="patient-meta">{patient.age}{patient.sex}, admitted {patient.admitted} · {patient.note}</p>
                </div>
              </div>
              <button className="btn primary sm">
                <i className="ti ti-file-plus" aria-hidden="true"></i> Escalate and order workup
              </button>
            </div>

            <div className="grid-3">
              <div className="stat-card" style={{ padding: 12 }}>
                <p className="stat-label">Risk score</p>
                <p className={`stat-value ${patient.tier}`} style={{ fontSize: 22 }}>{patient.risk}<span className="stat-unit">/100</span></p>
              </div>
              <div className="stat-card" style={{ padding: 12 }}>
                <p className="stat-label">Confidence interval</p>
                <p className="stat-value text-dim" style={{ fontSize: 22 }}>N/A</p>
              </div>
              <div className="stat-card" style={{ padding: 12 }}>
                <p className="stat-label">Projected trajectory</p>
                <p style={{ fontSize: 14, fontWeight: 500, marginTop: 8, color: patient.tier === 'critical' ? 'var(--trace-critical)' : 'var(--trace-watch)' }}>
                  {patient.trajectory}
                </p>
              </div>
            </div>
          </div>

          <div className="panel" style={{ marginBottom: 16 }}>
            <p className="panel-title">Vitals trend, last 12 hours</p>
            <div style={{ height: 200 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={patient.vitalsHistory}>
                  <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="t" tick={{ fill: 'var(--text-dim)', fontSize: 11 }} axisLine={{ stroke: 'var(--line)' }} tickLine={false} />
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
                    <div style={{ width: `${f.weight * 100}%`, height: '100%', borderRadius: 3, background: 'var(--trace-critical)' }} />
                  </div>
                  <span className="text-dim text-sm mono">{Math.round(f.weight * 100)}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
