import { useState } from 'react';
import { X, Check, Plus } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import { DismissReasonModal } from './DismissReasonModal';
import { VitalsEntryForm } from './VitalsEntryForm';

const STATUS_TEXT = { critical: 'text-pastel-pink', warning: 'text-pastel-amber', stable: 'text-pastel-teal', unassessed: 'text-pastel-sub' };
const STATUS_LABEL = { critical: 'Critical', warning: 'Watching', stable: 'Stable', unassessed: 'Unassessed' };

export function PatientDetailDrawer({ patient, onClose }) {
  const [showDismiss, setShowDismiss] = useState(false);
  const [showVitals, setShowVitals] = useState(false);
  const acknowledge = useAppStore((s) => s.acknowledge);
  const acknowledgedIds = useAppStore((s) => s.acknowledgedIds);
  const dismissedIds = useAppStore((s) => s.dismissedIds);
  const manualVitals = useAppStore((s) => s.manualVitals[patient.id] || []);

  const latest = patient.vitals[patient.vitals.length - 1];
  const isAcknowledged = acknowledgedIds.has(patient.id);
  const dismissInfo = dismissedIds.get(patient.id);

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/20" onClick={onClose} />
      <div className="fixed top-0 right-0 z-50 h-screen w-[380px] bg-white dark:bg-pastel-cardDark border-l border-pastel-brandLight dark:border-pastel-borderDark shadow-2xl overflow-y-auto animate-[drawer-in_0.25s_cubic-bezier(0.16,1,0.3,1)]">
        <div className="flex items-center justify-between p-4 border-b border-pastel-bg dark:border-pastel-borderDark sticky top-0 bg-white dark:bg-pastel-cardDark z-10">
          <div>
            <p className="text-[14.5px] font-semibold text-pastel-ink dark:text-pastel-inkDark">{patient.name}</p>
            <p className="text-[12px] text-pastel-sub dark:text-pastel-subDark">{patient.room} · {patient.age}y</p>
          </div>
          <button onClick={onClose} aria-label="Close" className="text-pastel-sub dark:text-pastel-subDark hover:text-pastel-ink dark:hover:text-pastel-inkDark">
            <X size={18} />
          </button>
        </div>

        <div className="p-4">
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="rounded-xl bg-pastel-bg dark:bg-white/5 p-3">
              <p className="text-[10.5px] text-pastel-sub dark:text-pastel-subDark mb-1">Risk score</p>
              <p className={`text-[19px] font-mono font-bold ${STATUS_TEXT[patient.status]}`}>{patient.risk ?? '—'}</p>
              <p className="text-[10.5px] text-pastel-sub dark:text-pastel-subDark">{STATUS_LABEL[patient.status]}</p>
            </div>
            <div className="rounded-xl bg-pastel-bg dark:bg-white/5 p-3">
              <p className="text-[10.5px] text-pastel-sub dark:text-pastel-subDark mb-1">Model confidence</p>
              <p className="text-[19px] font-mono font-bold text-pastel-ink dark:text-pastel-inkDark">—</p>
              <p className="text-[10.5px] text-pastel-sub dark:text-pastel-subDark">Not provided by backend</p>
            </div>
          </div>

          <p className="text-[11px] font-medium text-pastel-sub dark:text-pastel-subDark uppercase tracking-wide mb-2">Baseline vs current</p>
          <div className="rounded-xl border border-pastel-brandLight dark:border-pastel-borderDark overflow-hidden mb-4">
            <table className="w-full text-[12.5px]">
              <thead>
                <tr className="bg-pastel-bg dark:bg-white/5 text-pastel-sub dark:text-pastel-subDark">
                  <th className="text-left font-medium py-1.5 px-3">Vital</th>
                  <th className="text-right font-medium py-1.5 px-3">Baseline</th>
                  <th className="text-right font-medium py-1.5 px-3">Current</th>
                </tr>
              </thead>
              <tbody className="text-pastel-ink dark:text-pastel-inkDark">
                <tr className="border-t border-pastel-bg dark:border-pastel-borderDark">
                  <td className="py-1.5 px-3">Heart rate</td>
                  <td className="text-right px-3 font-mono text-pastel-sub dark:text-pastel-subDark">—</td>
                  <td className="text-right px-3 font-mono font-medium">{latest?.hr ?? '—'}</td>
                </tr>
                <tr className="border-t border-pastel-bg dark:border-pastel-borderDark">
                  <td className="py-1.5 px-3">Resp. rate</td>
                  <td className="text-right px-3 font-mono text-pastel-sub dark:text-pastel-subDark">—</td>
                  <td className="text-right px-3 font-mono font-medium">{latest?.rr ?? '—'}</td>
                </tr>
              </tbody>
            </table>
          </div>

          {patient.features.length > 0 && (
            <>
              <p className="text-[11px] font-medium text-pastel-sub dark:text-pastel-subDark uppercase tracking-wide mb-2">Why flagged</p>
              <div className="space-y-2 mb-4">
                {patient.features.map((f) => (
                  <div key={f.name} className="flex items-center gap-2">
                    <span className="text-[11.5px] text-pastel-sub dark:text-pastel-subDark w-32 shrink-0">{f.name}</span>
                    <div className="flex-1 h-1.5 rounded-full bg-pastel-bg dark:bg-white/10 overflow-hidden">
                      <div className="h-full rounded-full bg-pastel-brand" style={{ width: `${f.contribution}%` }} />
                    </div>
                    <span className="text-[11px] font-mono text-pastel-ink dark:text-pastel-inkDark w-8 text-right">{f.contribution}%</span>
                  </div>
                ))}
              </div>
            </>
          )}

          {manualVitals.length > 0 && (
            <div className="mb-4 rounded-xl bg-pastel-tealLight dark:bg-pastel-tealLightDark p-3">
              <p className="text-[11.5px] font-medium text-pastel-teal">{manualVitals.length} manual entry logged this shift</p>
            </div>
          )}

          {dismissInfo && (
            <div className="mb-4 rounded-xl bg-pastel-bg dark:bg-white/5 p-3">
              <p className="text-[11.5px] font-medium text-pastel-ink dark:text-pastel-inkDark">Dismissed: {dismissInfo.reason}</p>
              {dismissInfo.note && <p className="text-[11px] text-pastel-sub dark:text-pastel-subDark mt-0.5">{dismissInfo.note}</p>}
            </div>
          )}

          <div className="space-y-2">
            <button
              onClick={() => acknowledge(patient.id)}
              disabled={isAcknowledged}
              className="w-full h-10 rounded-xl bg-pastel-brand text-white text-[13px] font-medium flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <Check size={14} aria-hidden="true" /> {isAcknowledged ? 'Acknowledged' : 'Acknowledge'}
            </button>
            <button
              onClick={() => setShowDismiss(true)}
              disabled={!!dismissInfo}
              className="w-full h-10 rounded-xl border border-pastel-brandLight dark:border-pastel-borderDark text-[13px] font-medium text-pastel-ink dark:text-pastel-inkDark disabled:opacity-50"
            >
              {dismissInfo ? 'Dismissed' : 'Dismiss with reason'}
            </button>
            <button
              onClick={() => setShowVitals(true)}
              className="w-full h-10 rounded-xl border border-pastel-brandLight dark:border-pastel-borderDark text-[13px] font-medium text-pastel-ink dark:text-pastel-inkDark flex items-center justify-center gap-2"
            >
              <Plus size={14} aria-hidden="true" /> Add vitals
            </button>
          </div>
        </div>
      </div>

      {showDismiss && <DismissReasonModal patient={patient} onClose={() => setShowDismiss(false)} />}
      {showVitals && <VitalsEntryForm patient={patient} onClose={() => setShowVitals(false)} />}
    </>
  );
}
