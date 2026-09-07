export function RingStatCard({ title, total, segments }) {
  const sum = segments.reduce((a, s) => a + s.value, 0);
  const radius = 30;
  const circumference = 2 * Math.PI * radius;
  let offsetAcc = 0;

  return (
    <div className="rounded-2xl bg-white dark:bg-pastel-cardDark p-5 shadow-[0_1px_2px_rgba(30,27,57,0.04),0_8px_20px_rgba(30,27,57,0.05)] dark:shadow-none dark:border dark:border-pastel-borderDark">
      <p className="text-[13px] font-medium text-pastel-sub dark:text-pastel-subDark mb-3">{title}</p>
      <div className="flex items-center gap-4">
        <svg width="76" height="76" viewBox="0 0 76 76" role="img" aria-label={`${title}: ${total} total`}>
          <circle cx="38" cy="38" r={radius} fill="none" className="stroke-pastel-brandLight dark:stroke-pastel-brandLightDark" strokeWidth="9" />
          {segments.map((seg, i) => {
            const len = sum === 0 ? 0 : (seg.value / sum) * circumference;
            const el = (
              <circle
                key={seg.label}
                cx="38" cy="38" r={radius} fill="none" stroke={seg.color} strokeWidth="9"
                strokeDasharray={`${len} ${circumference - len}`}
                strokeDashoffset={-offsetAcc}
                strokeLinecap="round"
                transform="rotate(-90 38 38)"
              />
            );
            offsetAcc += len;
            return el;
          })}
          <text x="38" y="43" textAnchor="middle" fontSize="18" fontWeight="700" className="fill-pastel-ink dark:fill-pastel-inkDark">{total}</text>
        </svg>
        <div className="space-y-1.5">
          {segments.map((seg) => (
            <div key={seg.label} className="flex items-center gap-2 text-[12px]">
              <span className="h-2 w-2 rounded-full" style={{ background: seg.color }} aria-hidden="true" />
              <span className="text-pastel-sub dark:text-pastel-subDark">{seg.label}</span>
              <span className="font-semibold text-pastel-ink dark:text-pastel-inkDark">{seg.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
