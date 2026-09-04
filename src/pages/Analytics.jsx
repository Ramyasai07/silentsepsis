import { useState, useEffect, useCallback } from 'react';
import Topbar from '../components/Topbar';
import {
  getPrecisionRecallHistory,
  getStaffResponseByWard,
} from '../api/analytics';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { NetworkError, ApiError } from '../api/client';

// ── Helper ─────────────────────────────────────────────────────────────────────

function errorMessage(err) {
  if (err instanceof NetworkError) return 'Cannot reach server — check your connection.';
  if (err instanceof ApiError) return `Server error: ${err.message}`;
  return 'An unexpected error occurred.';
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function PanelLoading({ height = 200 }) {
  return (
    <div
      style={{
        height,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--text-dim)',
        fontSize: 13,
      }}
    >
      <span className="spinner" style={{ marginRight: 8 }} />
      Loading…
    </div>
  );
}

function PanelError({ message, onRetry, height = 200 }) {
  return (
    <div
      style={{
        height,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 10,
        color: 'var(--trace-critical)',
        fontSize: 13,
        textAlign: 'center',
        padding: '0 16px',
      }}
    >
      <i className="ti ti-alert-circle" style={{ fontSize: 22 }} />
      <span>{message}</span>
      {onRetry && (
        <button
          className="btn ghost"
          style={{ fontSize: 12, padding: '4px 12px' }}
          onClick={onRetry}
        >
          Retry
        </button>
      )}
    </div>
  );
}

function BackendGapPanel({ label, reason }) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        height: 180,
        color: 'var(--text-dim)',
        fontSize: 12,
        textAlign: 'center',
        padding: '0 16px',
      }}
    >
      <i className="ti ti-database-off" style={{ fontSize: 24, opacity: 0.5 }} />
      <strong style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
        {label} — not available
      </strong>
      <span style={{ opacity: 0.7 }}>{reason}</span>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────

export default function Analytics() {
  const [prHistory, setPrHistory] = useState(null);
  const [prLoading, setPrLoading] = useState(true);
  const [prError, setPrError] = useState(null);

  const [staffResponse, setStaffResponse] = useState(null);
  const [staffLoading, setStaffLoading] = useState(true);
  const [staffError, setStaffError] = useState(null);

  const fetchPrHistory = useCallback(async () => {
    setPrLoading(true);
    setPrError(null);
    try {
      const data = await getPrecisionRecallHistory({ days: 30, bucket_size_days: 5 });
      setPrHistory(data);
    } catch (err) {
      setPrError(errorMessage(err));
    } finally {
      setPrLoading(false);
    }
  }, []);

  const fetchStaffResponse = useCallback(async () => {
    setStaffLoading(true);
    setStaffError(null);
    try {
      const data = await getStaffResponseByWard({ days: 30 });
      setStaffResponse(data);
    } catch (err) {
      setStaffError(errorMessage(err));
    } finally {
      setStaffLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPrHistory();
    fetchStaffResponse();
  }, [fetchPrHistory, fetchStaffResponse]);

  const tooltipStyle = {
    contentStyle: {
      background: 'var(--bg-card-raised)',
      border: '1px solid var(--line-strong)',
      borderRadius: 8,
      fontSize: 12,
    },
  };
  const axisProps = { tick: { fill: 'var(--text-dim)', fontSize: 11 } };

  return (
    <>
      <Topbar title="Analytics and reports" subtitle="Model performance across all wards" />

      <div className="grid-2" style={{ marginBottom: 16 }}>
        {/* ── Staff response by ward (real data) ─────────────────────────────── */}
        <div className="panel">
          <p className="panel-title">Staff response rate by ward, last 30 days</p>
          {staffLoading && <PanelLoading />}
          {staffError && !staffLoading && (
            <PanelError message={staffError} onRetry={fetchStaffResponse} />
          )}
          {!staffLoading && !staffError && staffResponse !== null && (
            staffResponse.length === 0 ? (
              <div
                style={{
                  height: 200,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'var(--text-dim)',
                  fontSize: 13,
                }}
              >
                No alert data in the last 30 days.
              </div>
            ) : (
              <div style={{ height: 200 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={staffResponse}>
                    <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" vertical={false} />
                    <XAxis
                      dataKey="ward"
                      {...axisProps}
                      axisLine={{ stroke: 'var(--line)' }}
                      tickLine={false}
                    />
                    <YAxis
                      {...axisProps}
                      axisLine={false}
                      tickLine={false}
                      domain={[0, 100]}
                      unit="%"
                    />
                    <Tooltip
                      {...tooltipStyle}
                      formatter={(value) => [`${value}%`, 'Reviewed']}
                    />
                    <Bar dataKey="reviewed" fill="var(--trace-accent)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )
          )}
        </div>

        {/* ── Outcome breakdown — BACKEND GAP ────────────────────────────────── */}
        <div className="panel">
          <p className="panel-title">Outcome breakdown</p>
          <BackendGapPanel
            label="TP / FP / FN breakdown"
            reason={
              'No backend endpoint provides aggregate TP/FP/FN percentages. ' +
              'This panel will populate once a /analytics/outcome-summary endpoint is added.'
            }
          />
        </div>
      </div>

      {/* ── Precision / Recall trend (real data) ──────────────────────────────── */}
      <div className="panel">
        <p className="panel-title">
          Precision and recall, 30-day trend
          <span
            style={{
              marginLeft: 10,
              fontSize: 11,
              fontWeight: 400,
              color: 'var(--text-dim)',
              fontStyle: 'italic',
            }}
          >
            feedback-derived approximation — gaps indicate insufficient feedback in that bucket
          </span>
        </p>
        {prLoading && <PanelLoading height={220} />}
        {prError && !prLoading && (
          <PanelError message={prError} onRetry={fetchPrHistory} height={220} />
        )}
        {!prLoading && !prError && prHistory !== null && (
          prHistory.length === 0 ? (
            <div
              style={{
                height: 220,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--text-dim)',
                fontSize: 13,
              }}
            >
              No feedback data available for the selected window.
            </div>
          ) : (
            <div style={{ height: 220 }}>
              <ResponsiveContainer width="100%" height="100%">
                {/*
                  connectNulls is intentionally NOT set (defaults to false).
                  Null precision/recall values in buckets with no feedback
                  render as gaps in the line, which is the correct visual
                  representation — do not interpolate missing clinical data.
                */}
                <LineChart data={prHistory}>
                  <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="day"
                    {...axisProps}
                    axisLine={{ stroke: 'var(--line)' }}
                    tickLine={false}
                  />
                  <YAxis
                    {...axisProps}
                    axisLine={false}
                    tickLine={false}
                    domain={[0, 100]}
                    unit="%"
                  />
                  <Tooltip
                    {...tooltipStyle}
                    formatter={(value) =>
                      value === null ? ['No data', ''] : [`${value}%`, '']
                    }
                  />
                  <Legend
                    wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
                    formatter={(value) =>
                      value === 'precision' ? 'Precision' : 'Recall'
                    }
                  />
                  <Line
                    type="monotone"
                    dataKey="precision"
                    stroke="var(--trace-accent)"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="recall"
                    stroke="var(--trace-stable)"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )
        )}
      </div>

      <div className="flex gap-8 mt-24">
        <button className="btn">
          <i className="ti ti-download" aria-hidden="true" /> Export PDF report
        </button>
        <button className="btn ghost">
          <i className="ti ti-download" aria-hidden="true" /> Export CSV
        </button>
      </div>
    </>
  );
}
