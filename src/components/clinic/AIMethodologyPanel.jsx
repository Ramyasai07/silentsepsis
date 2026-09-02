import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Activity,
  AlertTriangle,
  Check,
  GitBranch,
  Layers,
  ShieldCheck,
  Sparkles,
  X,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useAppStore } from '../../store/useAppStore';

const MODEL_DATA = [
  { model: 'XGBoost', metric: 'ROC-AUC', value: 0.847, color: '#0E7490' },
  { model: 'XGBoost', metric: 'PR-AUC', value: 0.48, color: '#FDB022' },
  { model: 'GRU', metric: 'ROC-AUC', value: 0.807, color: '#20C5A0' },
  { model: 'GRU', metric: 'PR-AUC', value: 0.086, color: '#E0607E' },
  { model: 'LSTM baseline', metric: 'ROC-AUC', value: 0.79, color: '#0E7490' },
  { model: 'LSTM baseline', metric: 'PR-AUC', value: 0.082, color: '#FDB022' },
];

const SECTIONS = [
  { id: 'live', label: 'Live API', icon: Activity, tone: 'brand' },
  { id: 'models', label: 'Models', icon: GitBranch, tone: 'amber' },
  { id: 'features', label: 'Features', icon: Layers, tone: 'teal' },
  { id: 'trust', label: 'Trust', icon: ShieldCheck, tone: 'pink' },
];

function useCountUp(target, open) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!open) return undefined;
    let frame;
    const startedAt = performance.now();
    const duration = 850;
    const tick = (now) => {
      const progress = Math.min((now - startedAt) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(target * eased);
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, open]);

  return value.toFixed(3);
}

function Section({ id, tone, icon: Icon, title, children, index }) {
  const colors = {
    brand: 'bg-pastel-brandLight dark:bg-pastel-brandLightDark text-pastel-brand',
    amber: 'bg-pastel-amberLight dark:bg-pastel-amberLightDark text-pastel-amber',
    teal: 'bg-pastel-tealLight dark:bg-pastel-tealLightDark text-pastel-teal',
    pink: 'bg-pastel-pinkLight dark:bg-pastel-pinkLightDark text-pastel-pink',
  };
  return (
    <motion.section
      id={id}
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.12 + index * 0.07 }}
      className="snap-start scroll-mt-4 border-b border-pastel-brandLight dark:border-pastel-borderDark pb-7 pt-5"
    >
      <div className="flex gap-3">
        <div className={`h-9 w-9 shrink-0 rounded-xl flex items-center justify-center ${colors[tone]}`}>
          <Icon size={17} aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <h2 className="text-[15px] font-semibold text-pastel-ink dark:text-pastel-inkDark">{title}</h2>
          <div className="mt-3 text-[12.5px] leading-relaxed text-pastel-sub dark:text-pastel-subDark">{children}</div>
        </div>
      </div>
    </motion.section>
  );
}

function Metric({ label, value, suffix }) {
  const count = useCountUp(value, true);
  return (
    <div className="rounded-xl bg-pastel-bg dark:bg-pastel-bgDark p-3">
      <p className="text-[10px] uppercase tracking-wide text-pastel-sub dark:text-pastel-subDark">{label}</p>
      <p className="mt-1 text-[22px] font-semibold tabular-nums text-pastel-ink dark:text-pastel-inkDark">{count}{suffix}</p>
    </div>
  );
}

