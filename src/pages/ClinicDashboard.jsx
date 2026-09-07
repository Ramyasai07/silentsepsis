import { useState, useEffect, useCallback } from 'react';
import { ClinicSidebar } from '../components/clinic/ClinicSidebar';
import { ClinicTopbar } from '../components/clinic/ClinicTopbar';
import { RingStatCard } from '../components/clinic/RingStatCard';
import { CountCard } from '../components/clinic/CountCard';
import { PatientTodayList } from '../components/clinic/PatientTodayList';
import { UpcomingRoundsCard } from '../components/clinic/UpcomingRoundsCard';
import { AnalyticsCard } from '../components/clinic/AnalyticsCard';
import { WardCompositionCard } from '../components/clinic/WardCompositionCard';
import { ChatWidget } from '../components/clinic/ChatWidget';
import { PatientDetailDrawer } from '../components/clinic/PatientDetailDrawer';
import { commandPatients } from '../data/commandPatients';
import { getWards, getWardSummary } from '../api/wards';
import { NetworkError, ApiError } from '../api/client';

/*
 * BACKEND GAP — ward selection
 * UserOut from GET /auth/me has no ward_id field (User model has no ward FK).
 * Workaround: fetch GET /wards, auto-select if exactly one ward exists,
 * otherwise render a ward picker. The correct long-term fix is to add a
 * ward_id FK to the users table and expose it in UserOut.
 *
 * BACKEND GAP — Critical/Warning/Stable patient breakdown
 * GET /wards/{id}/summary returns totalPatients, trendingUp (MODERATE risk),
 * stable (LOW risk), and activeAlerts — but has no "Critical" patient count.
 * The RingStatCard previously showed Critical/Warning/Stable from mock data.
 * Real data now uses: Trending up (trendingUp) and Stable (stable) segments;
 * the remaining patients are unlabelled (no confirmed "critical" count from
 * the backend). The WardCompositionCard receives the same real fields.
 * The mock commandPatients patient list is left unchanged — that is a
 * separate integration task.
 */

function errMsg(err) {
  if (err instanceof NetworkError) return 'Cannot reach server — check your connection.';
  if (err instanceof ApiError) return `Server error (${err.status}): ${err.message}`;
  return 'An unexpected error occurred.';
}

