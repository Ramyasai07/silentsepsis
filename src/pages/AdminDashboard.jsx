import { useState } from 'react';
import Topbar from '../components/Topbar';
import { precisionRecallHistory, wardStaffResponse, auditLog } from '../data/mockData';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

export default function AdminDashboard() {
  const [query, setQuery] = useState('');
  const [auditLogOpen, setAuditLogOpen] = useState(false);
  const filteredAuditLog = auditLog.filter((entry) => {
    const normalizedQuery = query.toLowerCase();
    return entry.event.toLowerCase().includes(normalizedQuery) || entry.actor.toLowerCase().includes(normalizedQuery);
  });

  return (
    <>
      <Topbar title="System health" subtitle="All wards, last 30 days" onSearchChange={setQuery} searchPlaceholder="Search audit entries…" />

      <div className="flex justify-between items-center" style={{ marginBottom: 18 }}>
        <div />
        <button className="btn sm" onClick={() => setAuditLogOpen(true)}>
          <i className="ti ti-file-text" aria-hidden="true"></i> Full audit log
        </button>
      </div>

      <div className="stat-grid">
        <div className="stat-card">
          <p className="stat-label">Alert precision</p>
          <p className="stat-value stable">78<span className="stat-unit">%</span></p>
        </div>
        <div className="stat-card">
          <p className="stat-label">Alert recall</p>
          <p className="stat-value stable">91<span className="stat-unit">%</span></p>
        </div>
        <div className="stat-card">
          <p className="stat-label">Model drift</p>
          <p style={{ fontSize: 15, fontWeight: 500, marginTop: 8, color: 'var(--trace-stable)' }}>Stable</p>
        </div>
        <div className="stat-card">
          <p className="stat-label">Wards live</p>
          <p className="stat-value">3<span className="stat-unit">/3</span></p>
        </div>
      </div>

      <div className="panel" style={{ marginBottom: 16 }}>
        <p className="panel-title">Precision and recall over time</p>
        <div style={{ height: 220 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={precisionRecallHistory}>
              <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="day" tick={{ fill: 'var(--text-dim)', fontSize: 11 }} axisLine={{ stroke: 'var(--line)' }} tickLine={false} />
              <YAxis tick={{ fill: 'var(--text-dim)', fontSize: 11 }} axisLine={false} tickLine={false} domain={[50, 100]} />
              <Tooltip contentStyle={{ background: 'var(--bg-card-raised)', border: '1px solid var(--line-strong)', borderRadius: 8, fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)' }} />
              <Line type="monotone" dataKey="precision" stroke="var(--trace-accent)" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="recall" stroke="var(--trace-stable)" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid-2">
        <div className="panel">
          <p className="panel-title">Staff response by ward</p>
          {wardStaffResponse.map((w) => (
            <div key={w.ward} className="flex justify-between items-center" style={{ padding: '10px 0', borderBottom: '1px solid var(--line)' }}>
              <span style={{ fontSize: 13 }}>{w.ward}</span>
              <span
                className="mono text-sm"
                style={{ color: w.reviewed < 80 ? 'var(--trace-watch)' : 'var(--text-secondary)' }}
              >
                {w.reviewed}% alerts reviewed
              </span>
            </div>
          ))}
        </div>
        <div className="panel">
          <p className="panel-title">Recent audit entries</p>
          {filteredAuditLog.length === 0 && <p className="p-4 text-center text-dim text-sm">No entries found</p>}
          {filteredAuditLog.map((entry, i) => (
            <div key={i} style={{ padding: '10px 0', borderBottom: i < auditLog.length - 1 ? '1px solid var(--line)' : 'none' }}>
              <p style={{ fontSize: 12.5, margin: 0, color: 'var(--text-primary)' }}>{entry.event}</p>
              <p className="patient-meta text-dim">{entry.actor} · {entry.time}</p>
            </div>
          ))}
        </div>
      </div>

      {auditLogOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="audit-log-title"
          onClick={() => setAuditLogOpen(false)}
        >
          <div
            className="panel w-full max-w-2xl"
            style={{ maxHeight: '80vh', overflowY: 'auto', margin: 0, boxShadow: '0 20px 50px rgba(0,0,0,0.25)' }}
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex justify-between items-center" style={{ marginBottom: 16 }}>
              <div>
                <h2 id="audit-log-title" className="panel-title" style={{ marginBottom: 4 }}>Full audit log</h2>
                <p className="patient-meta">Recent system and clinical actions</p>
              </div>
              <button className="icon-btn" onClick={() => setAuditLogOpen(false)} aria-label="Close audit log" title="Close audit log">
                <i className="ti ti-x" aria-hidden="true"></i>
              </button>
            </div>
            <div>
              {auditLog.map((entry, index) => (
                <div
                  key={`${entry.time}-${index}`}
                  className="flex justify-between items-start gap-6"
                  style={{ padding: '12px 0', borderTop: '1px solid var(--line)' }}
                >
                  <div>
                    <p style={{ fontSize: 13, margin: 0, color: 'var(--text-primary)' }}>{entry.event}</p>
                    <p className="patient-meta" style={{ marginTop: 4 }}>{entry.actor}</p>
                  </div>
                  <span className="mono text-dim" style={{ fontSize: 11, whiteSpace: 'nowrap' }}>{entry.time}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
