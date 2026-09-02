import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutGrid, Users, CalendarClock, FlaskConical, BarChart3, ShieldCheck, ChevronDown, ListOrdered, Grid3x3, History } from 'lucide-react';
import { AIMethodologyPanel } from './AIMethodologyPanel';

const MAIN_NAV = [
  { to: '/nurse', icon: LayoutGrid, label: 'Dashboard' },
  { to: '/patients', icon: Users, label: 'Patients' },
  { to: '/watchlist', icon: ListOrdered, label: 'Priority watchlist' },
  { to: '/heatmap', icon: Grid3x3, label: 'Ward heatmap' },
  { to: '/timeline', icon: History, label: 'Patient timeline' },
  { to: '/alerts', icon: CalendarClock, label: 'Alerts' },
  { to: '/physician', icon: FlaskConical, label: 'Escalated' },
];
const OTHER_NAV = [
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
  { to: '/admin', icon: ShieldCheck, label: 'System' },
];

export function ClinicSidebar() {
  const [isHelpOpen, setIsHelpOpen] = useState(false);

  return (
    <aside className="w-[236px] shrink-0 bg-white dark:bg-pastel-cardDark border-r border-pastel-brandLight dark:border-pastel-borderDark h-screen sticky top-0 flex flex-col">
      <div className="h-16 flex items-center gap-2.5 px-5">
        <div className="h-8 w-8 rounded-xl bg-pastel-brand flex items-center justify-center text-white text-sm font-bold">S</div>
        <span className="text-[15px] font-semibold text-pastel-ink dark:text-pastel-inkDark">SilentSepsis</span>
      </div>

      <nav className="px-3 mt-2 space-y-0.5">
        {MAIN_NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 h-10 px-3 rounded-xl text-[13.5px] font-medium transition-colors ${
                isActive
                  ? 'bg-pastel-brand text-white'
                  : 'text-pastel-sub dark:text-pastel-subDark hover:bg-pastel-brandLight dark:hover:bg-pastel-brandLightDark hover:text-pastel-ink dark:hover:text-pastel-inkDark'
              }`
            }
          >
            <Icon size={17} aria-hidden="true" />
            {label}
          </NavLink>
        ))}
      </nav>

      <p className="px-5 mt-6 mb-1 text-[11px] font-semibold text-pastel-sub/70 dark:text-pastel-subDark/70 uppercase tracking-wide flex items-center gap-1">
        More <ChevronDown size={12} aria-hidden="true" />
      </p>
      <nav className="px-3 space-y-0.5">
        {OTHER_NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 h-10 px-3 rounded-xl text-[13.5px] font-medium transition-colors ${
                isActive
                  ? 'bg-pastel-brand text-white'
                  : 'text-pastel-sub dark:text-pastel-subDark hover:bg-pastel-brandLight dark:hover:bg-pastel-brandLightDark hover:text-pastel-ink dark:hover:text-pastel-inkDark'
              }`
            }
          >
            <Icon size={17} aria-hidden="true" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto p-4">
        <div className="rounded-2xl bg-pastel-brandLight dark:bg-pastel-brandLightDark p-4 text-center">
          <p className="text-[12px] font-medium text-pastel-ink dark:text-pastel-inkDark mb-1">Need help?</p>
          <p className="text-[11px] text-pastel-sub dark:text-pastel-subDark mb-3">Check the ward handover guide</p>
          <button
            onClick={() => setIsHelpOpen(true)}
            className="w-full h-8 rounded-lg bg-pastel-brand text-white text-[12px] font-medium"
          >
            Open guide
          </button>
        </div>
      </div>
      <AIMethodologyPanel open={isHelpOpen} onClose={() => setIsHelpOpen(false)} />
    </aside>
  );
}
