import { useEffect, useState, useCallback } from 'react';
import { RefreshCw, AlertCircle, Check, X, ShieldAlert, CheckCircle2 } from 'lucide-react';
import Topbar from '../components/Topbar';
import { getAlerts, acknowledgeAlert, confirmAlert, dismissAlert, resolveAlert } from '../api/alerts';
import { useAuth } from '../context/AuthContext';

const STATUS_TONE = {
  active: 'critical',
  watching: 'watch',
  acknowledged: 'watch',
  confirmed: 'watch',
  dismissed: 'stable',
  resolved: 'stable',
};

export default function Alerts() {
  const { user } = useAuth();
  const [alerts, setAlerts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modal / input state for dismiss action
  const [dismissingAlertId, setDismissingAlertId] = useState(null);
  const [dismissReason, setDismissReason] = useState('');
  const [actionError, setActionError] = useState(null);
  const [isSubmittingAction, setIsSubmittingAction] = useState(false);

  // Role gating checks against user's actual role from AuthContext
  const role = user?.role?.toLowerCase() ?? '';
  const canAcknowledgeOrDismiss = role === 'nurse' || role === 'physician' || role === 'admin';
  const canConfirmOrResolve = role === 'physician' || role === 'admin';

  const loadAlerts = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getAlerts();
      setAlerts(data || []);
    } catch (err) {
      setError(err?.message || 'Failed to fetch alerts.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAlerts();
  }, [loadAlerts]);

  async function handleAcknowledge(alertId) {
    setActionError(null);
    setIsSubmittingAction(true);
    try {
      const updated = await acknowledgeAlert(alertId);
      setAlerts((prev) => prev.map((a) => (a.id === alertId ? { ...a, status: updated.status } : a)));
    } catch (err) {
      setActionError(`Acknowledge failed: ${err.message}`);
    } finally {
      setIsSubmittingAction(false);
    }
  }

  async function handleConfirm(alertId) {
    setActionError(null);
    setIsSubmittingAction(true);
    try {
      const updated = await confirmAlert(alertId);
      setAlerts((prev) => prev.map((a) => (a.id === alertId ? { ...a, status: updated.status } : a)));
    } catch (err) {
      setActionError(`Confirm failed: ${err.message}`);
    } finally {
      setIsSubmittingAction(false);
    }
  }

  async function handleResolve(alertId) {
    setActionError(null);
    setIsSubmittingAction(true);
    try {
      const updated = await resolveAlert(alertId);
      setAlerts((prev) => prev.map((a) => (a.id === alertId ? { ...a, status: updated.status } : a)));
    } catch (err) {
      setActionError(`Resolve failed: ${err.message}`);
    } finally {
      setIsSubmittingAction(false);
    }
  }

  async function submitDismiss(e) {
    e.preventDefault();
    if (!dismissReason.trim() || !dismissingAlertId) return;

    setActionError(null);
    setIsSubmittingAction(true);
    try {
      const updated = await dismissAlert(dismissingAlertId, dismissReason.trim());
      setAlerts((prev) => prev.map((a) => (a.id === dismissingAlertId ? { ...a, status: updated.status } : a)));
      setDismissingAlertId(null);
      setDismissReason('');
    } catch (err) {
      setActionError(`Dismiss failed: ${err.message}`);
    } finally {
      setIsSubmittingAction(false);
    }
  }

  return (
    <>
      <Topbar title="Alert history" subtitle="All wards" />

      {actionError && (
        <div className="mb-4 p-3 rounded-xl bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 text-[13px] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle size={15} />
            <span>{actionError}</span>
          </div>
          <button onClick={() => setActionError(null)} className="text-red-500 hover:text-red-700">
            <X size={14} />
          </button>
        </div>
      )}

      <div className="panel" style={{ padding: 0 }}>
        {isLoading && (
          <div className="p-8 text-center text-pastel-sub flex items-center justify-center gap-2 text-[13.5px]">
            <RefreshCw size={16} className="animate-spin text-pastel-brand" />
            <span>Loading alerts from backend…</span>
          </div>
        )}

        {error && (
          <div className="p-6 text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-red-50 text-red-700 text-[13px] mb-3">
              <AlertCircle size={15} />
              <span>Failed to load alerts ({error})</span>
            </div>
            <div>
              <button onClick={loadAlerts} className="btn sm primary">
                Retry
              </button>
            </div>
          </div>
        )}

        {!isLoading && !error && alerts.length === 0 && (
          <div className="p-8 text-center text-pastel-sub text-[13.5px]">
            <CheckCircle2 size={24} className="mx-auto mb-2 text-pastel-teal" />
            <p className="font-medium">No open alerts</p>
            <p className="text-[12px] opacity-75 mt-0.5">All wards are currently clear.</p>
          </div>
        )}

        {!isLoading && !error && alerts.length > 0 && (
          <table className="data-table">
            <thead>
              <tr>
                <th>Patient ID</th>
                <th>Severity</th>
                <th>Message</th>
                <th>Status</th>
                <th>Time</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a) => {
                const statusLc = a.status?.toLowerCase() || 'active';
                const tone = STATUS_TONE[statusLc] || 'watch';
                const createdDate = new Date(a.created_at);
                const timeString = isNaN(createdDate.getTime())
                  ? 'N/A'
                  : createdDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

                return (
                  <tr key={a.id}>
                    <td className="mono text-[12px] font-semibold">{a.patient_id ? `${a.patient_id.slice(0, 8)}…` : 'N/A'}</td>
                    <td>
                      <span className={`badge ${tone}`}>{a.severity}</span>
                    </td>
                    <td className="text-[13px]">{a.message}</td>
                    <td>
                      <span className={`badge ${tone}`}>{a.status}</span>
                    </td>
                    <td className="mono text-[12px]">{timeString}</td>
                    <td>
                      <div className="flex items-center gap-2">
                        {/* Acknowledge Action (Active -> Watching) */}
                        {statusLc === 'active' && (
                          <button
                            onClick={() => handleAcknowledge(a.id)}
                            disabled={!canAcknowledgeOrDismiss || isSubmittingAction}
                            title={!canAcknowledgeOrDismiss ? 'Insufficient permissions' : 'Acknowledge alert'}
                            className="btn sm ghost text-[11px] py-1 px-2 disabled:opacity-40"
                          >
                            <Check size={12} className="inline mr-1" /> Ack
                          </button>
                        )}

                        {/* Confirm Action (Watching/Acknowledged -> Confirmed) */}
                        {(statusLc === 'active' || statusLc === 'watching' || statusLc === 'acknowledged') && (
                          <button
                            onClick={() => handleConfirm(a.id)}
                            disabled={!canConfirmOrResolve || isSubmittingAction}
                            title={!canConfirmOrResolve ? 'Requires Physician or Admin role' : 'Confirm sepsis alert'}
                            className="btn sm confirm text-[11px] py-1 px-2 disabled:opacity-40"
                          >
                            <ShieldAlert size={12} className="inline mr-1" /> Confirm
                          </button>
                        )}

                        {/* Dismiss Action (Active/Watching -> Dismissed) */}
                        {(statusLc === 'active' || statusLc === 'watching' || statusLc === 'acknowledged') && (
                          <button
                            onClick={() => {
                              setDismissingAlertId(a.id);
                              setDismissReason('');
                            }}
                            disabled={!canAcknowledgeOrDismiss || isSubmittingAction}
                            title={!canAcknowledgeOrDismiss ? 'Insufficient permissions' : 'Dismiss alert'}
                            className="btn sm ghost text-[11px] py-1 px-2 text-red-600 disabled:opacity-40"
                          >
                            Dismiss
                          </button>
                        )}

                        {/* Resolve Action (Confirmed -> Resolved) */}
                        {statusLc === 'confirmed' && (
                          <button
                            onClick={() => handleResolve(a.id)}
                            disabled={!canConfirmOrResolve || isSubmittingAction}
                            title={!canConfirmOrResolve ? 'Requires Physician or Admin role' : 'Resolve alert'}
                            className="btn sm primary text-[11px] py-1 px-2 disabled:opacity-40"
                          >
                            Resolve
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Dismiss Modal */}
      {dismissingAlertId && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <form
            onSubmit={submitDismiss}
            className="bg-white dark:bg-pastel-cardDark rounded-2xl p-6 max-w-md w-full shadow-2xl border border-pastel-brandLight dark:border-pastel-borderDark"
          >
            <h3 className="text-[16px] font-semibold text-pastel-ink dark:text-pastel-inkDark mb-2">
              Dismiss Sepsis Alert
            </h3>
            <p className="text-[12.5px] text-pastel-sub dark:text-pastel-subDark mb-4">
              Please enter a clinical rationale for dismissing this alert. This will be logged for model calibration.
            </p>

            <label className="block text-[12px] font-medium text-pastel-ink dark:text-pastel-inkDark mb-1.5">
              Dismiss Reason <span className="text-red-500">*</span>
            </label>
            <textarea
              required
              rows={3}
              placeholder="e.g. Transient artifact during patient movement"
              value={dismissReason}
              onChange={(e) => setDismissReason(e.target.value)}
              className="w-full p-3 rounded-xl border border-pastel-brandLight dark:border-pastel-borderDark bg-white dark:bg-pastel-bgDark text-[13px] text-pastel-ink dark:text-pastel-inkDark outline-none focus:border-pastel-brand mb-5"
            />

            <div className="flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setDismissingAlertId(null)}
                className="btn sm ghost"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!dismissReason.trim() || isSubmittingAction}
                className="btn sm primary bg-red-600 hover:bg-red-700 text-white border-none disabled:opacity-50"
              >
                {isSubmittingAction ? 'Dismissing…' : 'Submit Dismissal'}
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
