import { useState, useRef, useEffect } from 'react';
import { Bell } from 'lucide-react';

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function onClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="relative h-9 w-9 rounded-full bg-white dark:bg-pastel-cardDark border border-pastel-brandLight dark:border-pastel-borderDark flex items-center justify-center text-pastel-sub dark:text-pastel-subDark hover:text-pastel-ink dark:hover:text-pastel-inkDark transition-colors"
        aria-expanded={open}
        aria-label="Notifications"
      >
        <Bell size={16} aria-hidden="true" />
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 rounded-2xl bg-white dark:bg-pastel-cardDark border border-pastel-brandLight dark:border-pastel-borderDark shadow-lg overflow-hidden z-50">
          <div className="px-4 py-3 border-b border-pastel-bg dark:border-pastel-borderDark">
            <p className="text-[13px] font-semibold text-pastel-ink dark:text-pastel-inkDark">Notifications</p>
          </div>
          <div className="px-4 py-6 text-center">
            <p className="text-[13px] font-medium text-pastel-ink dark:text-pastel-inkDark">
              Notification feed unavailable
            </p>
            <p className="mt-1.5 text-[11.5px] leading-5 text-pastel-sub dark:text-pastel-subDark">
              No backend notification stream is connected for this demo.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
