const STATUS_CHIP = {
  critical: 'bg-pastel-pinkLight dark:bg-pastel-pinkLightDark text-pastel-pink',
  warning: 'bg-pastel-amberLight dark:bg-pastel-amberLightDark text-pastel-amber',
  stable: 'bg-pastel-tealLight dark:bg-pastel-tealLightDark text-pastel-teal',
};
const STATUS_LABEL = { critical: 'Critical', warning: 'Watching', stable: 'Stable' };
const AVATAR_BG = [
  'bg-pastel-brandLight dark:bg-pastel-brandLightDark text-pastel-brand',
  'bg-pastel-amberLight dark:bg-pastel-amberLightDark text-pastel-amber',
  'bg-pastel-tealLight dark:bg-pastel-tealLightDark text-pastel-teal',
  'bg-pastel-pinkLight dark:bg-pastel-pinkLightDark text-pastel-pink',
];

export function PatientTodayList({ patients, onSelect, selectedId }) {
  return (
    <div className="rounded-2xl bg-white dark:bg-pastel-cardDark p-5 shadow-[0_1px_2px_rgba(30,27,57,0.04),0_8px_20px_rgba(30,27,57,0.05)] dark:shadow-none dark:border dark:border-pastel-borderDark h-full">
      <div className="flex items-center justify-between mb-4">
        <p className="text-[14px] font-semibold text-pastel-ink dark:text-pastel-inkDark">Patients needing review</p>
        <button className="text-[12px] font-medium text-pastel-brand">All patients →</button>
      </div>
      <div className="space-y-1">
        {patients.map((p, i) => (
          <button
            key={p.id}
            onClick={() => onSelect(p.id)}
            className={`w-full flex items-center gap-3 p-2.5 rounded-xl transition-colors text-left ${
              selectedId === p.id ? 'bg-pastel-brandLight dark:bg-pastel-brandLightDark' : 'hover:bg-pastel-bg/60 dark:hover:bg-white/5'
            }`}
          >
            <div className={`h-9 w-9 rounded-full flex items-center justify-center text-[11px] font-semibold shrink-0 ${AVATAR_BG[i % 4]}`}>
              {p.name.split(' ').map((n) => n[0]).join('')}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-[13px] font-medium text-pastel-ink dark:text-pastel-inkDark truncate">{p.name}</p>
              <p className="text-[11.5px] text-pastel-sub dark:text-pastel-subDark truncate">{p.room} · {p.explanation}</p>
            </div>
            <span className={`text-[10.5px] font-semibold px-2 py-1 rounded-full shrink-0 ${STATUS_CHIP[p.status]}`}>
              {STATUS_LABEL[p.status] || 'Unassessed'}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
