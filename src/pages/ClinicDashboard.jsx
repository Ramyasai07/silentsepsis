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
import { useState } from 'react';

export default function ClinicDashboard() {
  const [selectedId, setSelectedId] = useState(null);
  const [query, setQuery] = useState('');
  const sorted = [...commandPatients].sort((a, b) => b.risk - a.risk);
  const filteredPatients = sorted.filter((p) =>
    p.name.toLowerCase().includes(query.toLowerCase()) || p.room.toLowerCase().includes(query.toLowerCase())
  );
  const selectedPatient = sorted.find((p) => p.id === selectedId);

  const counts = {
    Critical: sorted.filter((p) => p.status === 'critical').length,
    Warning: sorted.filter((p) => p.status === 'warning').length,
    Stable: sorted.filter((p) => p.status === 'stable').length,
  };

  return (
    <div className="min-h-screen bg-pastel-bg dark:bg-pastel-bgDark flex transition-colors">
      <ClinicSidebar />

      <div className="flex-1 min-w-0">
        <ClinicTopbar onSearchChange={setQuery} />

        <main className="px-6 pb-8 max-w-[1400px]">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <RingStatCard
              title="Total patients monitored"
              total={sorted.length}
              segments={[
                { label: 'Critical', value: counts.Critical, color: '#FF6B9D' },
                { label: 'Warning', value: counts.Warning, color: '#FDB022' },
                { label: 'Stable', value: counts.Stable, color: '#20C5A0' },
              ]}
            />
            <CountCard label="Active alerts" value={counts.Critical} delta="+2 today" color="#FF6B9D" bg="#FFE7EF" />
            <CountCard label="Avg confirm time" value="4m" delta="-1m" color="#20C5A0" bg="#E1F8F2" />
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
            <WardCompositionCard counts={counts} />
          </div>
        </main>
      </div>

      {selectedPatient && <PatientDetailDrawer patient={selectedPatient} onClose={() => setSelectedId(null)} />}
      <ChatWidget />
    </div>
  );
}
