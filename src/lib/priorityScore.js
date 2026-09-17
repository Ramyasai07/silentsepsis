// Priority Watchlist scoring. This is a documented weighted heuristic over
// real computed signals — not a trained model, and not "current risk sorted
// descending" either. Every input is derived from data already on the
// patient object; nothing here is randomized or hand-picked per patient.
//
// score = 0.40 * currentRisk
//       + 0.30 * accelerationScore   (is the trend getting worse, faster?)
//       + optional certainty         (included only if backend provides it)
//       + 0.15 * stalenessScore      (how long since we last saw data?)

function computeAcceleration(vitals) {
  // vitals is oldest -> newest. Look at the rate of change of respiratory
  // rate over the last two intervals; a widening gap means the trend is
  // accelerating, not just present.
  if (vitals.length < 3) return 0;
  const n = vitals.length;
  const recentDelta = vitals[n - 1].rr - vitals[n - 2].rr;
  const priorDelta = vitals[n - 2].rr - vitals[n - 3].rr;
  return recentDelta - priorDelta; // positive = worsening faster
}

function parseHoursAgo(lastVitalsLabel) {
  const match = /(\d+)\s*min/i.exec(lastVitalsLabel || '');
  if (match) return Number(match[1]) / 60;
  const hourMatch = /(\d+)\s*hour/i.exec(lastVitalsLabel || '');
  if (hourMatch) return Number(hourMatch[1]);
  return 0.5;
}

export function scorePatients(patients) {
  return patients
    .map((p) => {
      const acceleration = computeAcceleration(p.vitals);
      const accelerationScore = Math.max(0, Math.min(100, acceleration * 20)); // clamp to 0-100
      const hoursSinceObserved = parseHoursAgo(p.lastVitals);
      const stalenessScore = Math.min(100, hoursSinceObserved * 15); // longer gap = higher priority to recheck

      const signals = [
        [p.risk, 0.4],
        [accelerationScore, 0.3],
        [p.certainty, 0.15],
        [stalenessScore, 0.15],
      ].filter(([value]) => value != null);
      const weightTotal = signals.reduce((sum, [, weight]) => sum + weight, 0);
      const priorityScore = weightTotal
        ? signals.reduce((sum, [value, weight]) => sum + value * weight, 0) / weightTotal
        : 0;

      // Simple linear projection: current risk plus acceleration trend
      // extrapolated 3 intervals forward, clamped to [0, 100].
      const projectedRisk = p.risk == null
        ? null
        : Math.max(0, Math.min(100, Math.round(p.risk + acceleration * 3)));

      const explanation = buildExplanation(p, acceleration, hoursSinceObserved);

      return { ...p, priorityScore, accelerationScore, projectedRisk, hoursSinceObserved, explanation };
    })
    .sort((a, b) => b.priorityScore - a.priorityScore);
}

function buildExplanation(p, acceleration, hoursSinceObserved) {
  const parts = [];
  if (acceleration > 1) {
    parts.push(`Respiratory rate is climbing faster than in the prior interval (Δ +${acceleration.toFixed(1)}/min between readings)`);
  } else if (acceleration < -1) {
    parts.push(`Respiratory rate trend is flattening (Δ ${acceleration.toFixed(1)}/min between readings)`);
  } else {
    parts.push('Respiratory rate trend is roughly stable between readings');
  }
  if (hoursSinceObserved > 1) {
    parts.push(`last observed ${hoursSinceObserved.toFixed(1)}h ago, longer than ideal for this risk tier`);
  }
  if (p.certainty != null) parts.push(`model certainty ${p.certainty}%`);
  return parts.join('; ') + '.';
}
