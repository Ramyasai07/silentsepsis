import { useEffect, useRef, useState } from 'react';
import { NotificationBell } from './clinic/NotificationBell';
import { useAuth } from '../context/AuthContext';

// A real, ticking clock — not decoration. On a ward, "how long ago" only
// means something if the reference clock is actually live.
function useLiveClock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

export default function Topbar({ title, subtitle, alertCount = 0, user = { initials: 'NT', name: 'N. Thomas, RN' }, onSearchChange, searchPlaceholder = 'Search current page…' }) {
  const now = useLiveClock();
  const { user: authUser, logout } = useAuth();
  const [query, setQuery] = useState('');
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef(null);
  const time = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const profile = authUser || user;
  const displayName = profile?.name || profile?.full_name || 'N. Thomas, RN';
  const initials = displayName
    .split(' ')
    .filter(Boolean)
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  useEffect(() => {
    function onClick(event) {
      if (profileRef.current && !profileRef.current.contains(event.target)) setProfileOpen(false);
    }
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  return (
    <div className="topbar">
      <div>
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-sub">{subtitle}</p>}
      </div>
      <div className="topbar-right">
        <div className="live-clock" title="Ward reference time">
          <span className="dot dot-stable" style={{ marginRight: 2 }}></span>
          <span className="mono">{time}</span>
        </div>
        <label className="flex items-center gap-2 h-8 px-2.5 rounded-full border border-[var(--line)] bg-[var(--bg-card)] text-[var(--text-secondary)]" title={onSearchChange ? searchPlaceholder : 'Search current page'}>
          <i className="ti ti-search text-[13px]" aria-hidden="true"></i>
          <input
            type="search"
            value={query}
            onChange={(event) => {
              const nextQuery = event.target.value;
              setQuery(nextQuery);
              onSearchChange?.(nextQuery);
            }}
            placeholder={searchPlaceholder}
            aria-label={searchPlaceholder}
            className="w-28 bg-transparent text-[12px] text-[var(--text-primary)] outline-none placeholder:text-[var(--text-secondary)]"
          />
        </label>
        <NotificationBell />
        <div className="relative flex items-center gap-8" ref={profileRef}>
          <button
            className="avatar"
            onClick={() => setProfileOpen((open) => !open)}
            aria-expanded={profileOpen}
            aria-label="Open profile menu"
          >
            {initials}
          </button>
          {profileOpen && (
            <div className="absolute right-0 top-10 w-40 rounded-xl bg-[var(--bg-card-raised)] border border-[var(--line-strong)] shadow-lg p-2 z-50">
              <p className="px-2.5 py-1.5 text-[12px] text-dim truncate">{displayName}</p>
              <button
                onClick={logout}
                className="w-full rounded-lg px-2.5 py-2 text-left text-[12px] hover:bg-[var(--bg-panel)]"
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
