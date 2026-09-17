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
import { getWards, getWardSummary } from '../api/wards';
import { NetworkError, ApiError } from '../api/client';
import { useClinicalPatients } from '../hooks/useClinicalPatients';

function errMsg(err) {
  if (err instanceof NetworkError) return 'Cannot reach server - check your connection.';
  if (err instanceof ApiError) return `Server error (${err.status}): ${err.message}`;
  return 'An unexpected error occurred.';
}

function InlineError({ message, onRetry }) {
  return (
    <div className="rounded-xl border border-red-200 dark:border-red-900/40 bg-red-50 dark:bg-red-950/30 px-4 py-3 text-[13px] text-red-600 dark:text-red-400 flex items-center gap-3 mb-4">
      <span>{message}</span>
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

function buildRiskCounts(patients) {
  return patients.reduce(
    (counts, patient) => {
      const tier = patient.tier?.toUpperCase();
      if (tier === 'CRITICAL') counts.Critical += 1;
      else if (tier === 'HIGH') counts.High += 1;
      else if (tier === 'MODERATE') counts.Moderate += 1;
      else if (tier === 'LOW') counts.Low += 1;
      else counts.Unassessed += 1;
      return counts;
    },
    { Critical: 0, High: 0, Moderate: 0, Low: 0, Unassessed: 0 },
  );
}

export default function ClinicDashboard() {
  const [selectedId, setSelectedId] = useState(null);
  const [query, setQuery] = useState('');
  const [wards, setWards] = useState(null);
  const [wardsLoading, setWardsLoading] = useState(true);
  const [wardsError, setWardsError] = useState(null);
  const [selectedWardId, setSelectedWardId] = useState(null);
  const [summary, setSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState(null);

  const {
    data: clinicalPatients = [],
    isLoading: patientsLoading,
    error: patientsError,
  } = useClinicalPatients();

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
    if (!wardId) {
      setSummary(null);
      return;
    }
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

  useEffect(() => {
    fetchWards();
  }, [fetchWards]);

  useEffect(() => {
    fetchSummary(selectedWardId);
    setSelectedId(null);
  }, [selectedWardId, fetchSummary]);

  const selectedWard = wards?.find((ward) => ward.id === selectedWardId);
  const wardName = summary?.ward ?? selectedWard?.name ?? null;
  const sortedPatients = [...clinicalPatients].sort(
    (a, b) => (b.risk ?? -1) - (a.risk ?? -1),
  );
  const wardPatients = wardName
    ? sortedPatients.filter((patient) => patient.ward === wardName)
    : sortedPatients;
  const filteredPatients = wardPatients.filter(
    (patient) =>
      patient.name.toLowerCase().includes(query.toLowerCase()) ||
      patient.room.toLowerCase().includes(query.toLowerCase()),
  );
  const selectedPatient = wardPatients.find((patient) => patient.id === selectedId);
  const riskCounts = buildRiskCounts(wardPatients);
  const totalPatients = summary?.totalPatients ?? wardPatients.length;
  const activeAlerts = summary?.activeAlerts ?? 0;
  const avgConfirmMins = summary?.avgConfirmMinutes ?? null;
  const ringSummaryLoading = summaryLoading || wardsLoading;
  const ringSegments = [
    { label: 'Critical', value: riskCounts.Critical, color: '#FF6B9D' },
    { label: 'High', value: riskCounts.High, color: '#F97316' },
    { label: 'Moderate', value: riskCounts.Moderate, color: '#FDB022' },
    { label: 'Low', value: riskCounts.Low, color: '#20C5A0' },
  ];

  return (
    <div className="min-h-screen bg-pastel-bg dark:bg-pastel-bgDark flex transition-colors">
      <ClinicSidebar />

      <div className="flex-1 min-w-0">
        <ClinicTopbar onSearchChange={setQuery} />

        <main className="px-6 pb-8 max-w-[1400px]">
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
                <option value="">- Select ward -</option>
                {wards.map((ward) => (
                  <option key={ward.id} value={ward.id}>
                    {ward.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {wardsError && <InlineError message={wardsError} onRetry={fetchWards} />}
          {summaryError && !summaryLoading && (
            <InlineError message={summaryError} onRetry={() => fetchSummary(selectedWardId)} />
          )}
          {patientsError && (
            <InlineError message={patientsError.message || 'Unable to load patients.'} />
          )}

          <div className="mb-4 inline-flex items-center rounded-full border border-pastel-brandLight dark:border-pastel-borderDark bg-white/70 dark:bg-white/5 px-3 py-1 text-[11px] font-medium text-pastel-sub dark:text-pastel-subDark">
            Demo Environment · Synthetic Patient Data
          </div>

          {!wardsLoading && !wardsError && wards && wards.length > 1 && !selectedWardId && (
            <p className="text-[13px] text-pastel-sub dark:text-pastel-subDark mb-4">
              Select a ward above to populate the dashboard stats.
            </p>
          )}

          {!wardsLoading && !wardsError && wards && wards.length === 0 && (
            <p className="text-[13px] text-pastel-sub dark:text-pastel-subDark mb-4">
              No wards configured. Ask an administrator to add ward entries.
            </p>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <RingStatCard
              title={wardName ? `${wardName} - patients monitored` : 'Total patients monitored'}
              total={ringSummaryLoading ? '...' : totalPatients}
              segments={ringSegments}
            />

            <CountCard
              label="Active alerts"
              value={summaryLoading ? '...' : activeAlerts}
              color="#FF6B9D"
              bg="#FFE7EF"
            />

            <CountCard
              label="Avg confirm time"
              value={
                summaryLoading
                  ? '...'
                  : avgConfirmMins
                    ? `${avgConfirmMins}m`
                    : '-'
              }
              color="#20C5A0"
              bg="#E1F8F2"
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-4 mb-4">
            {patientsLoading ? (
              <div className="rounded-2xl bg-white dark:bg-pastel-cardDark p-5">
                <p className="text-[12px] text-pastel-sub">Loading patients...</p>
              </div>
            ) : filteredPatients.length > 0 ? (
              <PatientTodayList
                patients={filteredPatients}
                onSelect={setSelectedId}
                selectedId={selectedId}
              />
            ) : (
              <div className="rounded-2xl bg-white dark:bg-pastel-cardDark p-5 shadow-[0_1px_2px_rgba(30,27,57,0.04),0_8px_20px_rgba(30,27,57,0.05)] dark:shadow-none dark:border dark:border-pastel-borderDark h-full">
                <p className="text-[14px] font-semibold text-pastel-ink dark:text-pastel-inkDark mb-4">
                  Patients needing review
                </p>
                <p className="py-4 text-center text-[12px] text-pastel-sub dark:text-pastel-subDark">
                  No patients found
                </p>
              </div>
            )}
            <UpcomingRoundsCard />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-4">
            <AnalyticsCard />
            <WardCompositionCard counts={riskCounts} />
          </div>
        </main>
      </div>

      {selectedPatient && (
        <PatientDetailDrawer
          patient={selectedPatient}
          onClose={() => setSelectedId(null)}
        />
      )}
      <ChatWidget patients={clinicalPatients} />
    </div>
  );
}
