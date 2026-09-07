# Milestone 3: Trend-Based Feature Engineering Notes

## Objective

This feature layer augments the canonical patient-time-point data created by the preprocessing pipeline. It is designed to support later XGBoost models by creating interpretable, patient-aware deterioration features that do not rely on future information or cross-patient leakage.

## Why patient-specific baselines are used

Sepsis deterioration is highly patient-specific. A heart rate of 90 may be normal for one patient but elevated for another. A baseline computed per patient anchors each feature to that patient's own prior stability and makes the signal clinically more interpretable.

## Baseline-window definition

For each patient and each core vital, the baseline is calculated from the patient's earliest observations up to the first 6 hours of ICU time. This is implemented as a patient-specific baseline using all available observations during that initial stable window.

If a patient does not have enough observations in the first 6 hours, the script falls back to the available initial observations and records the fallback implicitly by using the mean of the observed early values. No future observations are used.

## Absolute deviation

Absolute deviation is the difference between the current value and the patient-specific baseline:

- current_value - patient_baseline

This value is calculated separately per patient and per vital.

## Percentage deviation

Percentage deviation is:

- ((current_value - baseline) / baseline) * 100

This uses a safe fallback when the baseline is zero or invalid to avoid division-by-zero and inf values. If the baseline is effectively zero, the percentage deviation is set to 0.0.

## First difference / trend

A first difference captures the immediate change from the preceding observation within the same patient. It is defined as:

- current_value - previous_value

The first observation for a patient is assigned 0.0 to avoid introducing a missing value and to preserve a consistent row shape. Differences are never calculated across patient boundaries.

## Rolling-window definition

For each patient, a rolling mean and rolling standard deviation are computed using a 3-observation window. The first observation uses the available period (minimum period 1) so the feature remains defined from the start of each patient's record.

The rolling statistics are computed within patient only. They never mix rows from other patients.

## Why rolling variability is useful

Rolling variability helps capture short-term instability. A patient whose vital signs are drifting upward or whose variability is increasing may be more clinically unstable even if the current value remains within a normal range.

## Composite deterioration feature

The project uses a simple shock-index-style feature:

- shock_index = heart_rate / systolic_bp

This is a clinically interpretable heuristic and is labelled as a project-derived deterioration signal. It is only computed when systolic BP is positive and finite; otherwise it defaults to 0.0.

This is intentionally not presented as a clinically validated risk score. It is a transparent, interpretable feature for later model development.

## Leakage protection

Leakage is prevented by design:

1. All calculations are performed per patient and by patient group.
2. No patient’s rows are mixed with another patient’s rows.
3. The split manifest is checked to ensure patient IDs do not overlap across splits.
4. Baseline windows are built only from the patient’s own earlier observations.
5. No target labels are used to create features.
6. No validation/test statistics are used to derive train-time baseline behavior.

## Limitations

- The baseline uses a fixed 6-hour window and may be less stable for very short ICU stays.
- A simple shock-index feature is interpretable but not clinically validated as a standalone sepsis rule.
- The engineered features are intended as a modeling layer for later XGBoost development, not as a final clinical risk score.
