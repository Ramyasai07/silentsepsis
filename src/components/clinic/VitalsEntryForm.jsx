import { useState } from 'react';
import { X } from 'lucide-react';
import { createPatientVital } from '../../api/patients';

const FIELDS = [
  { key: 'heart_rate', label: 'Heart rate', unit: 'bpm', placeholder: '78' },
  { key: 'respiratory_rate', label: 'Respiratory rate', unit: '/min', placeholder: '16' },
  { key: 'systolic_bp', label: 'Systolic blood pressure', unit: 'mmHg', placeholder: '120' },
  { key: 'diastolic_bp', label: 'Diastolic blood pressure', unit: 'mmHg', placeholder: '80' },
  { key: 'spo2', label: 'Oxygen saturation', unit: '%', placeholder: '97' },
  { key: 'temperature', label: 'Temperature', unit: '°C', placeholder: '37.0' },
];

export function VitalsEntryForm({ patient, onClose }) {
  const [values, setValues] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const filledCount = Object.values(values).filter((v) => v !== '' && v !== undefined).length;

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await createPatientVital(patient.id, {
        heart_rate: Number(values.heart_rate),
        respiratory_rate: Number(values.respiratory_rate),
        systolic_bp: Number(values.systolic_bp),
        diastolic_bp: Number(values.diastolic_bp),
        spo2: Number(values.spo2),
        temperature: Number(values.temperature),
      });
      setSubmitted(true);
      setTimeout(onClose, 1100);
    } catch (err) {
      setError(err?.message || 'Unable to record vitals.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/30 backdrop-blur-[2px]" onClick={onClose}>
      <div
        className="w-[400px] rounded-2xl bg-white dark:bg-pastel-cardDark border border-pastel-brandLight dark:border-pastel-borderDark shadow-2xl p-5"
        onClick={(e) => e.stopPropagation()}
      >
        {submitted ? (
          <div className="py-6 text-center">
            <div className="h-10 w-10 rounded-full bg-pastel-tealLight dark:bg-pastel-tealLightDark text-pastel-teal flex items-center justify-center mx-auto mb-3 text-lg">✓</div>
            <p className="text-[14px] font-medium text-pastel-ink dark:text-pastel-inkDark">Vitals recorded</p>
            <p className="text-[12px] text-pastel-sub dark:text-pastel-subDark mt-1">Re-scoring {patient.name}'s risk trend…</p>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between mb-1">
              <h3 className="text-[14.5px] font-semibold text-pastel-ink dark:text-pastel-inkDark">Add vitals</h3>
              <button onClick={onClose} aria-label="Close" className="text-pastel-sub dark:text-pastel-subDark hover:text-pastel-ink">
                <X size={16} />
              </button>
            </div>
            <p className="text-[12px] text-pastel-sub dark:text-pastel-subDark mb-4">
              {patient.name}, {patient.room} · manual entry for wards without continuous monitors
            </p>

            <form onSubmit={handleSubmit}>
              <div className="grid grid-cols-2 gap-3 mb-5">
                {FIELDS.map((f) => (
                  <div key={f.key}>
                    <label className="block text-[11.5px] font-medium text-pastel-ink dark:text-pastel-inkDark mb-1">
                      {f.label} <span className="text-pastel-sub dark:text-pastel-subDark font-normal">({f.unit})</span>
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      placeholder={f.placeholder}
                      value={values[f.key] || ''}
                      onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
                      className="w-full h-10 px-3 rounded-xl border border-pastel-brandLight dark:border-pastel-borderDark bg-white dark:bg-pastel-bgDark text-[13px] text-pastel-ink dark:text-pastel-inkDark outline-none focus:border-pastel-brand"
                    />
                  </div>
                ))}
              </div>
              {error && <p className="text-[12px] text-red-600 mb-3" role="alert">{error}</p>}

              <div className="flex gap-2">
                <button type="button" onClick={onClose} className="flex-1 h-10 rounded-xl border border-pastel-brandLight dark:border-pastel-borderDark text-[13px] font-medium text-pastel-ink dark:text-pastel-inkDark">
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={filledCount !== FIELDS.length || isSubmitting}
                  className="flex-1 h-10 rounded-xl bg-pastel-brand text-white text-[13px] font-semibold disabled:opacity-40"
                >
                  {isSubmitting ? 'Saving…' : 'Save vitals'}
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
