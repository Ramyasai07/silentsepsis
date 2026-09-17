import { useState, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search } from 'lucide-react';
import { ClinicSidebar } from '../components/clinic/ClinicSidebar';
import { ClinicTopbar } from '../components/clinic/ClinicTopbar';
import { buildTimeline } from '../lib/buildTimeline';
import { useAppStore } from '../store/useAppStore';
import { useClinicalPatients } from '../hooks/useClinicalPatients';

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'vitals', label: 'Vitals' },
  { key: 'annotation', label: 'AI trend' },
  { key: 'action', label: 'Actions' },
];

function timeAgo(date) {
  const mins = Math.round((Date.now() - date.getTime()) / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  return `${(mins / 60).toFixed(1)}h ago`;
}

export default function PatientTimeline() {
  const { data: patients = [], isLoading, error } = useClinicalPatients();
  const [patientId, setPatientId] = useState(null);
  const [filter, setFilter] = useState('all');
  const [query, setQuery] = useState('');
  const [expandedId, setExpandedId] = useState(null);
  const auditLog = useAppStore((s) => s.auditLog);
  useEffect(() => {
    if (!patientId && patients.length > 0) setPatientId(patients[0].id);
  }, [patientId, patients]);

  const patient = patients.find((p) => p.id === patientId);
  const events = useMemo(() => patient ? buildTimeline(patient, auditLog) : [], [patient, auditLog]);

  const filtered = events.filter((e) => {
    const matchesFilter =
      filter === 'all' ||
      (filter === 'action' && ['acknowledge', 'dismiss', 'vitals_entry', 'escalate'].includes(e.type)) ||
      e.type === filter;
    const matchesQuery = !query || e.detail.toLowerCase().includes(query.toLowerCase());
    return matchesFilter && matchesQuery;
  });

  return (
    <div className="min-h-screen bg-pastel-bg dark:bg-pastel-bgDark flex transition-colors">
      <ClinicSidebar />
      <div className="flex-1 min-w-0">
        <ClinicTopbar />
        <main className="px-6 pb-8 max-w-[760px]">
          <h1 className="text-[19px] font-semibold text-pastel-ink dark:text-pastel-inkDark mb-0.5">Patient timeline</h1>
          <p className="text-[13px] text-pastel-sub dark:text-pastel-subDark mb-4">The patient's story, chronologically — vitals, AI detections, and every nurse action, in one thread.</p>

          <div className="flex items-center gap-2 mb-4 flex-wrap">
            <select
              value={patientId}
              onChange={(e) => setPatientId(e.target.value)}
              className="h-9 px-3 rounded-full bg-white dark:bg-pastel-cardDark border border-pastel-brandLight dark:border-pastel-borderDark text-[13px] text-pastel-ink dark:text-pastel-inkDark outline-none"
            >
              {patients.map((p) => (
                <option key={p.id} value={p.id}>{p.name} — {p.room}</option>
              ))}
            </select>

            <div className="flex items-center gap-2 h-9 px-3 rounded-full bg-white dark:bg-pastel-cardDark border border-pastel-brandLight dark:border-pastel-borderDark w-52">
              <Search size={13} className="text-pastel-sub dark:text-pastel-subDark" aria-hidden="true" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search events…"
                className="flex-1 bg-transparent text-[12.5px] text-pastel-ink dark:text-pastel-inkDark outline-none placeholder:text-pastel-sub/70"
              />
            </div>

            <span className="text-[11px] text-pastel-sub dark:text-pastel-subDark ml-auto">Timeline uses backend vitals and local session actions.</span>
          </div>

          <div className="flex gap-1.5 mb-5">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                onClick={() => setFilter(f.key)}
                className={`px-3 py-1.5 rounded-full text-[12px] font-medium transition-colors ${
                  filter === f.key ? 'bg-pastel-brand text-white' : 'bg-white dark:bg-pastel-cardDark text-pastel-sub dark:text-pastel-subDark border border-pastel-brandLight dark:border-pastel-borderDark'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {isLoading && <p className="text-[13px] text-pastel-sub">Loading patients…</p>}
          {error && <p className="text-[13px] text-red-600">Unable to load patients: {error.message}</p>}
          {!isLoading && !error && !patient && <p className="text-[13px] text-pastel-sub">No patients returned by the backend.</p>}
          <div className="relative pl-6">
            <div className="absolute left-[9px] top-2 bottom-2 w-px bg-pastel-brandLight dark:bg-pastel-borderDark" aria-hidden="true" />
            <AnimatePresence initial={false}>
              {filtered.map((e, i) => {
                const Icon = e.meta.icon;
                const expanded = expandedId === e.id;
                return (
                  <motion.div
                    key={e.id}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.25, delay: i * 0.03 }}
                    className="relative mb-4"
                  >
                    <span
                      className="absolute -left-6 top-0.5 h-4 w-4 rounded-full flex items-center justify-center"
                      style={{ background: e.meta.color }}
                      aria-hidden="true"
                    >
                      <Icon size={10} className="text-white" />
                    </span>
                    <button
                      onClick={() => setExpandedId(expanded ? null : e.id)}
                      className="w-full text-left rounded-xl bg-white dark:bg-pastel-cardDark border border-pastel-brandLight dark:border-pastel-borderDark px-3.5 py-2.5 hover:shadow-sm transition-shadow"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[13px] font-medium text-pastel-ink dark:text-pastel-inkDark">{e.meta.label}</span>
                        <span className="text-[11px] text-pastel-sub dark:text-pastel-subDark">{timeAgo(e.time)}</span>
                      </div>
                      {expanded && <p className="text-[12px] text-pastel-sub dark:text-pastel-subDark mt-1.5">{e.detail}</p>}
                    </button>
                  </motion.div>
                );
              })}
            </AnimatePresence>
            {filtered.length === 0 && <p className="text-[13px] text-pastel-sub dark:text-pastel-subDark">No events match your filter.</p>}
          </div>
        </main>
      </div>
    </div>
  );
}
