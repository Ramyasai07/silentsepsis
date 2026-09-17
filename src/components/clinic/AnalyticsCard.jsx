export function AnalyticsCard() {
  return (
    <div className="rounded-2xl bg-white dark:bg-pastel-cardDark p-5 shadow-[0_1px_2px_rgba(30,27,57,0.04),0_8px_20px_rgba(30,27,57,0.05)] dark:shadow-none dark:border dark:border-pastel-borderDark">
      <p className="text-[14px] font-semibold text-pastel-ink dark:text-pastel-inkDark mb-3">Alerts generated, by month</p>
      <div className="h-[160px] rounded-xl bg-pastel-bg dark:bg-white/5 border border-pastel-brandLight dark:border-pastel-borderDark flex flex-col items-center justify-center px-5 text-center">
        <p className="text-[13px] font-medium text-pastel-ink dark:text-pastel-inkDark">Monthly alert analytics unavailable</p>
        <p className="mt-1.5 text-[11.5px] leading-5 text-pastel-sub dark:text-pastel-subDark">
          No backend endpoint currently provides historical monthly alert counts.
        </p>
      </div>
    </div>
  );
}