export function AIMethodologyPanel({ open, onClose }) {
  const darkMode = useAppStore((state) => state.darkMode);
  const panelRef = useRef(null);
  const [activeSection, setActiveSection] = useState('live');
  const rocAuc = useCountUp(0.847, open);
  const prAuc = useCountUp(0.48, open);

  useEffect(() => {
    if (!open) return undefined;
    const previousFocus = document.activeElement;
    const focusable = 'button, a, input, select, textarea, [tabindex]:not([tabindex="-1"])';
    const firstButton = panelRef.current?.querySelector(focusable);
    firstButton?.focus();

    function handleKeyDown(event) {
      if (event.key === 'Escape') onClose();
      if (event.key !== 'Tab' || !panelRef.current) return;
      const elements = [...panelRef.current.querySelectorAll(focusable)];
      const first = elements[0];
      const last = elements[elements.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      previousFocus?.focus?.();
    };
  }, [open, onClose]);

  function jumpTo(id) {
    setActiveSection(id);
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[70]" role="dialog" aria-modal="true" aria-labelledby="ai-methodology-title">
          <motion.button
            type="button"
            aria-label="Close methodology panel"
            className="absolute inset-0 h-full w-full cursor-default bg-black/25 backdrop-blur-[3px]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.aside
            ref={panelRef}
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="absolute right-0 top-0 flex h-full w-full max-w-[570px] flex-col bg-white shadow-2xl dark:bg-pastel-cardDark"
          >
            <header className="shrink-0 border-b border-pastel-brandLight bg-pastel-brandLight/50 px-5 pb-4 pt-5 dark:border-pastel-borderDark dark:bg-pastel-brandLightDark/60">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="mb-2 flex items-center gap-2 text-pastel-brand"><Sparkles size={15} /><span className="text-[11px] font-semibold uppercase tracking-[0.16em]">Methodology</span></div>
                  <h1 id="ai-methodology-title" className="text-[21px] font-semibold tracking-tight text-pastel-ink dark:text-pastel-inkDark">How SilentSepsis Scores Risk</h1>
                  <p className="mt-1 text-[12.5px] text-pastel-sub dark:text-pastel-subDark">A transparent look at what's real, what's research, and what's still missing.</p>
                </div>
                <button type="button" onClick={onClose} aria-label="Close" className="rounded-lg p-1.5 text-pastel-sub hover:bg-white/70 dark:hover:bg-white/10"><X size={18} /></button>
              </div>
              <nav aria-label="Methodology sections" className="mt-5 flex gap-1 overflow-x-auto">
                {SECTIONS.map(({ id, label, icon: Icon }) => (
                  <button key={id} type="button" onClick={() => jumpTo(id)} className={`flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-[11px] font-medium transition-colors ${activeSection === id ? 'bg-pastel-brand text-white' : 'bg-white/70 text-pastel-sub dark:bg-white/10 dark:text-pastel-subDark'}`}>
                    <Icon size={12} aria-hidden="true" /> {label}
                  </button>
                ))}
              </nav>
            </header>

            <div className="snap-y snap-mandatory overflow-y-auto px-5 pb-8" onScroll={(event) => {
              const current = [...event.currentTarget.querySelectorAll('section')].find((section) => section.getBoundingClientRect().top > 100);
              if (current) setActiveSection(current.id);
            }}>
              <Section id="live" tone="brand" icon={Activity} title="What's live in the API right now" index={0}>
                <div className="grid grid-cols-2 gap-2">
                  <div className="col-span-2 rounded-xl border border-pastel-brandLight p-3 dark:border-pastel-borderDark"><span className="font-semibold text-pastel-ink dark:text-pastel-inkDark">OnlineLogisticPredictor</span><span className="ml-2 text-[11px] text-pastel-brand">online-logistic-v1-calibrated</span></div>
                  <p className="col-span-2"><strong className="font-semibold text-pastel-ink dark:text-pastel-inkDark">15 features:</strong> HR, O2Sat, Temp, SBP, DBP, Resp, MAP, Age, Gender, plus missingness flags for HR/O2Sat/Temp/SBP/DBP/Resp.</p>
                  <p><strong className="font-semibold text-pastel-ink dark:text-pastel-inkDark">Calibration:</strong> Platt scaling, decision threshold ≈ 0.0315</p>
                  <p><strong className="font-semibold text-pastel-ink dark:text-pastel-inkDark">Wired to:</strong> app/api/v1/predictions.py and app/tasks/risk_evaluation.py</p>
                </div>
              </Section>

              <Section id="models" tone="amber" icon={GitBranch} title="Model comparison" index={1}>
                <div className="mb-3 grid grid-cols-2 gap-2"><Metric label="XGBoost ROC-AUC" value={0.847} /><Metric label="XGBoost PR-AUC" value={0.48} /></div>
                <div className="h-[235px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={MODEL_DATA} layout="vertical" margin={{ top: 4, right: 12, bottom: 4, left: 12 }}>
                      <CartesianGrid horizontal={false} stroke={darkMode ? '#283335' : '#E1EFF0'} />
                      <XAxis type="number" domain={[0, 0.9]} tick={{ fontSize: 10, fill: darkMode ? '#8FA0A2' : '#6B7A7C' }} />
                      <YAxis type="category" dataKey="model" width={82} tick={{ fontSize: 10, fill: darkMode ? '#8FA0A2' : '#6B7A7C' }} />
                      <Tooltip formatter={(value, name) => [Number(value).toFixed(3), name]} contentStyle={{ background: darkMode ? '#1B2426' : '#fff', borderColor: darkMode ? '#283335' : '#E1EFF0', fontSize: 11 }} />
                      <Bar dataKey="value" name="Test-set score" radius={[0, 4, 4, 0]} animationDuration={850}>
                        {MODEL_DATA.map((entry) => <Cell key={`${entry.model}-${entry.metric}`} fill={entry.color} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <p className="mt-2 text-[11px] font-medium text-pastel-amber">Test-set patient-level metrics. Trained and benchmarked. Not the model currently serving predictions.</p>
                <p className="mt-1 text-[11px]">ROC-AUC / PR-AUC: XGBoost (calibrated) 0.847 / 0.480; GRU 0.807 (val) / 0.086 (val); LSTM baseline 0.790 (val) / 0.082 (val).</p>
              </Section>

              <Section id="features" tone="teal" icon={Layers} title="How a feature becomes a risk score" index={2}>
                <div className="space-y-2">
                  {['patient vital', 'deviation from personal 6-hour baseline', 'rolling 3-reading trend', 'shock index [HR ÷ systolic BP]', 'weighted score'].map((step, index) => <motion.div key={step} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 + index * 0.1 }} className="flex items-center gap-2"><span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-pastel-teal text-[10px] font-semibold text-white">{index + 1}</span><span>{step}</span></motion.div>)}
                </div>
                <p className="mt-4">Built from src/sepsis_ai/features/trend_features.py. This personalized-baseline feature layer exists in code but is <strong className="font-semibold text-pastel-ink dark:text-pastel-inkDark">NOT yet wired into any deployed model's feature list</strong>.</p>
                <p className="mt-2">It's a research layer for future XGBoost work (per ai/docs/feature_engineering_notes.md).</p>
              </Section>

              <Section id="trust" tone="pink" icon={ShieldCheck} title="Explainability & calibration" index={3}>
                <ul className="space-y-2"><li><strong className="font-semibold text-pastel-ink dark:text-pastel-inkDark">Every prediction</strong> returns feature_contributions: which vitals drove the score, in which direction, from app/ml/base.py's PredictionResult dataclass.</li><li>SHAP analysis (analyze_lstm_shap.py, analyze_lstm_shap_direction.py) was run against the LSTM model to sanity-check feature importance/direction.</li><li>All models report Brier score alongside accuracy metrics, because calibrated probabilities matter more than raw scores in a clinical tool.</li></ul>
                <div className="mt-5 rounded-xl bg-pastel-pinkLight p-3 dark:bg-pastel-pinkLightDark"><p className="mb-2 font-semibold text-pastel-ink dark:text-pastel-inkDark">Reproducibility status</p><div className="space-y-2"><p><Check size={13} className="mr-1 inline text-pastel-teal" />XGBoost: trained weights committed (ai/artifacts/xgboost-v1/model.json) — fully runnable</p><p><AlertTriangle size={13} className="mr-1 inline text-pastel-amber" />Online logistic: metadata and test metrics are committed, but the actual model/imputer/calibrator .joblib files are gitignored and not present on this branch — the live endpoint will throw FileNotFoundError until they're regenerated via ai/scripts/train_online_logistic.py + calibrate_online_logistic.py</p><p><AlertTriangle size={13} className="mr-1 inline text-pastel-amber" />LSTM/GRU: results documented in ai/docs/, but ai/models/ (the .keras weights and raw eval JSONs) isn't committed — treat these numbers as reported research results, not something you can currently re-run</p><p><span className="mr-1 inline text-pastel-amber">•</span>Training data itself (ai/data/processed/*.csv) is also gitignored by design</p></div></div>
                <div className="mt-5"><h3 className="font-semibold text-pastel-ink dark:text-pastel-inkDark">Limitations</h3><ul className="mt-2 list-disc space-y-1 pl-4"><li>PR-AUC remains low across all models — expected given severe class imbalance in real sepsis incidence.</li><li>No clinically validated early-warning lead time can be claimed yet — sequence metadata doesn't support exact patient-level timing.</li><li>This is a research-grade clinical decision-support pipeline, not a diagnostic tool.</li></ul></div>
              </Section>
              <div className="flex justify-between gap-3 pt-5 text-[11px] text-pastel-sub dark:text-pastel-subDark"><span>Research status is part of the product.</span><span>Last reviewed 2026</span></div>
            </div>
          </motion.aside>
        </div>
      )}
    </AnimatePresence>
  );
}