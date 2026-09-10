import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, AlertCircle, RefreshCw } from 'lucide-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ClinicSidebar } from '../components/clinic/ClinicSidebar';
import { ClinicTopbar } from '../components/clinic/ClinicTopbar';
import { usePatients } from '../hooks/usePatients';
import { createPatient } from '../api/patients';
import { getWards } from '../api/wards';
import { ApiError, NetworkError } from '../api/client';
import { useAuth } from '../context/AuthContext';

const STATUS_CHIP = {
  critical: 'bg-pastel-pinkLight dark:bg-pastel-pinkLightDark text-pastel-pink',
  warning: 'bg-pastel-amberLight dark:bg-pastel-amberLightDark text-pastel-amber',
  stable: 'bg-pastel-tealLight dark:bg-pastel-tealLightDark text-pastel-teal',
  unassessed: 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400',
};

const TIER_ORDER = { CRITICAL: 4, HIGH: 3, MODERATE: 2, LOW: 1 };

function mapRiskTierToStatus(tier) {
  switch (tier?.toUpperCase()) {
    case 'CRITICAL':
    case 'HIGH':
      return { status: 'critical', label: tier === 'CRITICAL' ? 'Critical' : 'High' };
    case 'MODERATE':
      return { status: 'warning', label: 'Watching' };
    case 'LOW':
      return { status: 'stable', label: 'Stable' };
    default:
      return { status: 'unassessed', label: 'Unassessed' };
  }
}

const AVATAR_BG = [
  'bg-pastel-brandLight dark:bg-pastel-brandLightDark text-pastel-brand',
  'bg-pastel-amberLight dark:bg-pastel-amberLightDark text-pastel-amber',
  'bg-pastel-tealLight dark:bg-pastel-tealLightDark text-pastel-teal',
  'bg-pastel-pinkLight dark:bg-pastel-pinkLightDark text-pastel-pink',
];

