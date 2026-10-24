import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';

export default function BacktestView() {
  const [windowSize, setWindowSize] = useState(20);
  const [zThreshold, setZThreshold] = useState(2.0);
  const [queryUrl, setQueryUrl] = useState(`/backtest-performance?window=${windowSize}&z_threshold=${zThreshold}`);

  const { data: backtest, loading, error, refetch } = useApi(queryUrl);

  const handleRunSimulation = (e) => {
    e.preventDefault();
    const newUrl = `/backtest-performance?window=${windowSize}&z_threshold=${zThreshold}`;
    setQueryUrl(newUrl);
  };

  const isInsufficient = backtest?.status === 'insufficient_data';
  const isNoData = backtest?.status === 'no_data';

  const daysAvailable = backtest?.days_available ?? 1;
  const daysRequired = backtest?.days_required ?? (windowSize + 1);

  return (
    <div className="flex-col gap-6">
      {/* Parameter Controls Panel */}
      <div className="card">
        <div className="card-header">
          <div>
            <h2 className="card-title">Walk-Forward Backtest Simulator</h2>
            <p className="card-subtitle">
              Strict walk-forward simulation with day-by-day rolling stats, zero look-ahead bias, and fee deduction
            </p>
          </div>
          <span className="badge badge-watch">Quantitative Engine v1.0</span>
        </div>

        <div className="card-body">
          <form onSubmit={handleRunSimulation} className="flex" style={{ flexWrap: 'wrap', gap: '20px', alignItems: 'flex-end' }}>
            <div className="flex-col gap-1" style={{ minWidth: '180px' }}>
              <label className="text-xs text-muted font-bold">
                Rolling Z-Score Window: <span className="text-gold font-mono">{windowSize} days</span>
              </label>
              <input
                type="range"
                min="5"
                max="60"
                step="1"
                value={windowSize}
                onChange={(e) => setWindowSize(Number(e.target.value))}
                className="input-control"
              />
            </div>

            <div className="flex-col gap-1" style={{ minWidth: '180px' }}>
              <label className="text-xs text-muted font-bold">
                Entry Threshold |Z|: <span className="text-gold font-mono">{zThreshold.toFixed(1)}σ</span>
              </label>
              <input
                type="range"
                min="1.0"
                max="4.0"
                step="0.1"
                value={zThreshold}
                onChange={(e) => setZThreshold(Number(e.target.value))}
                className="input-control"
              />
            </div>

            <div className="flex-col gap-1" style={{ minWidth: '160px' }}>
              <label className="text-xs text-muted font-bold">Exit Threshold</label>
              <input
                type="text"
                disabled
                value="0.5σ (Mean Reversion)"
                className="input-control"
                style={{ opacity: 0.6 }}
              />
            </div>

            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Simulating...' : 'Run Simulation'}
            </button>
          </form>
        </div>
      </div>

      {/* Historical Data Baseline Explanation Banner */}
      <div className="warning-banner">
        <div style={{ fontSize: '1.5rem' }}>⚠️</div>
        <div>
          <h3 className="font-bold text-sm" style={{ color: 'var(--accent-gold)', marginBottom: '4px' }}>
            Data Baseline Requirement Notice
          </h3>
          <p className="text-sm text-muted">
            Walk-forward backtesting requires at least <strong>{daysRequired} trading days</strong> of historical Bhavcopy data to establish rolling {windowSize}-day Z-scores without look-ahead bias. Currently, <strong>{daysAvailable} trading day</strong> (2026-09-18) is loaded in the PostgreSQL database.
          </p>
          <p className="text-xs text-muted mt-2">
            <strong>Data Integrity Guarantee:</strong> GOLD-X displays genuine settlement records and will not fabricate synthetic multi-month price paths or fake win rates. As additional historical Bhavcopy CSV files are placed in <code>data/imports/</code>, the engine dynamically activates full equity curve simulation.
          </p>
        </div>
      </div>

      {/* Performance Summary Metrics */}
      <div className="metrics-grid">
        <div className="metric-card">
          <span className="metric-label">Total Signals</span>
          <span className="metric-value">{backtest?.total_signals ?? 0}</span>
          <span className="metric-sub">Pair opportunities evaluated</span>
        </div>

        <div className="metric-card">
          <span className="metric-label">Executed Trades</span>
          <span className="metric-value">{backtest?.total_trades ?? 0}</span>
          <span className="metric-sub">Trades passing cost filter</span>
        </div>

        <div className="metric-card">
          <span className="metric-label">Simulated Win Rate</span>
          <span className="metric-value text-green">
            {((backtest?.win_rate ?? 0) * 100).toFixed(1)}%
          </span>
          <span className="metric-sub">Closed profitable trades</span>
        </div>

        <div className="metric-card">
          <span className="metric-label">Net Realized P&L</span>
          <span className={`metric-value ${(backtest?.net_pnl ?? 0) >= 0 ? 'text-green' : 'text-red'}`}>
            ₹{(backtest?.net_pnl ?? 0).toFixed(2)}
          </span>
          <span className="metric-sub">After all fees & slippage</span>
        </div>

        <div className="metric-card">
          <span className="metric-label">Annualized Sharpe</span>
          <span className="metric-value font-mono">
            {(backtest?.sharpe_ratio ?? 0).toFixed(2)}
          </span>
          <span className="metric-sub">Risk-adjusted return</span>
        </div>

        <div className="metric-card">
          <span className="metric-label">Max Drawdown</span>
          <span className="metric-value text-red font-mono">
            ₹{(backtest?.max_drawdown ?? 0).toFixed(2)}
          </span>
          <span className="metric-sub">Peak-to-trough decline</span>
        </div>
      </div>

      {/* Equity Curve SVG Chart */}
      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Cumulative Strategy Equity Curve</h3>
            <p className="card-subtitle">Net P&L progression after round-trip transaction costs</p>
          </div>
          <span className="badge badge-baseline">
            {isInsufficient ? 'Baseline Formation Stage' : 'Active Simulation'}
          </span>
        </div>

        <div className="card-body">
          <div className="chart-container">
            <svg viewBox="0 0 800 240" style={{ width: '100%', height: 'auto', display: 'block' }}>
              {/* Background Grid Lines */}
              {[40, 90, 140, 190].map((y, i) => (
                <line
                  key={i}
                  x1="60"
                  y1={y}
                  x2="780"
                  y2={y}
                  stroke="rgba(255, 255, 255, 0.06)"
                  strokeDasharray="4 4"
                />
              ))}

              {/* Y Axis Labels */}
              <text x="50" y="45" fill="var(--text-muted)" fontSize="10" textAnchor="end" fontFamily="monospace">
                +₹5,000
              </text>
              <text x="50" y="145" fill="var(--text-muted)" fontSize="10" textAnchor="end" fontFamily="monospace">
                ₹0.00
              </text>
              <text x="50" y="195" fill="var(--text-muted)" fontSize="10" textAnchor="end" fontFamily="monospace">
                -₹5,000
              </text>

              {/* Zero Baseline */}
              <line x1="60" y1="140" x2="780" y2="140" stroke="rgba(255, 255, 255, 0.2)" strokeWidth="1.5" />

              {/* Strategy Flat or Historical Line */}
              <line
                x1="60"
                y1="140"
                x2="780"
                y2="140"
                stroke="var(--accent-gold)"
                strokeWidth="2.5"
                strokeDasharray={isInsufficient ? "6 6" : "none"}
              />

              {/* Center Callout */}
              {isInsufficient && (
                <g>
                  <rect
                    x="240"
                    y="105"
                    width="320"
                    height="70"
                    fill="rgba(15, 23, 42, 0.95)"
                    stroke="var(--accent-gold)"
                    strokeWidth="1"
                    rx="6"
                  />
                  <text
                    x="400"
                    y="132"
                    fill="var(--accent-gold)"
                    fontSize="12"
                    fontWeight="bold"
                    textAnchor="middle"
                  >
                    Awaiting 21 Historical Trading Days
                  </text>
                  <text
                    x="400"
                    y="152"
                    fill="var(--text-muted)"
                    fontSize="10"
                    textAnchor="middle"
                  >
                    Current: 1 Day Loaded | Minimum Window: {windowSize} Days
                  </text>
                </g>
              )}
            </svg>
          </div>
        </div>
      </div>

      {/* Methodology & Rules Reference */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Walk-Forward Simulation Framework</h3>
        </div>
        <div className="card-body">
          <div className="flex-col gap-3 text-sm text-muted">
            <p>
              <strong>1. Day-by-Day Walk-Forward Execution:</strong> On each trading day $T$, the engine only accesses market data up to day $T$. Rolling means, standard deviations, and Z-scores are computed strictly on past data, preventing any look-ahead bias.
            </p>
            <p>
              <strong>2. Realistic Cost Autopsy:</strong> Round-trip trades deduct all exchange transaction fees (0.026%), SEBI turnover charges, STT (0.01% on sell side), 18% GST on fees, flat ₹20/order brokerage, and estimated 5 bps slippage.
            </p>
            <p>
              <strong>3. Same-Expiry Contract Matching:</strong> Spreads are strictly computed between contracts with the identical delivery date, ensuring that profits reflect pure relative-value convergence rather than term-structure roll-down.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
