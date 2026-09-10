import { useEffect, useRef, useState } from 'react';
import { Search, Grid3x3, Moon, Sun, Download } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '../../store/useAppStore';
import { NotificationBell } from './NotificationBell';
import { downloadWardReport } from '../../lib/downloadReport';
import { commandPatients } from '../../data/commandPatients';
import { useAuth } from '../../context/AuthContext';

export function ClinicTopbar({ onSearchChange }) {
  const darkMode = useAppStore((s) => s.darkMode);
  const toggleDarkMode = useAppStore((s) => s.toggleDarkMode);
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [openPanel, setOpenPanel] = useState(null);
  const [query, setQuery] = useState('');
  const panelRef = useRef(null);
  const displayName = user?.name || 'N. Thomas';
  const displayRole = user?.role || 'Ward nurse';
  const initials = displayName
    .split(' ')
    .filter(Boolean)
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  useEffect(() => {
    function onClick(e) {
      if (panelRef.current && !panelRef.current.contains(e.target)) setOpenPanel(null);
    }
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  return (
    <div className="h-16 flex items-center justify-between px-6">
      <div className="flex items-center gap-2 h-9 px-3.5 rounded-full bg-white dark:bg-pastel-cardDark border border-pastel-brandLight dark:border-pastel-borderDark w-72">
        <Search size={15} className="text-pastel-sub dark:text-pastel-subDark" aria-hidden="true" />
        <input
          value={query}
          onChange={(e) => {
            const nextQuery = e.target.value;
            setQuery(nextQuery);
            onSearchChange?.(nextQuery);
          }}
          placeholder="Search patients, rooms…"
          className="flex-1 bg-transparent text-[13px] text-pastel-ink dark:text-pastel-inkDark outline-none placeholder:text-pastel-sub/70 dark:placeholder:text-pastel-subDark/70"
        />
      </div>

      <div className="flex items-center gap-2" ref={panelRef}>
        <button
          onClick={toggleDarkMode}
          className="h-9 w-9 rounded-full bg-white dark:bg-pastel-cardDark border border-pastel-brandLight dark:border-pastel-borderDark flex items-center justify-center text-pastel-sub dark:text-pastel-subDark hover:text-pastel-ink dark:hover:text-pastel-inkDark transition-colors"
          aria-pressed={darkMode}
          aria-label="Toggle dark mode"
        >
          {darkMode ? <Sun size={16} /> : <Moon size={16} />}
        </button>
        <div className="relative">
          <button
            onClick={() => setOpenPanel((panel) => panel === 'grid' ? null : 'grid')}
            className="h-9 w-9 rounded-full bg-white dark:bg-pastel-cardDark border border-pastel-brandLight dark:border-pastel-borderDark flex items-center justify-center text-pastel-sub dark:text-pastel-subDark hover:text-pastel-ink dark:hover:text-pastel-inkDark transition-colors"
            aria-expanded={openPanel === 'grid'}
            aria-label="Open quick views"
          >
            <Grid3x3 size={16} aria-hidden="true" />
          </button>
          {openPanel === 'grid' && (
            <div className="absolute right-0 mt-2 w-52 rounded-2xl bg-white dark:bg-pastel-cardDark border border-pastel-brandLight dark:border-pastel-borderDark shadow-lg p-3 z-50">
              <p className="text-[12px] font-semibold text-pastel-ink dark:text-pastel-inkDark">Quick views</p>
              <div className="mt-2 space-y-0.5">
                {[
                  ['Patients', '/patients'],
                  ['Priority Watchlist', '/watchlist'],
                  ['Ward Heatmap', '/heatmap'],
                  ['Patient Timeline', '/timeline'],
                ].map(([label, path]) => (
                  <button
                    key={path}
                    onClick={() => {
                      navigate(path);
                      setOpenPanel(null);
                    }}
                    className="w-full rounded-lg px-2.5 py-2 text-left text-[12px] text-pastel-sub dark:text-pastel-subDark hover:bg-pastel-bg dark:hover:bg-white/5 hover:text-pastel-ink dark:hover:text-pastel-inkDark transition-colors"
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
        <button
          onClick={() => downloadWardReport(commandPatients)}
          className="h-9 w-9 rounded-full bg-white dark:bg-pastel-cardDark border border-pastel-brandLight dark:border-pastel-borderDark flex items-center justify-center text-pastel-sub dark:text-pastel-subDark hover:text-pastel-ink dark:hover:text-pastel-inkDark transition-colors"
          aria-label="Download ward report"
          title="Download ward report"
        >
          <Download size={16} aria-hidden="true" />
        </button>
        <NotificationBell />
        <div className="relative pl-2">
          <button
            onClick={() => setOpenPanel((panel) => panel === 'profile' ? null : 'profile')}
            className="flex items-center gap-2.5 text-left"
            aria-expanded={openPanel === 'profile'}
            aria-label="Open profile menu"
          >
            <div className="h-9 w-9 rounded-full bg-pastel-amberLight dark:bg-pastel-amberLightDark text-pastel-amber flex items-center justify-center text-[12px] font-semibold">{initials || 'NT'}</div>
            <div>
              <p className="text-[13px] font-medium text-pastel-ink dark:text-pastel-inkDark leading-tight">{displayName}</p>
              <p className="text-[11px] text-pastel-sub dark:text-pastel-subDark leading-tight">{displayRole}</p>
            </div>
          </button>
          {openPanel === 'profile' && (
            <div className="absolute right-0 mt-2 w-40 rounded-2xl bg-white dark:bg-pastel-cardDark border border-pastel-brandLight dark:border-pastel-borderDark shadow-lg p-2 z-50">
              <button
                onClick={logout}
                className="w-full rounded-lg px-2.5 py-2 text-left text-[12px] text-pastel-sub dark:text-pastel-subDark hover:bg-pastel-bg dark:hover:bg-white/5 hover:text-pastel-ink dark:hover:text-pastel-inkDark transition-colors"
              >
                Log out
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