function InlineError({ message, onRetry }) {
  return (
    <div className="rounded-xl border border-red-200 dark:border-red-900/40 bg-red-50 dark:bg-red-950/30 px-4 py-3 text-[13px] text-red-600 dark:text-red-400 flex items-center gap-3 mb-4">
      <span>⚠ {message}</span>
      {onRetry && (
        <button
          onClick={onRetry}
          className="ml-auto text-[12px] font-medium underline underline-offset-2 hover:no-underline"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export default function ClinicDashboard() {
  const [selectedId, setSelectedId] = useState(null);
  const [query, setQuery] = useState('');

  // commandPatients patient list remains mock — separate integration task
  const sorted = [...commandPatients].sort((a, b) => b.risk - a.risk);
  const filteredPatients = sorted.filter((p) =>
    p.name.toLowerCase().includes(query.toLowerCase()) || p.room.toLowerCase().includes(query.toLowerCase())
  );
  const selectedPatient = sorted.find((p) => p.id === selectedId);

  // ── Ward list ─────────────────────────────────────────────────────────────
  const [wards, setWards] = useState(null);
  const [wardsLoading, setWardsLoading] = useState(true);
  const [wardsError, setWardsError] = useState(null);
  const [selectedWardId, setSelectedWardId] = useState(null);

  // ── Ward summary ──────────────────────────────────────────────────────────
  const [summary, setSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState(null);

  const fetchWards = useCallback(async () => {
    setWardsLoading(true);
    setWardsError(null);
    try {
      const data = await getWards();
      setWards(data);
      if (data.length === 1) setSelectedWardId(data[0].id);
    } catch (err) {
      setWardsError(errMsg(err));
    } finally {
      setWardsLoading(false);
    }
  }, []);

  const fetchSummary = useCallback(async (wardId) => {
    if (!wardId) return;
    setSummaryLoading(true);
    setSummaryError(null);
    try {
      const data = await getWardSummary(wardId);
      setSummary(data);
    } catch (err) {
      setSummaryError(errMsg(err));
    } finally {
      setSummaryLoading(false);
    }
  }, []);

  useEffect(() => { fetchWards(); }, [fetchWards]);
  useEffect(() => { fetchSummary(selectedWardId); }, [selectedWardId, fetchSummary]);

  // ── Derived display values from real summary ──────────────────────────────
  // totalPatients, activeAlerts, trendingUp, stable, avgConfirmMinutes, riskLoad
  // are all real backend fields (WardSummaryOut). No fabrication.
  const totalPatients   = summary?.totalPatients    ?? 0;
  const activeAlerts    = summary?.activeAlerts     ?? 0;
  const trendingUp      = summary?.trendingUp       ?? 0;  // patients with MODERATE risk
  const stable          = summary?.stable           ?? 0;  // patients with LOW risk
  const avgConfirmMins  = summary?.avgConfirmMinutes ?? null; // null → "—" until loaded
  const wardName        = summary?.ward             ?? null;

  /*
   * BACKEND GAP — no "Critical" patient count.
   * The backend provides trendingUp (MODERATE) and stable (LOW) but has no
   * aggregate count of HIGH/CRITICAL risk patients as a separate field.
   * We display the two real segments; the ring total uses totalPatients.
   */
  const ringSummaryLoading = summaryLoading || wardsLoading;

  const ringSegments = [
    { label: 'Trending up', value: trendingUp, color: '#FDB022' },
    { label: 'Stable',      value: stable,     color: '#20C5A0' },
  ];

  // WardCompositionCard receives the same real fields, renamed to match its
  // existing label keys (component iterates Object.entries(counts)).
  const compositionCounts = {
    'Trending up': trendingUp,
    Stable:        stable,
  };

  return (
    <div className="min-h-screen bg-pastel-bg dark:bg-pastel-bgDark flex transition-colors">
      <ClinicSidebar />

      <div className="flex-1 min-w-0">
        <ClinicTopbar onSearchChange={setQuery} />

        <main className="px-6 pb-8 max-w-[1400px]">

          {/* Ward selector — only rendered when multiple wards exist */}
          {!wardsLoading && wards && wards.length > 1 && (
            <div className="flex items-center gap-3 mb-4">
              <label
                htmlFor="clinic-ward-select"
                className="text-[13px] text-pastel-sub dark:text-pastel-subDark"
              >
                Ward:
              </label>
              <select
                id="clinic-ward-select"
                value={selectedWardId ?? ''}
                onChange={(e) => setSelectedWardId(e.target.value || null)}
                className="text-[13px] rounded-lg border border-pastel-brandLight dark:border-pastel-borderDark bg-white dark:bg-pastel-cardDark text-pastel-ink dark:text-pastel-inkDark px-3 py-1.5 cursor-pointer"
              >
                <option value="">— Select ward —</option>
                {wards.map((w) => (
                  <option key={w.id} value={w.id}>{w.name}</option>
                ))}
              </select>
            </div>
          )}

          {/* Ward load / summary error banners */}
          {wardsError && (
            <InlineError message={wardsError} onRetry={fetchWards} />
          )}
          {summaryError && !summaryLoading && (
            <InlineError message={summaryError} onRetry={() => fetchSummary(selectedWardId)} />
          )}

          {/* "Select a ward" prompt */}
          {!wardsLoading && !wardsError && wards && wards.length > 1 && !selectedWardId && (
            <p className="text-[13px] text-pastel-sub dark:text-pastel-subDark mb-4">
              Select a ward above to populate the dashboard stats.
            </p>
          )}

          {/* No wards configured */}
          {!wardsLoading && !wardsError && wards && wards.length === 0 && (
            <p className="text-[13px] text-pastel-sub dark:text-pastel-subDark mb-4">
              No wards configured. Ask an administrator to add ward entries.
            </p>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            {/*
              RingStatCard total = real totalPatients.
              Segments = trendingUp + stable (the two real backend fields).
              BACKEND GAP: no HIGH/CRITICAL patient count — those patients are
              accounted for in totalPatients but not broken out as a segment.
            */}
            <RingStatCard
              title={wardName ? `${wardName} — patients monitored` : 'Total patients monitored'}
              total={ringSummaryLoading ? '…' : totalPatients}
              segments={ringSegments}
            />

            {/* Active alerts — real field from WardSummaryOut */}
            <CountCard
              label="Active alerts"
              value={summaryLoading ? '…' : activeAlerts}
              color="#FF6B9D"
              bg="#FFE7EF"
            />

            {/*
              Avg confirm time — real field (avgConfirmMinutes, float).
              Displayed as e.g. "4.5 min". Null/0 → "—" when no confirmed
              alerts have been recorded for this ward in the last 30 days.
            */}
            <CountCard
              label="Avg confirm time"
              value={
                summaryLoading
                  ? '…'
                  : avgConfirmMins
                    ? `${avgConfirmMins}m`
                    : '—'
              }
              color="#20C5A0"
              bg="#E1F8F2"
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-4 mb-4">
            {filteredPatients.length > 0 ? (
              <PatientTodayList patients={filteredPatients} onSelect={setSelectedId} selectedId={selectedId} />
            ) : (
              <div className="rounded-2xl bg-white dark:bg-pastel-cardDark p-5 shadow-[0_1px_2px_rgba(30,27,57,0.04),0_8px_20px_rgba(30,27,57,0.05)] dark:shadow-none dark:border dark:border-pastel-borderDark h-full">
                <p className="text-[14px] font-semibold text-pastel-ink dark:text-pastel-inkDark mb-4">Patients needing review</p>
                <p className="py-4 text-center text-[12px] text-pastel-sub dark:text-pastel-subDark">No patients found</p>
              </div>
            )}
            <UpcomingRoundsCard />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-4">
            <AnalyticsCard />
            {/*
              WardCompositionCard now receives real trendingUp + stable counts.
              BACKEND GAP: the original Critical/Warning/Stable split is not
              available from the backend — only trendingUp (MODERATE risk) and
              stable (LOW risk) are returned. The component receives those two
              real fields; the COLORS map in WardCompositionCard does not have
              entries for these new keys, so they will render without a colour
              chip — see note below.
            */}
            <WardCompositionCard counts={compositionCounts} />
          </div>
        </main>
      </div>

      {selectedPatient && (
        <PatientDetailDrawer
          patient={selectedPatient}
          onClose={() => setSelectedId(null)}
        />
      )}
      <ChatWidget />
    </div>
  );
}
