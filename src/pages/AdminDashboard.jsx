import { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import Topbar from '../components/Topbar';
import { precisionRecallHistory, wardStaffResponse, auditLog } from '../data/mockData';
import { ApiError, NetworkError } from '../api/client';
import { getAuditLog, getAuditLogs } from '../api/auditLogs';
import { createUser } from '../api/auth';
import { useAuth } from '../context/AuthContext';

const EMPTY_USER = {
  email: '',
  staff_id: '',
  full_name: '',
  password: '',
  role_name: 'Nurse',
};

function formatAction(action) {
  return action.replaceAll('_', ' ');
}

function formatDate(value) {
  return new Date(value).toLocaleString();
}

function errorMessage(error, fallback) {
  if (error instanceof NetworkError) return "Can't reach the server. Is the backend running?";
  if (error instanceof ApiError) return `${fallback} (${error.status}): ${error.message}`;
  return fallback;
}

export default function AdminDashboard() {
  const [query, setQuery] = useState('');
  const [auditLogOpen, setAuditLogOpen] = useState(false);
  const { user } = useAuth();
  const [logs, setLogs] = useState([]);
  const [selectedLog, setSelectedLog] = useState(null);
  const [filters, setFilters] = useState({ entity: '', entity_id: '', user_id: '', action: '', limit: 50, offset: 0 });
  const [logsLoading, setLogsLoading] = useState(false);
  const [logsError, setLogsError] = useState(null);
  const [userForm, setUserForm] = useState(EMPTY_USER);
  const [creatingUser, setCreatingUser] = useState(false);
  const [userMessage, setUserMessage] = useState(null);

  const normalizedQuery = query.toLowerCase();
  const filteredAuditLog = auditLog.filter((entry) =>
    entry.event.toLowerCase().includes(normalizedQuery) || entry.actor.toLowerCase().includes(normalizedQuery)
  );
  const filteredLogs = logs.filter((entry) =>
    [entry.action, entry.entity, entry.entity_id, entry.user_id]
      .some((value) => String(value ?? '').toLowerCase().includes(normalizedQuery))
  );

  async function loadLogs(nextFilters = filters) {
    setLogsLoading(true);
    setLogsError(null);
    try {
      setLogs(await getAuditLogs(nextFilters));
    } catch (error) {
      setLogsError(errorMessage(error, 'Unable to load audit logs'));
    } finally {
      setLogsLoading(false);
    }
  }

  useEffect(() => {
    if (user?.role?.toLowerCase() === 'admin') {
      loadLogs();
    }
  }, [user?.role]);

  async function handleLogSelect(id) {
    setLogsError(null);
    try {
      setSelectedLog(await getAuditLog(id));
    } catch (error) {
      setLogsError(errorMessage(error, 'Unable to load audit log details'));
    }
  }

  function updateFilter(event) {
    const { name, value } = event.target;
    setFilters((current) => ({ ...current, [name]: value }));
  }

  async function handleCreateUser(event) {
    event.preventDefault();
    setCreatingUser(true);
    setUserMessage(null);
    try {
      const created = await createUser(userForm);
      setUserMessage({ type: 'success', text: `Created ${created.full_name} (${created.email})` });
      setUserForm(EMPTY_USER);
      await loadLogs();
    } catch (error) {
      setUserMessage({ type: 'error', text: errorMessage(error, 'Unable to create user') });
    } finally {
      setCreatingUser(false);
    }
  }

  if (user?.role?.toLowerCase() !== 'admin') {
    return (
      <>
        <Topbar title="System health" subtitle="Administrator access required" />
        <div className="panel" role="alert">
          <p className="panel-title">Access denied</p>
          <p className="text-sm text-dim">This dashboard is available to administrators only.</p>
        </div>
      </>
    );
  }

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

      <div className="grid-2" style={{ marginBottom: 16 }}>
        <div className="panel">
          <p className="panel-title">Create user</p>
          <form onSubmit={handleCreateUser}>
            {[
              ['email', 'Email', 'email'],
              ['staff_id', 'Staff ID', 'text'],
              ['full_name', 'Full name', 'text'],
              ['password', 'Password', 'password'],
            ].map(([name, label, type]) => (
              <label key={name} className="block text-sm" style={{ marginBottom: 10 }}>
                <span className="text-dim">{label}</span>
                <input
                  name={name}
                  type={type}
                  value={userForm[name]}
                  onChange={(event) => setUserForm((current) => ({ ...current, [name]: event.target.value }))}
                  required
                  minLength={name === 'password' ? 8 : undefined}
                  className="w-full mt-1 px-3 py-2 rounded border border-[var(--line)] bg-[var(--bg-card)]"
                />
              </label>
            ))}
            <label className="block text-sm" style={{ marginBottom: 12 }}>
              <span className="text-dim">Role</span>
              <select
                name="role_name"
                value={userForm.role_name}
                onChange={(event) => setUserForm((current) => ({ ...current, role_name: event.target.value }))}
                className="w-full mt-1 px-3 py-2 rounded border border-[var(--line)] bg-[var(--bg-card)]"
              >
                <option>Admin</option>
                <option>Nurse</option>
                <option>Physician</option>
              </select>
            </label>
            <button className="btn sm" type="submit" disabled={creatingUser}>
              {creatingUser ? 'Creating…' : 'Create user'}
            </button>
            {userMessage && <p className={userMessage.type === 'error' ? 'text-sm text-red-600' : 'text-sm text-green-600'} role="status" style={{ marginTop: 10 }}>{userMessage.text}</p>}
          </form>
        </div>

        <div className="panel">
          <p className="panel-title">Staff response by ward</p>
          {wardStaffResponse.map((w) => (
            <div key={w.ward} className="flex justify-between items-center" style={{ padding: '10px 0', borderBottom: '1px solid var(--line)' }}>
              <span style={{ fontSize: 13 }}>{w.ward}</span>
              <span className="mono text-sm" style={{ color: w.reviewed < 80 ? 'var(--trace-watch)' : 'var(--text-secondary)' }}>
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

      <div className="panel">
        <div className="flex justify-between items-center" style={{ marginBottom: 12 }}>
          <p className="panel-title" style={{ marginBottom: 0 }}>Audit log</p>
          <button className="btn sm" type="button" onClick={() => loadLogs()}>Refresh</button>
        </div>
        <form className="grid-2" onSubmit={(event) => { event.preventDefault(); loadLogs(); }} style={{ marginBottom: 14 }}>
          {[
            ['entity', 'Entity'],
            ['entity_id', 'Entity ID'],
            ['user_id', 'User ID'],
            ['action', 'Action'],
          ].map(([name, label]) => (
            <label key={name} className="text-sm">
              <span className="text-dim">{label}</span>
              <input name={name} value={filters[name]} onChange={updateFilter} className="w-full mt-1 px-3 py-2 rounded border border-[var(--line)] bg-[var(--bg-card)]" />
            </label>
          ))}
          <label className="text-sm">
            <span className="text-dim">Limit</span>
            <input name="limit" type="number" min="1" max="200" value={filters.limit} onChange={updateFilter} className="w-full mt-1 px-3 py-2 rounded border border-[var(--line)] bg-[var(--bg-card)]" />
          </label>
          <label className="text-sm">
            <span className="text-dim">Offset</span>
            <input name="offset" type="number" min="0" value={filters.offset} onChange={updateFilter} className="w-full mt-1 px-3 py-2 rounded border border-[var(--line)] bg-[var(--bg-card)]" />
          </label>
          <button className="btn sm" type="submit">Apply filters</button>
        </form>
        {logsError && <p className="text-sm text-red-600" role="alert">{logsError}</p>}
        {logsLoading ? <p className="text-sm text-dim">Loading audit logs…</p> : filteredLogs.length === 0 ? <p className="text-sm text-dim">No audit logs returned.</p> : filteredLogs.map((entry) => (
          <button key={entry.id} type="button" onClick={() => handleLogSelect(entry.id)} className="block w-full text-left" style={{ padding: '10px 0', borderBottom: '1px solid var(--line)' }}>
            <p style={{ fontSize: 12.5, margin: 0, color: 'var(--text-primary)' }}>{formatAction(entry.action)} · {entry.entity}</p>
            <p className="patient-meta text-dim">{entry.user_id ?? '—'} · {formatDate(entry.created_at)}</p>
          </button>
        ))}
        {selectedLog && (
          <div className="panel" style={{ marginTop: 16 }} aria-label="Audit log details">
            <div className="flex justify-between items-center">
              <p className="panel-title">Audit log detail</p>
              <button className="btn sm" type="button" onClick={() => setSelectedLog(null)}>Close</button>
            </div>
            <p className="text-sm"><strong>Action:</strong> {formatAction(selectedLog.action)}</p>
            <p className="text-sm"><strong>Entity:</strong> {selectedLog.entity}</p>
            <p className="text-sm"><strong>Entity ID:</strong> {selectedLog.entity_id ?? '—'}</p>
            <p className="text-sm"><strong>User ID:</strong> {selectedLog.user_id ?? '—'}</p>
            <p className="text-sm"><strong>Created:</strong> {formatDate(selectedLog.created_at)}</p>
            <p className="text-sm"><strong>IP address:</strong> {selectedLog.ip_address ?? '—'}</p>
          </div>
        )}
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
