import { useState, useRef } from 'react';
import { ZoomIn, ZoomOut, Search, MapPin } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { ClinicSidebar } from '../components/clinic/ClinicSidebar';
import { ClinicTopbar } from '../components/clinic/ClinicTopbar';
import { PatientDetailDrawer } from '../components/clinic/PatientDetailDrawer';
import { wardFloors } from '../data/wardRooms';

// Design decision: reduce alarm fatigue. Only critical tiles are visually loud;
// stable or watching patients should recede so the board does not compete
// for attention. Visual weight is therefore applied by risk thresholds below.
const RISK_CRITICAL = 80; // >= this is critical (loud)
const RISK_WATCHING = 50; // 50-79 is watching (calmer tint + border)

const STATUS_COLOR = { critical: '#E24B4A', warning: '#EF9F27', watchingBorder: '#EF9F27', watchingFill: '#FAEEDA', watchingText: '#854F0B', stable: '#DDE3E3', empty: '#DDE3E3' };
const STATUS_LABEL = { critical: 'Critical', warning: 'Watching', stable: 'Stable', empty: 'Unoccupied' };

const PLAN_WIDTH = 720; // visual floor plan size used for pan constraints
const PLAN_HEIGHT = 320;

function hexToRgba(hex, alpha = 1) {
  const h = hex.replace('#', '');
  const bigint = parseInt(h, 16);
  const r = (bigint >> 16) & 255;
  const g = (bigint >> 8) & 255;
  const b = bigint & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function RoomTile({ entry, onSelect, dim }) {
  const status = entry.patient ? entry.patient.status : 'empty';
  const [hover, setHover] = useState(false);

  const initials = entry.patient
    ? entry.patient.name
        .split(' ')
        .map((s) => s[0])
        .slice(0, 2)
        .join('')
        .toUpperCase()
    : null;

  // Determine visual tier from risk value (not just status string):
  // - risk >= RISK_CRITICAL => critical (loud)
  // - RISK_WATCHING <= risk < RISK_CRITICAL => watching (calm tint + border)
  // - risk < RISK_WATCHING => stable (resembles empty)
  const risk = entry.patient ? Number(entry.patient.risk ?? 0) : null;
  const tier = entry.patient ? (risk >= RISK_CRITICAL ? 'critical' : risk >= RISK_WATCHING ? 'watching' : 'stable') : 'empty';

  // style building per tier
  const commonStyle = { opacity: dim ? 0.22 : 1 };

  const criticalStyle = {
    background: STATUS_COLOR.critical,
    color: '#FFFFFF',
    border: 'none',
    boxShadow: '0 6px 18px rgba(226,75,74,0.12)',
    animation: 'pulse-ring 1.8s infinite',
  };

  const watchingStyle = {
    background: STATUS_COLOR.watchingFill,
    color: STATUS_COLOR.watchingText,
    borderColor: STATUS_COLOR.watchingBorder,
    borderWidth: '1.5px',
  };

  const stableStyle = {
    background: 'transparent',
    color: undefined,
    borderWidth: '1.5px',
  };

  return (
    <div
      className="relative flex items-center justify-center"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      {/* inject keyframes for pulse ring locally */}
      <style>{`
        @keyframes pulse-ring { 0%, 100% { box-shadow: 0 0 0 0 rgba(226,75,74,0.5); } 50% { box-shadow: 0 0 0 8px rgba(226,75,74,0); } }
      `}</style>

      <motion.button
        onClick={() => entry.patient && onSelect(entry.patient.id)}
        disabled={!entry.patient}
        layout
        whileHover={entry.patient ? { translateY: -6, scale: 1.03 } : {}}
        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
        className={`h-16 w-28 rounded-xl flex flex-col items-center justify-center text-[11.5px] font-semibold transition-colors duration-300 border border-pastel-brandLight dark:border-pastel-borderDark ${
          entry.patient ? 'cursor-pointer' : 'cursor-default'
        }`}
        style={{
          ...(tier === 'critical' ? criticalStyle : {}),
          ...(tier === 'watching' ? watchingStyle : {}),
          ...(tier === 'stable' || tier === 'empty' ? { background: 'transparent' } : {}),
          ...(tier === 'stable' || tier === 'empty' ? { borderColor: undefined } : {}),
          ...(tier === 'stable' ? { borderColor: undefined } : {}),
          boxShadow: tier === 'stable' ? 'inset 0 2px 8px rgba(11,13,14,0.04)' : undefined,
          ...(tier === 'stable' || tier === 'empty' ? { borderWidth: '1.5px' } : {}),
          ...(tier === 'stable' || tier === 'empty' ? { borderColor: undefined } : {}),
          ...commonStyle,
        }}
      >
        {entry.patient ? (
          <>
            <div className={`text-[13px] font-bold leading-none ${tier === 'critical' ? 'text-white' : 'text-pastel-sub dark:text-pastel-subDark'}`}>
              {initials}
            </div>
            <div className={`text-[11px] mt-0.5 ${tier === 'critical' ? 'text-white' : 'text-pastel-sub dark:text-pastel-subDark'}`}>
              {entry.room} · risk {risk}
            </div>
          </>
        ) : (
          <div className="text-[11px] text-pastel-sub dark:text-pastel-subDark">{entry.room}</div>
        )}
      </motion.button>

      <AnimatePresence>
        {hover && entry.patient && !dim && (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 6 }}
            transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
            className="absolute z-30 top-full mt-2 left-1/2 -translate-x-1/2 w-56 rounded-2xl bg-white dark:bg-pastel-cardDark border border-pastel-brandLight dark:border-pastel-borderDark p-3 shadow-[0_6px_20px_rgba(11,13,14,0.08)] text-pastel-ink dark:text-pastel-inkDark pointer-events-none"
          >
            <p className="text-[12px] font-semibold">{entry.patient.name}</p>
            <p className="text-[11px] text-pastel-sub dark:text-pastel-subDark mb-1">Risk {entry.patient.risk} · {STATUS_LABEL[status]}</p>
            <p className="text-[10.5px] opacity-80 leading-snug">{entry.patient.explanation}</p>
            <p className="text-[10px] opacity-60 mt-1.5">Last vitals {entry.patient.lastVitals}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function WardHeatmap() {
  const [floorId, setFloorId] = useState('3');
  const [zoom, setZoom] = useState(1);
  const [query, setQuery] = useState('');
  const [selectedId, setSelectedId] = useState(null);
  const dragState = useRef(null);
  const [pan, setPan] = useState({ x: 0, y: 0 });

  const floor = wardFloors.find((f) => f.id === floorId);
  const allPatients = wardFloors.flatMap((f) => f.rooms.map((r) => r.patient).filter(Boolean));
  const selectedPatient = allPatients.find((p) => p.id === selectedId);

  function clamp(val, a, b) {
    return Math.max(a, Math.min(b, val));
  }

  function onMouseDown(e) {
    dragState.current = { startX: e.clientX - pan.x, startY: e.clientY - pan.y };
  }
  function onMouseMove(e) {
    if (!dragState.current) return;
    const rawX = e.clientX - dragState.current.startX;
    const rawY = e.clientY - dragState.current.startY;

    // compute soft bounds so plan can't be dragged entirely off-screen
    const maxX = 200;
    const minX = -Math.max(0, PLAN_WIDTH * zoom - (window.innerWidth - 240));
    const maxY = 80;
    const minY = -Math.max(0, PLAN_HEIGHT * zoom - 200);

    setPan({ x: clamp(rawX, minX, maxX), y: clamp(rawY, minY, maxY) });
  }
  function onMouseUp() {
    dragState.current = null;
  }

  const counts = { critical: 0, warning: 0, stable: 0, empty: 0 };
  floor.rooms.forEach((r) => counts[r.patient ? r.patient.status : 'empty']++);

  return (
    <div className="min-h-screen bg-pastel-bg dark:bg-pastel-bgDark flex transition-colors">
      <ClinicSidebar />
      <div className="flex-1 min-w-0">
        <ClinicTopbar />
        <main className="px-6 pb-8 max-w-[1100px]">
          <div className="flex items-center justify-between mb-1">
            <h1 className="text-[19px] font-semibold text-pastel-ink dark:text-pastel-inkDark">Ward heatmap</h1>
          </div>
          <p className="text-[13px] text-pastel-sub dark:text-pastel-subDark mb-4">Live occupancy and risk across all floors.</p>

          <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
            <div className="flex gap-1.5 border-b border-transparent">
                {wardFloors.map((f) => (
                  <button
                    key={f.id}
                    onClick={() => setFloorId(f.id)}
                    className={`px-3 pb-2 text-[12.5px] font-medium transition-colors ${
                      floorId === f.id
                        ? 'text-pastel-ink dark:text-pastel-inkDark border-b-2 border-pastel-brand'
                        : 'text-pastel-sub dark:text-pastel-subDark'
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>

            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2 h-9 px-3 rounded-full bg-white dark:bg-pastel-cardDark border border-pastel-brandLight dark:border-pastel-borderDark w-52">
                <Search size={13} className="text-pastel-sub dark:text-pastel-subDark" aria-hidden="true" />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Find room or patient…"
                  className="flex-1 bg-transparent text-[12.5px] text-pastel-ink dark:text-pastel-inkDark outline-none placeholder:text-pastel-sub/70"
                />
              </div>
              <button onClick={() => setZoom((z) => Math.max(0.6, z - 0.2))} className="h-9 w-9 rounded-full bg-white dark:bg-pastel-cardDark border border-pastel-brandLight dark:border-pastel-borderDark flex items-center justify-center text-pastel-sub dark:text-pastel-subDark" aria-label="Zoom out">
                <ZoomOut size={15} />
              </button>
              <button onClick={() => setZoom((z) => Math.min(1.8, z + 0.2))} className="h-9 w-9 rounded-full bg-white dark:bg-pastel-cardDark border border-pastel-brandLight dark:border-pastel-borderDark flex items-center justify-center text-pastel-sub dark:text-pastel-subDark" aria-label="Zoom in">
                <ZoomIn size={15} />
              </button>
            </div>
          </div>

          <div className="flex items-center gap-4 mb-4">
            {Object.entries(STATUS_LABEL).map(([key, label]) => (
              <span key={key} className="flex items-center gap-2 text-[11.5px] text-pastel-sub dark:text-pastel-subDark">
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{
                    background: STATUS_COLOR[key],
                    boxShadow: `0 0 12px ${hexToRgba(STATUS_COLOR[key], 0.08)}`,
                  }}
                  aria-hidden="true"
                />
                {label} ({counts[key]})
              </span>
            ))}
          </div>

          <div
            className="rounded-2xl bg-white dark:bg-pastel-cardDark border border-pastel-brandLight dark:border-pastel-borderDark p-8 overflow-hidden cursor-grab active:cursor-grabbing select-none"
            onMouseDown={onMouseDown}
            onMouseMove={onMouseMove}
            onMouseUp={onMouseUp}
            onMouseLeave={onMouseUp}
          >
            <motion.div
              style={{ transformOrigin: 'top left' }}
              animate={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }}
              transition={dragState.current ? { duration: 0 } : { duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
            >
              {/* Floor plan: corridor with rooms along top & bottom, nurse-station marker in center */}
              <div className="w-[720px] h-[320px] relative">
                {/* Corridor */}
                <div className="absolute left-6 right-6 top-1/2 -translate-y-1/2 h-12 flex items-center justify-center">
                  <div className="w-full h-2 rounded-full bg-pastel-brandLight dark:bg-pastel-brandLightDark" />
                </div>

                {/* Nurse station marker */}
                <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex items-center gap-2">
                  <div className="rounded-full bg-white dark:bg-pastel-cardDark border border-pastel-brandLight dark:border-pastel-borderDark p-2 shadow-[0_6px_20px_rgba(11,13,14,0.06)]">
                    <MapPin size={18} className="text-pastel-brand" />
                  </div>
                  <div className="text-[12px] font-medium text-pastel-sub dark:text-pastel-subDark">Nurse station</div>
                </div>

                {/* Top row rooms */}
                <div className="absolute left-6 right-6 top-[20%] flex justify-between items-center gap-3 px-2">
                  {floor.rooms.slice(0, Math.ceil(floor.rooms.length / 2)).map((entry) => {
                    const dim = query && !(entry.room.toLowerCase().includes(query.toLowerCase()) || entry.patient?.name.toLowerCase().includes(query.toLowerCase()));
                    return <RoomTile key={entry.room} entry={entry} onSelect={setSelectedId} dim={dim} />;
                  })}
                </div>

                {/* Bottom row rooms */}
                <div className="absolute left-6 right-6 bottom-[20%] flex justify-between items-center gap-3 px-2">
                  {floor.rooms.slice(Math.ceil(floor.rooms.length / 2)).map((entry) => {
                    const dim = query && !(entry.room.toLowerCase().includes(query.toLowerCase()) || entry.patient?.name.toLowerCase().includes(query.toLowerCase()));
                    return <RoomTile key={entry.room} entry={entry} onSelect={setSelectedId} dim={dim} />;
                  })}
                </div>
              </div>
            </motion.div>
          </div>
        </main>
      </div>
      {selectedPatient && <PatientDetailDrawer patient={selectedPatient} onClose={() => setSelectedId(null)} />}
    </div>
  );
}
