import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { useAppStore } from '../../store/useAppStore';

const COLORS = {
  Critical:      '#FF6B9D',
  Warning:       '#FDB022',
  Stable:        '#20C5A0',
  'Trending up': '#FDB022', // maps to MODERATE risk — same amber as Warning
};

export function WardCompositionCard({ counts }) {
  const darkMode = useAppStore((s) => s.darkMode);
  const data = Object.entries(counts).map(([name, value]) => ({ name, value }));

  return (
    <div className="rounded-2xl bg-white dark:bg-pastel-cardDark p-5 shadow-[0_1px_2px_rgba(30,27,57,0.04),0_8px_20px_rgba(30,27,57,0.05)] dark:shadow-none dark:border dark:border-pastel-borderDark">
      <p className="text-[14px] font-semibold text-pastel-ink dark:text-pastel-inkDark mb-3">Ward composition</p>
      <div className="flex items-center gap-4">
        <div className="h-[130px] w-[130px] shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data} dataKey="value" nameKey="name" innerRadius={38} outerRadius={58} paddingAngle={3}>
                {data.map((d) => (
                  <Cell key={d.name} fill={COLORS[d.name]} stroke="none" />
                ))}
              </Pie>
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: darkMode ? '1px solid #283335' : '1px solid #F3F5F4', background: darkMode ? '#1B2426' : '#fff', color: darkMode ? '#E9EEEE' : '#1B2426' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="space-y-2">
          {data.map((d) => (
            <div key={d.name} className="flex items-center gap-2 text-[12.5px]">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: COLORS[d.name] }} aria-hidden="true" />
              <span className="text-pastel-sub dark:text-pastel-subDark">{d.name}</span>
              <span className="font-semibold text-pastel-ink dark:text-pastel-inkDark">{d.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
