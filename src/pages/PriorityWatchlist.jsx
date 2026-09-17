import { useState, useMemo } from 'react';
import { TrendingUp, Clock } from 'lucide-react';
import { ClinicSidebar } from '../components/clinic/ClinicSidebar';
import { ClinicTopbar } from '../components/clinic/ClinicTopbar';
import { PatientDetailDrawer } from '../components/clinic/PatientDetailDrawer';
import { scorePatients } from '../lib/priorityScore';
import { useClinicalPatients } from '../hooks/useClinicalPatients';

const STATUS_TEXT = { critical: 'text-pastel-pink', warning: 'text-pastel-amber', stable: 'text-pastel-teal' };
const RANK_BG = ['bg-pastel-pink', 'bg-pastel-amber', 'bg-pastel-brand'];

export default function PriorityWatchlist() {
  const [selectedId, setSelectedId] = useState(null);
  const { data: patients = [], isLoading, error } = useClinicalPatients();
  const ranked = useMemo(() => scorePatients(patients), [patients]);
  const selectedPatient = ranked.find((p) => p.id === selectedId);

  return (
    <div className="min-h-screen bg-pastel-bg dark:bg-pastel-bgDark flex transition-colors">
      <ClinicSidebar />
      <div className="flex-1 min-w-0">
        <ClinicTopbar />
        <main className="px-6 pb-8 max-w-[900px]">
          <h1 className="text-[19px] font-semibold text-pastel-ink dark:text-pastel-inkDark mb-0.5">Priority watchlist</h1>
          <p className="text-[13px] text-pastel-sub dark:text-pastel-subDark mb-1">
            Patients most likely to deteriorate within the next 6 hours
          </p>
          <p className="text-[11px] text-pastel-sub dark:text-pastel-subDark mb-5">
            Ranked by backend risk, observed vital trend acceleration, and time since last observation. Model certainty is included only when the backend provides it.
          </p>

          <div className="space-y-3">
            {isLoading && <p className="text-[13px] text-pastel-sub">Loading patients…</p>}
            {error && <p className="text-[13px] text-red-600">Unable to load patients: {error.message}</p>}
            {!isLoading && !error && ranked.length === 0 && <p className="text-[13px] text-pastel-sub">No patients returned by the backend.</p>}
            {ranked.map((p, i) => (
              <button
                key={p.id}
                onClick={() => setSelectedId(p.id)}
                className="w-full text-left rounded-2xl bg-white dark:bg-pastel-cardDark border border-pastel-brandLight dark:border-pastel-borderDark p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start gap-3">
                  <div className={`h-8 w-8 rounded-full ${RANK_BG[i] || 'bg-pastel-sub'} text-white text-[13px] font-bold flex items-center justify-center shrink-0`}>
                    {i + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-[14px] font-semibold text-pastel-ink dark:text-pastel-inkDark">{p.name} <span className="text-[12px] font-normal text-pastel-sub dark:text-pastel-subDark">{p.room}</span></p>
                      <div className="flex items-center gap-3 text-right shrink-0">
                        <div>
                          <p className={`text-[15px] font-mono font-bold ${STATUS_TEXT[p.status] || 'text-pastel-sub'}`}>{p.risk ?? '—'} → {p.projectedRisk ?? '—'}</p>
                          <p className="text-[10px] text-pastel-sub dark:text-pastel-subDark">current → projected</p>
                        </div>
                      </div>
                    </div>
                    <p className="text-[12px] text-pastel-sub dark:text-pastel-subDark leading-relaxed mb-2">{p.explanation}</p>
                    <div className="flex items-center gap-4">
                      <span className="flex items-center gap-1 text-[11px] text-pastel-sub dark:text-pastel-subDark">
                        <TrendingUp size={12} aria-hidden="true" /> Priority score {Math.round(p.priorityScore)}
                      </span>
                      {p.timeToIntervention && (
                        <span className="flex items-center gap-1 text-[11px] text-pastel-pink">
                          <Clock size={12} aria-hidden="true" /> {p.timeToIntervention}
                        </span>
                      )}
                      <span className="text-[11px] text-pastel-sub dark:text-pastel-subDark">Confidence unavailable</span>
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </main>
      </div>
      {selectedPatient && <PatientDetailDrawer patient={selectedPatient} onClose={() => setSelectedId(null)} />}
    </div>
  );
}