export default function PatientsPage() {
  const [query, setQuery] = useState('');
  const [form, setForm] = useState({ name: '', age: '', sex: 'MALE', ward_id: '', bed_number: '', admission_date: new Date().toISOString().slice(0, 16), admission_reason: '' });
  const [isCreating, setIsCreating] = useState(false);
  const [formMessage, setFormMessage] = useState(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const { data: rawPatients, isLoading, isError, error, refetch } = usePatients();
  const { data: wards = [], isLoading: wardsLoading } = useQuery({ queryKey: ['wards'], queryFn: getWards });
  const canCreate = ['admin', 'physician'].includes(user?.role?.toLowerCase());

  function errorMessage(err) {
    if (err instanceof NetworkError) return "Can't reach the server. Is the backend running?";
    if (err instanceof ApiError) return `Unable to create patient (${err.status}): ${err.message}`;
    return 'Unable to create patient.';
  }

  async function handleCreate(event) {
    event.preventDefault();
    setIsCreating(true);
    setFormMessage(null);
    try {
      const created = await createPatient({
        ...form,
        age: Number(form.age),
        admission_date: new Date(form.admission_date).toISOString(),
      });
      setFormMessage({ type: 'success', text: `${created.name} was admitted successfully.` });
      setForm((current) => ({ ...current, name: '', age: '', ward_id: '', bed_number: '', admission_reason: '' }));
      await queryClient.invalidateQueries({ queryKey: ['patients'] });
    } catch (err) {
      setFormMessage({ type: 'error', text: errorMessage(err) });
    } finally {
      setIsCreating(false);
    }
  }

  // Map backend PatientListItem (uses real risk_tier from DB)
  const patients = (rawPatients || []).map((p) => {
    const { status, label } = mapRiskTierToStatus(p.risk_tier);
    const room = p.bed_number ? `${p.bed_number} (${p.ward_name || ''})` : (p.ward_name || '');
    return {
      id: p.id,
      name: p.name,
      room,
      status,
      statusLabel: label,
      statusRaw: p.current_status || 'ADMITTED',
      tierRaw: p.risk_tier || 'UNASSESSED',
      tierWeight: TIER_ORDER[p.risk_tier?.toUpperCase()] || 0,
    };
  });

  const filtered = patients
    .filter((p) => p.name.toLowerCase().includes(query.toLowerCase()) || p.room.toLowerCase().includes(query.toLowerCase()))
    .sort((a, b) => b.tierWeight - a.tierWeight);

  return (
    <div className="min-h-screen bg-pastel-bg dark:bg-pastel-bgDark flex transition-colors">
      <ClinicSidebar />
      <div className="flex-1 min-w-0">
        <ClinicTopbar />
        <main className="px-6 pb-8 max-w-[1000px]">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-[19px] font-semibold text-pastel-ink dark:text-pastel-inkDark">All patients</h1>
            <div className="flex items-center gap-2 h-9 px-3.5 rounded-full bg-white dark:bg-pastel-cardDark border border-pastel-brandLight dark:border-pastel-borderDark w-64">
              <Search size={14} className="text-pastel-sub dark:text-pastel-subDark" aria-hidden="true" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Filter by name or room…"
                className="flex-1 bg-transparent text-[13px] text-pastel-ink dark:text-pastel-inkDark outline-none placeholder:text-pastel-sub/70"
              />
            </div>
          </div>
          {canCreate && (
            <div className="mb-4 rounded-2xl bg-white dark:bg-pastel-cardDark p-4 border border-pastel-brandLight dark:border-pastel-borderDark">
              <p className="text-[14px] font-semibold text-pastel-ink dark:text-pastel-inkDark mb-3">Register patient</p>
              <form onSubmit={handleCreate} className="grid grid-cols-2 gap-3">
                {[
                  ['name', 'Full name', 'text'],
                  ['age', 'Age', 'number'],
                  ['bed_number', 'Bed number', 'text'],
                  ['admission_reason', 'Admission reason', 'text'],
                ].map(([name, label, type]) => (
                  <label key={name} className="text-[12px] text-pastel-sub dark:text-pastel-subDark">
                    {label}
                    <input
                      name={name}
                      type={type}
                      min={name === 'age' ? 0 : undefined}
                      value={form[name]}
                      onChange={(event) => setForm((current) => ({ ...current, [name]: event.target.value }))}
                      required
                      className="w-full mt-1 h-9 px-2.5 rounded-lg border border-pastel-brandLight dark:border-pastel-borderDark bg-transparent text-pastel-ink dark:text-pastel-inkDark"
                    />
                  </label>
                ))}
                <label className="text-[12px] text-pastel-sub dark:text-pastel-subDark">
                  Sex
                  <select value={form.sex} onChange={(event) => setForm((current) => ({ ...current, sex: event.target.value }))} className="w-full mt-1 h-9 px-2.5 rounded-lg border border-pastel-brandLight dark:border-pastel-borderDark bg-transparent text-pastel-ink dark:text-pastel-inkDark">
                    <option value="MALE">Male</option>
                    <option value="FEMALE">Female</option>
                    <option value="OTHER">Other</option>
                  </select>
                </label>
                <label className="text-[12px] text-pastel-sub dark:text-pastel-subDark">
                  Ward
                  <select value={form.ward_id} onChange={(event) => setForm((current) => ({ ...current, ward_id: event.target.value }))} required className="w-full mt-1 h-9 px-2.5 rounded-lg border border-pastel-brandLight dark:border-pastel-borderDark bg-transparent text-pastel-ink dark:text-pastel-inkDark" disabled={wardsLoading}>
                    <option value="">Select ward</option>
                    {wards.map((ward) => <option key={ward.id} value={ward.id}>{ward.name}</option>)}
                  </select>
                </label>
                <label className="text-[12px] text-pastel-sub dark:text-pastel-subDark col-span-2">
                  Admission date
                  <input type="datetime-local" value={form.admission_date} onChange={(event) => setForm((current) => ({ ...current, admission_date: event.target.value }))} required className="w-full mt-1 h-9 px-2.5 rounded-lg border border-pastel-brandLight dark:border-pastel-borderDark bg-transparent text-pastel-ink dark:text-pastel-inkDark" />
                </label>
                <div className="col-span-2 flex items-center gap-3">
                  <button type="submit" disabled={isCreating || wardsLoading || wards.length === 0} className="h-9 px-4 rounded-lg bg-pastel-brand text-white text-[12.5px] font-medium disabled:opacity-40">
                    {isCreating ? 'Registering…' : 'Register patient'}
                  </button>
                  {formMessage && <p className={`text-[12px] ${formMessage.type === 'error' ? 'text-red-600' : 'text-green-600'}`} role="status">{formMessage.text}</p>}
                </div>
              </form>
            </div>
          )}

          <div className="rounded-2xl bg-white dark:bg-pastel-cardDark shadow-[0_1px_2px_rgba(27,36,38,0.04),0_8px_20px_rgba(27,36,38,0.05)] dark:shadow-none dark:border dark:border-pastel-borderDark overflow-hidden">
            {/* Loading State */}
            {isLoading && (
              <div className="p-8 text-center text-pastel-sub dark:text-pastel-subDark flex items-center justify-center gap-2 text-[13.5px]">
                <RefreshCw size={16} className="animate-spin text-pastel-brand" />
                <span>Loading patient census from backend…</span>
              </div>
            )}

            {/* Error State */}
            {isError && (
              <div className="p-6 text-center">
                <div className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 text-[13px] mb-3">
                  <AlertCircle size={15} />
                  <span>Failed to load patients ({error?.message || 'Server error'})</span>
                </div>
                <div>
                  <button
                    onClick={() => refetch()}
                    className="px-3.5 py-1.5 rounded-lg bg-pastel-brand text-white text-[12.5px] font-medium hover:bg-[#0B5D74] transition-colors"
                  >
                    Retry
                  </button>
                </div>
              </div>
            )}

            {/* Empty State */}
            {!isLoading && !isError && filtered.length === 0 && (
              <p className="p-6 text-center text-[13.5px] text-pastel-sub dark:text-pastel-subDark">
                {query ? `No patients match "${query}".` : 'No patients registered in the system.'}
              </p>
            )}

            {/* Data List */}
            {!isLoading && !isError && filtered.map((p, i) => (
              <button
                key={p.id}
                onClick={() => navigate(`/patient/${p.id}`)}
                className="w-full flex items-center gap-3 p-3.5 border-b last:border-b-0 border-pastel-bg dark:border-pastel-borderDark hover:bg-pastel-bg/60 dark:hover:bg-white/5 transition-colors text-left"
              >
                <div className={`h-10 w-10 rounded-full flex items-center justify-center text-[12px] font-semibold shrink-0 ${AVATAR_BG[i % 4]}`}>
                  {p.name.split(' ').map((n) => n[0]).join('')}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-[13.5px] font-medium text-pastel-ink dark:text-pastel-inkDark">{p.name}</p>
                  <p className="text-[12px] text-pastel-sub dark:text-pastel-subDark">{p.room} · Status: {p.statusRaw}</p>
                </div>
                <span className="text-[12px] font-mono font-medium text-pastel-ink dark:text-pastel-inkDark px-2 py-0.5 rounded bg-pastel-bg dark:bg-white/5 shrink-0">
                  {p.tierRaw}
                </span>
                <span className={`text-[10.5px] font-semibold px-2.5 py-1 rounded-full shrink-0 ${STATUS_CHIP[p.status]}`}>
                  {p.statusLabel}
                </span>
              </button>
            ))}
          </div>
        </main>
      </div>
    </div>
  );
}
